# G3 正式实验结果报告

## 证据状态

- 解释器：`D:\shumo\shumo\projects\20260901-CUMCM2020C-credit-decision\.venv\Scripts\python.exe`
- G3 审计：`VERIFIED`，证据文件为 `reports/code-audit/g3/audit.json`。
- 审计重放：`main-smoke` 退出码 0，2.50 秒；`main-full` 退出码 0，86.39 秒。
- 代码质量：Ruff 通过；Pytest 6 项全部通过，覆盖正常、边界与失败输入。
- 外部接口：SciPy MILP、XGBoost 分类器和 SHAP TreeExplainer 均有本机成功执行证据。

## 关键数值核对表

| 核对项 | 结果 | 数据定位 |
| --- | ---: | --- |
| 源域/目标域企业数 | 123 / 302 | `results/summary.json` |
| 经营特征数 | 32 | `results/summary.json` |
| 融合权重（XGBoost） | 0.80 | `model_metrics.selected_xgboost_weight` |
| 折外 Accuracy / Macro-F1 | 0.6016 / 0.6086 | `model_metrics.ensemble` |
| 折外二次加权 Kappa | 0.6666 | `model_metrics.ensemble.quadratic_kappa` |
| CRI 对历史违约的折外 AUC | 0.9066 | `model_metrics.oof_default_auc` |
| 问题一展示预算 | 5000 万元 | `results/problem1_budget_curve.csv` |
| 问题一入选企业 | 50 家，D 级为 0 家 | `results/problem1_strategy.csv` |
| 问题二年度预算 | 1 亿元，误差 0 元 | `results/problem2_risk_return_curve.csv` |
| 问题二主策略 | 101 家，23.19 万至 100 万元 | 同上，风险上限 1.30% |
| 问题二期望效益 | 142.90 万元 | 同上 |
| 问题三轻/中/重压力效益 | 132.46 / 114.75 / 90.99 万元 | `results/problem3_scenarios.csv` |
| 1.5 倍压力最坏效益 | 69.96 万元 | `results/problem3_stress_sensitivity.csv` |

## 结论边界

信誉评级是主监督标签；违约字段只用于历史外部有效性核验和评级到组合风险损失尺度的平滑映射。输出的风险损失系数不是可直接用于监管资本或会计拨备的校准违约概率。1.30% 风险敞口上限、LGD 和压力情景参数均为模型决策假设，附件没有提供银行风险偏好和真实疫情损失观测，因此论文将同时给出敏感性结果，不把这些参数写成数据事实。

## 一键复现

在项目根目录执行：

```powershell
& ".\.venv\Scripts\python.exe" "code\main.py" --run
```

正式产物 SHA-256 记录在 `results/summary.json` 和 `reports/code-audit/g3/audit.json`。当前结果只使用本项目 `inputs/` 中冻结的题面和三个附件，未读取工作区旧题目的数据、代码、参数或结论。
