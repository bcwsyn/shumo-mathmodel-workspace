# 最终学习版验收报告

## 结论

**PASS（学习复现模式）**。用户于 2026-08-08 预先授权 G0-G7 连续执行；代码、结果、论文源文件、预览版与最终 PDF 已完成闭环复验。本结论不构成真实竞赛提交或当年规则合规声明。

## 检查项

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 题面归档 | PASS | `inputs/B题.pdf`，SHA-256 `F54529DD15D729B046E248EA41033B4F66EF68333BE2BEE912B0C54EAFD227AB` |
| 最终代码审计 | VERIFIED | `reports/code-audit/final/audit.json`；正式与冒烟入口均成功 |
| 代码质量 | PASS | Ruff 通过；Pytest 8/8 通过；正常、边界和失败输入均有测试 |
| 文本质量门禁 | PASS | `writing_check.py` 实际运行通过 |
| 数值一致性 | PASS | 论文关键值与 `results/g3_summary.json`、`reports/PAPER_NUMBER_CHECK.md` 一致 |
| 图表引用 | PASS | 四张数据图均存在并在对应章节引用；两张 DrawIO 源图未冒充已导出图件 |
| Typst 编译 | PASS | Typst 0.15.1，使用 `--root .` 成功编译 |
| PDF 视觉检查 | PASS | Poppler 150 dpi 渲染 9 页逐页检查，无裁切、重叠、缺字或乱码 |

## 关键修复记录

G7 初检时发现问题三报废分支漏计失败后重新购置上游投入。已回退 G3 修正更新成本方程、更新测试和数值，并重跑 G3/final 审计。修正后问题三最佳候选由旧结论改为“半成品失败后拆解、成品不检、售后拆解”，期望净收益为 **60.222222 元**。问题四已补充每节点样本量 100/500 的 Jeffreys 后验数值情景，不再仅停留于框架描述。

## 数值一致性

- 问题一：22 件全合格的 90% 单侧上界为 9.9372%；5%/15% 情景平均检测数为 103.51/130.60。
- 问题二：六种情形推荐策略与净收益均来自正式结果；情形 1 为 18.111111 元。
- 问题三：修正后最佳候选为 60.222222 元，最差候选为 37.119342 元。
- 问题四：问题三策略在每节点 n=100/500 时的逐次最优频率为 92.9%/100%，后验均值为 59.048357/59.973857 元。

## 编译与视觉检查

- 最终文件：`paper/final_learning.pdf`
- 页数与尺寸：9 页，A4，342820 字节
- SHA-256：`6791C69CB3EA5C3F639FFFDCC3F24EFAE97BB764BAC7BFEDD4E113EB8260E0A9`
- 最终 PDF 的 9 张 150 dpi 页面图与已逐页目检的 G7 预览逐页哈希完全一致。

## 非阻断警告

1. 文本门禁未识别 `#super("[n]")` 手工上标引文格式，提示未检测到引文；最终 PDF 中 [1]-[3] 与参考文献逐项对应。
2. 本机未找到 DrawIO CLI，`fig_roadmap.drawio` 与 `fig_decision_flow.drawio` 仅保留可编辑源文件，导出状态为 `UNVERIFIED`；论文未引用其 PDF，不影响最终内容。
3. `scikit-learn` 与 `PyYAML` 不属于本题实际 imports，环境探测中未安装不影响代码或论文就绪状态。

## 完整学习交付清单

- 题面：`inputs/B题.pdf`；
- 规划与记录：`plan.md`、`todo.md`；
- 论文：`paper/main.typ`、`paper/sections/`、`paper/references.typ`、`paper/preview.pdf`、`paper/final_learning.pdf`；
- 代码：`code/main.py`、`code/audit_manifest.json`、`tests/test_main.py`、`requirements.txt`；
- 结果与图表：`results/`、`figures/`；
- 报告与审计：`reports/ANALYSIS_MODELING_REPORT.md`、`RESULTS_REPORT.md`、`DRAWIO_REPORT.md`、`PAPER_NUMBER_CHECK.md`、`reports/code-audit/`；
- 复现说明：`README.md` 与 `.codex/runtime.local.json`。
