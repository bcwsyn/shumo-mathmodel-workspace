# 复现说明

## 已确认环境

- Python：`.venv/Scripts/python.exe`，版本 3.12.13
- Typst：项目 `.codex/runtime.local.json` 中记录的绝对路径，版本 0.15.1
- 依赖版本：见 `requirements.txt`
- 随机设置：正式结果与 NSGA-II 种子记录在 `results/formal_results.json`

以下命令均在项目根目录的 PowerShell 中执行。

## 快速复验

```powershell
$runtime = Get-Content -LiteralPath '.codex/runtime.local.json' -Raw -Encoding UTF8 | ConvertFrom-Json
& $runtime.python -m ruff check code tests
& $runtime.python -m pytest -q tests
& $runtime.python code/g3.py --replay
& $runtime.python code/g3.py --verify-artifacts
& $runtime.typst compile --root . paper/main.typ paper/reproduced.pdf
```

预期结果：

- Ruff 输出 `All checks passed!`；
- pytest 输出 `12 passed`；
- 两个轻量入口退出码均为 0；
- 正式产物哈希与 `results/g3_run_manifest.json`、`results/g3_artifact_check.json` 一致；
- `paper/reproduced.pdf` 为 21 页 A4 PDF。

## 完整正式实验

```powershell
$runtime = Get-Content -LiteralPath '.codex/runtime.local.json' -Raw -Encoding UTF8 | ConvertFrom-Json
& $runtime.python code/g3.py --formal --workers 4
```

已记录的正式运行耗时约 483 s。该命令会重新执行参数标定、问题二完整枚举、问题三双重枚举、临界网格复核、NSGA-II 多种子交叉验证、稳健性计算和正式制图，并更新 `results/`、`figures/` 与 `logs/` 中相应产物。

## 数据来源

原始题面与附件保存在 `inputs/`。程序不覆盖原始附件；计算结果写入 `results/`，图表写入 `figures/`，运行日志写入 `logs/`。

