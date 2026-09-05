# 工作流能力移植：第一批实现

用户已选择方案 1：把工作流能力接入现有 Codex 文件工程。执行者继续使用现有 G0–G7 技能，新增 Python 标准库调度器负责可验证的状态、证据和交接。本批不建设独立 App。

## 来源证据与具体映射

只读观察对象为 Modex-MH-Agent 1.7.3 的安装目录。以下是静态代码/结构证据，不代表已经运行并验证 Modex 的对应功能。

| Modex 可见证据（相对 resources/app） | 移植能力 | 本工程实现 | 验收 |
| --- | --- | --- | --- |
| backend/main.py：get_templates、resolve_template_steps | 模板与步骤解析 | workflow/templates/mathmodel.json；templates/next 命令 | 解析出 G0–G7、Final 及技能与必需产物 |
| backend/db/schema.sql：workflows、workflow_steps | 项目初始化与逐步状态 | init、start；workflow/state.json | 新项目独立目录，已有项目不覆盖，输入复制并校验哈希 |
| schema.sql：checkpoints、response、waiting_checkpoint | 人工检查点与反馈 | submit、approve、reject、skip | 缺产物不能提交；等待批准不能进入下一步；仅 G4 可批准跳过 |
| main.py：get_workflows_to_resume、start_heartbeat | 中断后继续 | pause、fail、resume、next | 恢复同一步并给出已有证据/技能入口，不自行重跑实验 |
| schema.sql：output_files、workflow_logs | 产物登记、历史与归档 | 提交证据的 SHA-256、events/history、manifest、bundle | 文件被改或丢失可检出；只有全部审批完毕可打包 |
| schema.sql：model_used | 执行来源记录 | start --executor | 记录实际执行者/模型标识；未知填 unknown，不推断模型 |
| backend/services/*.pyd、skills/comp-modeling/SKILL.md.enc | 工作流内部实现不可直接读取 | 使用现有本地阶段技能独立实现 | 工具执行不依赖 D:/modex、不加载 pyd、不解密技能 |

Git 同步沿用 TEAM_CODEX_GUIDE.md，是本工程已有能力。论文编辑、编译、绘图仍由现有技能执行；调度器不冒充生成模型或论文编译器。DOCX 自动导出、多模型 API 执行、后台心跳重启和桌面 UI 留给后续独立任务，本批不声称已移植。

## 设计选择

比较三个方案：文件状态调度器、SQLite+服务端调度、完整 Electron 平台。选择第一个，因为现有入口是 Codex，团队需要 Git 共享且尚不需要常驻服务。JSON 状态便于审阅；单个项目状态文件必须串行编辑，Git 冲突需人工处理。进程锁只保护同一机器短事务，不能替代跨机器协作协议。

数据流：用户任务 → init 复制明确输入 → next 返回技能/必需产物 → Codex 执行该技能 → submit 绑定证据 → 用户决定 → approve/reject → 下一阶段；最后 manifest/bundle 导出已经登记的产物。

状态序列：pending → running → waiting → approved；running 可 paused/failed，resume 回到 running；reject 回到 running 并保留旧提交记录；reopen 指定阶段撤销该阶段及下游审批。已批准文件变化时必须重新评估最早受影响阶段，不能继续沿用旧审批。

## 文件与一致性

- 工具：workflow/runner.py；模板：workflow/templates/mathmodel.json；使用说明：docs/WORKFLOW_CAPABILITIES.md。
- 每个新项目保存 workflow/state.json：模板快照、输入指纹、阶段状态、证据指纹、审批原文、执行者、事件历史。路径均相对项目，禁止目录外文件及链接路径。
- plan.md、todo.md 指向状态入口，只负责科研规划/人工笔记，不保存第二份机器审批表；status/next 即时生成当前视图。
- 通过独占短事务锁及原子替换保存状态；发现已有锁立即报告，不自行删锁。状态冲突或格式错误停止，不从零重建。
- 新项目必须显式提供至少一个输入文件。旧项目不自动接管，更不根据旧报告的 PASS 字样推定审批。
- 审批记录要求用户原话非空，但 CLI 无法鉴别人类身份；Codex 必须依据真实对话调用，禁止自行编造批准。
- 本版保留逐阶段审批（含 Final 的打包放行），暂不实现取消全部审批。用户提出连续自动执行时需明确告知此限制。
- submit 的文件齐全与哈希检查仅是结构验收，科学正确性、实际运行和页面 QA 由阶段技能与人工审批负责。
- bundle 复制显式登记且指纹匹配的输入/证据，带完整状态和清单；新建目标目录，禁止覆盖。阶段执行者必须登记全部依赖源文件；不能仅登记报告和 PDF 后声称可复现。

## 验证与实施顺序

1. 实现模板、状态机、证据检查、并发锁和 CLI。
2. 临时目录测试新建/恢复/退回/批准/跳过/失效重开/归档，以及路径越界、缺件和锁冲突。
3. 接入总入口、README 和团队口令；旧信贷项目及其未提交修改保持原样。
4. 只用合成测试文件验证调度能力，不把测试当作真实 G0–G7 科研验收，不自动提交或上传。
