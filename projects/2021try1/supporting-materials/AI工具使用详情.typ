#set document(
  title: "AI 工具使用详情",
  author: (),
)
#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 2.5cm, right: 2.5cm),
  numbering: "1",
)
#set text(font: ("Times New Roman", "SimSun", "Microsoft YaHei"), size: 11pt, lang: "zh")
#set par(justify: true, first-line-indent: 2em, leading: 0.7em)
#show heading.where(level: 1): set align(center)

= AI 工具使用详情

本文件对应《FAST 主动反射面形状调节的约束优化与接收性能分析》。该工作是对 2021 年全国大学生数学建模竞赛 A 题的赛后教学复现，不是 2021 年竞赛期间形成的原始参赛作品。

== 工具信息

- 工具：OpenAI Codex 桌面环境；
- 开发机构：OpenAI；
- 使用日期：2026 年 7 月 23 日；
- 模型版本：由 Codex 平台记录的当前后端版本，本地文档不另行推断或伪造版本号。

== 使用目的与环节

AI 工具用于辅助整理题面与附件、比较建模方案、编写和检查 Python 程序、解释优化与射线追踪结果、生成数据图和流程图、组织 Typst 论文以及执行最终一致性检查。

== 关键交互与人工审批

用户要求按数学建模工作流完成题目，并依次明确批准 G0 至 G7：题意、建模方案、最小代码、正式结果、非数据图、论文大纲、完整源文件和预览 PDF。每个阶段均在批准后才进入下一阶段。

== 采纳、修改与验证

AI 生成的方案和代码没有直接作为无证据结论使用。正式程序使用项目指定的 Python 解释器运行，依赖版本、入口退出码、测试、Ruff、产物路径和 SHA-256 哈希由审计脚本记录。论文关键数值逐项对照正式结果 JSON，PDF 由 Typst 实际编译并逐页栅格化检查。发现的附录续编号问题已人工复核并修正。

== 责任与限制

本项目保留 AI 使用事实，不声称“未使用 AI”，也不以规避检测为目标。模型假设、程序实现、结果解释和论文内容仍需使用者自行理解、复核并承担责任。若将材料提交给课程、竞赛或其他机构，应继续遵守该接收方在提交时生效的诚信和披露规定。
