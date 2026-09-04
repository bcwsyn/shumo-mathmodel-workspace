# 验证和验收报告

## 结论

**PASS**

项目已通过代码证据复验、正式产物哈希核对、论文文本门禁、章节与图表检查、关键数值一致性检查、Typst 编译和最终 PDF 全页视觉检查，可作为完整的数学建模学习复现成果交付。

本项目处于学习复现模式，仅套用竞赛论文的中文写作与版式习惯，不声明满足真实参赛的匿名、页数、文件大小、AI 披露或支撑材料规则。

## 检查项

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| G7 前置审批 | PASS | `plan.md` 已记录用户回复“批准 G7，继续” |
| Python 运行环境 | PASS | 项目解释器为 Python 3.12.13 |
| final 代码审计 | PASS | `reports/code-audit/final/audit.json` 状态为 `VERIFIED` |
| Ruff | PASS | 退出码 0，`All checks passed!` |
| pytest | PASS | 12 项测试全部通过 |
| final 轻量入口 | PASS | `g3-replay` 与 `g3-artifact-check` 均退出码 0 |
| 正式产物哈希 | PASS | 与 G3 运行清单一致 |
| 文本质量门禁 | PASS | 无占位符、内部路径泄露或缺失章节 |
| 图表与引用 | PASS | 论文引用的 10 幅图均存在且位置、图题和正文解释匹配 |
| 关键数值一致性 | PASS | 摘要、正文、结论与正式 JSON/结果报告一致 |
| 参考文献 | PASS | 5 条文献均在正文按编号引用 |
| Typst 编译 | PASS | Typst 0.15.1，退出码 0 |
| PDF 程序化检查 | PASS | 21 页、A4、15,140,262 字节，21 页均有文本 |
| PDF 视觉检查 | PASS | 全部 21 页逐页检查，无裁切、重叠、乱码或缺页 |
| 完整交付 | PASS | 论文、代码、测试、结果、图表、日志和报告齐全 |

## 章节结构

`paper/main.typ` 依次引入问题重述、问题分析、模型假设、符号说明、问题一、问题二、问题三、敏感性分析和模型评价九个正文章节，并通过附录入口引入核心代码。章节文件均存在，一级标题和顺序正确，无重复引用或未完成占位内容。

## 图表引用

正文使用总体技术路线图、四层传热结构图以及 8 幅正式数据图，共 10 幅。引用路径均可解析，图题、编号、章节语义和解释文字一致。`figures/g2_skin_temperature_diagnostic.pdf` 是保留的 G2 基线诊断图，未进入正式论文，属于有意保留的备用证据。

## 数值一致性

论文关键数值与 `results/key_numbers.json`、`results/formal_results.json` 和 `reports/RESULTS_REPORT.md` 一致：

- \(h_o=120.991689\) W/(m²·K)，\(h_b=8.364912\) W/(m²·K)，RMSE 0.002627°C；
- 问题二名义最小第二层厚度 17.6 mm，最高皮肤温度 44.07684°C，超 44°C 时长 293.5 s；
- 问题三名义最优为 (19.3, 6.4) mm，总厚度 25.7 mm，最高皮肤温度 44.78600°C，超阈时长 293.67183 s；
- 问题三联合 10% 不利情景稳健设计为 (23.5, 6.4) mm，最高皮肤温度 44.93951°C，超阈时长 294.46253 s；
- 问题二在同一联合不利情景下于题设厚度范围内无稳健可行解。

## 代码证据复验

final 审计使用 `.codex/runtime.local.json` 指定的绝对解释器：

`C:\hiyan-codex\shumo\CUMCM2018A_HighTemperatureClothing\.venv\Scripts\python.exe`

审计结果：

- Python 文件、顶层 imports、静态风险和外部接口均为 `VERIFIED`；
- Ruff 0.16.0 通过；
- pytest 9.1.1 收集并通过 12 项测试；
- `g3-replay` 用时约 1.80 s；
- `g3-artifact-check` 用时约 1.64 s；
- 正式完整实验没有重复执行；其原始运行耗时约 483 s，G3 日志、运行清单和产物仍存在，final 小样本重放及正式产物哈希核对均通过。

关键正式产物 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `results/formal_results.json` | `20FD422DC5339EEE1E6BDE86198A296BD5F1485FD6047191C93CACC78639B9C3` |
| `results/key_numbers.json` | `043A847E27245DF4C6B9AB7B391942C9B3B12A4CD267D0BD7670FAB57DE97206` |
| `results/problem1.xlsx` | `7405804FEE609513FB7085484D588F3B8FA87FD3EB66C0977402FD2D94D80524` |
| `code/main.py` | `3BE6CA41EC5E0DEE94EF88050C4C769D2DC039713B4FB666A9D2FA8AC22372DF` |
| `code/g3.py` | `17A2870D83F00EFDE71EDE8707C43FDAF393D8134FABBDD852EC69B0030346A4` |

## 文本质量门禁

`writing_check.py` 返回 `PASS`。问题重述和模型假设章节较短、问题一存在三级标题，属于结构性警告而非缺失；论文仍保持完整论证。扫描未发现 `TODO`、`PLACEHOLDER`、待补充、示例数据、内部结果路径或临时目录泄露。

## 编译

- 编译器：Typst 0.15.1（9dfd3a08）
- 命令：`typst compile --root . paper/main.typ paper/final-learning-version.pdf`
- 退出码：0
- 最终文件：`paper/final-learning-version.pdf`
- 文件大小：15,140,262 字节
- SHA-256：`FBE21D65C4DA33D4C7E66A1140D4EEAE6A131F86BBCC88F79CEC7C3A20989C7F`

G7 预览文件 `paper/preview.pdf` 继续保留，其 SHA-256 为 `6DB7DE63C89C86EC98E98692370C81770D4E6C9136D273B38962D1953C7E18EC`。最终学习版没有覆盖预览版。

## PDF 视觉检查

环境探测确认 Typst、DrawIO 和 Poppler `pdftoppm` 的真实最小调用均为 `VERIFIED`。环境总状态中的 `UNVERIFIED` 仅来自本项目未使用的 scikit-learn、PyYAML、mutool 和 ImageMagick，不影响当前编译与栅格验收。

最终 PDF 使用 Poppler 按 160 DPI 导出全部 21 页并逐页查看：

- 封面摘要恰好一页，目录完整收于一页；
- 中文、英文、数学符号和单位无缺字或乱码；
- 表格、公式、图题和页码均未越界、裁切或重叠；
- 10 幅图在最终排版尺寸下可辨识；
- 参考文献和两页附录代码均完整；
- 页码 1–21 连续，页面规格统一为 A4。

PDF 文本复查确认 21 页均可提取非空文本，未检出 Unicode 替换字符或 NUL。`pypdf` 对一幅大型嵌入图的 XForm 解压给出递归限制警告，但文本抽取继续完成，Poppler 全页渲染和视觉检查正常，不构成版式缺陷。

## 仍需处理的问题

无阻止交付的硬错误。

保留的限制是研究结论本身已在论文中披露的适用边界：换热系数来自单一实验装置，跨 65–80°C 工况使用依赖敏感性分析而非独立外部实验；稳健方案只对本文定义的不利参数集成立。

## 完整学习交付清单

详见 `reports/DELIVERY_MANIFEST.md` 和项目根目录 `README.md`。复现命令见 `REPRODUCE.md`。

