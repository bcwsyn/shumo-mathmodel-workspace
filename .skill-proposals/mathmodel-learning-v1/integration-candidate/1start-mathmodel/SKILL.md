---
name: 1start-mathmodel
description: "数学建模竞赛工作流入口。用于启动带人工审批门的完整建模流程：生成 plan.md 和 todo.md，在题意、建模方案、代码结果、图表、论文草稿和预览 PDF 等节点等待用户明确批准，再调用后续 skills。"
---

# 数学建模工作流

本 skill 是数学建模竞赛项目的总控入口。它不替代后续阶段 skill，而是负责启动流程、询问偏好、记录决策、生成计划，并按顺序调用各阶段 skill。

## 人工审批模式

启动时必须读取 `../_references/approval_gates.md` 并执行其中的审批协议。默认启用人工审批；只有用户明确要求连续执行且不需要中途确认时，才能关闭。

总控只调度已获批准的下一阶段。任一阶段返回 `WAITING_FOR_APPROVAL` 后立即停止，不得在同一轮继续调用下游 Skill。

## 数学建模规范参考

如需领域判断，读取 `../_references/math_modeling_norms.md`。该文件只提供数学建模基本规范和防错知识，不改变本 skill 的阶段顺序和产出约定。

## 学习知识库（可选）

若项目存在 `knowledge/mathmodel/approved/`，可在 G1 使用 `mathmodel-learning` 检索用户已批准的论文卡和方法卡。必须先由 `2analysis-modeling` 独立完成当前赛题的 G0 题意与数据分析，再检索历史经验，防止被优秀论文锚定。

- 只有 `approved/` 内容可作为 G1 参考；`drafts/` 和原始资料不得自动进入建模方案。
- 学习库只提供候选思路、适用条件和风险，不替用户确定最终模型。
- 检索结果随 G1 建模方案一起审批，不增加或跳过任何 G0–G7 审批门。
- 未安装学习 Skill、知识库为空或没有相关卡片时，直接跳过，不阻塞标准工作流。

## 必须产出

在当前工作目录中创建或更新以下文件：

- `plan.md`：整体流程方案、建模方向、阶段顺序、预期产物和风险控制。
- `todo.md`：具体待办事项列表，记录每个阶段的任务和状态。

## 工作流

### 1. 询问用户偏好 AskUserQuestions

在规划前，只询问会实质影响流程的问题。问题要少而关键。

优先询问（按重要性排序）：

1. **排版引擎**：Typst 还是 LaTeX？— 决定 5writing 使用哪套模板和编译命令。两套引擎均覆盖全部模板（14 中 + 3 英）。Typst 使用 `typst` 命令编译；LaTeX 使用 `xelatex` 命令编译（需跑两遍解决交叉引用）。
2. **竞赛类型**：国赛/华为杯/华中杯/MCM/...— 决定模板选择，见 5writing 的模板族清单。
3. **论文语言**：中文/英文 — MCM/ICM/COMAP 强制英文，其他默认中文。
4. **子问题数量是否已知**：影响章节文件生成数量。若未知，由 2analysis-modeling 阶段根据题面确定。
5. **审批方式**：默认逐阶段审批；记录用户是否明确要求合并或取消某个审批点。

将用户的选择记录到 `plan.md` 的"方案"小节中。


### 2. 制定方案

按以下结构编写 `plan.md`：

```markdown
# 方案

要依次调用这些 skill，按照里面要求完成任务。

用户偏好：
- 排版引擎：<Typst / LaTeX>
- 竞赛类型：<国赛 / 华为杯 / MCM / ...>
- 论文语言：<中文 / 英文>
- 子问题数量：<已知 N 个 / 待分析确定>

workflow:
   gate      skills
G0. 材料与题意确认 - `2analysis-modeling`
G1. 建模方案确认 - `2analysis-modeling`（可选调用 `mathmodel-learning` 检索已批准经验）
G2. 最小代码验证确认 - `3coding-visual`
G3. 完整结果与数据图确认 - `3coding-visual`
G4. 非数据图示确认或批准跳过 - `4drawio`
G5. 论文大纲确认 - `5writing`
G6. 论文正文源文件确认 - `5writing`
G7. 预览 PDF 确认 - `5writing`
最终验收与最终 PDF - `6verity`（仅在 G7 批准后）
```

在 `plan.md` 中同时加入 `approval_gates.md` 规定的审批状态表。初始状态全部为 `PENDING`。

## 项目目录结构

各阶段按此骨架创建和填充文件：

```text
.
├── plan.md                      # 1: 本文件
├── todo.md                      # 1: 待办事项
├── reports/                     # 各阶段文档报告
│   ├── ANALYSIS_MODELING_REPORT.md  # 1: 赛题分析-建模报告（2analysis-modeling）
│   ├── RESULTS_REPORT.md            # 2: 结果报告（3coding-visual）
│   ├── DRAWIO_REPORT.md             # 3: 非数据图说明（4drawio）
│   ├── VERIFY_REPORT.md             # 5: 验收报告（6verity）
├── code/                        # 2: 代码（3coding-visual）
│   ├── problem1.py
│   ├── problem2.py
│   ├── problem3.py               # 问题的数量应该更具题目动态调整
│   ├── ... 
│   └── utils.py
├── results/                     # 2: 结果记录（3coding-visual）
├── figures/                     # 2+3: 所有图表（3coding-visual + 4drawio）
│   ├── *.pdf                    #     数据图 + 非数据图 PDF
│   ├── *.drawio                 #     非数据图源文件
├── paper/                       # 4: 论文（5writing）
│   ├── main.typ / main.tex      #     论文主文件（按用户选择的引擎）
│   └── sections/                #     各节文件（.typ 或 .tex）
```

方案必须明确每个阶段由哪个下游 skill 负责，以及该阶段应产出什么文件。

### 3. 生成待办

将 `todo.md` 写成执行与审批分离的 checklist，格式如下：

```markdown
# 待办事项

- [ ] G0 执行：材料与题意检查 - `2analysis-modeling`
- [ ] G0 审批：用户确认题意
- [ ] G1 执行：建模方案 - `2analysis-modeling`
- [ ] G1 审批：用户批准最终建模方案
- [ ] G2 执行：最小代码验证 - `3coding-visual`
- [ ] G2 审批：用户确认模型可行
- [ ] G3 执行：完整实验和数据图 - `3coding-visual`
- [ ] G3 审批：用户确认结果
- [ ] G4 执行：非数据图示 - `4drawio`
- [ ] G4 审批：用户确认图示或批准跳过
- [ ] G5 执行：论文大纲 - `5writing`
- [ ] G5 审批：用户确认结构
- [ ] G6 执行：论文正文草稿 - `5writing`
- [ ] G6 审批：用户确认内容
- [ ] G7 执行：预览 PDF - `5writing`
- [ ] G7 审批：用户确认版式
- [ ] 最终验收与最终 PDF - `6verity`
```

每完成一个阶段，都要更新 `todo.md` 中对应任务的状态。

### 4. 按批准状态执行阶段

每次只执行审批表中第一个“前置审批已通过且自身未完成”的阶段。执行完提交审批并停止。用户批准后更新 `plan.md` 和 `todo.md`，下一轮才进入后续阶段。

禁止在 G1 批准前写正式求解代码；禁止在 G3 批准前写论文；禁止在 G6 批准前生成预览 PDF；禁止在 G7 批准前调用 `6verity` 生成最终 PDF。

按以下顺序调用下游 skills：

| 阶段 | Skill | 作用 | 主要产物 |
| --- | --- | --- | --- |
| G0 材料与题意 | `2analysis-modeling` | 盘点附件、理解题意、识别歧义和子问题。 | 建模报告的材料与题意部分 |
| G1 建模方案 | `2analysis-modeling` | 比较候选模型，确定假设、公式、约束、算法和验证方案。 | `ANALYSIS_MODELING_REPORT.md` |
| G2 最小验证 | `3coding-visual` | 建立最小代码、基线或可行解，尽早暴露错误。 | 初步代码与验证结果 |
| G3 完整结果 | `3coding-visual` | 完成正式实验、稳健性分析、结果表和数据图。 | `code/`, `results/`, `RESULTS_REPORT.md`, 数据图 |
| G4 非数据图 | `4drawio` | 按需绘制流程、架构和概念图；可批准跳过。 | `*.drawio`, 图示 PDF, `DRAWIO_REPORT.md` |
| G5 论文大纲 | `5writing` | 确认章节、论点、公式与图表位置。 | 大纲和图表规划 |
| G6 正文草稿 | `5writing` | 完成论文源文件并核对引用和数值。 | `paper/` 源文件 |
| G7 预览 PDF | `5writing` | 编译并逐页检查供用户确认的预览版。 | `paper/preview.pdf` |
| 最终验收 | `6verity` | 仅在 G7 批准后验收并生成最终提交版。 | `VERIFY_REPORT.md`, 最终 PDF |

## 阶段边界

- `3coding-visual` 负责生成所有依赖计算结果或实验输出的数据图表。
- `4drawio` 只负责概念图、算法流程图、架构图、路线图等非数据型图示。
- 不要让 `4drawio` 重复绘制 `3coding-visual` 已经生成的统计图或数据图。
- `5writing` 负责决定图表在论文中的位置，并按所选引擎写入图表代码：
  - Typst：`#figure(image("../../figures/xxx.pdf", width: 85%), caption: [...])`
  - LaTeX：`\begin{figure}[H]\centering\includegraphics[width=0.85\textwidth]{../../figures/xxx.pdf}\caption{...}\label{fig:xxx}\end{figure}`
- 不要让 `5writing` 编造数值结论。论文中的数值必须来自 `RESULTS_REPORT.md`、结果表或已生成图表的数据。
