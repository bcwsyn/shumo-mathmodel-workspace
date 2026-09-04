"""G2 最小可行入口。

该入口读取真实附件，完成两个方向的理想抛物面一维搜索、问题二
可行基线选择、解析聚焦测试，并保存 JSON 与诊断 PDF。
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from fast_geometry import build_direction_frame, load_fast_data
from g2_plot import plot_g2_diagnostic
from problem1 import FocalSearchResult, search_hardware_friendly_focal_length
from problem2 import choose_feasible_baseline
from problem3 import ideal_paraboloid_focus_error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行 FAST G2 最小可行验证")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--figure", type=Path, required=True)
    return parser


def _search_payload(search: FocalSearchResult) -> dict[str, Any]:
    return {
        "focal_length_m": search.focal_length,
        "vertex_radius_m": None,
        "optimizer_success": search.optimizer_success,
        "optimizer_message": search.optimizer_message,
        "constraint": search.constraint,
        "target_displacement_min_m": float(np.min(search.displacement)),
        "target_displacement_max_m": float(np.max(search.displacement)),
        "grid_focal_lengths_m": search.grid_focal_lengths.tolist(),
        "grid_hardware_utilization": search.grid_utilizations.tolist(),
    }


def run_g2_smoke(data_dir: Path, output: Path, figure: Path) -> dict[str, Any]:
    """执行 G2 最小验证并返回与保存的结果字典。

    参数:
        data_dir: 项目内原始附件目录。
        output: G2 JSON 结果路径。
        figure: G2 诊断 PDF 路径。

    返回:
        已写入 JSON 的可审计结果。
    """

    started = time.perf_counter()
    data = load_fast_data(data_dir)
    # 两个问题复用同一模型定义，仅观测轴和离散工作口径不同。
    frame1 = build_direction_frame(data, 0.0, 90.0)
    frame2 = build_direction_frame(data, 36.795, 78.169)
    search1 = search_hardware_friendly_focal_length(data, frame1)
    search2 = search_hardware_friendly_focal_length(data, frame2)
    baseline2 = choose_feasible_baseline(data, frame2, search2.displacement)
    focus_error1 = ideal_paraboloid_focus_error(frame1, search1.focal_length)
    focus_error2 = ideal_paraboloid_focus_error(frame2, search2.focal_length)
    payload1 = _search_payload(search1)
    payload2 = _search_payload(search2)
    focus_radius = float(np.linalg.norm(frame1.focus))
    payload1["vertex_radius_m"] = focus_radius + search1.focal_length
    payload2["vertex_radius_m"] = focus_radius + search2.focal_length
    result: dict[str, Any] = {
        "stage": "g2-minimal-validation",
        "status": "BASELINE_ONLY",
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "pandas", "matplotlib")
            },
        },
        "data": {
            "nodes": len(data.node_ids),
            "panels": len(data.panels),
            "edges": len(data.edges),
            "radius_m": data.radius,
        },
        "problem1": {
            **payload1,
            "active_nodes": int(np.sum(frame1.active_nodes)),
            "focus_error_m": focus_error1,
        },
        "problem2": {
            **payload2,
            "active_nodes": int(np.sum(frame2.active_nodes)),
            "focus_error_m": focus_error2,
            "baseline_source": baseline2.source,
            "baseline_constraint": baseline2.constraint,
            "baseline_mean_square_error_m2": baseline2.weighted_mean_square_error,
            "baseline_max_abs_target_error_m": baseline2.max_abs_target_error_m,
        },
        "runtime_seconds": time.perf_counter() - started,
        "limitations": [
            "G2 只使用固定半宽的一维搜索，不是 G3 自动扩张正式搜索。",
            "G2 仅选择目标面或零位移可行基线，未运行正式顺序凸化。",
            "G2 只验证解析聚焦公式，未计算正式面板接收比。",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    plot_g2_diagnostic(output, figure)
    return result


def main() -> None:
    """解析命令行并运行 G2 最小验证。"""

    arguments = _parser().parse_args()
    result = run_g2_smoke(arguments.data_dir, arguments.output, arguments.figure)
    print(
        json.dumps(
            {
                "status": result["status"],
                "problem1_feasible": result["problem1"]["constraint"]["feasible"],
                "problem2_baseline": result["problem2"]["baseline_source"],
                "runtime_seconds": result["runtime_seconds"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
