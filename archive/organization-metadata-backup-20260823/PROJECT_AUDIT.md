# 项目资料审计与整理报告

日期：2026-08-23

## 结论

项目已调整为“高质量完整建模”默认模式。G0–G7 逐阶段审批保留，且新增贯穿 G1 到 Final 的 reports/QUALITY_SCORECARD.md 质量证据门禁。新题必须进入独立 projects/ 目录，最终生成独立 deliverables/ 交付包，不再复用根目录上一题的计划、代码、结果或论文。

## AI 限制清理

已从当前生效的工作流中移除：

- 公共规范中的 2025 CUMCM AI 使用规定摘要。
- 公共规范中的 2026 MCM/ICM AI 声明与页数硬编码。
- 写作阶段对 AI 披露包的默认分支。
- 最终验收脚本中的 --ai-use-status、未使用声明、正文 AI 标记和 AI工具使用详情.pdf 强制检查。
- 最终验收中的 2025 页数、文件大小和支撑材料硬编码。
- “学习复现/最终学习版”作为默认产物定位。

未在项目中发现用户所述 2025/2026 原始规则 PDF；找到的是已写入技能规范的摘要和旧案例产物。当前默认流程不再读取这些摘要。若未来明确要求直接参赛合规，只依据用户指定的赛事、年份和正式文件另行核验，不降低完整建模稿质量。

## 质量增强

新增六维质量证据门禁：题意与数据、模型与数学、代码与实验、结论与论证、图表与排版、复现与交付。

核心结论无证据、运行不可复现、引用不可核验或正文仍有明显模板化空话时，最终验收不得标记 PASS。

## 资料分区

当前生效：

- .agents/skills/1start-mathmodel 至 6verity
- .agents/skills/_references
- .agents/skills/verify-generated-code
- knowledge/mathmodel/approved
- 学习资料

历史完整项目（保留原位置，未删除）：

- 2021try1
- B题_数学建模_20260808
- CUMCM2018A_HighTemperatureClothing
- 交付包_生产质量决策模型_20260808

已安全归档：

- archive/legacy-root-run-20260808/：原先散落在根目录的上一题 plan.md、todo.md、代码、测试、结果、图表、论文和报告。
- archive/temporary-quarantine-20260823/：原根目录 tmp、.pytest_cache、.ruff_cache。为避免误删，采用隔离而非永久删除。

保留但不生效：

- .skill-backups/
- .skill-proposals/

这些仅为历史备份或提案，不在当前 .agents/skills/ 调用链中。

## 已知环境事实

根目录存在空 .git 目录，但它不是有效 Git 仓库；为避免误删潜在元数据，本次未修改它。因此不能用 git status 提供差异记录，本报告和当前文件内容构成变更审计依据。