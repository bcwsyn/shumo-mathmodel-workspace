# LaTeX 摘要可编辑性验收

本目录是独立试验，不替代现有 V9.0 DOCX/PDF。

## 修改方式

只编辑 `sections/abstract.tex`，然后在本目录执行：

```powershell
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
```

`main.tex` 不承载摘要正文，便于不同成员只修改各自的章节文件并降低 Git 冲突概率。

## 本次验收

1. 初始摘要编译为 `build/abstract-v1.pdf`。
2. 仅修改 `sections/abstract.tex` 的一句结尾表述。
3. 修改后摘要编译为 `build/abstract-v2.pdf`。

两个 PDF 仅用于编辑体验核验；`build/` 中的 PDF 与 XeLaTeX 中间文件均不提交。
