---
name: doctor
description: "检查基于 Typst 的数学建模工作流实际运行环境并提供安装向导。用于验证用户指定、VS Code 选定、项目 .venv 或系统 Python 的绝对路径、包导入，以及 Typst、DrawIO、PDF 栅格工具的真实最小调用；仅在用户明确要求环境检查或安装时执行，安装前必须再次获得批准。"
---

# 环境检查与安装向导

把“项目没有虚拟环境”和“电脑没有可用环境”分开。允许直接复用用户已有的外部 Python；只有用户需要隔离或复现时才建议创建项目 `.venv`。

## 解释器发现

按顺序查找并验证：

1. 用户明确提供的 Python 绝对路径。
2. `MATHMODEL_PYTHON`。
3. `.codex/runtime.local.json` 的 `python` 字段。
4. `.venv/Scripts/python.exe` 或 `.venv/bin/python`。
5. VS Code 中通过 `Python: Select Interpreter` 得到的 `sys.executable`。
6. PATH 中的 `python` 或 `python3`，仅作为待确认候选。

对候选执行 `import sys; print(sys.executable)`。候选不存在、拒绝运行或输出的解释器与请求不一致时，不得静默换用其他 Python。

## 确定性检查

使用选定解释器运行本 skill 的脚本：

```powershell
& "<python.exe>" "<skill-dir>/scripts/check_environment.py" --output "reports/environment-check.json"
```

脚本检查 Python、pip、numpy、scipy、pandas、matplotlib、scikit-learn、openpyxl、PyYAML，以及 typst、drawio、pdftoppm、mutool、magick。外部工具优先读取 `.codex/runtime.local.json` 中同名字段，再回退到 PATH。LaTeX 不属于本项目的就绪条件，不检查也不安装。

路径存在不等于工具可用。脚本必须实际导入 Python 包，并分别执行：最小 Typst 编译、最小 DrawIO PDF 导出、真实 PDF 到 PNG 转换。报告包含绝对路径、发现来源、退出码、版本或最小调用证据；任一工具只有在真实产物及文件签名均通过后才能标记为 `VERIFIED`。

固定包清单只覆盖工作流基线。代码阶段仍必须由 `verify-generated-code` 从实际 imports 检查额外依赖；不要声称 doctor 已覆盖“所有模型依赖”。

## 就绪判断

- 代码阶段最低要求：可运行的 Python，以及当前赛题实际 imports 所需的包。
- 论文阶段只要求 Typst；LaTeX 明确不进入本项目的环境就绪判断。
- DrawIO 仅在 G4 需要其导出时要求。
- PDF 栅格工具至少一个通过真实 PDF 到 PNG 转换；仅找到命令或包装器不得标记为可用。
- PyYAML 只用于 skill 格式校验等辅助任务，不是数学建模运行的通用必需项。
- 已安装但未加入 PATH 的 Typst 和 DrawIO 可以通过 `.codex/runtime.local.json` 的绝对路径正常使用；不要重复安装。

## 安装规则

先展示缺失项、用途、将使用的解释器和准确安装目标，再请求用户批准。批准前不得运行 pip、winget、conda、uv 或其他安装命令。

Python 包必须通过选定解释器安装：

```powershell
& "<python.exe>" -m pip install <package>
```

不要裸调用 `pip`。不要因为某个包存在于另一解释器中就判定当前环境可用。系统工具按实际操作系统和可用包管理器给出命令；Windows 使用 PowerShell 原生命令检测，不在 PowerShell 中提供 `command -v`、shell 函数或 heredoc。

安装后必须重新运行检查脚本，并把安装前后差异展示给用户。

## 报告

输出以下结论：

- 选定解释器及来源。
- 当前赛题代码阶段是否就绪。
- 论文、DrawIO 和 PDF 检查能力。
- 缺失项及其影响。
- 已验证事实与仍未验证事实。

只使用 `VERIFIED`、`UNVERIFIED`、`FAILED` 表述证据状态。
