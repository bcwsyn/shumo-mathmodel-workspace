---
name: 6verity
description: "高质量数学建模项目的最终验证与完整交付阶段。仅在 G7 批准后检查论文、代码、结果、图表、引用、数值、可复现性与版式，修复硬错误并生成最终完整交付版 PDF、全套源文件清单和验收报告。"
---

# 最终完整交付版验证和验收（LaTeX 源码优先）

本 skill 是完整工作流的最后一关。它不重新建模、不生成新结果、不代替写作阶段重写论文；它负责发现硬错误、修复可直接修复的问题，并输出 `reports/VERIFY_REPORT.md`。

开始时读取 `../_references/learning_project_contract.md` 和 `../_references/python_engineering_standard.md`。默认验收目标是高质量、可学习、可复现、可继续修改的完整成果，不把外部提交资格作为 PASS 条件。

## 启动条件

开始时读取 `../_references/approval_gates.md` 和 `plan.md`。只有 G7 明确记录为 `APPROVED` 才能执行。若没有批准依据，停止并提示用户先确认预览 PDF；不得把 G6 的正文批准或一般性评价推断为 G7 批准。

最终验收允许修复拼写、引用、路径、编译和轻微排版等不改变模型结论的问题。若修复会改变模型、关键公式、核心数值、结论或大幅改变用户已批准的版式，停止并回到相应审批阶段重新确认。

只有 `plan.md` 明确记录为“直接参赛”时，才读取用户指定的合规报告和当年正式规则；核验不通过时不得生成“可参赛提交版”。高质量完整建模模式无需该合规报告，仍可生成最终完整交付版。

## 数学建模规范参考

如需领域判断，读取 `../_references/math_modeling_norms.md` 中的"论文验收与一致性"小节。该文件只是规范知识库，不是固定执行流程；具体目录、入口文件、结果文件和图表目录由当前项目结构决定。

## 阶段边界

- 本阶段负责：代码证据复验、LaTeX 源码结构验收、文本质量门禁、图表引用检查、结果一致性检查、XeLaTeX 编译检查、PDF 视觉检查、提交清单。
- 本阶段不负责：重新设计模型、重新跑大规模实验、重新组织整篇论文。
- 发现硬错误时，优先做小范围修复；如果需要回到前序阶段，写入 `reports/VERIFY_REPORT.md` 并标记为未通过。

## 输入

由模型先根据当前工作区判断项目布局，再把实际路径传给检查脚本。常见输入包括但不限于：

1. 论文入口文件：`main.tex`。
2. 正文章节目录或若干正文文件（`.tex`）。
3. 参考文献文件（`references.tex`）或模板指定的 `.bib`。
4. 前序阶段的分析、建模、结果、图示报告。
5. 图表目录
6. 可复现代码目录。
7. 编译后的 PDF，或可由入口文件编译得到的输出 PDF。

优先把 G7 的 `paper/build/preview.pdf` 作为视觉基线。最终完整交付版必须从同一 `main.tex` 生成 `paper/build/final.pdf`，不得手工修改 PDF 或仅交付 PDF。直接参赛模式才使用比赛要求的文件名。

不要假设论文目录一定叫 `paper/`，也不要假设结果文件一定在项目根。若项目使用不同命名，按实际结构传参并在 `reports/VERIFY_REPORT.md` 中说明。

## 工作流程

### Step 0: 运行最终代码证据复验

读取 `verify-generated-code`，使用项目已确认的解释器运行 `final` 审计。至少重跑 `code/audit_manifest.json` 中所有 final 轻量入口，核对正式结果产物哈希，并把 `reports/code-audit/final/audit.json` 的状态写入验收报告。

完整实验耗时过长时可以不重跑全部正式计算，但必须同时满足：已有 G3 正式运行日志和产物哈希仍存在、final 小样本重放成功、论文关键数值可追溯。仅做源码扫描、import 检查或“理论可运行”说明不能通过。

final 状态为 `FAILED` 时验收失败；为 `UNVERIFIED` 时不得生成最终完整交付版，除非缺失证据属于用户明确接受且不影响任何代码结果真实性的外部接口，并在报告中逐项说明。

### Step 0.5: 核对质量证据表

同时读取 `../research-evidence/SKILL.md`，运行 `--stage Final`，人工复核模型贡献类型、对照/消融/适用边界、正文数字和图源是否确实得到所引证据支持。先处理结构 FAIL，再执行本技能完整验收。`STRUCTURAL_PASS` 不等于最终 PASS。旧项目没有台账时记录缺口，按现有材料补定位；不能补造实验、时间或历史批准，也不能仅靠读取模板宣布能力已验证。

读取 `reports/QUALITY_SCORECARD.md`，核对题意与数据、模型与数学、代码与实验、结论与论证、图表与排版、复现与交付六个维度。每项必须列出可打开的证据文件和仍存缺陷；缺失该表、核心结论无证据或存在未关闭硬缺陷时，最终验收失败。

### Step 1: 运行文本质量门禁

读取 `.codex/runtime.local.json` 的 `python` 字段，并用该绝对解释器直接运行本 skill 的跨平台 Python 脚本。不要调用 Bash，不要假设存在 `python3`：

```powershell
$runtime = if (Test-Path -LiteralPath '.codex/runtime.local.json') {
  Get-Content -Raw -Encoding UTF8 -LiteralPath '.codex/runtime.local.json' | ConvertFrom-Json
} else { @{} }
$python = $runtime.python
$script = '<按当前 skill 实际位置确定>/scripts/writing_check.py'
& $python -X utf8 $script `
  --paper-dir $PAPER_DIR `
  --root-dir $ROOT_DIR `
  --main $MAIN_FILE `
  --sections-dir $SECTIONS_DIR `
  --references $REFERENCES_FILE `
  --figures-dir $FIGURES_DIR `
  --results-file $RESULTS_FILE `
  --problem-analysis $PROBLEM_ANALYSIS_FILE `
  --all-results $ALL_RESULTS_FILE
if ($LASTEXITCODE -ne 0) { throw 'writing text gate failed' }
```

如果本 skill 被复制到其他目录，使用实际脚本路径。可以先运行 `& $python $script --help` 查看参数。不要把脚本路径、论文目录或文件名写死在验收逻辑中。

脚本只扫描文本，不生成论文，也不编译 PDF。它的 `FAIL` 属于硬错误，必须修复后重跑。

### Step 2: 章节数量和标题顺序

- 入口 `main.tex` 中 `\input{...}` / `\include{...}` 的数量是否与实际正文结构匹配。
- include 顺序是否符合文件名前缀顺序，例如 `1_...`, `2_...`, `3_...`。
- 每个 section 是否有明确一级标题（通常为 `\section{标题}`）。
- 标题顺序是否符合所选论文类型。

- 章节文件是否缺失、重复引用、未被引用。
- 如果题目不是三问，不强行要求三段问题章节；按 `ANALYSIS_MODELING_REPORT.md` 的子问题数量核对。

### Step 3: 图表和章节匹配

- 图表目录中的 PDF 是否在正文中被引用。
- `\includegraphics{...}` 的图片是否真实存在。图片路径必须相对于 `.tex` 文件。
- 数据图是否放在对应结果/分析章节，非数据流程图是否放在方法/总体思路章节。

- 连续图表之间是否有足够解释文字。
- caption 是否过长、过泛或与图意不一致。
- 图表编号、正文引用和章节语义是否一致。

不要生成与正文脱节的图表清单源文件；图表必须直接嵌在对应 section 中。

### Step 4: 写作质量和泄露检查

检查并修复：

- `TODO`、`PLACEHOLDER`、`待补充`、`待续写`、`示例数据` 等占位符。
- 论文正文出现内部工作流文件名、临时目录名、代码目录名或结果 JSON 路径。
- 过多列表式写作（大量 `itemize`、`enumerate`）。
- 段落反复以"如图""由图""图 X 展示了"开头。
- 图表后没有解释、公式后没有变量含义、结论只报数不解释。
- 高频空泛套话、机械连接词和不含题目实体的通用段落。
- 连续多个段落使用相同开头、相同句式骨架或固定模板。
- 只宣称“效果良好、具有重要意义、验证了有效性”却没有指标、图表或理论依据。

专业表达检查用于提高可读性、题目针对性和原创论证质量，不使用所谓检测分数代替论文质量判断。

### Step 4.5: 直接参赛合规检查（条件执行）

高质量完整建模模式跳过本步骤，并在报告中记录“仅套用竞赛格式模板，未执行外部提交合规”。直接参赛模式按用户指定的合规报告逐项核验，并至少检查：

- 摘要页、正文和附录不含姓名、学校、赛区、指导教师、文件作者元数据等身份信息。
- 电子版第一页为摘要专用页，不含承诺书和编号专用页；摘要含标题和关键词且不超过一页。
- 是否设置目录、摘要位置、页数和文件大小均以用户指定的当年正式材料为准，不在通用验收中硬编码。
- 论文附录列出支撑材料文件，并包含全部完整可运行源代码；论文、代码、结果和支撑材料相互一致。
- 论文格式、支撑材料格式和文件大小按用户指定的当年正式材料核验。
- 所有公开资料在正文标注并列入真实参考文献。


### Step 5: 数值和结果一致性

检查：

- 论文中的关键数值必须来自当前工作流声明的结果记录或结果 JSON。
- 目标函数值、误差指标、排名、权重、阈值、灵敏度结果不得与结果记录冲突。
- 如果存在汇总结果 JSON，抽取关键指标并确认论文正文中有对应结果。
- 公式中的符号应在符号说明或正文首次出现处解释。

发现数值冲突时，不要自行发明新结果；应回到结果记录或代码输出修正论文。

### Step 6: 引用和模板规范

检查：

- 参考文献文件是否存在，或模板是否采用了其他真实参考文献机制。
- 正文引用标记（例如 `\cite{key}`）是否能对应到真实参考文献。
- 中文论文 caption、表题、摘要语言保持中文；英文论文保持英文。
- 选定的模板入口是否保留所选比赛模板的必要封面、摘要、编号、页眉页脚或提交格式。
- 不要把模板结构误删成普通空白文档。


### Step 7: 编译

```powershell
$runtime = if (Test-Path -LiteralPath '.codex/runtime.local.json') {
  Get-Content -Raw -Encoding UTF8 -LiteralPath '.codex/runtime.local.json' | ConvertFrom-Json
} else { @{} }
$xelatex = if ($runtime.xelatex) { $runtime.xelatex } else { (Get-Command xelatex -ErrorAction Stop).Source }
New-Item -ItemType Directory -Force -Path 'paper/build' | Out-Null
& $xelatex -interaction=nonstopmode -halt-on-error -jobname=final -output-directory='paper/build' 'paper/main.tex'
if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX first compilation failed' }
& $xelatex -interaction=nonstopmode -halt-on-error -jobname=final -output-directory='paper/build' 'paper/main.tex'
if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX second compilation failed' }
```

优先读取 `.codex/runtime.local.json` 的 `xelatex` 字段，未配置时再从 PATH 解析；先执行 `--version`，再实际编译并记录绝对路径、版本、退出码和 `paper/build/final.pdf` 哈希。只有 doctor 的 `paper_latex=VERIFIED` 才能进入本步骤。

编译失败必须修复语法、路径、图片引用或模板问题后重跑。编译通过后确认输出 PDF 非空。

### Step 8: PDF 视觉检查

如果模型有视觉能力，必须把编译后的 PDF 每页导出为 PNG 并逐页查看。这个步骤用于发现纯文本扫描和编译器无法发现的版式错误。

先运行 `doctor/scripts/check_environment.py --output reports/environment-check.json`。只使用其中通过真实转换测试且状态为 `VERIFIED` 的 PDF 栅格工具；路径存在但最小调用失败的工具不得使用。Windows PowerShell 示例：

```powershell
$environment = Get-Content -Raw -Encoding UTF8 -LiteralPath 'reports/environment-check.json' | ConvertFrom-Json
$raster = $environment.tools | Where-Object { $_.name -eq 'pdftoppm' -and $_.status -eq 'VERIFIED' } | Select-Object -First 1
if (-not $raster) { throw 'no verified PDF rasterizer' }
New-Item -ItemType Directory -Force -Path '_tmp/pdf-pages' | Out-Null
& $raster.path -png -r 160 $OUTPUT_PDF '_tmp/pdf-pages/page'
if ($LASTEXITCODE -ne 0) { throw 'PDF rasterization failed' }
```

导出后逐页检查：

- 页面是否空白、缺页、页数异常或页面尺寸异常。
- 标题、摘要、正文、页眉页脚、页码是否被裁切或位置明显错误。
- 表格是否超出页边距，单元格文字是否重叠、溢出、被截断。
- 图片、图题、表题、公式、编号是否与正文重叠。
- 公式是否越界，长公式是否压到页边距或下一段文字。
- 列表、段落、脚注、参考文献是否出现异常大空白、重叠或孤立残行。
- 中文/英文/数学符号字体是否明显缺字、乱码或 fallback 异常。
- 封面、摘要页、目录、附录等模板关键页面是否保留比赛要求的视觉结构。
- CUMCM 电子版第一页是否确为摘要，摘要是否恰好一页，是否误含目录、承诺书或编号页。
- 图中文字在最终排版尺寸下是否清晰，栅格图是否达到项目质量阈值，矢量图字体是否嵌入且无缺字。

如果是模板转换或已有参考 PDF 的项目，还应将不同引擎的 PDF 都逐页导出 PNG，按页对比版式差异；页数或页面尺寸不一致必须记录为硬错误或明确说明原因。

如果模型没有视觉能力，必须在 `reports/VERIFY_REPORT.md` 中明确写出“未执行视觉检查”的原因，并至少完成 PDF 非空、页数、页面尺寸等可程序化检查。

### Step 9: 写验收报告

创建 `reports/VERIFY_REPORT.md`：

```markdown
# 验证和验收报告

## 结论
PASS / FAIL

## 检查项
| 检查项 | 结果 | 说明 |
| --- | --- | --- |

## 章节结构

## 图表引用

## 数值一致性

## 代码证据复验

## 文本质量门禁

## 编译

## PDF 视觉检查

## 仍需处理的问题

## 完整学习交付清单
```

只有当代码证据复验通过、硬错误都修复、文本门禁通过、核心图表都引用、数值一致、XeLaTeX 编译通过且视觉检查通过时，才写 `PASS`。通过后把 `main.tex`、全部章节、参考文献源、已引用图的导出物与图源、`paper/build/final.pdf`、代码、结果和报告复制到独立的 `deliverables/<项目名>/`，并生成根目录 `README.md`、`MANIFEST.md` 与 `REPRODUCE.md`；不得把缓存、临时渲染页、`.aux`、`.log`、`.out`、`.toc`、`.fls`、`.fdb_latexmk`、虚拟环境或中间草稿混入交付包。

验收为 `PASS` 后，交付最终 PDF、论文源文件、完整代码与测试、依赖记录、运行日志、结果数据、图表及源数据、阶段报告和复现清单，并明确区分 `preview.pdf` 与最终文件。若为 `FAIL`，不得把当前 PDF 标记为最终版。

## 硬错误标准

以下问题必须判定 `FAIL`：

- 缺少 `main.tex` 或核心正文。
- 论文入口引用的章节文件不存在。
- LaTeX 入口缺少对应的 `\input` / `\include`。
- 正文章节缺少一级标题，或 `\section{...}` 标题结构明显错误。
- 章节顺序明显错误或重复。
- 正文仍有占位符。
- 正文泄露内部工作流文件名。
- 缺少 `reports/QUALITY_SCORECARD.md`、`code/main.py`、必要测试、依赖版本记录、结果数据、图表源数据或复现入口，导致成果不完整。
- 引用的图片不存在。
- 关键数值与结果记录冲突。
- 未找到已确认解释器、final 轻量入口未成功运行、关键 import 不存在或正式结果无法关联到 G3/final 审计证据。
- Mock、模拟数据、缓存或手工填写的结果被冒充为正式运行结果。
- 直接参赛模式下：用户明确指定的当年规则未核验或所要求的外部合规检查失败。
- 编译器可用但论文编译失败。
- 编译后的 PDF 为空、缺页、页数异常或页面尺寸异常且无法解释。
- 视觉检查发现正文、表格、图片、公式、页眉页脚、页码等关键元素重叠、裁切、越界或乱码。

## 警告标准

以下问题可判定为 `WARN`，但应尽量修复：

- 未引用的备用图片。
- 某章节过短或明显不均衡。
- caption 偏长。
- 参考文献偏少。
- 图表后解释文字不足。
- 代码完整复现耗时过长，但 G3 正式运行证据、产物哈希和 final 小样本重放均已通过。
