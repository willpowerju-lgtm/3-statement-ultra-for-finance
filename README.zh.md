# 3-Statements-Ultra — 公开版

[English](README.md) | **中文**

**版本：** 4.8 · 公开版
**发布日期：** 2026年4月（新增 Claude Code 一等公民支持）
**兼容平台：** Claude Code / Cowork（Anthropic）

---

## 这个 Skill 做什么

从零开始，在 Excel 中构建机构级**三表财务模型**（利润表、资产负债表、现金流量表）——所有预测单元格均为 Excel 公式（零硬编码），并内置 9 步质量控制验证。

输出质量目标：IPO 招股书 / 卖方研究 initiating coverage 级别。

核心特性：
- **中国准则 / IFRS / US GAAP** — 三套会计准则全部支持
- **季报 / 半年报 / 年报** 颗粒度自动识别
- **全公式预测** — IS/BS/CF 每一个预测单元格均为引用 Assumptions 的 Excel 公式，永不硬编码
- **断点续跑** — 5 个 Session 独立构建，支持随时中断、下次接着跑
- **9 项 QC 检查** — BS CHECK、CF CHECK、NI CHECK、REV CHECK、硬编码扫描、NCI 连续性、公式完整性、去除网格线、Summary 链接检查
- **数据台账** — 每个输入值和派生值均记录来源与公式链路

---

## 环境依赖

```bash
pip install openpyxl yfinance pandas
pip install "notebooklm-py[browser]" && playwright install chromium   # 可选 — 仅在使用 NotebookLM 作为数据源时需要（见下方"推荐升级 — NLM"）
```

需要 Python 3.9+。

---

## 安装方式

仓库同时提供两种形态：解压后的 `3-statements-ultra/` 文件夹（给 Claude Code 用）和 `3-statements-ultra-public.skill` zip 包（给 Cowork 用）。挑对应你客户端的那一种即可。

### Claude Code — 推荐（git clone + 软链接）

这是最省心的路径：之后 `git pull` 就能自动拿到最新版本，不需要重装。

```bash
# 1. 在任意位置 clone 仓库（不要直接 clone 到 ~/.claude/skills/ 里）
git clone https://github.com/willpowerju-lgtm/3-statement-ultra-for-finance.git
cd 3-statement-ultra-for-finance

# 2. 把 skill 文件夹软链接到 Claude Code 的 skills 目录
# Linux / macOS：
ln -s "$PWD/3-statements-ultra" ~/.claude/skills/3-statements-ultra

# Windows（PowerShell，需要管理员身份 或 启用开发者模式）：
New-Item -ItemType SymbolicLink -Path "$HOME\.claude\skills\3-statements-ultra" -Target "$PWD\3-statements-ultra"
```

**验证 Claude Code 已识别：**

```bash
# 在任意 Claude Code session 里：
/skills
# 期望在列表中看到："3-statements-ultra"
```

然后在任意 session 触发即可：

```
建个三表模型 for BABA
# 或
build a 3-statement model for Tencent (0700.HK)
```

**后续更新：** `cd 3-statement-ultra-for-finance && git pull` —— 因为是软链接，Claude Code 立刻能看到新版本。

### Claude Code — 替代方案（直接拷贝，不用软链接）

如果你的环境不方便建软链接：

```bash
git clone https://github.com/willpowerju-lgtm/3-statement-ultra-for-finance.git
cp -r 3-statement-ultra-for-finance/3-statements-ultra ~/.claude/skills/
```

更新时需要重新 cp 覆盖。

### Cowork（.skill zip 包）

1. 从本仓库（raw 文件或 Releases）下载 `3-statements-ultra-public.skill`。
2. Cowork 中：**Settings → Skills → Install from file** → 选择 `.skill` 文件。

### 手动解压（旧版 Claude Code 路径）

如果你更喜欢解压 zip 而不是用文件夹：

```bash
unzip 3-statements-ultra-public.skill -d ~/.claude/skills/3-statements-ultra/
```

---

## 建议配置 — User Preference

**第一次使用前**，把下面这段"断点恢复协议"贴进 Claude 用户偏好。这是为了防止建模**中途**触发 context compaction 后状态丢失——skill auto-load 只在触发词命中时重新注入 SKILL.md，已经在建模中途发生的 compaction 不会自动重载。没有这段协议，LLM 可能凭记忆拼行号、静默污染模型。

粘贴位置因客户端而异：

- **Claude Code** → 追加到 `~/.claude/CLAUDE.md`（或你在用的项目级 `CLAUDE.md`）。
- **Cowork** → Settings → Profile → Custom Instructions。
- **Claude.ai**（网页/桌面）→ Settings → Profile → Custom Instructions。

```
## 3-Statements-Ultra — 断点恢复协议
当我在使用 3-statements-ultra skill 构建三表模型时，
每次发生 context compaction 后，你必须：
1. 重新读取 3-statements-ultra SKILL.md，再写任何代码
2. 打开 Excel 文件，读取 _State tab，确认精确的恢复点
3. 读取 _model_log.md，恢复上一 session 的关键输出数字
4. 读取 _pending_links.json，检查 BS→CF 的 Cash 回填是否待处理
5. 用 RAW_MAP + ASM_MAP spot-check 验证行号，再使用任何行号
6. IS/BS/CF 预测列单元格不得硬编码，每个单元格必须是字符串公式
7. 只从下一个未完成步骤继续，不重跑已完成的部分
不得依赖对话记忆来还原行号或中间计算结果。
磁盘状态（_State、_model_log.md、_pending_links.json）永远是权威来源。
```

---

## 快速开始

说出以下任意触发词，Skill 自动接管：

```
三表模型
financial model
3-statement model
建模
从零建模
build a 3-statement model for [公司名]
```

Skill 会先问你有哪些数据来源，然后引导你逐步完成 5 个 Session。

---

## 五个 Session 构建流程

| Session | 构建内容 | 做什么 | 时间 |
|---------|---------|--------|------|
| **A** | Raw_Info + Assumptions | 数据提取（NLM / Excel / Web）；颗粒度识别；假设参数设置 | 15–30 分钟 |
| **B** | IS（利润表） | 各业务线收入、中国准则 R8 插项、少数股东损益 | 15–20 分钟 |
| **C** | BS（资产负债表） | 资产负债表，货币资金暂为占位符；写入 `_pending_links.json` | 15–20 分钟 |
| **D** | CF（现金流量表） | 逐年构建现金流；R3 Others 插项；BS 货币资金回填；9 项 QC 检查 | 15–25 分钟 |
| **E** | Returns + Cross_Check + Summary | ROIC/ROE/DuPont；假设交叉验证；Summary Tab 链接 | 15–20 分钟 |

每个 Session **完全独立** — Session 之间可以关闭对话。状态保存在 Excel 的 `_State` Tab 和两个辅助文件（`_model_log.md`、`_pending_links.json`）中。

---

## 数据来源选择

| 优先级 | 来源 | 配置成本 | Token 消耗 | 说明 |
|--------|------|---------|-----------|------|
| ✅ **首选** | **Excel 历史数据**（IS/BS/CF 已整理） | 无 | 低 | 开箱即用，上传即开始 |
| ✅ **次选** | **NotebookLM notebook**（已上传年报/财报） | 两步配置（见下方） | 极低 | 预测假设质量更高，值得配置 |
| ✅ **兜底** | **Web**（Sina / Yahoo Finance） | 无 | 低 | 自动运行，始终作为交叉验证层 |
| ⚠️ **Pro 用户慎用** | **直接上传完整 PDF**（年报、招股书全文） | 无 | 🔴 极高 | 200+ 页报告快速消耗 Context |

**为什么 Excel 首选？** 不需要认证，不需要预载——直接上传一份包含 3–5 年 IS/BS/CF 的表格，Skill 直接读取。如果你有业绩发布、关键页摘录等短篇 PDF，一并上传作为补充。

**为什么 NLM 次选，又说值得配置？** NotebookLM 的 12 题并发问答能提取远比结构化财务数据丰富得多的运营情报：分业务线拆分驱动因子、管理层指引原话、资本开支计划、营运资本管理逻辑、竞争格局分析。这些内容直接决定 Assumptions Tab 的质量，最终影响预测的可信度。代价是需要两步配置：

1. **先自己往 NotebookLM 上传资料** — 年报、季报、招股书，或任何你认为有参考价值的卖方研报。NLM 负责解析 PDF，Claude 只需接收问答结果，不用直接处理原始文件。
2. **一次性 OAuth 认证**（约 5 分钟，只需做一次）。我们使用 [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py) —— 一个非官方的 NotebookLM Python 客户端：

```bash
pip install "notebooklm-py[browser]"
playwright install chromium

# CLI 认证 — 浏览器弹出，Google 登录，session 本地保存
notebooklm login

# 验证是否可用
python3 -c "
import asyncio
from notebooklm import NotebookLMClient
async def check():
    async with await NotebookLMClient.from_storage() as client:
        nbs = await client.notebooks.list()
        print(f'认证成功 — 可访问 {len(nbs)} 个 notebook')
asyncio.run(check())
"
# 约 7 天后 session 过期，重新执行 `notebooklm login` 即可
```

> ⚠️ `notebooklm-py` 是非官方库，依赖未公开的 Google API，接口可能随时变动。用来做个人研究/原型没问题（本 skill 就是这个场景），不要拿它跑生产管线。

---

## 输出 Excel 文件结构

```
[1] Summary        ← 公司简介、财务亮点、催化剂、风险
[2] Assumptions    ← 所有预测驱动因子（唯一数据源）
[3] IS             ← 利润表
[4] BS             ← 资产负债表
[5] CF             ← 现金流量表（间接法）
[6] Returns        ← ROIC / ROE / ROA / DuPont 分析
[7] Cross_Check    ← 假设参数与外部来源交叉验证日志
[8] Raw_Info       ← 历史数据提取（建好后不再回读原始来源）
[_Registry]        ← 数据来源台账（Session E 末尾构建）
[_State]           ← Session 元数据（MODEL_COMPLETE 后删除）
```

---

## 核心规则（摘要）

| 规则 | 说明 |
|------|------|
| **Rule Zero** | IS/BS/CF 所有预测单元格必须是 Excel 公式字符串，不得为数字 |
| **R3 Others 插项** | CFO 中唯一允许的非现金调整插项；同时保证 BS CHECK 和 CF CHECK 均为 0 |
| **R6 Cash 最后** | BS 货币资金在 Session D 之前始终为 0 占位符，Session D 从 CF 期末现金回填 |
| **代码块行数限制** | 每个 Python 代码块最多 400 行，执行后再写下一块 |
| **单一来源** | Raw_Info 完成后，所有数据只通过 `=Raw_Info!` 公式引用，不再回读原始来源 |

---

## 常见问题

**Q：没有 NotebookLM 也能用吗？**
可以。NotebookLM 是可选的。没有的话，Skill 自动降级到 Web（Sina / Yahoo Finance）作为主要数据源。

**Q：我只有年度数据，但公司按季度披露，怎么处理？**
Skill 通过 yfinance 自动识别颗粒度。只要任何来源显示有季度数据，就使用季度模式。Phase 0 时也可以手动确认。

**Q：Session 中途可以暂停、下次再继续吗？**
可以。每个代码块执行后都会在 Excel 的 `_State` Tab 写入进度标记。每个 Session 启动时会自动找到上次完成的步骤并从下一步继续。

**Q：为什么要跑 5 个 Session，不能一次跑完吗？**
季报模式的利润表每个 Section 就有 300+ 行 Python 代码。一次性生成会触及大模型的输出上限，代码被静默截断，Excel 文件写到一半没有任何报错。5 个 Session 逐段执行完全规避了这个问题。

**Q：Session C 结束后 BS CHECK ≠ 0，是 bug 吗？**
不是，这是预期行为。货币资金在 Session D 之前是 0 占位符，Session D 从 CF 期末现金回填后 BS CHECK 才会归零。不要在 Session C 里强行平衡资产负债表。

**Q：US GAAP 公司（纽交所/纳斯达克）也支持吗？**
支持。Phase 0 中使用标准 ticker 格式（如 `"AAPL"`），Skill 会自动识别 IFRS/US GAAP 并套用对应的利润表模板。

---

## 与官方 `financial-analysis:3-statements` Skill 的对比

Claude 插件市场中有一个官方三表模型 Skill（`financial-analysis:3-statements`）。两者定位不同，质量标准差异显著。

### 官方 Skill 的优势

速度快。如果你已经有一个半填好的 Excel 模板，只需要把公式链接起来，官方 Skill 一个 Session 就能搞定，不需要任何配置。适合快速出一个粗略模型、对结构正确性要求不高的场景。

### 本 Skill 的核心差异 — 为什么这些差异对严肃工作至关重要

**1. 货币资金永不倒推。**

这是最根本的结构差异。官方 Skill 用倒推法计算货币资金：`Cash = 负债合计 + 所有者权益 − 非现金资产`。这样资产负债表表面上平衡了，但结构上是错的。用这种方式算出来的货币资金和实际现金生成能力毫无关系——它只是一个残差，只要任何其他科目稍有偏差，这个数就会把所有偏差吸收进去，严重失真。正确的做法是，货币资金必须等于现金流量表的期末现金，由完整的现金流量瀑布推导得出。本 Skill 无条件强制执行这一规则：Session C 中货币资金保留为占位符，Session D 从现金流量表回填，没有例外。

**2. 收入按业务线拆分，各自独立驱动。**

官方 Skill 将收入作为一行处理。本 Skill 为每条业务线单独构建行，配有各自的 YoY 增速假设、量价拆分结构（如适用）以及季度模型的季节性比例。单行收入假设对于粗略估算尚可接受，但用于卖方研究或 IC Memo 时完全不够，因为你需要能单独压力测试各产品线或地区的表现。

**3. 所有预测单元格均为 Excel 公式，没有例外。**

本 Skill 的 Rule Zero：IS/BS/CF 中没有任何预测单元格可以存数字。每个单元格必须是引用 Assumptions Tab 或其他单元格的字符串公式。官方 Skill 经常直接把数值写入预测单元格，这意味着一旦修改任何假设，受影响的单元格不会重新计算，因为它存的是数字不是公式。

**4. 原生支持中国会计准则。**

中国会计准则利润表在"营业总成本"和"营业利润"之间存在若干科目（其他收益、信用减值损失、资产减值损失等），IFRS 和 US GAAP 中没有对应项。本 Skill 用专门的 R8 插项行来捕捉这部分差额——即来源中的营业利润与模型推导的 EBIT 之间的残差。用通用模板忽略这些科目，会导致 A 股和港股中国准则公司的 EBIT 系统性偏差。

**5. 9 项 QC 检查必须全部通过，模型才能标记为完成。**

没有通过全部检查，模型无法写入 MODEL_COMPLETE 状态：BS CHECK = 0、CF CHECK = 0、NI CHECK ≈ 0、REV CHECK = 0、预测列硬编码扫描、NCI 连续性检查、公式完整性抽样检查、去除网格线检查、Summary Tab 零硬编码检查。官方 Skill 没有对应的质量门控。

**6. 少数股东权益始终滚动计算。**

如果公司存在少数股东，资产负债表上的少数股东权益必须每期复利累计：`NCI_期末 = NCI_期初 + 归属少数股东净利润 − 少数股东分红`。将预测期 NCI 设为零或直接用最后一期历史值延续是常见错误，会同时影响资产负债表和利润表中的归属计算。本 Skill 强制执行滚动公式，并在 QC-5 中验证。

### 对比表

| | `3-statements-ultra`（本 Skill） | `financial-analysis:3-statements`（官方） |
|---|---|---|
| 货币资金来源 | `= CF 期末现金`（始终如此） | 资产负债表残差倒推 |
| 收入结构 | 按业务线拆分，各自独立驱动 | 单行 |
| 预测单元格 | 100% Excel 公式 | 公式与硬编码混用 |
| 中国准则支持 | 原生（R8 插项、营业利润对账） | 通用模板 |
| QC 验证 | 9 项强制检查 | 无 |
| NCI 滚动计算 | 强制执行 | 不保证 |
| 季度颗粒度 | 完整支持（每年 35 列） | 仅年度 |
| 配置成本 | 5 个 Session，约 1–2 小时 | 单 Session |
| 适用场景 | IPO / 卖方研究质量模型 | 快速填充模板 |

### 如何选择

如果你需要在 20 分钟内出一个粗略模型，数字不需要经得起推敲，用官方 Skill。

如果模型将用于 IC Memo、研究报告、投资者材料，或者任何会被人仔细检查是否平衡、假设是否正确传导的场景，用本 Skill。

---

## 许可证

本 Skill 供个人和研究使用，不提供任何保证。由本 Skill 生成的财务模型在用于投资决策前，应经过独立核实。
