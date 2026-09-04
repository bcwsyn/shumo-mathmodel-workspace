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
| `projects/CUMCM2018A_HighTemperatureClothing/` | 2018 A 题高温服装项目 | 已清除独立 `.venv` 与临时文件；运行前按 `requirements.txt` 重建环境 |

## 交付包

| 路径 | 内容 | 备注 |
| --- | --- | --- |
| `deliverables/交付包_生产质量决策模型_20260808/` | 生产质量决策模型历史交付包 | 已清除缓存和临时渲染目录 |

## 归档

| 路径 | 内容 | 恢复方式 |
| --- | --- | --- |
| `archive/legacy-root-run-20260808/` | 旧根目录运行产物 | 按需移回独立项目目录 |
| `archive/incomplete-projects/B题_数学建模_20260808/` | 未形成完整项目的题面与临时文件 | 继续建模时移入 `projects/` |
| `archive/organization-metadata-backup-20260823/` | 整理前的说明与运行时配置备份 | 仅用于审计 |

## 历史配置

- `.skill-backups/`：技能历史备份，不参与当前调用。
- `.skill-proposals/`：尚未启用的技能提案，不参与当前调用。

## 维护约定

1. 新题统一放入 `projects/<YYYYMMDD>-<题目短名>/`。
2. 只有验收完成的干净产物进入 `deliverables/`。
3. 临时文件确认无用后及时清理，重要中间结果移入项目的 `results/` 或 `reports/`。
4. 根目录不再新增单题的 `plan.md`、`todo.md`、`code/`、`results/`、`figures/` 或 `paper/`。
5. 虚拟环境与缓存不计入项目资料目录；历史项目运行前按各自依赖清单重建环境。
