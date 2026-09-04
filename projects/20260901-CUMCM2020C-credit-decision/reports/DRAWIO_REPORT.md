# DrawIO 图示生成报告

## 图示清单

| 文件 | 类型 | 来源依据 | 用途 | 状态 |
| --- | --- | --- | --- | --- |
| `figures/fig_roadmap.drawio` | 技术路线图 | `ANALYSIS_MODELING_REPORT.md` 与 `RESULTS_REPORT.md` | 连接三个附件、风险迁移、需求响应、三问优化和解释验证 | 源文件已生成并通过 XML 解析 |
| `figures/fig_roadmap.pdf` | PDF 导出 | 同上 | 论文绪论后嵌入 | UNVERIFIED：当前机器没有可执行的 Draw.io |

## 未生成图示及原因

未单独生成 `fig_flow_q1`、`fig_flow_q2` 和 `fig_flow_q3`。三问的数据流与依赖已在一张技术路线图中表达，单独流程图会与正文公式和求解步骤重复；数据型图表由正式实验阶段生成，不在本阶段重画。

## 导出与自检记录

`fig_roadmap.drawio` 为未压缩 XML，包含 10 个功能节点和 12 条正交有向边，采用统一字号、同类配色、无渐变和无阴影。节点按“输入—特征/需求—风险模型—三个子问题—解释验证”自上而下布置。

工作区配置的 Draw.io 路径为 `C:\Users\lw195\AppData\Local\Programs\draw.io\draw.io.exe`，该文件在当前机器不存在；`Get-Command drawio, draw.io` 也未解析到可执行程序。因此没有伪造 PDF 导出状态。安装 Draw.io 后可按 `4drawio` 技能中的 `--export --format pdf --crop` 命令导出。

## 给论文阶段的嵌入建议

建议放在“问题分析与总体思路”末尾，caption 为“信用风险迁移、需求响应与鲁棒信贷优化的总体技术路线”。在 Draw.io PDF 未导出前，论文初稿可不嵌入该图，不影响数据图和数值结论；源文件保留供最终定稿时编辑。
