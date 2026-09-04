# DrawIO 图示生成报告

| 文件 | 类型 | 用途 | 状态 |
| --- | --- | --- | --- |
| `figures/fig_roadmap.drawio` | 技术路线图 | 说明四问之间的数据与方法依赖 | 源文件已验证；PDF 未导出 |
| `figures/fig_decision_flow.drawio` | 生产决策流程图 | 说明检测、售后与拆解循环 | 源文件已验证；PDF 未导出 |

未额外生成子问题流程图，避免与已有结果图重复。

本机未找到 DrawIO/diagrams.net CLI，且运行时配置未提供 `drawio` 路径，故 PDF 导出状态为 `UNVERIFIED`。建议安装 DrawIO Desktop 后以 `--export --format pdf --crop` 导出两个源文件。

论文建议：`fig_roadmap` 放在总体思路后；`fig_decision_flow` 放在问题 2 模型建立之前。
