# 论文图表复现索引

统一绘图代码：`code/plot_publication_figures.py`  
输出目录：`figures/publication/`  
每幅图同时提供300 DPI PNG、矢量PDF和可编辑SVG。

| 论文图号 | 输出文件前缀 | 输入数据或逻辑来源 |
| --- | --- | --- |
| 图1 | `figure01_method_overview` | 题目三问关系与论文第1章分析，无外部数据 |
| 图2 | `figure02_risk_pipeline` | `code/main.py`的特征、折内预处理、融合概率与CRI定义 |
| 图3 | `figure03_cri_distribution` | `results/problem1_strategy.csv`、`results/problem2_strategy.csv` |
| 图4 | `figure04_interest_loss` | `inputs/附件3：银行贷款年利率与客户流失率关系的统计数据.xlsx` |
| 图5 | `figure05_budget_benefit` | `results/problem1_budget_curve.csv` |
| 图6 | `figure06_transfer_shift` | `results/transfer_feature_shift.csv` |
| 图7 | `figure07_risk_return` | `results/problem2_risk_return_curve.csv` |
| 图8 | `figure08_stress_transmission` | 论文式（8）—（11）与`code/main.py`压力情景逻辑 |
| 图9 | `figure09_robust_scenarios` | `results/problem3_scenarios.csv` |
| 图10 | `figure10_shap_importance` | `results/shap_global.csv` |
| 图11 | `figure11_sensitivity` | `results/problem2_lgd_sensitivity.csv`、`results/problem3_stress_sensitivity.csv` |

图7的局部框只放大1.30%主方案附近的有效前沿，用于观察风险上限放宽时的边际效益变化，并辨识约1.34%处的平台起点。它不代表新增样本、插值结果或另一套模型。

复现命令：

```powershell
.\.venv\Scripts\python.exe code\plot_publication_figures.py
```
