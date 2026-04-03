# SESSION A — Raw_Info + Assumptions
# Load this file at Step 7 of session startup for SESSION A only.

---

## ██ PRE-FLIGHT — DATA SOURCE INVENTORY ██
## ██ Run ONCE. Skip entirely if DATA_SOURCES key already exists in _State. ██

用 `AskUserQuestion` 问用户（**多选**，不是三选一）：

```
你有哪些数据来源可以用？（可多选，有几个选几个）

□ A) NotebookLM notebook — 有这家公司的年报/季报/招股书 notebook
      → 请提供 notebook 链接或名称关键词

□ B) Excel 历史数据 — 有整理好的历史财务 Excel（IS/BS/CF 已在里面）
      → 请上传文件

□ C) 额外 PDF — 研报、公告、招股书等
      → 请上传文件

（Web Search 始终作为 cross-check 层运行，无需选择）
```

根据用户选择，确定数据栈并写入 _State：

```
DATA_SOURCES: [NLM, EXCEL, WEB]   ← 实际用到的来源列表
DATA_CONFIDENCE: HIGH / MEDIUM / LOW
  HIGH   = NLM + EXCEL 同时可用（双源交叉验证）
  MEDIUM = NLM 或 EXCEL 其中一个可用（单源 + Web cross-check）
  LOW    = 仅 Web + PDF（兜底路径）
```

然后**按以下顺序**执行 Phase 0：

```
Step 1: 并行运行所有可用的高置信度来源（NLM batch + Excel 读取）
Step 2: Web cross-check（始终运行 — 核心数字验证 + 0B 补充 + fallback）
Step 3: Merge — 交叉验证，冲突标注，写入 Raw_Info
```

---

## Phase 0 — Step 0: 颗粒度验证（最先执行，锁定模型结构）

> 颗粒度决定 IS/CF 的列数和 COL_MAP 结构（季报=35列 vs 年报=10列）。
> 必须在任何数据提取之前确认，否则 Raw_Info 行结构和 Assumptions 行数全部可能白建。

### 自动检测（yfinance）

```python
import yfinance as yf

ticker = "[TICKER]"   # e.g. "BABA", "0700.HK", "600519.SS"
tk = yf.Ticker(ticker)

# 看 quarterly_financials 的列（每列是一个季度末日期）
try:
    qcols = tk.quarterly_financials.columns
    months = sorted(set(c.month for c in qcols))
    print(f"quarterly_financials months disclosed: {months}")
    if len(months) >= 3:
        detected = "Quarterly"       # {3,6,9,12} 或至少3个月份 = 季报
    elif set(months) == {6, 12}:
        detected = "Semi-annual"     # {6,12} = HK中报+年报
    else:
        detected = "Annual"
except Exception as e:
    detected = "Unknown"
    print(f"yfinance 检测失败: {e}")

print(f"yfinance 检测结果: {detected}")
```

### 交叉确认（三源核对，决策用）

| 来源 | 检查方式 | 结果 |
|---|---|---|
| yfinance | 上方代码，看 months 集合 | `{3,6,9,12}` → Quarterly；`{6,12}` → Semi-annual |
| NLM（如有）| 0A_IS 回答里是否有 Q1/Q2/Q3/Q4 行 | 有季度列 → Quarterly |
| Excel（如有）| 列名是否含 "Q1" / "H1" 等 | 含季度 → Quarterly |
| 交易所披露规则 | A股必须披露季报；港股只披中报+年报 | A股默认 Quarterly；港股默认 Semi-annual |

**决策规则：**
```
三源中有任一显示 Quarterly → IS_GRANULARITY: Quarterly（不降级）
三源均显示 Semi-annual    → IS_GRANULARITY: Semi-annual
三源均显示 Annual         → IS_GRANULARITY: Annual
检测结果冲突              → 用 AskUserQuestion 问用户确认，不猜
```

如果 yfinance FAIL 且无 NLM/Excel → 用交易所规则推断，然后用 AskUserQuestion 请用户确认。

### 写入 _State（此步完成后才能进入 Step 1）

```python
write_state_key(wb, "IS_GRANULARITY", detected)   # Quarterly / Semi-annual / Annual
write_state_key(wb, "CF_GRANULARITY", detected)   # 与 IS 一致
write_state_key(wb, "BS_GRANULARITY", "Annual")   # BS 永远 Annual
print(f"✅ 颗粒度锁定: IS/CF={detected}, BS=Annual")
```

⚠ **STOP 条件：** 如果颗粒度未能确认（yfinance FAIL + 无其他来源 + 用户未确认），
不得进入 Step 1。COL_MAP 结构依赖此值，错误的颗粒度会导致整个模型结构错误。

---

## Phase 0 — Step 1: 高置信度来源（并行）

### 1A — NLM Batch（如用户选了 A）

安装依赖：
```bash
pip install notebooklm   # 若尚未安装
```

健康检查：
```python
import os
python3 -c "
from notebooklm import NotebookLMClient
print('NLM_PY: OK' if os.path.exists(os.path.expanduser('~/.notebooklm/storage_state.json')) else 'AUTH_MISSING')
" 2>/dev/null || echo "NLM_PY: FAIL"
```
如果 AUTH_MISSING → 需先完成 NotebookLM 登录授权（运行一次 `NotebookLMClient.from_storage()`）。
如果 FAIL → 跳过 NLM，降级到 MEDIUM confidence。

确认 Notebook ID（用户提供 link 直接解析；提供关键词时搜索）：
```python
import asyncio

async def find_notebook(keyword):
    from notebooklm import NotebookLMClient
    async with await NotebookLMClient.from_storage(timeout=90.0) as client:
        notebooks = await client.notebooks.list()
        matches = [nb for nb in notebooks if keyword.lower() in nb.title.lower()]
        if matches:
            for nb in matches: print(f"ID: {nb.id}  Title: {nb.title}")
        else:
            print("未找到，全部列表：")
            for nb in notebooks: print(f"  [{nb.id}] {nb.title}")

asyncio.run(find_notebook("[COMPANY_KEYWORD]"))
```

12 题并发（3 题 0A 财务数字 + 9 题 0B 运营情报）：
```python
import asyncio, json

NOTEBOOK_ID = "[NLM_NOTEBOOK_ID]"

NLM_QUESTIONS = [
    # 0A — 财务报表数字（结构化表格）
    ("0A_IS",
     "请以表格形式提取公司过去5年每年的完整利润表（年度；如有季报则同时提供季度）："
     "营业收入（总额及各业务线拆分）、营业成本、毛利润、研发/销售/管理费用、"
     "营业利润/EBIT、财务费用、税前利润、所得税、净利润、"
     "归属母公司股东净利润、少数股东损益。行=科目，列=年份。"),
    ("0A_BS",
     "请以表格形式提取公司过去5年每年末的完整资产负债表："
     "流动资产（货币资金、应收账款、存货、预付款、其他流动）、"
     "非流动资产（PP&E净值、在建工程、无形资产、商誉、长期股权投资、使用权资产、DTA）、"
     "流动负债（短期借款、应付账款、合同负债、一年内到期长期债）、"
     "非流动负债（长期借款、租赁负债、DTL）、"
     "归属母公司权益（股本、资本公积、未分配利润）、少数股东权益。行=科目，列=年末。"),
    ("0A_CF",
     "请以表格形式提取公司过去5年每年的完整现金流量表："
     "经营活动（净额、含净利润/折旧摊销/股权激励/各项营运资本变动）、"
     "投资活动（净额、含资本开支/收购/处置）、"
     "筹资活动（净额、含借款/偿债/分红/回购/股权融资）、期末现金。"
     "补充资料：D&A拆分（固定资产折旧/无形摊销/ROU摊销）、资产减值准备。"),
    # 0B — 运营情报
    ("0B-1_revenue",
     "请列出公司各业务线/产品线/地区的收入拆分和占比（过去3-5年），"
     "说明 Volume 和 Price 的驱动分解，以及季节性规律。"),
    ("0B-2_cost",
     "请梳理各业务线历年毛利率、COGS主要构成（原材料/人工/制造费用占比）、"
     "运营费用趋势，以及管理层对毛利变动的具体解释。"),
    ("0B-3_kpi",
     "请提取公司年报/季报/半年报中主动披露的所有运营KPI数字（过去3-5年）："
     "产量、产能利用率、客户数、客单价、复购率、渠道覆盖、订单积压等，记录实际数值。"),
    ("0B-4_capex",
     "请详细说明过去5年资本开支（金额、占收入比），在建工程项目名称/预算/完工时间/"
     "预计新增产能，以及固定资产和无形资产的折旧/摊销政策。"),
    ("0B-5_wc",
     "请提供AR/Inv/AP周转天数历年数据，管理层对CCC变化的解释，"
     "包括大客户账期条款和库存策略。"),
    ("0B-6_capital",
     "请梳理债务结构（各笔金额/利率/到期日）、分红政策（派息率/实际分红额）、"
     "回购计划、主要股东构成、股权激励计划。"),
    ("0B-7_guidance",
     "请引用管理层对未来1-3年的业绩指引原话（收入增速/利润率目标/CapEx计划），"
     "以及年报中反复强调的核心战略方向。"),
    ("0B-8_compete",
     "请梳理年报/招股书中披露的主要竞争对手、市占率估算、"
     "自身定价权描述，以及主要行业壁垒。"),
    ("0B-risk",
     "请列出年报风险章节最重要的5-8个实质性风险（非套话），"
     "以及重大监管政策变化对业务的具体影响。"),
]

async def run_nlm():
    from notebooklm import NotebookLMClient
    print(f"NLM: {len(NLM_QUESTIONS)} 题并发，预计 ~60s...")
    async with await NotebookLMClient.from_storage(timeout=150.0) as client:
        tasks = [client.chat.ask(NOTEBOOK_ID, q) for _, q in NLM_QUESTIONS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    output = {}
    for (section, _), r in zip(NLM_QUESTIONS, results):
        if isinstance(r, Exception):
            output[section] = f"[ERROR: {str(r)[:80]}]"
            print(f"  ⚠  {section}: 失败")
        else:
            output[section] = r.answer
            print(f"  ✅ {section}: {len(r.answer)}字")
    with open("nlm_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("✅ NLM 完成 → nlm_results.json")

asyncio.run(run_nlm())
```

---

### 1B — Excel 读取（如用户选了 B）

```python
import pandas as pd, json

user_excel_path = "[UPLOADED_FILE_PATH]"  # e.g., /path/to/your/financials.xlsx
sheets = pd.read_excel(user_excel_path, sheet_name=None)

# 识别结构：行=科目/列=年份（模式A）或列=科目/行=年份（模式B，需转置）
for name, df in sheets.items():
    print(f"\n=== {name} ===")
    print(df.head(8).to_string())
    print(f"Shape: {df.shape}")

# 解析后输出为标准化 dict：{label: {year: value, ...}, ...}
# 写入 excel_data.json 供 Step 3 merge 使用
```

关键检查：
- 确认单位（万元/千元/百万元）→ 统一换算
- 确认年份列顺序
- 标注哪些科目有数据，哪些缺失

---

## Phase 0 — Step 2: Web Cross-Check（始终运行）

Web 层的三个角色：

**角色 1 — 核心数字验证（NLM 或 Excel 可用时）**
快速抓取 Sina/Yahoo 最近 2 年的 Revenue / Net Income / Total Assets / Cash，
与 NLM/Excel 数字对比：
- 差异 < 5% → 确认，标注 ✅
- 差异 5-15% → 记录差异，检查单位或GAAP重分类，标注 ⚠
- 差异 > 15% → 标注 ❌，需用户确认，暂停 Raw_Info 写入直到解决

**角色 2 — 0B 定性补充（NLM 不可用时）**
读最近 1-2 份年报/中报全文，提取 0B-1 至 0B-8 全部项目（见 Tier 3 详细列表）。
Web Search 策略：
```
0B-7 指引:   "[公司名] 业绩说明会" / "管理层指引"
0B-8 竞争:   "[行业] 竞争格局研报"
0B-3 KPI:    最新季报/年报经营数据页
```

**角色 3 — 0A Fallback（NLM 和 Excel 均不可用时）**
完整执行 Sina/Yahoo 抓取：

```
Sina URL: https://money.finance.sina.com.cn/corp/go.php/vFD_{Statement}/stockid/{code}/ctrl/{year}/displaytype/4.phtml
  Statement: ProfitStatement | BalanceSheet | CashFlow

Yahoo URL: https://finance.yahoo.com/quote/{ticker}/{page}/
  page: financials | balance-sheet | cash-flow (点 Expand All)
```

数据源对比（先比较，选更详细的）：

| 报表 | Sina | Yahoo | 通常选 |
|---|---|---|---|
| IS | ~30行，CN GAAP原生 | ~20行，可能IFRS重分类 | Sina |
| BS | ~94行，完整拆分 | ~30-50行 | Sina |
| CF | ~40行+补充D&A | ~25行，无补充资料 | Sina |

单位换算：Sina=万元(×10→千元)；招股书/Yahoo=千元(×1)。

YTD→单季转换（Sina IS/CF 是累计YTD）：
```
Q1=Q1_YTD · Q2=H1_YTD−Q1 · Q3=Q3_YTD−H1 · Q4=FY−Q3_YTD
```
BS是时点数，无需转换。

---

## Phase 0 — Step 3: Merge → 写入 Raw_Info

置信度优先级（每个数字选最可信来源）：

```
财务数字：  Excel（用户直接提供，已验证）≥ NLM（原始文件提取）> Web（抓取/重分类）
定性情报：  NLM（原文引用）> Web Search > 人工读PDF
```

合并规则：
```
1. 两个来源数字一致（< 5%差异）：
   → 取其一，标注 "[NLM✅]" 或 "[Excel✅]"（选更精确的格式）

2. 两个来源存在差异（5-15%）：
   → Raw_Info 写入高置信度值，Notes 列写 "⚠ Web差异X%: [web值] — 检查单位/GAAP"

3. 严重冲突（> 15%）：
   → Raw_Info 写入 "[CONFLICT]"，Notes 列并排写两个值和来源
   → 在 SESSION A 结束前必须解决，否则 PHASE_DONE 不写入

4. 仅一个来源有数据：
   → 直接写入，标注来源

5. 所有来源均无数据：
   → 写入 0 或 "--"，标注 "[缺失]"，触发 Assumption 时用历史均值
```

```python
# Raw_Info 来源标注格式（Notes 列，即每行最后一列）：
"[NLM]"          # NLM 单一来源
"[Excel]"        # Excel 单一来源
"[Web: Sina]"    # Web 抓取，Sina
"[NLM+Excel✅]"  # 两源一致
"⚠ [NLM] Web差异8%: 1,234 → 检查单位"
"❌ [CONFLICT] NLM: 5,678 | Excel: 4,500 — 待解决"
```

完成后写入 _State：
```
DATA_SOURCES: [NLM, EXCEL, WEB]   ← 实际用到的列表，如仅Web则 [WEB]
DATA_CONFIDENCE: HIGH              ← HIGH/MEDIUM/LOW
NLM_AVAILABLE: true/false
NLM_NOTEBOOK_ID: [id]             ← 如有
CONFLICT_COUNT: 0                  ← 未解决冲突数；必须为 0 才能写 PHASE_DONE
```

---

## SESSION A Steps

**Steps:**
1. Create `_State` tab (last in tab order)
2. Run PRE-FLIGHT → execute Phase 0 Steps 1-3
3. Write RAW_MAP to _State as JSON: `{"label": row_number, ...}` for every data row
4. Build Assumptions: all forecast driver rows (navy text, light-blue bg)
5. Write ASM_MAP to _State as JSON: `{"driver label": row_number, ...}`
6. Write metadata to _State:
```
SKILL_VERSION: 4.7
DATA_SOURCES: [NLM, EXCEL, WEB]
DATA_CONFIDENCE: HIGH / MEDIUM / LOW
IS_GRANULARITY: [Quarterly / Semi-annual / Annual]
BS_GRANULARITY: Annual
CF_GRANULARITY: [matches IS]
BS_COL_MAP: {"2021": "B", "2022": "C", "2023": "D", "2024": "E", "2025": "F"}
CF_COL_MAP: {"2021": "B", ...}  ← if quarterly: {"2021Q1": "B", "2021Q2": "C", ...}
HIST_YEARS: ["2021", "2022", "2023"]
FCST_YEARS: ["2024", "2025"]
UNIT: [万元 / 千元 / 百万元]
GAAP: [CN GAAP / IFRS / US GAAP]
NLM_AVAILABLE: [true / false]
BS_CASH_STATUS: PENDING_BACKFILL
CONFLICT_COUNT: 0
```
7. Save file. Write `FILE_HASH: {os.path.getmtime(filepath)}` to _State after save
8. Write `PHASE_DONE: SESSION_A` to _State — **only if CONFLICT_COUNT = 0**

**End condition:** PHASE_DONE: SESSION_A written, RAW_MAP + ASM_MAP spot-check passes on a fresh open.

---

## Raw_Info Layout（通用）

```
Row 1:  [公司名] [Ticker] [GAAP] [单位] [DATA_CONFIDENCE: X] [来源: NLM+Excel+Web]
Row 2:  IS: Revenue (Total)    | Y1 | Y2 | Y3 | ... | [来源标注]
...
Row N:  [0B-1 Revenue Architecture]
Row N+1: Segment A Revenue     | Y1 | Y2 | Y3 | ... | [NLM+Excel✅]
...
Row M:  [0B-7 Management Guidance]
Row M+1: Rev Guidance FY2024   | [原话 + 来源日期]       | [NLM]
```

---

## Assumptions Tab (Phase 1)

Revenue: per segment YoY% (or Vol × ASP). Margins: GM%, each opex % of rev.
BS: AR/Inv/AP days, capex, debt schedule. Other: NCI ratio, share count, FX.

CN GAAP: Other Op Inc assumption (R8 plug), quarterly seasonality % per segment.

Granularity: if IS_GRANULARITY = Quarterly → add seasonality % rows (Q1/Q2/Q3/Q4 % of FY) per revenue segment.
