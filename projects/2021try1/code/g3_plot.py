"""从 G3 已保存结果生成论文用数据图。

本模块不重新运行模型，只读取 JSON/CSV 结果并输出矢量 PDF。
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _configure_chinese_font() -> None:
    # 图表统一使用可嵌入的中文字体，并保留坐标轴负号的数学含义。
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def plot_focal_search(summary_path: Path, output_path: Path) -> None:
    """绘制两个方向的焦距—硬件占用率曲线。"""

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    _configure_chinese_font()
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.4), constrained_layout=True)
    for axis, key, label in zip(
        axes,
        ("problem1", "problem2"),
        ("正上方观测", "指定方向观测"),
        strict=True,
    ):
        values = summary[key]["focal_models"]
        axis.plot(
            values["grid_focal_lengths_m"],
            values["grid_hardware_utilization"],
            color="#0072B2",
            linewidth=1.6,
            label="最大硬件占用率",
        )
        axis.axvline(
            values["selected_focal_length_m"],
            color="#D55E00",
            linestyle="--",
            linewidth=1.2,
            label="硬件友好焦距",
        )
        axis.axvline(
            values["least_squares_focal_length_m"],
            color="#009E73",
            linestyle="-.",
            linewidth=1.1,
            label="最小二乘焦距",
        )
        axis.axhline(1.0, color="#444444", linestyle=":", linewidth=1.0)
        axis.set_xlabel("抛物面焦距（米）")
        axis.set_ylabel("最大归一化硬件占用率")
        axis.text(0.03, 0.94, label, transform=axis.transAxes, va="top")
        axis.grid(alpha=0.22)
    axes[0].legend(fontsize=8)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf")
    plt.close(figure)


def plot_displacement_and_stroke(nodes_path: Path, output_path: Path) -> None:
    """绘制节点目标/实际位移与促动器伸缩量分布。"""

    nodes = pd.read_csv(nodes_path)
    _configure_chinese_font()
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.5), constrained_layout=True)
    order = np.argsort(nodes["rho_m"].to_numpy())
    axes[0].plot(
        nodes["rho_m"].to_numpy()[order],
        nodes["target_displacement_m"].to_numpy()[order],
        color="#999999",
        linewidth=1.0,
        label="理想目标",
    )
    axes[0].scatter(
        nodes["rho_m"],
        nodes["displacement_m"],
        s=8,
        color="#0072B2",
        alpha=0.65,
        label="约束优化后",
    )
    axes[0].set_xlabel("离观测轴投影距离（米）")
    axes[0].set_ylabel("向球心径向位移（米）")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.22)
    axes[1].hist(
        nodes["stroke_m"],
        bins=32,
        color="#009E73",
        edgecolor="white",
        linewidth=0.4,
    )
    axes[1].axvline(-0.6, color="#D55E00", linestyle="--", linewidth=1.0)
    axes[1].axvline(0.6, color="#D55E00", linestyle="--", linewidth=1.0)
    axes[1].set_xlabel("促动器向球心伸缩量（米）")
    axes[1].set_ylabel("节点数")
    axes[1].grid(axis="y", alpha=0.22)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf")
    plt.close(figure)


def plot_constraint_usage(edges_path: Path, output_path: Path) -> None:
    """绘制主索相对变化的排序曲线和分布。"""

    edges = pd.read_csv(edges_path)
    values = np.sort(edges["absolute_relative_change"].to_numpy())
    _configure_chinese_font()
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.4), constrained_layout=True)
    axes[0].plot(np.arange(1, len(values) + 1), 100.0 * values, color="#0072B2")
    axes[0].axhline(0.07, color="#D55E00", linestyle="--", label="0.07% 上限")
    axes[0].set_xlabel("相关主索（按相对变化排序）")
    axes[0].set_ylabel("绝对相对长度变化（%）")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.22)
    axes[1].hist(100.0 * values, bins=36, color="#56B4E9", edgecolor="white")
    axes[1].axvline(0.07, color="#D55E00", linestyle="--")
    axes[1].set_xlabel("绝对相对长度变化（%）")
    axes[1].set_ylabel("主索数")
    axes[1].grid(axis="y", alpha=0.22)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf")
    plt.close(figure)


def plot_receiver_results(
    convergence_path: Path,
    landings_path: Path,
    output_path: Path,
) -> None:
    """绘制接收比收敛和面板中心落点。"""

    convergence = pd.read_csv(convergence_path)
    landings = pd.read_csv(landings_path)
    _configure_chinese_font()
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.7), constrained_layout=True)
    for surface, color, label in (
        ("baseline", "#999999", "基准球面"),
        ("work", "#0072B2", "调节工作面"),
    ):
        subset = convergence[convergence["surface"] == surface]
        axes[0].plot(
            subset["subdivision"],
            subset["reception_ratio"],
            marker="o",
            color=color,
            label=label,
        )
    axes[0].set_xscale("log", base=2)
    axes[0].set_xlabel("三角边细分级别")
    axes[0].set_ylabel("接收比")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.22)
    for surface, color, label in (
        ("baseline", "#999999", "基准球面"),
        ("work", "#0072B2", "调节工作面"),
    ):
        subset = landings[landings["surface"] == surface]
        axes[1].scatter(
            subset["receiver_x_m"],
            subset["receiver_y_m"],
            s=5,
            alpha=0.35,
            color=color,
            label=label,
        )
    circle = plt.Circle((0, 0), 0.5, fill=False, color="#D55E00", linewidth=1.2)
    axes[1].add_patch(circle)
    axes[1].set_aspect("equal", adjustable="box")
    axes[1].set_xlim(-3.0, 3.0)
    axes[1].set_ylim(-3.0, 3.0)
    axes[1].set_xlabel("馈源平面横向坐标（米）")
    axes[1].set_ylabel("馈源平面纵向坐标（米）")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.22)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf")
    plt.close(figure)


def plot_sensitivity(sensitivity_path: Path, output_path: Path) -> None:
    """绘制口径边界和权重口径的接收比敏感性。"""

    sensitivity = pd.read_csv(sensitivity_path)
    _configure_chinese_font()
    figure, axis = plt.subplots(figsize=(5.4, 3.5), constrained_layout=True)
    for surface, color, label in (
        ("baseline", "#999999", "基准球面"),
        ("work", "#0072B2", "调节工作面"),
    ):
        subset = sensitivity[
            (sensitivity["surface"] == surface)
            & (sensitivity["weighting"] == "projected")
        ]
        axis.plot(
            subset["aperture_radius_m"],
            subset["reception_ratio"],
            marker="o",
            color=color,
            label=label,
        )
    axis.set_xlabel("投影口径半径（米）")
    axis.set_ylabel("接收比")
    axis.legend(fontsize=8)
    axis.grid(alpha=0.22)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf")
    plt.close(figure)
