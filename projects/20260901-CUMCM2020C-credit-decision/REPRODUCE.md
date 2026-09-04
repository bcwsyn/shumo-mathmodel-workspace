# 复现说明

以下命令在项目根目录的 PowerShell 中执行。当前已验证环境为 Windows 11、Python 3.12.13，随机种子固定为 42。

## 1. 创建环境

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. 审计输入并运行实验

```powershell
.\.venv\Scripts\python.exe code\audit_inputs.py
.\.venv\Scripts\python.exe code\main.py --smoke
.\.venv\Scripts\python.exe code\main.py --run
```

`--run` 会重新生成 `results/` 中的策略与统计表，以及 `figures/` 中的 7 张数据图。在最终验收机器上，全量入口用时约 82.7 秒。核心结果摘要和生成物哈希位于 `results/summary.json`。

## 3. 运行测试与静态检查

```powershell
.\.venv\Scripts\python.exe -m ruff check code tests
.\.venv\Scripts\python.exe -m pytest -q tests
```

验收结果为 Ruff 通过，Pytest 6/6 通过；测试覆盖正常、边界和失败路径。

## 4. 重建论文

先确认模型结果已经生成，再执行：

```powershell
.\.venv\Scripts\python.exe paper\build_paper.py
powershell -ExecutionPolicy Bypass -File paper\export_pdf.ps1
```

第一条命令生成 `paper/中小微企业信贷决策论文初稿.docx`。第二条命令通过本机 Microsoft Word 的 COM 接口导出 `paper/preview.pdf`，要求已安装桌面版 Word。PDF 的二进制哈希可能因 Office 版本或导出元数据而变化，应以页数、A4 页面尺寸、正文内容和视觉检查为版式复现标准。

## 5. 结果解释边界

- 评级是主标签，违约记录仅用于外部核验与风险尺度映射；
- 问题二冻结问题一的特征与模型关系，不使用目标域标签重训；
- 压力情景、LGD 和 1.30% 风险上限属于决策假设；
- 如用于真实授信，应补充跨期样本、真实回收率与资金成本后重新校准。
