# 论文初稿生成与核对报告

## 输出

- `paper/中小微企业信贷决策论文初稿.docx`
- `paper/preview.pdf`
- `paper/OUTLINE.md`
- `paper/build_paper.py`

## 内容结构

论文共16页，包括封面、摘要、目录、问题分析、数据审计与假设、信用风险模型、三个子问题、SHAP解释、敏感性、模型评价、结论、复现参数和8条参考文献。正文嵌入7张正式数据图和12张固定宽度表，包含11个编号公式。

## 数值核对

| 论文数值 | 结果来源 | 状态 |
| --- | --- | --- |
| 融合模型 Macro-F1 0.6086、二次 Kappa 0.6666 | `results/summary.json` | 一致 |
| CRI 对历史违约 AUC 0.9066 | `results/summary.json` | 一致 |
| 问题一 5000 万元、50 家、D 级 0 家 | `problem1_strategy.csv` | 一致 |
| 问题二 101 家、1亿元、风险130.00万元、效益142.90万元 | `problem2_risk_return_curve.csv` | 一致 |
| 问题三轻/中/重 132.46/114.75/90.99 万元 | `problem3_scenarios.csv` | 一致 |
| 1.5倍压力最坏效益 69.96 万元 | `problem3_stress_sensitivity.csv` | 一致 |

## 文档与视觉证据

- 标准 DOCX 渲染器因 LibreOffice 缺失未运行成功，随后使用本机 Microsoft Word COM 无界面导出 PDF。
- `paper/preview.pdf` 签名为 `%PDF`，共16页，最终 SHA-256 为 `C902B5054A23A14487A37D89496460B5941F052132DCDA754DFD32C74ED72A27`。
- 12张表经 `table_geometry.py` 审计，固定几何全部一致。
- 图片替代文本审计 high/medium/low 均为0。
- 16页均以144 DPI导出为1191×1684 PNG并逐页检查。最后一次修订只改变第6、9、11页；三页已再次按原始分辨率确认。

## 文本质量复核

正文使用具体数据、公式和适用边界展开，没有宣传性结论、模糊专家归因、聊天语气或通用积极结尾。风险损失尺度没有写成已校准违约概率，压力系数和1.30%风险上限均明确标为决策假设。

## 工具限制

当前机器未发现 Typst 和 Draw.io 可执行程序，工作区配置中的 Draw.io 路径属于不存在的旧用户目录。按环境规则未静默安装系统工具。因此主论文交付改为经过 Word 实际导出和逐页检查的 DOCX/PDF；技术路线图保留可编辑 `.drawio` 源，未伪造其 PDF 导出状态。
