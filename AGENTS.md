# 团队数学建模工作区

本仓库根目录是共享工作流，具体题目在 `projects/`。先定位用户正在处理的项目，读取其 `plan.md`、`todo.md`、报告及更近层级的指令；已有批准、正式输入与主稿以当前文件和真实对话为依据。

## Codex 对话入口

- 开始新题/完整建模：读取 `.agents/skills/1start-mathmodel/SKILL.md`。
- 改模型、加深建模、验证创新：读取 `.agents/skills/2analysis-modeling/SKILL.md` 与 `.agents/skills/research-evidence/SKILL.md`，按已授权阶段落实推导、基线、实验计划；运行实验时再读取 `3coding-visual`。
- 修改论文/摘要：读取 `.agents/skills/5writing/SKILL.md` 与 `research-evidence`；仅改当前正式主稿及相关证据，不能假定历史 DOCX 已迁移为 LaTeX。
- 数据图：读取 `.agents/skills/3coding-visual/SKILL.md`；流程图/技术路线图：读取 `.agents/skills/4drawio/SKILL.md`；两者均按 `research-evidence` 保留证据和实际视觉复核。
- 最终核验：读取 `.agents/skills/6verity/SKILL.md` 与 `research-evidence`，区分结构检查、真实运行、科研判断及页面验收。
- 上传/同步：读取根目录 `TEAM_CODEX_GUIDE.md`；上传以用户明确请求为准。

能力由当前 Codex 会话和本地工具执行，不依赖 Modex 安装包或专用 API。需要付费外部服务或另一个模型时，先明确该依赖，不能虚构已调用。新项目使用 XeLaTeX 源码和 PDF，原有项目保留其主稿；团队共享代码、模板、证据和图源，不共享机器专属虚拟环境与密钥。

现有 G0–G7 协议继续生效。`workflow/runner.py` 是前期未接入的状态调度草稿，不作为生产入口；本轮采用已有 `plan.md` 审批和 `research-evidence` 内容核验，不启动第二份状态真源。
