# LaTeX 源码优先的论文交付工作流设计

## 决策

后续数学建模项目的论文正式主稿统一采用 XeLaTeX 源码。PDF 是由源码编译得到的预览或交付物，不是编辑入口，也不能作为唯一论文产物。现有 Word/Typst 项目保持原状；不自动迁移，不以新规则否定其既有验证状态。

## 目录与单一真源

```text
paper/
  main.tex
  sections/
    abstract.tex
    01_overview.tex
    ...
  references.tex
  figures/
  build/
    preview.pdf
    final.pdf
```

`main.tex` 负责模板、章节装配与全局宏；每个可协作章节独立为 `.tex` 文件；`references.tex` 保存参考文献源；`build/` 仅保存可再生 PDF 与编译副产物，不允许手工修改。图的可编辑 SVG/Draw.io 源继续保留在项目 `figures/`，LaTeX 引用已验收的 PDF/PNG 导出物。

## 写作与验收规则

1. G5 创建或选取 `*-latex` 模板，并验证 XeLaTeX 可编译最小中文、公式 PDF。
2. G6 交付 `main.tex`、独立章节和 `references.tex`，摘要必须是单独章节文件，便于小范围改写和 Git 合并。
3. G7 将 `main.tex` 编译为 `paper/build/preview.pdf` 并逐页检查；编译日志和 PDF 哈希进入报告。
4. G7 通过后，最终验收再次从同一 `main.tex` 编译 `paper/build/final.pdf`，交付包同时包含全部 `.tex`、图源、已引用图的导出物、PDF、代码、结果和复现说明。
5. 不保存或共享 LaTeX 的 `.aux`、`.log`、`.out`、`.toc`、`.fls`、`.fdb_latexmk` 等可再生中间文件。

## 团队协作

成员优先各自修改不同的 `sections/*.tex`、图源或代码文件；同一 `main.tex`、同一章节文件、同一二进制 Word/Excel/Draw.io 文件仍需串行合并。默认口令保持不变，并增加：

- “修改摘要：<内容> 并重新编译论文”
- “同步团队最新论文并编译”
- “上传本次论文修改”

Codex 在编译前同步远端、检查冲突；在构建成功且用户授权上传时提交源码与可交付 PDF。编译失败、冲突或 XeLaTeX 缺失均停止并给出最小修复步骤，不回退到修改 PDF。

## 非目标与风险

- 不把 DOCX 与 `.tex` 同时设为正式主稿。
- 不自动将已完成 DOCX 转为 LaTeX；迁移须由用户另行授权并以原 PDF 逐页比对。
- 不因 `xelatex` 路径存在而声称可用；doctor 必须完成真实最小中文文档编译和 PDF 签名检查。
