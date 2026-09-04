# 生产质量决策模型：学习复现交付包

本文件夹汇总本次对话产生的、与“2024 CUMCM B 题：生产过程中的决策问题”相关的可交付成果。

## 目录

- `paper/`：Typst 论文源文件、预览版与最终学习版 PDF；
- `inputs/`：归档题面及其来源哈希；
- `code/`、`tests/`：可复现实验程序与测试；
- `results/`：程序生成的数值结果；
- `figures/`：论文图表及可编辑 DrawIO 技术路线图源文件；
- `reports/`：建模、实验、论文数值核对、最终验收与代码审计报告；
- `plan.md`、`todo.md`：审批流程与工作记录；
- `requirements.txt`：Python 依赖说明。

## 复现

在项目根目录执行：

使用 `.codex/runtime.local.json` 记录的 Python 与 Typst 绝对路径，在项目根目录执行：

```text
<python> code/main.py --full
<python> -m ruff check code tests
<python> -m pytest -q tests
<typst> compile --root . paper/main.typ paper/preview.pdf
```

最终验收状态和已知限制见 `reports/VERIFY_REPORT.md`。本包仅供数学建模学习与复现，不构成真实竞赛提交。
