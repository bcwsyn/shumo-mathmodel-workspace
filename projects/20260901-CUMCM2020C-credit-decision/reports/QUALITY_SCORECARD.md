# 质量证据表

| 维度 | 当前证据 | 未关闭缺陷 | 状态 |
| --- | --- | --- | --- |
| 题意与数据 | 四输入 SHA-256；企业数、发票行数、日期、重复、负数、状态和金额恒等式审计；附件 2 方向按字段识别；正式管线得到 123/302 家完整特征 | 无已知阻断项 | G0 COMPLETE |
| 模型与数学 | 32 维经营特征、Logistic/XGBoost 融合、单调流失响应、风险迁移、名义与 maximin MILP；LGD 和压力强度敏感性已求解 | 压力参数和 1.30% 风险上限为决策假设，论文必须明示 | G3 COMPLETE |
| 代码与实验 | Ruff 通过；Pytest 6/6；正式入口退出码 0；G3 证据审计 VERIFIED | 未做不同随机种子的全量重复训练 | G3 VERIFIED |
| 结论与论证 | 折外 Macro-F1 0.6086、二次加权 Kappa 0.6666；问题二选 101 家且预算守恒；问题三最坏效益 90.99 万元；均已写入论文并与结果表核对 | 无已知数值冲突 | G7 COMPLETE |
| 图表与排版 | 7 张 PDF 数据图及源 CSV；技术路线 `.drawio` 源；DOCX 含7图12表11式；16页 PDF 已逐页检查 | Draw.io PDF 未导出；Typst 不可用，均已登记为工具限制 | G7 VERIFIED |
| 复现与交付 | 独立 `.venv`、requirements、日志、结果哈希、final 代码审计、论文构建与 PDF 导出脚本、DOCX/PDF、验证报告和完整交付包已保存 | Typst 与 Draw.io 导出工具不可用；不影响 DOCX/PDF 初稿交付，但不得外推为相应工具链 PASS | FINAL VERIFIED WITH LIMITATIONS |
