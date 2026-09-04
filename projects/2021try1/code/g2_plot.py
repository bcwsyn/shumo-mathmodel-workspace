"""从已保存的 G2 JSON 结果生成最小诊断图。"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


def plot_g2_diagnostic(result_path: Path, output_path: Path) -> None:
    """绘制两个观测方向的一维硬件占用率搜索曲线。"""

    # 绘图只消费已落盘 JSON，避免作图阶段重新计算或改写核心指标。
    result = json.loads(result_path.read_text(encoding="utf-8"))
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.4), constrained_layout=True)
    for axis, key, label in zip(
        axes,
        ("problem1", "problem2"),
        ("问题一：正上方", "问题二：指定方向"),
        strict=True,
    ):
        values = result[key]
        focal = values["grid_focal_lengths_m"]
        utilization = values["grid_hardware_utilization"]
        axis.plot(focal, utilization, color="#0072B2", linewidth=1.6)
        axis.axvline(
            values["focal_length_m"],
            color="#D55E00",
            linestyle="--",
            linewidth=1.2,
            label="G2 最优焦距",
        )
        axis.axhline(1.0, color="#444444", linestyle=":", linewidth=1.0, label="硬约束上限")
        axis.set_xlabel("抛物面焦距（米）")
        axis.set_ylabel("最大归一化硬件占用率")
        axis.set_title(label, fontsize=10)
        axis.grid(alpha=0.25)
    axes[0].legend(fontsize=8)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf")
    plt.close(figure)
