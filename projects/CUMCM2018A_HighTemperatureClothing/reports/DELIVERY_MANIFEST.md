# 完整学习交付清单

## 根目录入口

- `README.md`：成果入口与核心结论
- `REPRODUCE.md`：快速复验与完整实验命令
- `plan.md`、`todo.md`：阶段状态与审批记录
- `requirements.txt`：Python 依赖版本
- `.codex/runtime.local.json`：已确认的 Python、Typst 与 DrawIO 路径

## 原始材料

- `inputs/CUMCM-2018-Problem-A-Chinese.docx`
- `inputs/CUMCM-2018-Problem-A-Chinese-Appendix.xlsx`

## 论文

- `paper/main.typ`、`paper/lib.typ`、`paper/references.typ`
- `paper/sections/1_restatement.typ`
- `paper/sections/2_analysis.typ`
- `paper/sections/3_assumptions.typ`
- `paper/sections/4_symbols.typ`
- `paper/sections/5_problem1.typ`
- `paper/sections/6_problem2.typ`
- `paper/sections/7_problem3.typ`
- `paper/sections/8_sensitivity.typ`
- `paper/sections/9_evaluation.typ`
- `paper/sections/A_code.typ`
- `paper/preview.pdf`：G7 已批准的预览版
- `paper/final-learning-version.pdf`：最终学习版
- `paper/preview-page-01.png`、`paper/final-learning-version-page-01.png`

## 代码、测试与环境

- `code/main.py`：传热数值内核与 G2 入口
- `code/g3.py`：正式实验、枚举优化、NSGA-II、稳健性、制图与复验入口
- `code/audit_manifest.json`：确定性审计运行清单
- `tests/test_main.py`：12 项正常、边界和失败路径测试
- `requirements.txt`

## 正式结果

- `results/formal_results.json`
- `results/key_numbers.json`
- `results/g3_run_manifest.json`
- `results/g3_artifact_check.json`
- `results/g3_replay.json`
- `results/g2_baseline.json`
- `results/problem1.xlsx`
- `results/problem1_parameters.csv`
- `results/problem1_checks.csv`
- `results/q1_skin_temperature.csv`
- `results/q1_temperature_field.csv`
- `results/q2_enumeration_fast.csv`
- `results/q2_boundary_formal.csv`
- `results/q2_grid_refinement.csv`
- `results/q2_robust_search.csv`
- `results/q3_enumeration_fast.csv`
- `results/q3_boundary_formal.csv`
- `results/q3_grid_refinement.csv`
- `results/q3_robust_search.csv`
- `results/sensitivity.csv`

## 图表与可编辑源文件

- `figures/fig_roadmap.drawio`、`figures/fig_roadmap.pdf`
- `figures/fig_model_heat_transfer.drawio`、`figures/fig_model_heat_transfer.pdf`
- `figures/q1_model_fit.pdf`、`figures/q1_model_fit.svg`
- `figures/q1_residual_diagnostics.pdf`、`figures/q1_residual_diagnostics.svg`
- `figures/q1_temperature_field.pdf`、`figures/q1_temperature_field.svg`
- `figures/q1_temperature_profiles.pdf`、`figures/q1_temperature_profiles.svg`
- `figures/q2_enumeration.pdf`、`figures/q2_enumeration.svg`
- `figures/q3_feasible_region.pdf`、`figures/q3_feasible_region.svg`
- `figures/q3_pareto_cross_validation.pdf`、`figures/q3_pareto_cross_validation.svg`
- `figures/sensitivity_tornado.pdf`、`figures/sensitivity_tornado.svg`
- `figures/g2_skin_temperature_diagnostic.pdf`：G2 基线诊断图，不纳入论文正文

## 日志与证据

- `logs/g2_smoke.log`
- `logs/g3_formal.log`
- `logs/g3_validation.log`
- `logs/g3_process_stdout.log`
- `logs/g3_process_stderr.log`
- `reports/code-audit/preflight/audit.json`
- `reports/code-audit/g2/audit.json` 及对应入口日志
- `reports/code-audit/g3/audit.json` 及对应入口日志
- `reports/code-audit/final/audit.json` 及对应入口日志
- `reports/environment-check-g5.json`
- `reports/environment-check.json`

## 阶段与验收报告

- `reports/ANALYSIS_MODELING_REPORT.md`
- `reports/RESULTS_REPORT.md`
- `reports/DRAWIO_REPORT.md`
- `reports/PAPER_OUTLINE.md`
- `reports/PAPER_SOURCE_REPORT.md`
- `reports/PREVIEW_REPORT.md`
- `reports/VERIFY_REPORT.md`
- `reports/DELIVERY_MANIFEST.md`

`tmp/`、Python 缓存和工具缓存属于过程性文件，不作为正式交付入口。

