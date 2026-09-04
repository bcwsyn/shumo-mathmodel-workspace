# FAST 主动反射面模型支撑材料说明

## 运行环境

- Python：3.13.0
- NumPy：2.2.3
- SciPy：1.17.1
- Pandas：2.2.3
- Matplotlib：3.10.1
- CVXPY：1.8.1
- OSQP：1.1.1
- Clarabel：0.11.1

## 目录

- `code/`：数据几何、三个子问题、正式优化、射线追踪和绘图入口。
- `tests/`：真实附件正常路径、边界和失败输入测试。

正式提交支撑材料时，还应加入题目附件、`result.xlsx`、正式结果 CSV、图表 PDF 和运行清单。支撑材料及文档属性中不得出现参赛者、学校或赛区身份信息。

## 正式入口

在支撑材料根目录执行：

```powershell
python code/g3_run.py --data-dir data/raw --output-dir results --figures-dir figures
```

质量检查：

```powershell
python -m ruff check code tests
python -m pytest -q tests
```
