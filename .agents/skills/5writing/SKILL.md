---
name: 5writing
description: "高质量数学建模项目的 Typst 论文撰写阶段。模拟有多年经验的优秀建模团队，使用对应竞赛的格式与模板完成高水平论文，依次通过 G5 大纲、G6 完整源文件和 G7 预览 PDF 审批。"
---

# 高质量数学建模论文撰写（Typst）

本 skill 承接 `3coding-visual` 和 `4drawio`。前序阶段提供真实结果、图表 PDF 和记录文件；本阶段只使用 Typst 组织论文、嵌入图表并编译预览 PDF。LaTeX 不属于本项目工作流；若外部规则强制提交 `.tex`，报告阻塞并请求用户另行决定，不得静默切换引擎。

开始时读取 `../_references/learning_project_contract.md`。默认模拟有多年竞赛经验的优秀建模团队写作：主动强化论证、组织语言和核对证据，只借用相应竞赛的格式、模板和章节习惯。外部提交合规只在用户明确启用时另行处理。

## 人工审批边界

开始时读取 `../_references/approval_gates.md`。确认 G3 已批准，且 G4 已批准或已明确批准跳过。论文阶段分三轮：

- G5：只提交论文大纲、章节论点、公式清单和图表放置计划。
- G6：仅在 G5 批准后完成全部 `.typ` 源文件，提交内容草稿和数值核对表；不生成最终完整交付版。
- G7：仅在 G6 批准后编译 `preview.pdf`，逐页视觉检查并提交预览。

每个审批点结束后立即停止。G5、G6、G7 提交前分别更新 `reports/QUALITY_SCORECARD.md` 的结论与论证、图表与排版、引用与数值一致性证据。G7 批准前不得调用 `6verity`，不得把预览文件称为最终论文。需要 Typst 语法、排版或调试帮助时调用 `typst-author`。

## 规范与证据

如需领域判断，读取 `../_references/math_modeling_norms.md` 中的“论文写作”“图表与可视化”和“非数据图工具选择”。论文中的数值、排序、误差、权重和结论必须能追溯到 `reports/RESULTS_REPORT.md`、结果文件或图表数据；不得估算、编造或更换四舍五入口径。

只有项目模式明确为“直接参赛”时，才读取用户指定的当年外部提交规则。默认高质量完整建模模式不启用这些提交条款。

## Typst 模板族

模板位于 `templates/<lang>/<竞赛>/main.typ`。支持：

- 中文：`apmcm`、`changsanjiao`、`cumcm`、`default`、`diangongbei`、`dongsansheng`、`huashubei`、`huaweibei`、`huazhongbei`、`mathorcup`、`mcm`、`shuweibei`、`stats`、`wuyibei`。
- 英文：`apmcm`、`default`、`mcm`。

华为杯、华中杯、五一杯分别使用 `huaweibei`、`huazhongbei`、`wuyibei`。除非用户明确要求中文，否则 MCM/ICM/COMAP 使用英文模板。

## 工作流

### Step 0：确认项目模式、格式模板和 Typst 运行证据

从 `plan.md` 读取项目模式。未记录时写入“高质量完整建模”，不得因选择 CUMCM/MCM 模板自动切换为直接参赛。

高质量完整建模模式：

- 使用对应竞赛模板的版式、语言、页面结构与章节习惯。
- 完整完成论文起草、改写、论证增强和证据校验，不创建参赛披露包、匿名检查表或文件大小合规表。
- 保持事实、数值、引用和复现信息真实，以数学正确性、题目针对性、创新性、证据强度和表达质量为目标。

直接参赛模式：

- 创建或更新 `reports/<COMPETITION>_COMPLIANCE.md`，核验用户指定的当年官方格式与提交要求。
- 规则未发布或无法核验时标记 `UNVERIFIED`，不得静默沿用上一年度规则。
- 外部规则与当前成果冲突时单独报告，不得通过删减模型、实验或论证来把高质量完整稿降格为合规稿。

从 `plan.md` 读取排版引擎。未记录时写入 `Typst`；若记录为其他引擎，向用户说明本项目当前固定使用 Typst并等待确认，不要继续沿用旧值。

读取 `.codex/runtime.local.json` 的 `typst` 绝对路径，使用 `doctor/scripts/check_environment.py` 验证最小 Typst 编译。只有 `paper_typst` 为 `VERIFIED` 才能进入 G5。仅执行 `--version` 或仅检查路径不足以证明可编译。

### Step 1：选择语言和模板

模板键示例：

```text
长三角 -> zh/changsanjiao
APMCM 英文版 -> en/apmcm
全国赛/国赛/CUMCM -> zh/cumcm
统计建模 -> zh/stats
MCM/ICM/COMAP -> en/mcm
```

用当前平台的文件 API 检查入口，不使用 `ls` 或 Bash 条件表达式。Windows PowerShell 示例：

```powershell
$template = Join-Path $SKILL_DIR 'templates/zh/<竞赛>/main.typ'
if (-not (Test-Path -LiteralPath $template)) { throw "missing Typst template: $template" }
```

入口存在时整目录复制到 `paper/`，然后用 `apply_patch` 修改论文源文件。存在匹配模板时不得从空白文件重建；入口缺失时标记 `FAILED`，不要假装模板已安装。

### Step 2：保留模板结构

读取所选模板的 `main.typ` 及其全部 `#include("...")`：

- 保留比赛封面、摘要、编号、页眉页脚、目录和附录结构。
- 章节文件名和顺序以模板真实 include 为准，根据题目实际子问题数量增删问题章节。
- 每个正文 section 使用明确一级标题 `= 标题`。
- 正文使用连贯学术段落，避免大量列表。
- 正文不得出现 `reports/`、内部 JSON 路径、审批门名称或其他工作流术语。

### Step 3：构建图表规划

根据 `figures/*.pdf`、`reports/RESULTS_REPORT.md` 和存在时的 `reports/DRAWIO_REPORT.md` 建立“图表 → 章节 → 论证作用”映射。数据图放在对应结果或分析章节，非数据图放在方法或总体思路章节。

从 `paper/sections/*.typ` 引用项目图表时通常使用两级相对路径：

```typst
#figure(
  image("../../figures/fig_q1_error_dist.pdf", width: 85%),
  caption: [问题一预测误差分布],
)
```

英文论文使用英文 caption。每张图前后必须有解释，不能连续堆图或以图代替结论。

### Step 4：提交 G5 大纲审批

提交：章节结构、每节核心论点、主要公式、表格、图表位置、摘要拟包含的关键结果和参考文献计划。按审批协议提交 G5 后停止；只有 G5 获批才能写正文。

### Step 5：撰写与核对正文

按模板逐节写作：

- 问题重述只重组题意，不照抄题面。
- 假设说明必要性、适用范围及偏差风险。
- 符号表与公式保持一一对应。
- 每个子问题给出模型、算法、参数、结果和解释。
- 灵敏度、稳健性、优缺点和推广必须基于真实实验或明确的理论分析。
- 摘要最后撰写，覆盖每个子问题的方法和精确数值结果。

执行专业表达与论证复核：

- 每段围绕具体题意、公式、数据、图表或实验事实展开，形成“主张—证据—解释—限制”的论证链。
- 删除不承载信息的套话、夸张评价和机械连接词，避免多个段落使用相同句式、相同开头和固定四段式模板。
- 保留真实的方案比较、失败尝试、假设边界和结果限制，不把研究过程润色成没有分歧的完美叙事。
- 专业术语、变量和结论保持稳定，不为追求语言变化随意替换造成含义漂移。
- 不使用 AI 检测分数作为质量证据，不承诺所谓“低 AI 率”。

参考文献只写真实可核验来源，使用 `paper/references.typ`。正文引用方式应与模板一致，例如 `#super("[1]")`、`@label` 或 `#cite(...)`，不得虚构 DOI、作者、期刊或年份。

### Step 6：提交 G6 源文件审批

完成源文件后提交：

- 摘要和关键词。
- 每个子问题的方法、关键公式和精确结果。
- 结论、优缺点和灵敏度分析。
- 图表与章节对应表。
- 关键数值与 `RESULTS_REPORT.md` 的核对表。
- 参考文献清单及其可核验信息。
- 全部 `.typ` 源文件链接。
- 项目模式与模板选择依据；仅直接参赛模式附用户明确要求的当年规则核验状态。
- 文本门禁发现的套话密度、重复段落开头、过短段落和空泛结论警告及人工处置说明。

用户修改意见不等于批准；修改后重新提交 G6。G6 前不生成最终完整交付版 PDF。

### Step 7：编译并提交 G7 预览

仅在 G6 批准后执行：

```powershell
$runtime = Get-Content -Raw -Encoding UTF8 -LiteralPath '.codex/runtime.local.json' | ConvertFrom-Json
$typst = $runtime.typst
& $typst --version
if ($LASTEXITCODE -ne 0) { throw 'Typst version probe failed' }
& $typst compile 'paper/main.typ' 'paper/preview.pdf'
if ($LASTEXITCODE -ne 0) { throw 'Typst compile failed' }
$pdf = Get-Item -LiteralPath 'paper/preview.pdf'
if ($pdf.Length -eq 0) { throw 'preview.pdf is empty' }
Get-FileHash -Algorithm SHA256 -LiteralPath $pdf.FullName
```

编译后使用 doctor 报告中通过真实转换测试的 PDF 栅格工具把每页导出为 PNG，逐页检查缺页、乱码、裁切、图表和公式越界、页眉页脚、页码、异常空白及字体 fallback。不得仅凭编译退出码宣称版式正确。

向用户提供预览 PDF、页面预览、已知版式问题和拟修复项，提交 G7 后停止。用户批准 G7 后，本 Skill 才完成；最终验收交给 `6verity`。

## 通过条件

- Typst 最小调用和论文实际编译均成功。
- `preview.pdf` 非空、哈希已记录并完成逐页视觉检查。
- 所有关键数值可追溯，图片路径和引用真实存在。
- 无占位符、内部工作流泄露、缺字乱码或影响阅读的版式错误。
