---
name: 4drawio
description: "高质量数学建模项目的非数据型图示阶段。仅在 G3 结果批准后按论证需要生成专业技术路线图、流程图和模型结构图，保留可编辑源文件并提交 G4 审批。"
---

# 高质量非数据图示绘制

本 skill 承接 `3coding-visual`。它只负责论文中的**非数据型图示**，例如技术路线图、求解流程图、模型结构图、数据处理流程图、变量关系图、指标体系图和决策闭环图等。图示必须先服务论文论证，再进行视觉设计；不是用方框堆砌方法名或装饰页面。

开始时读取 `../_references/learning_project_contract.md`。图示服务高质量论文的论证，不以凑图数或装饰页面为目标。G4 提交前更新 `reports/QUALITY_SCORECARD.md` 的图表与排版证据。

## 人工审批边界

开始时读取 `../_references/approval_gates.md`，确认 G3 已批准。若论文不需要非数据图，列出判断依据并提交“跳过 G4”的审批请求；用户明确批准后才能进入论文大纲阶段。

生成图示时，完成清单、源文件、导出文件和自检报告后提交 G4 并停止。G4 批准前不得开始论文正文。

## 数学建模规范参考

如需领域判断，读取 `../_references/math_modeling_norms.md` 中的“图表与可视化”和“非数据图工具选择”小节。该文件只作为规范知识库，不要求为了凑数量生成额外图示。

## 图示论证合同与视觉规范

读取 `../research-evidence/SKILL.md` 与 `references/writing-figures.md`。将现有论证合同里的来源、可编辑图源、PDF/PNG、最终尺寸、内容检查和实际视觉检查登记到项目 `reports/research_evidence.json`；导出物变化必须重新打开复核。G4 提交前运行 `--stage G4`，程序通过只表示登记一致。明确批准跳过图示时登记实际批准记录为 `diagram_waiver`，不虚构一张图来满足检查。

在开始制图前，先建立每张图的“图示论证合同”，并写入 `reports/DRAWIO_REPORT.md` 的计划部分：

1. 这张图要证明或解释的单一论点；
2. 当前论文、建模报告、代码或结果中的直接依据；
3. 读者应在三秒内获取的主问题、主路径与最终输出；
4. 必须出现的模块、禁止出现的未经证实内容，以及与已有数据图不重复的理由；
5. 拟采用的图型：主流程、因果树、决策闸门、层级结构或反馈闭环。

在合同之后补一张“证据映射表”：将每个拟绘制模块逐项定位到论文章节、报告小节、代码产物或结果文件；标明该要素属于数据事实、模型关系、决策偏好或情景假设。图中的文字必须由这张映射表收敛而来，不凭记忆补充。若图示来自外部 Word/PDF，先提取标题、章节、图表标题和与该图直接相关的段落，再开始构图。

只有当前工作区证据支持的模型、指标、数值、约束和结论可以进入正式图。参考论文、旧版本图或通用模板只能借鉴布局、层级、配色和表达方式，不能作为科学内容来源。

视觉语言必须统一：

- 每种主色只表达一种语义；实线箭头表示数据或决策主流，虚线表示反馈、条件或监控。
- 使用白底或浅底、克制的低饱和配色、统一圆角/边框/字号与足够留白；不使用装饰性阴影、过度渐变、卡通图标或 AI 水印。
- 一个模块只回答一个问题。节点文字短，正文解释不搬入节点；箭头不得穿过核心节点，不为连接关系牺牲阅读顺序。
- AI 可以协助提炼结构和发现视觉问题；正式图必须保留可编辑 SVG 或 Draw.io 主源，并在图示记录中如实说明 AI 参与的具体环节、主源编辑方式、是否含生成位图或水印，以及适用的披露要求。不得将 AI 生成图直接作为唯一正式图源。

## 阶段边界

- 本阶段负责：可编辑 SVG 或 Draw.io 主源、非数据图 PDF/PNG、图示生成记录。
- 本阶段不负责：折线图、柱状图、散点图、热力图、箱线图、雷达图等数据图。这些由 `3coding-visual` 生成。
- 本阶段不重跑模型、不修改 `code/`，不改写 `reports/RESULTS_REPORT.md` 的数值结论。

## 必须产出

在当前工作目录创建或更新：

```text
figures/
  fig_roadmap.drawio
  fig_roadmap.pdf
  fig_flow_q1.drawio
  fig_flow_q1.pdf
  ...
reports/DRAWIO_REPORT.md
```

如果某类图不需要生成，必须在 `reports/DRAWIO_REPORT.md` 中说明原因。高质量建模论文通常适合至少一张 `fig_roadmap` 技术路线图，但没有论证价值时可申请跳过。

读取这些文件的目的不是提取数据作图，而是理解论文方法、章节结构、子问题关系和已有图表，避免重复。

## 工作流程

### Step 1: 盘点、论证合同与图型选择

先读取以下文件（存在则读取）：`reports/ANALYSIS_MODELING_REPORT.md`、`reports/RESULTS_REPORT.md`、`figures/` 目录列表。

然后从前序文档提取非数据图需求，为候选模块建立“模块—证据—属性”映射表，再完成每张候选图的“图示论证合同”，最后输出清单。必须先区分数据事实、模型关系、风险偏好和情景假设；任何无法定位的模块不进入正式图。

```text
DRAWIO PLAN CHECKLIST:
[ ] fig_roadmap      技术路线图，放在问题重述/绪论
[ ] fig_flow_q1      问题一求解流程图
[ ] fig_flow_q2      问题二求解流程图
[ ] fig_flow_q3      问题三求解流程图
[ ] fig_pipeline     数据处理流程图
[ ] fig_model        模型结构/变量关系图
```

清单不是固定模板，要根据题目实际删减或增补。不要为了凑图生成无意义图示。

### Step 2: 判定图类型

常见图示选择：

| 图类型 | 文件名建议 | 适用场景 |
| --- | --- | --- |
| 技术路线图 | `fig_roadmap` | 展示整体解题路线、章节逻辑、方法串联 |
| 子问题求解流程图 | `fig_flow_q1`, `fig_flow_q2` | 展示单个子问题的输入、判断、算法、输出 |
| 数据处理流程图 | `fig_pipeline` | 展示数据清洗、特征构造、建模输入 |
| 模型结构图 | `fig_model` | 展示模块关系、变量关系、模型层次 |
| 指标体系图 | `fig_index_system` | 展示目标层、准则层、指标层 |
| 决策树/规则图 | `fig_decision_tree` | 展示分类规则、设备选择、策略分支 |

不要用 DrawIO 画这些图：

- 结果对比柱状图
- 预测误差曲线
- 灵敏度曲线
- 相关性热力图
- 分布图和箱线图

### Step 3: 生成可编辑主源

简单且需要多人图形界面维护的图使用 Draw.io；复杂、高层级或需要精确排版的图使用 SVG。每张图只有一个可编辑主源，放在 `figures/`；不得只交付截图或不可修改的位图。

主源内容要求：

- 文字语言与论文语言一致。
- 节点文字短，必要时双行，不堆长句。
- 同类节点样式统一。
- 箭头方向清晰，避免交叉。
- 图中不写大段解释，解释留给论文正文。
- 不使用装饰性阴影和过度渐变。

使用 `apply_patch` 创建或修改 `.drawio` 或 `.svg` 文件；不要在 PowerShell 中使用 Bash heredoc、`cat` 或 `mkdir -p`。生成 Draw.io 大 XML 时分段提交补丁并在每次提交后验证 XML 完整性。最小结构示例：

```xml
<mxfile>
  <diagram name="Page-1">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- nodes and edges -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### Step 4: 导出与渲染预览

对于 SVG：先验证 XML 可解析，再使用可用浏览器或渲染器实际导出高清 PNG；同时导出 PDF。对于 Draw.io：按以下方式导出 PDF，并同时保留 PNG 预览。导出失败时保留主源，记录真实失败原因和建议命令，状态为 `UNVERIFIED`；不得把“源文件存在”写成已经完成视觉验收。

宽幅或长幅 SVG 的 PDF 导出不得依赖浏览器默认纸张。浏览器常默认 Letter/A4 页面，可能将右侧或底部模块裁切。导出后必须用 `pdfinfo` 或等效工具核对页数、页面宽高和主源画布比例；再渲染 PDF 检查所有边缘节点、连线和页脚文字均可见。若纸张尺寸与目标图形明显不匹配，必须改用自定义页面尺寸、SVG 专用导出器或其他无裁切方案重新导出。

先读取 `.codex/runtime.local.json` 的 `drawio` 字段；未配置时再用当前平台的命令发现机制解析 DrawIO 绝对路径。Windows 上 DrawIO 是 GUI 子系统程序，直接使用 `& draw.io.exe` 可能在文件完成写盘前返回并留下空的 `$LASTEXITCODE`，因此必须等待进程并验证产物：

```powershell
$runtime = Get-Content -Raw -Encoding UTF8 -LiteralPath '.codex/runtime.local.json' | ConvertFrom-Json
$drawio = $runtime.drawio
$input = (Resolve-Path -LiteralPath 'figures/fig_roadmap.drawio').Path
$output = Join-Path (Resolve-Path -LiteralPath 'figures').Path 'fig_roadmap.pdf'
$arguments = @('--export', '--format', 'pdf', '--crop', '--output', $output, $input)
$process = Start-Process -FilePath $drawio -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "DrawIO export failed: $($process.ExitCode)" }
if (-not (Test-Path -LiteralPath $output)) { throw 'DrawIO did not create the PDF' }
$bytes = [IO.File]::ReadAllBytes($output)
if ($bytes.Length -eq 0 -or [Text.Encoding]::ASCII.GetString($bytes[0..3]) -ne '%PDF') {
  throw 'DrawIO output is not a valid non-empty PDF'
}
```

配置路径必须真实存在。未配置时，Windows PowerShell 使用 `Get-Command drawio, draw.io -ErrorAction SilentlyContinue`，Unix shell 使用 `command -v`。必须记录所用工具、进程退出码、PDF/PNG 大小和哈希；工具不存在时标记为 `UNVERIFIED`。如果无法导出 PDF，保留主源，在 `reports/DRAWIO_REPORT.md` 记录失败原因和建议导出命令，不得虚构工具或静默宣称导出成功。

### Step 5: 自检和修复

每张图必须检查：

- 图的实际主路径、最终输出和颜色/线型语义是否与图示论证合同一致；每个要素是否可回溯到当前证据。
- 可编辑主源文件非空。
- 若主源为 SVG，XML 可解析；若导出成功，`.pdf` 与 `.png` 均非空。
- PDF 页数、页面尺寸与主源画布比例合理；对宽幅图，最右、最下模块及页脚均未被默认纸张裁切。
- 节点没有明显重叠。
- 箭头不穿过核心节点。
- 字号、颜色、边框风格一致，缩至论文目标尺寸后仍能读清节点文字。
- 文件名和图意一致。
- 没有与 `3coding-visual` 的数据图重复。

必须实际打开 PNG 和 PDF 的渲染预览进行视觉检查，确认文字清晰、箭头避让、模块对齐、留白、裁切和阅读顺序；发现问题要修主源并重新导出，不要只在报告里解释。

### Step 6: 写生成记录

创建 `reports/DRAWIO_REPORT.md`，至少包含：

```markdown
# 非数据图示生成报告

## 图示论证合同与清单
| 文件 | 类型 | 单一论点 | 来源依据 | 工具与主源 | 用途 | 状态 |
| --- | --- | --- | --- | --- |

## 未生成图示及原因

## 导出、内容核对与视觉验收记录

## 模块—证据映射与 AI 使用披露

## 给论文阶段的嵌入建议
```

记录必须逐图说明：模块与证据定位、属性（数据事实/模型关系/决策偏好/情景假设）、AI 参与环节、可编辑主源和是否存在生成位图或水印。嵌入建议只说明每张图适合放入哪个章节和建议 caption，不生成与正文脱节的图表清单源文件。最终的 LaTeX `\includegraphics`、`\caption` 与 `\label` 由 `5writing` 根据论文结构决定。

报告完成后按审批协议展示每张图的预览、用途和文件链接，状态设为 `WAITING_FOR_APPROVAL`。用户要求修改时只修改本阶段图示并重新提交 G4。

## 质量要求

- 图示服务论文论证，不为装饰而画；读者应能在三秒内识别主问题、主路径和最终输出。
- 每张图必须能对应到`reports/ANALYSIS_MODELING_REPORT.md` 中的真实方法。
- 数据型图表不得在本阶段重复生成。
- 论文阶段引用的非数据图都应有 SVG 或 `.drawio` 主源、PDF 和 PNG，或者在 `reports/DRAWIO_REPORT.md` 说明导出失败。
