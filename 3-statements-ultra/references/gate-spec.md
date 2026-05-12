# Gate Spec — Severity Model + JSON Schema

## Severity tiers (2 档)

```
BLOCKER  exit 2   硬阻断；下一 session 不得启动 / MODEL_COMPLETE 不得写入 _State
                  典型：Rule Zero 硬编码 / 单位错 / RAW_MAP 失配 / BS 不平 / NCI=0
WARNING  exit 1   软警告；写入 sidecar JSON + _model_log.md，继续；用户决定是否修
                  典型：Others/CFO > 15% / Gridlines 没关 / 字体非 Book Antiqua / 0B 数据缺失
PASS     exit 0   全部通过
```

格式/注释细节（原 INFO 候选）→ 不进 gate，只进 `pitfalls.md` 文档索引。避免 gate 噪音淹没真正的 BLOCKER。

## Defense layer 矩阵

每个 pitfall 配置一种或多种防御手段：

| 层 | 触发时机 | 拦截手段 | 失败成本 |
|---|---|---|---|
| **Hook** | bash 命令执行前 | regex 匹配 + 立即 exit 2 | 零返工（在写之前拦） |
| **Preflight gate** | SESSION A 末尾 | `preflight_check.py`，open xlsx，检查 _State + Raw_Info | ≤1 session 返工 |
| **Per-session gate** | SESSION B/C/D/E 末尾 | `per_session_gate.py` → `qc_suite.py` 子集 | ≤1 session 返工 |
| **Full QC suite** | SESSION E 末尾 | `qc_suite.py --full`（19 QC）| 必须重跑前序 session |
| **Doc-only** | — | `pitfalls.md` 索引，Claude 写代码时自觉 | 取决于格式严重度 |

## JSON sidecar schema

所有 gate 脚本输出统一格式的 JSON，存储在与 xlsx 同目录：

```json
{
  "skill": "3-statements-ultra",
  "gate": "qc_suite" | "preflight" | "per_session_gate",
  "xlsx": "<absolute path>",
  "ts": "2026-05-12T10:30:00",
  "tabs_checked": ["IS", "BS", "CF"],
  "mode": "smoke" | "full",
  "summary": {
    "BLOCKER": <int>,
    "WARNING": <int>,
    "PASS": <int>
  },
  "exit_code": 0 | 1 | 2,
  "findings": [
    {
      "qc": "QC-3" | "PF-1" | ...,
      "severity": "BLOCKER" | "WARNING" | "PASS",
      "sheet": "<sheet name or null>",
      "cell": "<cell ref or null>",
      "msg": "<one-line description>",
      "fix_hint": "<actionable fix>"
    }
  ]
}
```

## Exit code conventions

与 `qc_tier1.py` / `pptx-eval` / `data-validator` 一致：

- `0` — 全 PASS
- `1` — 有 WARNING（无 BLOCKER）→ 可继续，但写报告
- `2` — 有 BLOCKER → 阻断，必须先修
- `127` — 脚本错误（依赖缺失、文件不存在等）

## 调用矩阵

| Session | 入口 | 启用的 hooks | 跑的 QC |
|---|---|---|---|
| 启动前（每条 bash） | — | H1, H2, H3, H4, H5 | — |
| **A** 末尾 | `python scripts/per_session_gate.py --session A --xlsx <p>` | (同上) | PF-1..8（preflight） |
| **B** 末尾 | `python scripts/per_session_gate.py --session B --xlsx <p>` | (同上) | QC-2,5,6,11,12 |
| **C** 末尾 | `python scripts/per_session_gate.py --session C --xlsx <p>` | (同上) | QC-2,6,7 + _pending_links 写入校验 |
| **D** 末尾 | `python scripts/per_session_gate.py --session D --xlsx <p>` | (同上) | QC-1,2,3,4,6,13 + back-fill 清零 |
| **E** 末尾 | `python scripts/per_session_gate.py --session E --xlsx <p>` | (同上) | QC-1..19（全集）+ data-validator |

## 实现状态 (v0 → v1)

**v0（当前）— 7 个格式 QC 已实现**：QC-2 (smoke)、QC-8、QC-14、QC-15、QC-17、QC-18、QC-19。这套对 representative 模型实测 38/39 PASS。

**v1 待移植（占位 stub 已加，full 模式跑时会 emit WARNING 提示未实现）**：
- QC-1 数值重算 (BS_CHECK / CF_CHECK)
- QC-3 Others/CFO 双阈值
- QC-4 BS Cash = `=CF!`
- QC-5 NCI 滚动公式
- QC-6 公式完整性抽查 (hist→Raw_Info, fcst→formula)
- QC-7 _State 14 个必需 key
- QC-9 Summary tab 无 hardcode
- QC-10 WC days vs 3yr avg
- QC-11 Σ(segments) = Total Revenue
- QC-12 Effective tax rate 偏离
- QC-13 R3 Others 历史来源
- QC-16 Input cell 颜色 = FF0070C0

移植源：`references/session-e.md` L225-403 的 QC 实现代码。v1 时直接拷贝进 `qc_suite.py` 作为独立函数，append 到 `FULL_QCS` 列表即可（架构已就位）。

**未实现的 QC 不会让 full mode 假 PASS**：`qc_full_not_implemented()` 占位会 emit `QC-FULL-COVERAGE WARNING`，确保 gate exit code 至少是 1（不会误判 exit 0）。

## 后续步骤

PASS 后下一 session 启动前，由 H2 hook 自动校验前一档 `GATE_<X>_PASSED` 已写入 _State（SKILL.md Session startup Step 6）。
SESSION E 全 PASS 后调用 `data-validator/scripts/validate.py --mode full` 做 Registry 校验。
最后 `REGISTRY_VALIDATED: TRUE` + `PHASE_DONE: MODEL_COMPLETE` 才写入 _State。
