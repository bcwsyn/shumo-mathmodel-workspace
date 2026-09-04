# CUMCM 2018 A 题：高温作业专用服装设计

本目录是完整的数学建模学习复现成果，包含题面附件、分析报告、可运行代码、测试、正式结果、数据图、Typst 论文源文件、预览 PDF、最终学习版 PDF 和验收证据。

## 主要结论

- 问题一：标定得到外侧、人体侧等效换热系数分别为 120.991689 W/(m²·K) 和 8.364912 W/(m²·K)，全时段拟合 RMSE 为 0.002627°C。
- 问题二：第四层厚度为 5.5 mm 时，第二层名义最小厚度为 17.6 mm。
- 问题三：名义最优厚度为第二层 19.3 mm、第四层 6.4 mm；联合 10% 不利情景下的稳健设计为 23.5 mm、6.4 mm。

## 入口文件

- 最终学习版论文：`paper/final-learning-version.pdf`
- 论文源文件：`paper/main.typ`
- 主数值实现：`code/main.py`
- 正式实验与优化：`code/g3.py`
- 自动测试：`tests/test_main.py`
- 结构化正式结果：`results/formal_results.json`
- 问题一工作簿：`results/problem1.xlsx`
- 最终验收报告：`reports/VERIFY_REPORT.md`
- 完整交付清单：`reports/DELIVERY_MANIFEST.md`
- 复现说明：`REPRODUCE.md`

## 使用说明

本成果属于 AI 主导的学习复现项目，不声明满足任何年份真实竞赛的提交、匿名、AI 披露或支撑材料合规要求。

