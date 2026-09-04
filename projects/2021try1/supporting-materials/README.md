# FAST 主动反射面赛后教学复现支撑材料

## 内容

- `code/`：全部 Python 源程序和审计运行清单；
- `tests/`：正常、边界和失败输入测试；
- `results/`：正式结果 JSON、CSV 及题目要求的 `result.xlsx`；
- `figures/`：论文使用的数据图、流程图 PDF 与 DrawIO 源文件；
- `audit-summary.md`：不含本机绝对路径的最终代码审计摘要；
- `AI工具使用详情.pdf`：AI 使用目的、环节、审批和复核说明。

题目提供的原始附件未重复放入支撑材料。运行时将其置于项目 `data/raw/`，文件结构应与原赛题附件一致。

## 运行环境

- Python：3.13.0；
- NumPy：2.2.3；
- SciPy：1.17.1；
- pandas：2.2.3；
- Matplotlib：3.10.1；
- CVXPY：1.8.1；
- OSQP：1.1.1；
- Clarabel：0.11.1。

## 复现命令

在项目根目录中使用已安装上述依赖的 Python：

```powershell
python code/g2_smoke.py --data-dir data/raw --output results/g2_baseline.json --figure figures/g2_hardware_utilization.pdf
python code/g3_run.py --data-dir data/raw --output-dir results --figures-dir figures
python -m ruff check code tests
python -m pytest -q tests
```

正式入口最近一次实际运行耗时约 349 秒。最终审计状态为 `VERIFIED`，Ruff 通过，Pytest 为 9/9 通过。含本机绝对路径的原始审计文件不进入匿名提交包。

## 诚信说明

本材料是 2026 年对 2021 年赛题的赛后教学复现，使用了 OpenAI Codex。它不作为 2021 年竞赛期间由参赛队独立完成的原始作品。使用者若向课程或其他机构提交，应继续遵守接收方当时有效的诚信和披露要求。
