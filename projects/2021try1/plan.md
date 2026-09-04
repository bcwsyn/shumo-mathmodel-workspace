# 方案

要依次调用这些 skill，按照其中要求完成 2021 年高教社杯全国大学生数学建模竞赛 A 题“FAST 主动反射面的形状调节”。默认启用逐阶段人工审批；任何阶段进入 `WAITING_FOR_APPROVAL` 后停止，不提前制作下游正式产物。

## 用户偏好

- 排版引擎：Typst（项目固定）
- 竞赛类型：全国大学生数学建模竞赛（CUMCM，2021 年 A 题）
- 论文语言：中文
- 子问题数量：3 个（已由题面确认）
- 审批方式：G0–G7 逐阶段审批
- 原始材料位置：`C:\Users\lw195\Desktop\A`
- 本机项目解释器：`.codex/runtime.local.json` 中记录的绝对路径

## 总体路线

```text
题面与附件核验
  -> 坐标、拓扑和促动器几何审计
  -> 理想抛物面候选定义与歧义消解
  -> 节点/促动器约束优化
  -> 反射光线与接收比计算
  -> 稳健性、灵敏度和误差分析
  -> 数据图与非数据图
  -> Typst 论文
  -> 代码复验和最终 PDF
```

本路线目前只用于安排工作。理想抛物面参数化、节点运动口径、目标函数和接收比离散方式须在 G1 比较后由用户批准，G0 不把候选方案写成最终模型。

## Workflow

| 阶段 | Skill | 本阶段职责 | 主要产物 |
| --- | --- | --- | --- |
| G0 材料与题意确认 | `2analysis-modeling` | 盘点题面和附件，核验字段、规模、拓扑、歧义和子问题依赖 | `reports/ANALYSIS_MODELING_REPORT.md` 的 G0 部分、`reports/CUMCM_COMPLIANCE.md` |
| G1 建模方案确认 | `2analysis-modeling` | 比较候选模型，确定假设、公式、约束、算法与校验计划；可选检索已批准知识库 | 完整 `reports/ANALYSIS_MODELING_REPORT.md` |
| G2 最小代码验证确认 | `3coding-visual` + `verify-generated-code` | 建立最小可行代码与基线结果，核验解释器、依赖、入口和产物 | `code/` 初版、`code/audit_manifest.json`、G2 审计记录 |
| G3 完整结果与数据图确认 | `3coding-visual` + `verify-generated-code` | 完成正式实验、约束回代、稳健性分析、结果表和数据图 | `code/`、`results/`、`figures/`、`reports/RESULTS_REPORT.md`、G3 审计记录 |
| G4 非数据图示确认或批准跳过 | `4drawio` | 绘制技术路线、模型结构或算法流程等非数据图 | `figures/*.drawio`、图示 PDF、`reports/DRAWIO_REPORT.md`，或经批准跳过 |
| G5 论文大纲确认 | `5writing` | 确认章节论点、公式与图表放置 | 论文大纲和图表规划 |
| G6 论文正文源文件确认 | `5writing` | 编写并核对完整 Typst 正文 | `paper/main.typ`、`paper/sections/` |
| G7 预览 PDF 确认 | `5writing` | 编译并逐页检查预览版 | `paper/preview.pdf` |
| 最终验收与最终 PDF | `6verity` + `verify-generated-code` | 仅在 G7 批准后复验代码入口、数值和版式 | `reports/VERIFY_REPORT.md`、最终审计记录、最终 PDF |

## 风险控制

- 原始文件只读使用，不覆盖 CSV、XLSX 或题面 PDF。
- CSV 与同名 XLSX 是重复载体；后续固定一个权威输入版本并以哈希防止混用。
- 300 m 口径、焦面交点符号、理想抛物面自由参数、节点运动方向和接收信号权重均在 G1 前明确。
- 所有 6525 条主索边逐条检查长度相对变化不超过 0.07%，所有促动器伸缩量逐条检查在 `[-0.6, 0.6] m`。
- 启发式或非凸优化不宣称全局最优；使用精确/局部基线、多起点、网格或参数敏感性作对照。
- 接收比用几何光学射线追踪并进行网格/采样收敛检查；基准球面与调节面采用完全一致的计量口径。
- 论文中的数值只引用正式结果文件和图表数据；所有程序入口和产物由真实解释器复验。
- 2021 当年格式规则未完整取得的条款保持 `UNVERIFIED`，不以 2025/2026 规则倒推 2021。

## 审批状态

| 审批点 | 状态 | 批准依据 | 日期/备注 |
| --- | --- | --- | --- |
| G0 | APPROVED | 用户回复“批准 G0，继续” | 2026-07-23 |
| G1 | APPROVED | 用户回复“批准 G1，继续” | 2026-07-23 |
| G2 | APPROVED | 用户回复“批准 G2，继续” | 2026-07-23 |
| G3 | APPROVED | 用户回复“批准 G3，继续” | 2026-07-23 |
| G4 | APPROVED | 用户回复“批准 G4，继续” | 2026-07-23 |
| G5 | APPROVED | 用户回复“批准 G5，继续” | 2026-07-23 |
| G6 | APPROVED | 用户回复“批准 G6，继续” | 2026-07-23 |
| G7 | APPROVED | 用户回复“批准 G7，继续” | 2026-07-23 |
| 最终验收 | COMPLETE | `reports/VERIFY_REPORT.md` 结论 PASS | 2026-07-23 |
