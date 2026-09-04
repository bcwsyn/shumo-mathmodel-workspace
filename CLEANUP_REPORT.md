# 空间清理报告

日期：2026-08-23

## 已永久清除

- `projects/CUMCM2018A_HighTemperatureClothing/.venv/` 及随之失效的本地运行时配置。
- 历史项目和交付包中的 `tmp/`、`.cache/`、`.ruff_cache/`、`.matplotlib/` 与 `__pycache__/`。
- `archive/temporary-quarantine-20260823/`。
- 空的 `archive/invalid-git-dir-20260823/`。

共释放约 413 MB。论文、代码、输入、结果、图表、报告、依赖清单和技能备份均未删除。

## 运行影响

`projects/CUMCM2018A_HighTemperatureClothing/requirements.txt` 已保留。该项目再次运行前需要根据此文件重建虚拟环境；共享环境当前缺少 `pymoo`，不能直接替代原独立环境。

## 未能删除

以下两个空目录受 Windows ACL 保护，未能移除，但内部没有文件，不占实际资料空间：

- `projects/CUMCM2018A_HighTemperatureClothing/.pytest_cache/`
- `deliverables/交付包_生产质量决策模型_20260808/.pytest_cache/`
