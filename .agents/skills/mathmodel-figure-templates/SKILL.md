---
name: mathmodel-figure-templates
description: Use this skill in MathModel projects when the user asks to reproduce built-in scientific visualization templates, especially prompts mentioning $mathmodel-figure-templates, 科研绘图模板, SHAP蜂群柱状图, 配对云雨图, 交叉验证ROC, 泰勒图, 相关矩阵组合图, 预测真实值边缘分布图, TPE调参3D曲面, 下三角相关矩阵半边小提琴图, 分组环形热图, 城市公园降温组合图, or Nature和弦图. It runs bundled Python scripts with the project-confirmed interpreter.
---

# MathModel Figure Templates

This skill contains ready-to-run Python/matplotlib scripts for the figure templates exposed in the MathModel Improve tab. Resolve the skill directory from the current `SKILL.md` location; never assume a Claude, Linux, home-directory, or workspace path.

When used inside the full modeling workflow, read `../_references/learning_project_contract.md` and `../_references/python_engineering_standard.md`. Use the template only as a visual starting point, replace simulated data with verified project results, and preserve the result-to-figure evidence chain.

## Fast Path

1. Match the requested chart in `references/figure-catalog.md`.
2. Resolve the confirmed Python interpreter using `verify-generated-code`, then run the renderer from the current workspace with the template id:

```powershell
& "<python.exe>" "<skill-dir>/scripts/render_template.py" paired-raincloud
```

3. The renderer copies the bundled template script into `绘图复刻/scripts/`, runs it there, and writes outputs to `绘图复刻/outputs/`.
4. Return the generated PNG/PDF/SVG paths and the copied script path to the user.

Use `--list` to show supported ids:

```powershell
& "<python.exe>" "<skill-dir>/scripts/render_template.py" --list
```

## Output Contract

- Work under the current workspace unless the user gives another path.
- Default project folder: `绘图复刻`.
- Script path: `绘图复刻/scripts/make_<template>.py`.
- Outputs: `绘图复刻/outputs/<template>_replica.png`, `.pdf`, `.svg`.
- Use the bundled scripts as the first choice; edit the copied workspace script only when the user requests customization.
- The bundled scripts use deterministic simulated data. Do not claim simulated values reproduce a source study exactly.
- Before reporting success, require a zero exit code and verify that the announced PNG/PDF/SVG files exist. Treat missing Python packages as `FAILED`; do not invent a fallback renderer.

## Template Ids

- `multiclass-shap-combo`
- `paired-raincloud`
- `cv-roc-ci`
- `taylor-diagram`
- `correlation-pairgrid`
- `prediction-marginal-grid`
- `rf-tpe-surface`
- `grouped-corr-split-violin`
- `grouped-circular-heatmap`
- `urban-park-cooling-combo`
- `nature-chord-diagram`

## When Customizing

If the user asks for changes, copy/run the nearest template first, then edit the copied file in `绘图复刻/scripts/`. Preserve:

- `MPLCONFIGDIR` before importing matplotlib.
- deterministic seeds for simulated data.
- PNG/PDF/SVG export.
- readable labels, legends, and high-DPI output.

Use `references/plot-recipes.md` for implementation patterns.
