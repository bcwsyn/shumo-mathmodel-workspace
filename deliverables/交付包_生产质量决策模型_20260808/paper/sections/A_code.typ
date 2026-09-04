#v(1.1em)

完整、可运行实现位于项目的 `code/main.py`，其中包含精确置信界、SPRT、问题二状态报酬方程、问题三候选策略递推以及图表生成入口。复现实验使用：

```powershell
python code/main.py --full
```

该入口生成问题一运行特性、问题二敏感性与问题三候选策略比较所需的结果数据和图表；测试入口为 `python -m pytest -q tests`。
