# 项目目录索引

更新日期：2026-08-23

## 当前工作区

| 路径 | 用途 | 状态 |
| --- | --- | --- |
| `.agents/skills/` | 数学建模工作流、验证工具与绘图技能 | 当前生效 |
| `.codex/` | 共享 Python 与工具运行配置 | 当前生效 |
| `.venv/` | 共享技能运行环境 | 当前生效，不手工整理内部文件 |
| `knowledge/mathmodel/approved/` | 已审批的方法卡和论文卡 | 当前生效 |
| `学习资料/` | 原始算法、论文与教材资料 | 参考资料 |

## 建模项目

| 路径 | 内容 | 备注 |
| --- | --- | --- |
| `projects/2021try1/` | 2021 年历史项目 | 完整保留 |
| `projects/CUMCM2018A_HighTemperatureClothing/` | 2018 A 题高温服装项目 | 约 628 MB，其中独立 `.venv` 约 382 MB |

## 交付包

| 路径 | 内容 | 备注 |
| --- | --- | --- |
| `deliverables/交付包_生产质量决策模型_20260808/` | 生产质量决策模型历史交付包 | 按原样保留，含历史临时产物 |

## 归档

| 路径 | 内容 | 恢复方式 |
| --- | --- | --- |
| `archive/legacy-root-run-20260808/` | 旧根目录运行产物 | 按需移回独立项目目录 |
| `archive/temporary-quarantine-20260823/` | 旧缓存与临时文件 | 确认无用后可删除 |
| `archive/incomplete-projects/B题_数学建模_20260808/` | 未形成完整项目的题面与临时文件 | 继续建模时移入 `projects/` |
| `archive/invalid-git-dir-20260823/` | 空的无效 Git 目录 | 通常无需恢复 |

## 历史配置

- `.skill-backups/`：技能历史备份，不参与当前调用。
- `.skill-proposals/`：尚未启用的技能提案，不参与当前调用。

## 维护约定

1. 新题统一放入 `projects/<YYYYMMDD>-<题目短名>/`。
2. 只有验收完成的干净产物进入 `deliverables/`。
3. 临时文件先移入 `archive/temporary-quarantine-<日期>/`，确认后再删除。
4. 根目录不再新增单题的 `plan.md`、`todo.md`、`code/`、`results/`、`figures/` 或 `paper/`。
5. 虚拟环境与缓存不计入项目资料目录；项目需要独立环境时必须在 README 中注明。
