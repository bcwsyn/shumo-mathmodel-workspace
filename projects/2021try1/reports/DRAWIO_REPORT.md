# DrawIO 图示生成报告

> 当前状态：G4 非数据图示已完成，`WAITING_FOR_APPROVAL`。

## 1. 图示规划清单

- [x] `fig_roadmap`：三问依赖、输入输出与统一验证层。
- [x] `fig_flow_optimization`：问题二顺序凸化、精确回代、多起点和 L∞ 精修流程。
- [x] `fig_model_raytrace`：问题三面板细分、反射、命中、权重和接收比模型。
- [ ] 独立问题一流程图：不生成；焦距候选比较已由总体路线和数据图完整表达。
- [ ] 数据处理流程图：不生成；数据字段恢复只是前处理，不是本文主要创新。
- [ ] 指标体系图：不适用；本题是机理与约束优化问题，不是多指标评价问题。

## 2. 图示清单

| 文件 | 类型 | 来源依据 | 论文用途 | 状态 |
| --- | --- | --- | --- | --- |
| `figures/fig_roadmap.drawio` / `.pdf` | 技术路线图 | 三问依赖链“理想面→约束工作面→接收比” | 问题重述或模型总体框架 | VERIFIED |
| `figures/fig_flow_optimization.drawio` / `.pdf` | 算法流程图 | 顺序凸化、多起点、精确非线性回代和二阶段精修 | 问题二模型求解 | VERIFIED |
| `figures/fig_model_raytrace.drawio` / `.pdf` | 模型结构图 | 三角面板确定性细分、镜面反射、馈源命中和能量加权 | 问题三接收比模型 | VERIFIED |

三张图均直接对应 `reports/ANALYSIS_MODELING_REPORT.md` 的正式方法，没有重复 G3 的焦距曲线、约束分布、落点或敏感性等数据图。

## 3. 导出记录

- DrawIO：`C:\Users\lw195\AppData\Local\Programs\draw.io\draw.io.exe`
- 导出参数：`--export --format pdf --crop`
- 三次最终导出进程退出码：均为 0
- PDF 文件头：均为 `%PDF`

| PDF | 大小 | SHA-256 |
| --- | ---: | --- |
| `fig_roadmap.pdf` | 207027 B | `6ed10bd45a681b1118157d428945d712b3eede59bdb6cac16fba2235bc83a18f` |
| `fig_flow_optimization.pdf` | 213397 B | `d1d79c34ec854c8d19e1ecba7f0dbd4b2e89eee12c63acc0041245232ef1e0db` |
| `fig_model_raytrace.pdf` | 180023 B | `d773ab9d89d72f139d18187f2ee58d7c396223d76900c70712bc9e5b81f5a4bb` |

## 4. 自检与修复

- 三个 `.drawio` 均可解析为 `mxfile` XML，源文件非空且可编辑。
- 三个 PDF 均已用 Poppler 栅格化并逐张检查。
- 初次预览发现总体路线图的一条输入连线穿过问题二节点、优化流程图的循环线与主流程重合；均已调整路径并重新导出。
- 最终版本没有连线穿越核心节点；箭头方向、判断分支、返回循环和输入输出关系清楚。
- 中文、变量、单位和公式完整；颜色在同类节点中一致，无阴影、渐变或装饰性元素。

## 5. 给论文阶段的嵌入建议

| 图 | 建议章节 | 建议 caption |
| --- | --- | --- |
| `fig_roadmap.pdf` | 问题分析之后、模型假设之前 | FAST 主动反射面三问统一建模技术路线 |
| `fig_flow_optimization.pdf` | 问题二“模型求解”小节 | 严格可行顺序凸化与二阶段精修流程 |
| `fig_model_raytrace.pdf` | 问题三“接收比模型”小节 | 面板确定性细分与馈源接收比计算结构 |

论文中应在图前说明图要回答的问题，并在图后解释关键分支；不应连续堆放三张图。最终 Typst 插图尺寸和编号由 G5/G6 根据版面确定。
