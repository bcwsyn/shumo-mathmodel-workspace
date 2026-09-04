# 方案

本项目按数学建模学习复现流程依次调用阶段 skill，所有产物统一保存在本目录。

## 用户偏好

- 项目模式：学习复现
- 排版引擎：Typst（项目固定）
- 竞赛类型：全国大学生数学建模竞赛（CUMCM）2018 年 A 题
- 论文语言：中文
- 子问题数量：预计 3 个，以 G0 题面核验为准
- 审批方式：G0–G7 逐阶段人工审批
- 方法偏好：将一维热传导 PDE、隐式差分、Thomas 算法、枚举/遍历、多目标遗传算法或粒子群算法、向量化/并行计算纳入候选比较；最终方法由题意、数据、精度和可复现性共同决定

## 工作流

| 阶段 | 负责 skill | 主要产物 |
| --- | --- | --- |
| G0 材料与题意确认 | `2analysis-modeling` | `reports/ANALYSIS_MODELING_REPORT.md` 的材料与题意审查部分 |
| G1 建模方案确认 | `2analysis-modeling`（可选 `mathmodel-learning`） | 完整 `reports/ANALYSIS_MODELING_REPORT.md` |
| G2 最小代码验证确认 | `3coding-visual` + `verify-generated-code` | 最小实现、测试、环境及运行证据 |
| G3 完整结果与数据图确认 | `3coding-visual` + `verify-generated-code` | `code/`、`tests/`、`results/`、数据图和 `reports/RESULTS_REPORT.md` |
| G4 非数据图示确认或批准跳过 | `4drawio` | 可编辑流程图/模型图、PDF 和 `reports/DRAWIO_REPORT.md` |
| G5 论文大纲确认 | `5writing` | 章节大纲、公式与图表规划 |
| G6 论文正文源文件确认 | `5writing` | `paper/` Typst 源文件 |
| G7 预览 PDF 确认 | `5writing` | `paper/preview.pdf` |
| 最终学习版验收 | `6verity` + `verify-generated-code` | 最终 PDF、`reports/VERIFY_REPORT.md`、代码复验与完整交付清单 |

## 总体建模方向（待 G1 决策）

以多层复合介质一维非稳态导热为机理主线，优先检查边界换热、层间连续性、人体侧边界和温度阈值的准确口径；在 G1 比较解析/半解析、有限差分和其他数值方案。优化阶段根据决策变量的离散性和规模，比较向量化枚举、分层搜索、精确小规模对照以及 GA/PSO/NSGA-II 等候选方法。

## 风险控制

- 题面、附件、单位和边界条件以原始文件为准，保留 SHA-256 哈希。
- G1 批准前不创建正式求解代码；G3 批准前不撰写论文。
- PDE 阶段必须做网格/时间步收敛、能量与界面连续性、极限情形校验。
- 启发式优化不宣称全局最优；须用枚举或小规模精确解交叉验证，并报告多随机种子稳定性。
- 所有论文数值必须可追溯到结果文件和真实运行日志。
- 原始附件只读使用，计算使用统一目录中的副本。

## 审批状态

| 审批点 | 状态 | 批准依据 | 日期/备注 |
| --- | --- | --- | --- |
| G0 | APPROVED | 用户回复“批准 G0，继续” | 2026-07-27 |
| G1 | APPROVED | 用户回复“批准 G1，继续” | 2026-07-27 |
| G2 | APPROVED | 用户回复“批准 G2，继续” | 2026-07-27 |
| G3 | APPROVED | 用户回复“批准 G3，继续” | 2026-07-27 |
| G4 | APPROVED | 用户回复“批准 G4，继续” | 2026-07-27 |
| G5 | APPROVED | 用户回复“批准 G5，继续” | 2026-07-27 |
| G6 | APPROVED | 用户回复“批准 G6，继续” | 2026-07-27 |
| G7 | APPROVED | 用户回复“批准 G7，继续” | 2026-07-27 |

## 最终验收状态

- 状态：PASS
- 启动依据：G7 已批准
- 验收范围：代码证据、结果一致性、论文文本、引用、Typst 编译、PDF 视觉质量与完整交付清单
- 最终产物：`paper/final-learning-version.pdf`
- 验收报告：`reports/VERIFY_REPORT.md`
