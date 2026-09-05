# 台账格式 v1

台账路径为项目 `reports/research_evidence.json`，所有证据使用项目内相对路径。文献网页本身不能填本地路径字段；先保存实际阅读后的来源索引/核验摘记，包含 URL、读取日期及支持范围，再引用这个索引文件。禁止把密钥、账号配置或无关日志纳入台账。

通用文件引用 ref：`{"path":"reports/model.md","sha256":"64位实际SHA256"}`。用 `Get-FileHash -Algorithm SHA256 -LiteralPath <文件>` 取得真实值，填小写或大写均可。检查器只读，无自动改哈希功能。

数组成员的 ID 在同类内唯一；建议 M1/E1/C1/F1/P1。以下所有字段均需按当前任务填写，不能直接把示例当证据。

## models（G1 起）

每个模型：id、question、baseline、change、mechanism、assumptions、verification_plan、failure_modes、complexity、selection_reason 为非空文本；derivation 为 ref，指向真实推导；contribution_type 为 application/method/theory；literature_status 为 verified/unknown，literature 为 ref 数组。method/theory 声明要求 verified 且有实际来源核验记录。application 允许 unknown，但不可宣称新方法。assumptions 等字段可用报告小节定位文本，内容必须在报告中实际展开。

## experiments（G1 规划，G2/G3 更新）

字段：id、model_id、role（baseline/improved/ablation/stress）、status（planned/succeeded/failed/not_applicable）、protocol（ref）、reason（说明实验目的或不适用原因）。协议是项目内 JSON，记录数据、划分、预处理、预算、指标定义等；同一比较的 baseline/improved 使用内容哈希一致的 protocol。

succeeded 额外要求 run_record（ref）和 metrics（ref）；metrics 是非空 JSON 数值字典，例如 `{"rmse":0.21}`，不允许 NaN/Infinity。run_record 是 JSON，包含实际 command（非空 argv 数组）、python、started_at、finished_at（带时区 ISO 时间）、exit_code（0）、inputs（非空 ref 数组）、code（非空 ref 数组）、log（ref）、seed（整数或 null）。退出码失败不允许伪填 0；failed 记录原因，并保留可得的运行日志。不适用的 role 用 not_applicable 并引用 rationale（ref）说明适用性和替代验证。

G2 至少一个成功 baseline。G3 起所有采用模型都有 baseline 成功，以及 improved/ablation/stress 的已处理记录（成功或有理由的不适用）；失败记录可以保留，但不能替代必需的成功/适用性说明。planned 记录不能通过 G3 交接；没有提升不等于执行失败，实验运行正常应标 succeeded，假说是否成立由 claims 表达。

## claims（G3 起）

字段：id、model_id、statement、kind（empirical/theoretical）、verdict（supported/not_supported/inconclusive）、limitations（文本）、analysis（ref）、experiment_ids（数组）。经验主张要关联至少一次成功实验；理论主张通过 analysis 指向完整推导/证明与人工复核。

声称指标改善时必须有 comparison：`{"baseline_id":"E1","candidate_id":"E2","metric":"rmse","direction":"min","minimum_gain":0.01}`。direction 只能 min/max，minimum_gain 非负，按指标原单位的绝对改善量定义。程序核对实验属于同一模型、角色/协议可比，读取指标，supported 要求改善为正且达到阈值。程序不判断统计显著性、理论原创性和因果关系，这些必须人工读 analysis。

## figures（G3 数据图，G4 图示）

字段：id、kind（data/diagram）、purpose、claim_ids（可空：探索图）、source（ref）、exports（非空 ref 数组）、data（ref 数组）、width_mm（正数）、content_review（ref）、visual_review（ref）。数据图必须有 data 且指向成功实验的 metrics 文件或其 run_record 中登记的 `artifacts` 数组中的 ref；数据图 source 为可编辑绘图代码（如 .py/.r/.jl/.m），diagram source 为 .svg/.drawio。

exports 包含 PDF 或 PNG 正式导出物。若输出 PNG，要提供 raster_width_px（正整数，实际像素宽度，检查器会核对 PNG IHDR）；同图多个 PNG 应宽度一致，尺寸不同请分项登记。visual_review 为 JSON：`{"status":"reviewed","reviewer":"实际检查者","reviewed_at":"带时区ISO时间","findings":"检查项目与发现/修复","outputs":[ref]}`，outputs 覆盖本图全部导出物并匹配当前哈希。程序不读取截图判断美观；reviewed 只能在真正打开检查后写入。

图示不适用时，diagram_waiver 为 ref，指向用户真实批准跳过的记录。G3 只检查数据图，G4 起检查全部图；没有数据图也须依据项目实际情况调整任务方案，本模板的完整实验路径默认要求至少一张有论证价值的数据图。

## paper（G5 规划，G6 起核验正文）

字段：id、purpose、claim_ids、figure_ids。G5 至少一个章节计划，关联的 claim 必须 supported；尚未证实的假说可在限制/讨论段落明确表述，不能作为已确认结论引用。每项 G6 增加 source（ref：实际章节 .tex/.md 或现有 .docx）、numbers（数组）。可编辑 DOCX 需要人工核对文字；数字自动定位只支持 UTF-8 .tex/.md/.txt，DOCX 请引用由同一 DOCX 提取并人工核对的段落文本文件作为 source，正式主稿仍为 DOCX。

numbers 项：experiment_id、metric、text、value、decimals、scale。text 是在章节中真实出现的完整显示文本（含上下文更好）；value 为其显示数值，decimals 为小数位数 0–10，scale 只能 1（原单位）或 100（百分比）；允许误差为最后一位半个单位。执行者人工核对 text 对应的数字/单位与 value 一致；程序核对 value 与结果、text 是否出现，不能理解任意数学排版。

G7/Final：layout_review ref 指向 JSON，格式与 visual_review 一致，outputs 含本次实际 PDF ref。该记录证明存在人工声明，不能证明已逐页看过；完整逐页证据仍按 5writing/6verity 留存并人工核对。

## 执行结果的含义

检查器 fail-closed：未知枚举、错误类型、空模板、缺依赖/文件或哈希变化返回 2。采用 G1→G2→G3→G4→G5→G6→G7→Final 累积检查，避免下游掩盖上游缺口。既有项目首次接入不伪造历史记录；先如实报告未满足项，再在授权范围内补证据。
