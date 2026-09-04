# 数学建模团队 Codex 同步指南

本仓库是团队唯一共享工作区，覆盖工作流、建模项目、论文、图表、知识库和交付材料：

`https://github.com/bcwsyn/shumo-mathmodel-workspace`

每名队员在自己的电脑上拥有一个本地副本。大家可以并行修改不同文件；GitHub `main` 汇合已经上传的非冲突修改。不要通过微信、OneDrive 副本或压缩包替代 GitHub 的共同版本。

GitHub 登录、密码、验证码和授权页面必须由本人完成，不能提供给 Codex。

## 首次同步

对自己的 Codex 说：

> 请首次同步数学建模团队总仓库 `https://github.com/bcwsyn/shumo-mathmodel-workspace.git` 到本机合适的工作目录，切换并同步 `main` 分支。若出现 GitHub 登录或授权页面，请提示我手动完成。不要修改、删除、提交或上传文件。完成后报告本地路径、当前提交号，并确认根目录的 `TEAM_CODEX_GUIDE.md`、`.agents/skills/`、`projects/`、`knowledge/`、`deliverables/` 与 `docs/` 均可读取。

如仓库读取失败，先检查是否已接受 GitHub 协作者邀请、是否登录正确账号；Git LFS 未安装或未能下载时，由 Codex 报告具体文件和最小修复命令。

## 日常协作：只使用两句口令

完成自己的工作且需要共享时，对 Codex 说：

> 上传本次修改

Codex 应检查变更、先同步远端 `main`、在没有冲突时创建能概括变更的提交并推送。提交前若发现认证失败、合并冲突，或存在无法安全归类的异常文件，必须停止报告，不能覆盖远端内容。

需要获得其他成员的最新修改时，对 Codex 说：

> 同步团队最新修改

Codex 应检查本地工作区是否干净；干净时同步远端 `main` 并报告新增提交与改动摘要。若本地存在未提交修改或发生冲突，必须停止报告，不能覆盖本地文件。

## 共同规则

- 禁止使用 `git push --force`、`git reset --hard` 或 `git checkout --` 覆盖他人或本地工作。
- 同一 Word、PDF、Excel、Draw.io 或同一段文本不能由多人同时编辑；开始前先在团队群说明文件路径。
- `.venv/`、缓存和临时渲染目录不进入版本控制；正式代码、论文、图表、结果、报告、工作流与知识资料由总仓库同步。
- 大型 `q1_temperature_field.svg` 由 Git LFS 管理；不要删除 `.gitattributes`，也不要用普通 Git 文件替代该 LFS 指针。
- 推送成功后，在团队群发送提交号和 Codex 生成的改动摘要；其他成员再执行“同步团队最新修改”。
