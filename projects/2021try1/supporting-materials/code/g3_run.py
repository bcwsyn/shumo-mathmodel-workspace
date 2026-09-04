"""G3 正式实验入口。

入口读取真实附件，完成理想面比较、约束优化、接收比与稳健性分析，
保存可追溯结果表，并仅从落盘数据生成论文用矢量图。
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
import pandas as pd

from fast_geometry import (
    DirectionFrame,
    FastData,
    build_direction_frame,
    load_fast_data,
)
from g3_plot import (
    plot_constraint_usage,
    plot_displacement_and_stroke,
    plot_focal_search,
    plot_receiver_results,
    plot_sensitivity,
)
from optimization import OptimizationResult, optimize_work_surface
from problem1 import FocalModelComparison, compare_focal_models
from raytrace import panel_centroid_landings, trace_convergence, trace_surface


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行 FAST G3 正式实验")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, required=True)
    return parser


def _focal_payload(
    data: FastData,
    frame: DirectionFrame,
    comparison: FocalModelComparison,
) -> dict[str, Any]:
    selected = comparison.hardware_result
    focus_radius = float(np.linalg.norm(frame.focus))
    return {
        "geometric_focal_length_m": comparison.geometric_focal_length,
        "least_squares_focal_length_m": comparison.least_squares_focal_length,
        "selected_focal_length_m": selected.focal_length,
        "selected_vertex_radius_m": focus_radius + selected.focal_length,
        "selected_vertex_xyz_m": (
            (focus_radius + selected.focal_length) * frame.axis
        ).tolist(),
        "candidate_metrics": comparison.metrics,
        "grid_focal_lengths_m": selected.grid_focal_lengths.tolist(),
        "grid_hardware_utilization": selected.grid_utilizations.tolist(),
        "active_nodes": int(np.sum(frame.active_nodes)),
        "sphere_radius_m": data.radius,
    }


def _save_solution_tables(
    data: FastData,
    frame: DirectionFrame,
    target: np.ndarray,
    solution: OptimizationResult,
    output_dir: Path,
) -> dict[str, Path]:
    active = frame.active_nodes
    adjusted = solution.adjusted_nodes[active]
    axial = data.nodes @ frame.axis
    rho = np.sqrt(np.maximum(0.0, np.sum(data.nodes**2, axis=1) - axial**2))
    nodes_frame = pd.DataFrame(
        {
            "node_id": data.node_ids[active],
            "x_m": adjusted[:, 0],
            "y_m": adjusted[:, 1],
            "z_m": adjusted[:, 2],
            "rho_m": rho[active],
            "displacement_m": solution.displacement[active],
            "target_displacement_m": target[active],
            "stroke_m": solution.strokes[active],
        }
    )
    nodes_path = output_dir / "problem2_nodes.csv"
    nodes_frame.to_csv(nodes_path, index=False, encoding="utf-8")

    edges = data.edges[frame.incident_edges]
    baseline_lengths = data.edge_lengths[frame.incident_edges]
    differences = solution.adjusted_nodes[edges[:, 0]] - solution.adjusted_nodes[edges[:, 1]]
    adjusted_lengths = np.linalg.norm(differences, axis=1)
    relative = adjusted_lengths / baseline_lengths - 1.0
    edge_frame = pd.DataFrame(
        {
            "left_node_id": data.node_ids[edges[:, 0]],
            "right_node_id": data.node_ids[edges[:, 1]],
            "baseline_length_m": baseline_lengths,
            "adjusted_length_m": adjusted_lengths,
            "relative_change": relative,
            "absolute_relative_change": np.abs(relative),
        }
    )
    edges_path = output_dir / "constraint_edges.csv"
    edge_frame.to_csv(edges_path, index=False, encoding="utf-8")
    history_path = output_dir / "optimization_history.csv"
    pd.DataFrame(solution.histories).to_csv(history_path, index=False, encoding="utf-8")
    return {"nodes": nodes_path, "edges": edges_path, "history": history_path}


def _save_workbook_payload(
    data: FastData,
    frame: DirectionFrame,
    solution: OptimizationResult,
    vertex_xyz: list[float],
    output_dir: Path,
) -> Path:
    """保存供 artifact-tool 写入竞赛模板的纯 JSON 数据。"""

    active = frame.active_nodes
    adjusted = solution.adjusted_nodes[active]
    payload = {
        "vertex_xyz_m": vertex_xyz,
        "adjusted_nodes": [
            [str(node_id), float(x), float(y), float(z)]
            for node_id, (x, y, z) in zip(
                data.node_ids[active],
                adjusted,
                strict=True,
            )
        ],
        "actuator_strokes": [
            [str(node_id), float(stroke)]
            for node_id, stroke in zip(
                data.node_ids[active],
                solution.strokes[active],
                strict=True,
            )
        ],
    }
    payload_path = output_dir / "workbook_payload.json"
    payload_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload_path


def _trace_convergence_table(
    data: FastData,
    frame: DirectionFrame,
    adjusted_nodes: np.ndarray,
    output_dir: Path,
) -> tuple[dict[str, list[Any]], Path]:
    """保存基准面和工作面的射线细分收敛表。"""

    # 64 阶用于确认 0.5 米馈源半径下离散命中边界的收敛稳定性。
    levels = (2, 4, 8, 16, 32, 64)
    records: list[dict[str, Any]] = []
    series: dict[str, list[Any]] = {}
    for name, nodes in (("baseline", data.nodes), ("work", adjusted_nodes)):
        results = trace_convergence(data, frame, nodes, levels=levels)
        series[name] = results
        records.extend(
            {
                "surface": name,
                "subdivision": item.subdivision,
                "reception_ratio": item.reception_ratio,
                "received_weight": item.received_weight,
                "total_weight": item.total_weight,
                "included_samples": item.included_samples,
            }
            for item in results
        )
    convergence_path = output_dir / "raytrace_convergence.csv"
    pd.DataFrame(records).to_csv(convergence_path, index=False, encoding="utf-8")
    return series, convergence_path


def _trace_sensitivity_table(
    data: FastData,
    frame: DirectionFrame,
    adjusted_nodes: np.ndarray,
    output_dir: Path,
) -> Path:
    """保存口径半径与能量权重口径的敏感性结果。"""

    sensitivity_records: list[dict[str, Any]] = []
    for radius in (149.5, 150.0, 150.5):
        for name, nodes in (("baseline", data.nodes), ("work", adjusted_nodes)):
            for weighting, projected in (("projected", True), ("equal_panel", False)):
                result = trace_surface(
                    data,
                    frame,
                    nodes,
                    subdivision=16,
                    aperture_radius=radius,
                    projected_weight=projected,
                )
                sensitivity_records.append(
                    {
                        "surface": name,
                        "aperture_radius_m": radius,
                        "weighting": weighting,
                        "reception_ratio": result.reception_ratio,
                    }
                )
    sensitivity_path = output_dir / "raytrace_sensitivity.csv"
    pd.DataFrame(sensitivity_records).to_csv(
        sensitivity_path,
        index=False,
        encoding="utf-8",
    )
    return sensitivity_path


def _trace_landing_table(
    data: FastData,
    frame: DirectionFrame,
    adjusted_nodes: np.ndarray,
    output_dir: Path,
) -> Path:
    """保存基准面和工作面的面板中心馈源平面落点。"""

    landing_records: list[pd.DataFrame] = []
    for name, nodes in (("baseline", data.nodes), ("work", adjusted_nodes)):
        landings = panel_centroid_landings(data, frame, nodes)
        landing_records.append(
            pd.DataFrame(
                {
                    "surface": name,
                    "receiver_x_m": landings[:, 0],
                    "receiver_y_m": landings[:, 1],
                }
            )
        )
    landings_path = output_dir / "receiver_landings.csv"
    pd.concat(landing_records, ignore_index=True).to_csv(
        landings_path,
        index=False,
        encoding="utf-8",
    )
    return landings_path


def _summarize_ray_series(series: dict[str, list[Any]]) -> dict[str, Any]:
    """从最高两档细分计算接收比及末步离散误差。"""

    levels = [item.subdivision for item in series["baseline"]]
    baseline_final = series["baseline"][-1].reception_ratio
    work_final = series["work"][-1].reception_ratio
    return {
        "subdivision_levels": levels,
        "baseline_reception_ratio": baseline_final,
        "work_reception_ratio": work_final,
        "absolute_improvement": work_final - baseline_final,
        "relative_improvement": (
            (work_final - baseline_final) / baseline_final
            if baseline_final > 0
            else None
        ),
        "baseline_last_change": abs(
            series["baseline"][-1].reception_ratio
            - series["baseline"][-2].reception_ratio
        ),
        "work_last_change": abs(
            series["work"][-1].reception_ratio
            - series["work"][-2].reception_ratio
        ),
    }


def _run_ray_experiments(
    data: FastData,
    frame: DirectionFrame,
    adjusted_nodes: np.ndarray,
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, Path]]:
    """运行收敛、敏感性和落点三组确定性射线实验。"""

    series, convergence_path = _trace_convergence_table(
        data,
        frame,
        adjusted_nodes,
        output_dir,
    )
    sensitivity_path = _trace_sensitivity_table(
        data,
        frame,
        adjusted_nodes,
        output_dir,
    )
    landings_path = _trace_landing_table(
        data,
        frame,
        adjusted_nodes,
        output_dir,
    )
    paths = {
        "convergence": convergence_path,
        "sensitivity": sensitivity_path,
        "landings": landings_path,
    }
    return _summarize_ray_series(series), paths


def _make_figures(
    summary_path: Path,
    tables: dict[str, Path],
    ray_paths: dict[str, Path],
    figures_dir: Path,
) -> list[Path]:
    figures = [
        figures_dir / "focal_model_comparison.pdf",
        figures_dir / "displacement_and_stroke.pdf",
        figures_dir / "constraint_usage.pdf",
        figures_dir / "receiver_results.pdf",
        figures_dir / "raytrace_sensitivity.pdf",
    ]
    plot_focal_search(summary_path, figures[0])
    plot_displacement_and_stroke(tables["nodes"], figures[1])
    plot_constraint_usage(tables["edges"], figures[2])
    plot_receiver_results(ray_paths["convergence"], ray_paths["landings"], figures[3])
    plot_sensitivity(ray_paths["sensitivity"], figures[4])
    return figures


def _environment_payload() -> dict[str, Any]:
    """记录正式实验所用解释器与关键科学计算包版本。"""

    package_names = (
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "cvxpy",
        "osqp",
        "clarabel",
    )
    return {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "packages": {
            name: importlib.metadata.version(name)
            for name in package_names
        },
    }


def _optimization_payload(
    solution: OptimizationResult,
    frame: DirectionFrame,
) -> dict[str, Any]:
    """提取优化误差、约束占用率和促动器范围。"""

    active = frame.active_nodes
    return {
        "objective_mse_m2": solution.objective_mse_m2,
        "rmse_m": float(np.sqrt(solution.objective_mse_m2)),
        "max_abs_error_m": solution.max_abs_error_m,
        "selected_start": solution.selected_start,
        "constraint": solution.constraint,
        "displacement_min_m": float(np.min(solution.displacement[active])),
        "displacement_max_m": float(np.max(solution.displacement[active])),
        "stroke_min_m": float(np.min(solution.strokes[active])),
        "stroke_max_m": float(np.max(solution.strokes[active])),
        "solver_statuses": sorted(set(solution.solver_statuses)),
    }


def run_formal_experiment(
    data_dir: Path,
    output_dir: Path,
    figures_dir: Path,
) -> dict[str, Any]:
    """运行 G3 正式模型、保存结果数据并生成矢量图。"""

    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    data = load_fast_data(data_dir)
    frame1 = build_direction_frame(data, 0.0, 90.0)
    frame2 = build_direction_frame(data, 36.795, 78.169)
    comparison1 = compare_focal_models(data, frame1)
    comparison2 = compare_focal_models(data, frame2)
    target2 = comparison2.hardware_result.displacement
    solution = optimize_work_surface(data, frame2, target2)
    tables = _save_solution_tables(data, frame2, target2, solution, output_dir)
    vertex_xyz = _focal_payload(data, frame2, comparison2)["selected_vertex_xyz_m"]
    workbook_payload = _save_workbook_payload(
        data,
        frame2,
        solution,
        vertex_xyz,
        output_dir,
    )
    ray_summary, ray_paths = _run_ray_experiments(
        data,
        frame2,
        solution.adjusted_nodes,
        output_dir,
    )
    summary: dict[str, Any] = {
        "stage": "g3-formal",
        "status": "FORMAL_RESULTS",
        "environment": _environment_payload(),
        "problem1": {"focal_models": _focal_payload(data, frame1, comparison1)},
        "problem2": {
            "focal_models": _focal_payload(data, frame2, comparison2),
            "optimization": _optimization_payload(solution, frame2),
        },
        "problem3": ray_summary,
        "runtime_seconds": None,
    }
    summary_path = output_dir / "formal_results.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    figures = _make_figures(summary_path, tables, ray_paths, figures_dir)
    summary["runtime_seconds"] = time.perf_counter() - started
    summary["artifacts"] = {
        "tables": {key: str(value) for key, value in tables.items()},
        "ray_tables": {key: str(value) for key, value in ray_paths.items()},
        "figures": [str(value) for value in figures],
        "workbook_payload": str(workbook_payload),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    """解析命令行并运行 G3 正式实验。"""

    arguments = _parser().parse_args()
    result = run_formal_experiment(
        arguments.data_dir,
        arguments.output_dir,
        arguments.figures_dir,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "work_reception_ratio": result["problem3"]["work_reception_ratio"],
                "baseline_reception_ratio": result["problem3"]["baseline_reception_ratio"],
                "runtime_seconds": result["runtime_seconds"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
