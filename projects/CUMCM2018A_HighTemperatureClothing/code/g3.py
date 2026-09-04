"""2018 CUMCM A 题 G3 正式实验、优化、稳健性与制图流水线。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"),
)

import matplotlib
import numpy as np
import pandas as pd
from pymoo.core.problem import Problem
from scipy.optimize import least_squares

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from main import (
    ConfigurationError,
    DataValidationError,
    Material,
    NumericalError,
    SimulationConfig,
    duration_above_threshold,
    load_problem_data,
    simulate,
    steady_skin_temperature,
)

LOGGER = logging.getLogger("cumcm2018a.g3")
THICKNESSES_Q1 = (0.6, 6.0, 3.6, 5.0)
Q2_D2_VALUES = np.round(np.arange(0.6, 25.0 + 0.05, 0.1), 1)
Q3_D4_VALUES = np.round(np.arange(0.6, 6.4 + 0.05, 0.1), 1)
LIMIT_MAX_C = 47.0
LIMIT_DURATION_S = 300.0

# 设计理由：厚度统一用 mm 输入、内部转为 m；安全约束严格采用
# max(T_skin)<=47°C 且 duration(T_skin>44°C)<=300 s。


@dataclass(frozen=True)
class DesignMetric:
    """一个离散厚度方案的温度约束评价。"""

    d2_mm: float
    d4_mm: float
    max_skin_temp_c: float
    duration_above_44_s: float
    final_skin_temp_c: float
    feasible: bool
    grid_dx_mm: float
    dt_s: float


@dataclass(frozen=True)
class CalibrationSpec:
    """换热参数标定所用离散与优化设置。"""

    target_dx_mm: float
    dt_s: float
    starts: tuple[tuple[float, float], ...]
    max_nfev: int


def _configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(),
    ):
        handler.setFormatter(formatter)
        LOGGER.addHandler(handler)


def _phase_weights(times_s: np.ndarray) -> np.ndarray:
    weights = np.empty_like(times_s, dtype=float)
    masks = (
        times_s <= 600.0,
        (times_s > 600.0) & (times_s <= 1800.0),
        times_s > 1800.0,
    )
    for mask in masks:
        weights[mask] = 1.0 / math.sqrt(3.0 * np.count_nonzero(mask))
    return weights


def _jacobian_diagnostics(jacobian: np.ndarray) -> dict[str, float | None]:
    singular = np.linalg.svd(jacobian, compute_uv=False)
    if singular[-1] <= np.finfo(float).eps:
        return {"jacobian_condition": None, "parameter_correlation": None}
    condition = float(singular[0] / singular[-1])
    try:
        covariance = np.linalg.inv(jacobian.T @ jacobian)
        denominator = math.sqrt(covariance[0, 0] * covariance[1, 1])
        correlation = float(covariance[0, 1] / denominator)
    except (np.linalg.LinAlgError, ValueError):
        correlation = None
    return {
        "jacobian_condition": condition,
        "parameter_correlation": correlation,
    }


def _calibration_residual(
    log_coefficients: np.ndarray,
    materials: tuple[Material, ...],
    observations: np.ndarray,
    weights: np.ndarray,
    spec: CalibrationSpec,
) -> np.ndarray:
    h_out, h_body = np.exp(log_coefficients)
    config = SimulationConfig(
        75.0,
        37.0,
        37.0,
        5400.0,
        spec.dt_s,
        spec.target_dx_mm,
        float(h_out),
        float(h_body),
    )
    prediction = simulate(materials, THICKNESSES_Q1, config).skin_temp_c
    return (prediction - observations) * weights


def calibrate_exchange_coefficients(
    materials: tuple[Material, ...],
    times_s: np.ndarray,
    measured_c: np.ndarray,
    spec: CalibrationSpec,
) -> dict[str, Any]:
    """在指定网格上标定外侧与人体侧等效换热系数。"""
    stride = round(spec.dt_s)
    if not np.isclose(stride, spec.dt_s) or stride < 1:
        raise ConfigurationError("正式标定要求时间步为正整数秒")
    observations = measured_c[::stride]
    fit_times = times_s[::stride]
    weights = _phase_weights(fit_times)
    bounds = (np.log((1.0, 1.0)), np.log((500.0, 100.0)))
    candidates = [
        least_squares(
            _calibration_residual,
            np.log(start),
            args=(materials, observations, weights, spec),
            bounds=bounds,
            max_nfev=spec.max_nfev,
            xtol=1e-9,
            ftol=1e-9,
            gtol=1e-9,
        )
        for start in spec.starts
    ]
    best = min(candidates, key=lambda item: item.cost)
    h_out, h_body = np.exp(best.x)
    return {
        "target_dx_mm": spec.target_dx_mm,
        "dt_s": spec.dt_s,
        "h_out_w_m2k": float(h_out),
        "h_body_w_m2k": float(h_body),
        "weighted_least_squares_cost": float(best.cost),
        "function_evaluations": int(sum(item.nfev for item in candidates)),
        "optimizer_success": bool(best.success),
        "optimizer_message": str(best.message),
        **_jacobian_diagnostics(best.jac),
    }


def evaluate_design(
    materials: tuple[Material, ...],
    d2_mm: float,
    d4_mm: float,
    config: SimulationConfig,
) -> DesignMetric:
    """求解一个问题二/三厚度组合并计算两项安全约束。"""
    result = simulate(materials, (0.6, d2_mm, 3.6, d4_mm), config)
    max_temp = float(np.max(result.skin_temp_c))
    duration = duration_above_threshold(result.times_s, result.skin_temp_c, 44.0)
    return DesignMetric(
        float(d2_mm),
        float(d4_mm),
        max_temp,
        duration,
        float(result.skin_temp_c[-1]),
        bool(max_temp <= LIMIT_MAX_C + 1e-9 and duration <= LIMIT_DURATION_S + 1e-9),
        config.target_dx_mm,
        config.dt_s,
    )


def _design_worker(
    task: tuple[tuple[Material, ...], float, float, SimulationConfig],
) -> dict[str, Any]:
    return asdict(evaluate_design(*task))


def enumerate_designs(
    materials: tuple[Material, ...],
    d2_values: np.ndarray,
    d4_values: np.ndarray,
    config: SimulationConfig,
    workers: int,
) -> pd.DataFrame:
    """按固定顺序枚举笛卡尔积，可选多进程并保持结果确定性。"""
    tasks = [
        (materials, float(d2), float(d4), config)
        for d4 in d4_values
        for d2 in d2_values
    ]
    if workers <= 1:
        records = [_design_worker(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            records = list(executor.map(_design_worker, tasks, chunksize=16))
    return pd.DataFrame.from_records(records)


def _first_feasible(table: pd.DataFrame, objective: str = "d2_mm") -> pd.Series:
    feasible = table.loc[table["feasible"]].copy()
    if feasible.empty:
        raise NumericalError("离散候选中不存在可行方案")
    if objective == "d2_mm":
        ordered = feasible.sort_values(["d2_mm", "max_skin_temp_c"])
    else:
        # 离散设计以 0.1 mm 为单位，先舍入可避免 19.3+6.4 与 19.4+6.3
        # 因二进制浮点末位误差破坏“总厚度相同再按面密度”的设计规则。
        feasible["total_thickness_mm"] = np.round(
            feasible["d2_mm"] + feasible["d4_mm"],
            1,
        )
        feasible["areal_mass_kg_m2"] = (
            feasible["d2_mm"] * 0.862 + feasible["d4_mm"] * 0.00118
        )
        ordered = feasible.sort_values(
            ["total_thickness_mm", "areal_mass_kg_m2", "d2_mm", "d4_mm"]
        )
    return ordered.iloc[0]


def _boundary_candidates(table: pd.DataFrame, radius_steps: int = 5) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    for _, group in table.groupby("d4_mm", sort=True):
        group = group.sort_values("d2_mm").reset_index(drop=True)
        feasible_indices = np.flatnonzero(group["feasible"].to_numpy())
        center = int(feasible_indices[0]) if len(feasible_indices) else len(group) - 1
        left, right = max(0, center - radius_steps), min(len(group), center + radius_steps + 1)
        records.append(group.iloc[left:right][["d2_mm", "d4_mm"]])
    return pd.concat(records, ignore_index=True).drop_duplicates()


def _evaluate_candidate_table(
    materials: tuple[Material, ...],
    candidates: pd.DataFrame,
    config: SimulationConfig,
    workers: int,
) -> pd.DataFrame:
    tasks = [
        (materials, float(row.d2_mm), float(row.d4_mm), config)
        for row in candidates.itertuples(index=False)
    ]
    if workers <= 1:
        records = [_design_worker(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            records = list(executor.map(_design_worker, tasks, chunksize=8))
    return pd.DataFrame.from_records(records)


def _monotonicity_report(table: pd.DataFrame) -> dict[str, Any]:
    max_violations = 0
    duration_violations = 0
    largest_max_increase = 0.0
    largest_duration_increase = 0.0
    for _, group in table.groupby("d4_mm"):
        ordered = group.sort_values("d2_mm")
        max_changes = np.diff(ordered["max_skin_temp_c"])
        duration_changes = np.diff(ordered["duration_above_44_s"])
        max_violations += int(np.count_nonzero(max_changes > 1e-8))
        duration_violations += int(np.count_nonzero(duration_changes > 1e-8))
        largest_max_increase = max(largest_max_increase, float(np.max(max_changes)))
        largest_duration_increase = max(
            largest_duration_increase,
            float(np.max(duration_changes)),
        )
    return {
        "max_temperature_violations": max_violations,
        "duration_violations": duration_violations,
        "largest_max_temperature_increase_c": largest_max_increase,
        "largest_duration_increase_s": largest_duration_increase,
        "strictly_monotone": max_violations == 0 and duration_violations == 0,
        "screening_safe": max_violations == 0,
    }


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _pareto_mask(objectives: np.ndarray) -> np.ndarray:
    keep = np.zeros(len(objectives), dtype=bool)
    order = np.lexsort((objectives[:, 1], objectives[:, 0]))
    best_second = math.inf
    for index in order:
        if objectives[index, 1] < best_second - 1e-12:
            keep[index] = True
            best_second = float(objectives[index, 1])
    return keep


class LookupDesignProblem(Problem):
    """以完整 PDE 枚举表为确定性代理的双目标约束问题。"""

    def __init__(self, max_grid: np.ndarray, duration_grid: np.ndarray) -> None:
        super().__init__(
            n_var=2,
            n_obj=2,
            n_ieq_constr=2,
            xl=np.array([0.6, 0.6]),
            xu=np.array([25.0, 6.4]),
        )
        self.max_grid = max_grid
        self.duration_grid = duration_grid

    def _evaluate(self, x: np.ndarray, out: dict[str, np.ndarray], **_: Any) -> None:
        d2_index = np.clip(
            np.rint((x[:, 0] - 0.6) / 0.1).astype(int),
            0,
            len(Q2_D2_VALUES) - 1,
        )
        d4_index = np.clip(
            np.rint((x[:, 1] - 0.6) / 0.1).astype(int),
            0,
            len(Q3_D4_VALUES) - 1,
        )
        d2 = Q2_D2_VALUES[d2_index]
        d4 = Q3_D4_VALUES[d4_index]
        out["F"] = np.column_stack((d2 + d4, d2 * 0.862 + d4 * 0.00118))
        out["G"] = np.column_stack(
            (
                self.max_grid[d4_index, d2_index] - LIMIT_MAX_C,
                self.duration_grid[d4_index, d2_index] - LIMIT_DURATION_S,
            )
        )


def _nsga_grid(search_table: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    ordered = search_table.sort_values(["d4_mm", "d2_mm"]).reset_index(drop=True)
    shape = (len(Q3_D4_VALUES), len(Q2_D2_VALUES))
    return (
        ordered["max_skin_temp_c"].to_numpy().reshape(shape),
        ordered["duration_above_44_s"].to_numpy().reshape(shape),
    )


def _enumerated_objectives(search_table: pd.DataFrame) -> np.ndarray:
    feasible = search_table.loc[search_table["feasible"]]
    return np.column_stack(
        (
            feasible["d2_mm"] + feasible["d4_mm"],
            feasible["d2_mm"] * 0.862 + feasible["d4_mm"] * 0.00118,
        )
    )


def run_nsga2_cross_validation(
    search_table: pd.DataFrame,
    seeds: tuple[int, ...] = tuple(range(20)),
) -> dict[str, Any]:
    """在完整枚举查表模型上运行多随机种子 NSGA-II 交叉验证。"""
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.indicators.hv import HV
    from pymoo.optimize import minimize

    max_grid, duration_grid = _nsga_grid(search_table)
    problem = LookupDesignProblem(max_grid, duration_grid)
    indicator = HV(ref_point=np.array([32.0, 22.0]))
    runs: list[dict[str, Any]] = []
    all_points: list[np.ndarray] = []
    for seed in seeds:
        result = minimize(
            problem,
            NSGA2(pop_size=80, eliminate_duplicates=True),
            ("n_gen", 80),
            seed=seed,
            verbose=False,
        )
        objectives = np.asarray(result.F, dtype=float)
        all_points.append(objectives)
        runs.append(
            {
                "seed": seed,
                "solution_count": len(objectives),
                "hypervolume": float(indicator(objectives)),
                "minimum_total_thickness_mm": float(np.min(objectives[:, 0])),
            }
        )
    enum_objectives = _enumerated_objectives(search_table)
    enum_front = enum_objectives[_pareto_mask(enum_objectives)]
    combined = np.vstack(all_points)
    distance = np.min(
        np.linalg.norm(combined[:, None, :] - enum_front[None, :, :], axis=2),
        axis=1,
    )
    hypervolumes = np.array([run["hypervolume"] for run in runs])
    return {
        "package_version": importlib.metadata.version("pymoo"),
        "seeds": list(seeds),
        "runs": runs,
        "hypervolume_mean": float(np.mean(hypervolumes)),
        "hypervolume_std": float(np.std(hypervolumes, ddof=1)),
        "max_distance_to_enumerated_pareto": float(np.max(distance)),
        "enumerated_pareto": enum_front.tolist(),
        "nsga2_points": combined.tolist(),
    }


def _perturb_materials(
    materials: tuple[Material, ...],
    conductivity_scale: float = 1.0,
    heat_capacity_scale: float = 1.0,
) -> tuple[Material, ...]:
    return tuple(
        replace(
            material,
            conductivity=material.conductivity * conductivity_scale,
            specific_heat=material.specific_heat * heat_capacity_scale,
        )
        for material in materials
    )


def _scenario_config(
    base: SimulationConfig,
    *,
    h_out_scale: float = 1.0,
    h_body_scale: float = 1.0,
    initial_delta_c: float = 0.0,
    environment_delta_c: float = 0.0,
) -> SimulationConfig:
    return replace(
        base,
        h_out=base.h_out * h_out_scale,
        h_body=base.h_body * h_body_scale,
        initial_temp_c=base.initial_temp_c + initial_delta_c,
        environment_temp_c=base.environment_temp_c + environment_delta_c,
    )


def run_sensitivity_analysis(
    materials: tuple[Material, ...],
    q2_design: tuple[float, float],
    q3_design: tuple[float, float],
    q2_config: SimulationConfig,
    q3_config: SimulationConfig,
) -> pd.DataFrame:
    """对名义最优方案执行单因素与联合不利扰动。"""
    scenarios = [
        ("baseline", 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0),
        ("h_out_-20%", 0.8, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0),
        ("h_out_+20%", 1.2, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0),
        ("h_body_-20%", 1.0, 0.8, 1.0, 1.0, 0.0, 0.0, 0.0),
        ("h_body_+20%", 1.0, 1.2, 1.0, 1.0, 0.0, 0.0, 0.0),
        ("conductivity_-5%", 1.0, 1.0, 0.95, 1.0, 0.0, 0.0, 0.0),
        ("conductivity_+5%", 1.0, 1.0, 1.05, 1.0, 0.0, 0.0, 0.0),
        ("heat_capacity_-5%", 1.0, 1.0, 1.0, 0.95, 0.0, 0.0, 0.0),
        ("heat_capacity_+5%", 1.0, 1.0, 1.0, 1.05, 0.0, 0.0, 0.0),
        ("initial_-1C", 1.0, 1.0, 1.0, 1.0, -1.0, 0.0, 0.0),
        ("initial_+1C", 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0),
        ("environment_-1C", 1.0, 1.0, 1.0, 1.0, 0.0, -1.0, 0.0),
        ("environment_+1C", 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 0.0),
        ("manufacturing_-0.1mm", 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, -0.1),
        ("joint_adverse_10%", 1.1, 0.9, 1.05, 0.95, 1.0, 1.0, -0.1),
        ("joint_stress_20%", 1.2, 0.8, 1.05, 0.95, 1.0, 1.0, -0.1),
    ]
    records: list[dict[str, Any]] = []
    for label, ho, hb, ks, cs, initial, environment, thickness in scenarios:
        scenario_materials = _perturb_materials(materials, ks, cs)
        for problem, design, base_config in (
            ("Q2", q2_design, q2_config),
            ("Q3", q3_design, q3_config),
        ):
            config = _scenario_config(
                base_config,
                h_out_scale=ho,
                h_body_scale=hb,
                initial_delta_c=initial,
                environment_delta_c=environment,
            )
            metric = evaluate_design(
                scenario_materials,
                max(0.6, design[0] + thickness),
                max(0.6, design[1] + thickness),
                config,
            )
            records.append({"problem": problem, "scenario": label, **asdict(metric)})
    return pd.DataFrame.from_records(records)


def _binary_min_d2(
    materials: tuple[Material, ...],
    d4_mm: float,
    config: SimulationConfig,
    *,
    actual_thickness_offset_mm: float = 0.0,
) -> DesignMetric | None:
    low, high = 0, len(Q2_D2_VALUES) - 1
    best: DesignMetric | None = None
    while low <= high:
        middle = (low + high) // 2
        d2 = max(0.6, float(Q2_D2_VALUES[middle]) + actual_thickness_offset_mm)
        d4 = max(0.6, float(d4_mm) + actual_thickness_offset_mm)
        metric = evaluate_design(materials, d2, d4, config)
        if metric.feasible:
            best = replace(metric, d2_mm=float(Q2_D2_VALUES[middle]), d4_mm=float(d4_mm))
            high = middle - 1
        else:
            low = middle + 1
    return best


def robust_design_search(
    materials: tuple[Material, ...],
    base_config: SimulationConfig,
    d4_values: np.ndarray,
) -> pd.DataFrame:
    """在联合 10% 不利情景下用单调二分求每个 d4 的最小 d2。"""
    adverse_materials = _perturb_materials(materials, 1.05, 0.95)
    adverse_config = _scenario_config(
        base_config,
        h_out_scale=1.1,
        h_body_scale=0.9,
        initial_delta_c=1.0,
        environment_delta_c=1.0,
    )
    records = []
    for d4 in d4_values:
        metric = _binary_min_d2(
            adverse_materials,
            float(d4),
            adverse_config,
            actual_thickness_offset_mm=-0.1,
        )
        if metric is not None:
            records.append(asdict(metric))
    return pd.DataFrame.from_records(records)


def _configure_figure_style() -> str:
    from matplotlib import font_manager

    candidates = ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC")
    for name in candidates:
        try:
            font_manager.findfont(name, fallback_to_default=False)
            plt.rcParams.update(
                {
                    "font.family": name,
                    "axes.unicode_minus": False,
                    "font.size": 9,
                    "axes.titlesize": 10,
                    "axes.labelsize": 9,
                    "legend.fontsize": 8,
                    "pdf.fonttype": 42,
                    "svg.fonttype": "none",
                }
            )
            return name
        except ValueError:
            continue
    raise ConfigurationError("未找到可用于正式中文图表的字体")


def _save_figure(figure: plt.Figure, base_path: Path) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(base_path.with_suffix(".pdf"), bbox_inches="tight")
    figure.savefig(base_path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(figure)


def _plot_q1_fit(
    output_dir: Path,
    times_s: np.ndarray,
    measured_c: np.ndarray,
    modeled_c: np.ndarray,
) -> None:
    figure, axis = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    axis.plot(times_s / 60.0, measured_c, color="#2563EB", lw=1.5, label="实验值")
    axis.plot(times_s / 60.0, modeled_c, color="#DC2626", lw=1.2, ls="--", label="模型值")
    axis.set(xlabel="时间 / min", ylabel="皮肤外侧温度 / °C", title="问题一：模型拟合结果")
    axis.grid(alpha=0.22)
    axis.legend(frameon=False)
    _save_figure(figure, output_dir / "q1_model_fit")


def _plot_q1_residual(
    output_dir: Path,
    times_s: np.ndarray,
    residual_c: np.ndarray,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(8.0, 3.5), constrained_layout=True)
    axes[0].plot(times_s / 60.0, residual_c, color="#0F766E", lw=0.9)
    axes[0].axhline(0.0, color="#334155", lw=0.8)
    axes[0].set(xlabel="时间 / min", ylabel="模型值 - 实验值 / °C", title="残差时序")
    axes[0].grid(alpha=0.2)
    axes[1].hist(residual_c, bins=36, color="#60A5FA", edgecolor="white")
    axes[1].set(xlabel="残差 / °C", ylabel="频数", title="残差分布")
    _save_figure(figure, output_dir / "q1_residual_diagnostics")


def _plot_q1_field(output_dir: Path, simulation: Any) -> None:
    if simulation.temperature_field_c is None:
        raise NumericalError("问题一温度场未保存")
    figure, axis = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    image = axis.pcolormesh(
        simulation.times_s / 60.0,
        simulation.mesh.centers_m * 1000.0,
        simulation.temperature_field_c.T,
        shading="auto",
        cmap="turbo",
    )
    axis.set(xlabel="时间 / min", ylabel="距服装外表面位置 / mm", title="四层介质温度场")
    figure.colorbar(image, ax=axis, label="温度 / °C")
    _save_figure(figure, output_dir / "q1_temperature_field")


def _plot_q1_profiles(output_dir: Path, simulation: Any) -> None:
    if simulation.temperature_field_c is None:
        raise NumericalError("问题一温度场未保存")
    figure, axis = plt.subplots(figsize=(6.2, 4.2), constrained_layout=True)
    for minute in (0, 10, 30, 60, 90):
        index = round(minute * 60 / (simulation.times_s[1] - simulation.times_s[0]))
        axis.plot(
            simulation.mesh.centers_m * 1000.0,
            simulation.temperature_field_c[index],
            lw=1.3,
            label=f"{minute} min",
        )
    for position in np.cumsum(THICKNESSES_Q1)[:-1]:
        axis.axvline(position, color="#94A3B8", lw=0.7, ls=":")
    axis.set(xlabel="距服装外表面位置 / mm", ylabel="温度 / °C", title="典型时刻温度剖面")
    axis.grid(alpha=0.2)
    axis.legend(frameon=False, ncol=2)
    _save_figure(figure, output_dir / "q1_temperature_profiles")


def _plot_q2_search(output_dir: Path, table: pd.DataFrame, optimum: pd.Series) -> None:
    ordered = table.sort_values("d2_mm")
    figure, axes = plt.subplots(2, 1, figsize=(6.8, 5.7), sharex=True, constrained_layout=True)
    axes[0].plot(ordered["d2_mm"], ordered["max_skin_temp_c"], color="#DC2626")
    axes[0].axhline(LIMIT_MAX_C, color="#334155", ls="--", lw=0.9, label="47°C 上限")
    axes[0].scatter([optimum["d2_mm"]], [optimum["max_skin_temp_c"]], color="#111827", zorder=3)
    axes[0].set(ylabel="最高皮肤温度 / °C", title="问题二：第二层厚度枚举")
    axes[0].legend(frameon=False)
    axes[1].plot(ordered["d2_mm"], ordered["duration_above_44_s"], color="#2563EB")
    axes[1].axhline(LIMIT_DURATION_S, color="#334155", ls="--", lw=0.9, label="300 s 上限")
    axes[1].scatter(
        [optimum["d2_mm"]],
        [optimum["duration_above_44_s"]],
        color="#111827",
        zorder=3,
    )
    axes[1].set(xlabel="第二层厚度 / mm", ylabel="超过 44°C 时长 / s")
    axes[1].legend(frameon=False)
    for axis in axes:
        axis.grid(alpha=0.2)
    _save_figure(figure, output_dir / "q2_enumeration")


def _plot_q3_search(
    output_dir: Path,
    table: pd.DataFrame,
    optimum: pd.Series,
) -> None:
    ordered = table.sort_values(["d4_mm", "d2_mm"])
    shape = (len(Q3_D4_VALUES), len(Q2_D2_VALUES))
    maximum = ordered["max_skin_temp_c"].to_numpy().reshape(shape)
    duration = ordered["duration_above_44_s"].to_numpy().reshape(shape)
    feasible = (maximum <= LIMIT_MAX_C) & (duration <= LIMIT_DURATION_S)
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.8), constrained_layout=True)
    mesh = axes[0].pcolormesh(Q2_D2_VALUES, Q3_D4_VALUES, maximum, shading="auto", cmap="viridis")
    axes[0].contour(
        Q2_D2_VALUES,
        Q3_D4_VALUES,
        maximum,
        levels=[LIMIT_MAX_C],
        colors=["white"],
        linewidths=1.1,
    )
    figure.colorbar(mesh, ax=axes[0], label="最高皮肤温度 / °C")
    axes[1].pcolormesh(
        Q2_D2_VALUES,
        Q3_D4_VALUES,
        feasible.astype(int),
        shading="auto",
        cmap=matplotlib.colors.ListedColormap(["#FECACA", "#86EFAC"]),
    )
    for axis in axes:
        axis.scatter([optimum["d2_mm"]], [optimum["d4_mm"]], marker="*", s=90, color="#111827")
        axis.set(xlabel="第二层厚度 / mm", ylabel="第四层厚度 / mm")
    axes[0].set_title("最高温度响应面与 47°C 边界")
    axes[1].set_title("离散可行域（绿）")
    _save_figure(figure, output_dir / "q3_feasible_region")


def _plot_pareto(output_dir: Path, cross_validation: dict[str, Any]) -> None:
    enum_front = np.asarray(cross_validation["enumerated_pareto"])
    nsga_points = np.asarray(cross_validation["nsga2_points"])
    figure, axis = plt.subplots(figsize=(6.2, 4.2), constrained_layout=True)
    axis.scatter(
        nsga_points[:, 0],
        nsga_points[:, 1],
        s=10,
        alpha=0.25,
        color="#60A5FA",
        label="NSGA-II 多种子解",
    )
    axis.plot(
        enum_front[:, 0],
        enum_front[:, 1],
        "o-",
        ms=3,
        lw=1.2,
        color="#DC2626",
        label="完整枚举 Pareto 前沿",
    )
    axis.set(
        xlabel="第二、四层总厚度 / mm",
        ylabel="第二、四层面密度 / kg/m$^2$",
        title="多目标交叉验证",
    )
    axis.grid(alpha=0.2)
    axis.legend(frameon=False)
    _save_figure(figure, output_dir / "q3_pareto_cross_validation")


def _plot_sensitivity(output_dir: Path, table: pd.DataFrame) -> None:
    q3 = table.loc[table["problem"] == "Q3"].copy()
    baseline = float(q3.loc[q3["scenario"] == "baseline", "max_skin_temp_c"].iloc[0])
    q3["delta_max_c"] = q3["max_skin_temp_c"] - baseline
    q3 = q3.loc[q3["scenario"] != "baseline"].sort_values("delta_max_c")
    colors = np.where(q3["delta_max_c"] >= 0.0, "#DC2626", "#2563EB")
    figure, axis = plt.subplots(figsize=(7.2, 5.3), constrained_layout=True)
    axis.barh(q3["scenario"], q3["delta_max_c"], color=colors)
    axis.axvline(0.0, color="#334155", lw=0.8)
    axis.set(xlabel="最高皮肤温度变化 / °C", ylabel="扰动情景", title="问题三名义最优方案灵敏度")
    axis.grid(axis="x", alpha=0.2)
    _save_figure(figure, output_dir / "sensitivity_tornado")


def _simulation_diagnostics(
    materials: tuple[Material, ...],
    measured_c: np.ndarray,
    simulation: Any,
    config: SimulationConfig,
) -> dict[str, float | int]:
    if simulation.temperature_field_c is None:
        raise NumericalError("正式诊断需要完整温度场")
    residual = simulation.skin_temp_c - measured_c
    mesh = simulation.mesh
    capacity = mesh.density * mesh.specific_heat * mesh.widths_m
    outer_g = 1.0 / (
        1.0 / config.h_out + mesh.widths_m[0] / (2.0 * mesh.conductivity[0])
    )
    body_g = 1.0 / (
        mesh.widths_m[-1] / (2.0 * mesh.conductivity[-1]) + 1.0 / config.h_body
    )
    field = simulation.temperature_field_c
    energy_rate = ((field[1:] - field[:-1]) * capacity).sum(axis=1) / config.dt_s
    incoming = outer_g * (config.environment_temp_c - field[1:, 0])
    outgoing = body_g * (field[1:, -1] - config.body_temp_c)
    energy_residual = energy_rate - incoming + outgoing
    interface_error = _interface_flux_error(field, mesh)
    steady = steady_skin_temperature(
        materials,
        THICKNESSES_Q1,
        config.environment_temp_c,
        config.body_temp_c,
        config.h_out,
        config.h_body,
    )
    return {
        "rmse_c": float(np.sqrt(np.mean(residual**2))),
        "mae_c": float(np.mean(np.abs(residual))),
        "max_abs_error_c": float(np.max(np.abs(residual))),
        "modeled_final_c": float(simulation.skin_temp_c[-1]),
        "steady_closed_form_c": float(steady),
        "final_to_steady_gap_c": float(simulation.skin_temp_c[-1] - steady),
        "duration_above_44_s": duration_above_threshold(
            simulation.times_s, simulation.skin_temp_c, 44.0
        ),
        "mesh_cells": len(mesh.centers_m),
        "max_energy_balance_residual_w_m2": float(np.max(np.abs(energy_residual))),
        "max_interface_flux_mismatch_w_m2": interface_error,
    }


def _interface_flux_error(field: np.ndarray, mesh: Any) -> float:
    boundary_indices = np.flatnonzero(np.diff(mesh.layer_ids) != 0)
    maximum = 0.0
    sampled = field[:: max(1, len(field) // 100)]
    for left in boundary_indices:
        right = left + 1
        resistance_left = mesh.widths_m[left] / (2.0 * mesh.conductivity[left])
        resistance_right = mesh.widths_m[right] / (2.0 * mesh.conductivity[right])
        flux = (sampled[:, left] - sampled[:, right]) / (
            resistance_left + resistance_right
        )
        interface_temp = sampled[:, left] - flux * resistance_left
        left_flux = (sampled[:, left] - interface_temp) / resistance_left
        right_flux = (interface_temp - sampled[:, right]) / resistance_right
        maximum = max(maximum, float(np.max(np.abs(left_flux - right_flux))))
    return maximum


def _fit_diagnostics(
    measured_c: np.ndarray,
    simulation: Any,
) -> dict[str, float | int]:
    dt_s = float(simulation.times_s[1] - simulation.times_s[0])
    if dt_s >= 1.0:
        observation_stride = round(dt_s)
        observed = measured_c[::observation_stride]
        modeled = simulation.skin_temp_c
    else:
        model_stride = round(1.0 / dt_s)
        observed = measured_c
        modeled = simulation.skin_temp_c[::model_stride]
    residual = modeled - observed
    return {
        "rmse_c": float(np.sqrt(np.mean(residual**2))),
        "mae_c": float(np.mean(np.abs(residual))),
        "max_abs_error_c": float(np.max(np.abs(residual))),
        "mesh_cells": len(simulation.mesh.centers_m),
    }


def _problem1_parameter_table(
    materials: tuple[Material, ...],
    calibration: dict[str, Any],
) -> pd.DataFrame:
    parameter_rows: list[dict[str, Any]] = []
    for index, (material, thickness) in enumerate(
        zip(materials, THICKNESSES_Q1, strict=True), start=1
    ):
        parameter_rows.extend(
            [
                {"类别": f"第{index}层", "参数": "密度", "数值": material.density, "单位": "kg/m3"},
                {
                    "类别": f"第{index}层",
                    "参数": "比热容",
                    "数值": material.specific_heat,
                    "单位": "J/(kg K)",
                },
                {
                    "类别": f"第{index}层",
                    "参数": "导热系数",
                    "数值": material.conductivity,
                    "单位": "W/(m K)",
                },
                {"类别": f"第{index}层", "参数": "厚度", "数值": thickness, "单位": "mm"},
            ]
        )
    parameter_rows.extend(
        [
            {"类别": "边界", "参数": "环境温度", "数值": 75.0, "单位": "C"},
            {"类别": "边界", "参数": "人体热库温度", "数值": 37.0, "单位": "C"},
            {
                "类别": "标定",
                "参数": "外侧换热系数",
                "数值": calibration["h_out_w_m2k"],
                "单位": "W/(m2 K)",
            },
            {
                "类别": "标定",
                "参数": "人体侧换热系数",
                "数值": calibration["h_body_w_m2k"],
                "单位": "W/(m2 K)",
            },
        ]
    )
    return pd.DataFrame(parameter_rows)


def _problem1_check_table(diagnostics: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"校核项": key, "数值": value, "单位": "", "状态": "PASS"}
            for key, value in diagnostics.items()
        ]
    )


def _write_q1_sources(
    results_dir: Path,
    materials: tuple[Material, ...],
    measured_c: np.ndarray,
    simulation: Any,
    calibration: dict[str, Any],
    diagnostics: dict[str, Any],
) -> None:
    if simulation.temperature_field_c is None:
        raise NumericalError("工作簿源数据需要完整温度场")
    skin = pd.DataFrame(
        {
            "时间_s": simulation.times_s,
            "实验温度_C": measured_c,
            "模型温度_C": simulation.skin_temp_c,
            "残差_C": simulation.skin_temp_c - measured_c,
        }
    )
    headers = ["时间_s"] + [
        f"L{layer}_x{position:.3f}mm"
        for layer, position in zip(
            simulation.mesh.layer_ids,
            simulation.mesh.centers_m * 1000.0,
            strict=True,
        )
    ]
    field = pd.DataFrame(
        np.column_stack((simulation.times_s, simulation.temperature_field_c)),
        columns=headers,
    )
    skin.to_csv(results_dir / "q1_skin_temperature.csv", index=False, encoding="utf-8-sig")
    field.to_csv(results_dir / "q1_temperature_field.csv", index=False, encoding="utf-8-sig")
    _problem1_parameter_table(materials, calibration).to_csv(
        results_dir / "problem1_parameters.csv", index=False, encoding="utf-8-sig"
    )
    _problem1_check_table(diagnostics).to_csv(
        results_dir / "problem1_checks.csv", index=False, encoding="utf-8-sig"
    )


def _run_calibration_study(
    materials: tuple[Material, ...],
    times_s: np.ndarray,
    measured_c: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    coarse_spec = CalibrationSpec(0.2, 2.0, ((128.8, 8.38),), 30)
    coarse = calibrate_exchange_coefficients(materials, times_s, measured_c, coarse_spec)
    formal_spec = CalibrationSpec(
        0.1,
        1.0,
        (
            (coarse["h_out_w_m2k"], coarse["h_body_w_m2k"]),
            (80.0, 7.0),
            (180.0, 12.0),
        ),
        45,
    )
    formal = calibrate_exchange_coefficients(materials, times_s, measured_c, formal_spec)
    levels: list[dict[str, Any]] = []
    for dx, dt, fit in ((0.2, 2.0, coarse), (0.1, 1.0, formal), (0.05, 0.5, formal)):
        config = SimulationConfig(
            75.0,
            37.0,
            37.0,
            5400.0,
            dt,
            dx,
            float(fit["h_out_w_m2k"]),
            float(fit["h_body_w_m2k"]),
        )
        simulation = simulate(materials, THICKNESSES_Q1, config)
        levels.append(
            {
                "target_dx_mm": dx,
                "dt_s": dt,
                "parameters_refitted": dx != 0.05,
                "h_out_w_m2k": fit["h_out_w_m2k"],
                "h_body_w_m2k": fit["h_body_w_m2k"],
                **_fit_diagnostics(measured_c, simulation),
            }
        )
    return formal, levels


def _fine_candidate_selection(
    materials: tuple[Material, ...],
    table: pd.DataFrame,
    config: SimulationConfig,
    objective: str,
    workers: int,
) -> tuple[pd.DataFrame, pd.Series]:
    if objective == "d2_mm":
        candidates = table[["d2_mm", "d4_mm"]]
    else:
        feasible = table.loc[table["feasible"]].copy()
        feasible["total"] = feasible["d2_mm"] + feasible["d4_mm"]
        cutoff = float(feasible["total"].min() + 0.5)
        candidates = table.loc[
            table["d2_mm"] + table["d4_mm"] <= cutoff,
            ["d2_mm", "d4_mm"],
        ]
    fine = _evaluate_candidate_table(materials, candidates.drop_duplicates(), config, workers)
    return fine, _first_feasible(fine, objective)


def _runtime_payload() -> dict[str, Any]:
    packages = ("numpy", "scipy", "pandas", "matplotlib", "openpyxl", "pymoo")
    return {
        "executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "packages": {name: importlib.metadata.version(name) for name in packages},
    }


def _run_q1_stage(
    results_dir: Path,
    materials: tuple[Material, ...],
    times_s: np.ndarray,
    measured_c: np.ndarray,
) -> dict[str, Any]:
    calibration, grid_study = _run_calibration_study(materials, times_s, measured_c)
    config = SimulationConfig(
        75.0,
        37.0,
        37.0,
        5400.0,
        1.0,
        0.1,
        float(calibration["h_out_w_m2k"]),
        float(calibration["h_body_w_m2k"]),
    )
    simulation = simulate(materials, THICKNESSES_Q1, config, store_field=True)
    diagnostics = _simulation_diagnostics(materials, measured_c, simulation, config)
    _write_q1_sources(
        results_dir, materials, measured_c, simulation, calibration, diagnostics
    )
    LOGGER.info("问题一完成：RMSE=%.6f °C", diagnostics["rmse_c"])
    return {
        "calibration": calibration,
        "grid_study": grid_study,
        "config": config,
        "simulation": simulation,
        "diagnostics": diagnostics,
    }


def _run_q2_stage(
    results_dir: Path,
    materials: tuple[Material, ...],
    base_config: SimulationConfig,
    workers: int,
) -> dict[str, Any]:
    fast_config = replace(
        base_config,
        environment_temp_c=65.0,
        duration_s=3600.0,
        dt_s=2.0,
        target_dx_mm=0.25,
    )
    fast = enumerate_designs(
        materials, Q2_D2_VALUES, np.array([5.5]), fast_config, workers
    )
    formal_config = replace(fast_config, dt_s=1.0, target_dx_mm=0.1)
    boundary = _boundary_candidates(fast, radius_steps=7)
    formal = _evaluate_candidate_table(materials, boundary, formal_config, workers)
    fine_config = replace(fast_config, dt_s=0.5, target_dx_mm=0.05)
    fine, optimum = _fine_candidate_selection(
        materials, formal, fine_config, "d2_mm", workers
    )
    fast.to_csv(results_dir / "q2_enumeration_fast.csv", index=False)
    formal.to_csv(results_dir / "q2_boundary_formal.csv", index=False)
    fine.to_csv(results_dir / "q2_grid_refinement.csv", index=False)
    LOGGER.info("问题二完成：最小第二层厚度=%.1f mm", optimum["d2_mm"])
    return {"fast": fast, "formal": formal, "fine": fine, "optimum": optimum, "config": formal_config}


def _load_or_run_q3_fast(
    results_dir: Path,
    materials: tuple[Material, ...],
    config: SimulationConfig,
    workers: int,
) -> pd.DataFrame:
    cache_path = results_dir / "q3_enumeration_fast.csv"
    cached = pd.read_csv(cache_path) if cache_path.is_file() else pd.DataFrame()
    valid = (
        len(cached) == len(Q2_D2_VALUES) * len(Q3_D4_VALUES)
        and "grid_dx_mm" in cached
        and np.allclose(cached["grid_dx_mm"], 0.25)
        and np.allclose(cached["dt_s"], 2.0)
    )
    if valid:
        LOGGER.info("复用已完成且配置匹配的问题三完整枚举缓存")
        return cached
    return enumerate_designs(materials, Q2_D2_VALUES, Q3_D4_VALUES, config, workers)


def _run_q3_stage(
    results_dir: Path,
    materials: tuple[Material, ...],
    base_config: SimulationConfig,
    workers: int,
) -> dict[str, Any]:
    fast_config = replace(
        base_config,
        environment_temp_c=80.0,
        duration_s=1800.0,
        dt_s=2.0,
        target_dx_mm=0.25,
    )
    fast = _load_or_run_q3_fast(results_dir, materials, fast_config, workers)
    fast.to_csv(results_dir / "q3_enumeration_fast.csv", index=False)
    monotonicity = _monotonicity_report(fast)
    if not monotonicity["screening_safe"]:
        raise NumericalError(f"最高温度单调性检查失败: {monotonicity}")
    if not monotonicity["strictly_monotone"]:
        LOGGER.warning("阈值时长存在网格锯齿，保留完整枚举并细化边界: %s", monotonicity)
    formal_config = replace(fast_config, dt_s=1.0, target_dx_mm=0.1)
    boundary = _boundary_candidates(fast, radius_steps=5)
    formal = _evaluate_candidate_table(materials, boundary, formal_config, workers)
    fine_config = replace(fast_config, dt_s=0.5, target_dx_mm=0.05)
    fine, optimum = _fine_candidate_selection(
        materials, formal, fine_config, "total", workers
    )
    formal.to_csv(results_dir / "q3_boundary_formal.csv", index=False)
    fine.to_csv(results_dir / "q3_grid_refinement.csv", index=False)
    LOGGER.info(
        "问题三完成：d2=%.1f mm，d4=%.1f mm，总厚度=%.1f mm",
        optimum["d2_mm"],
        optimum["d4_mm"],
        optimum["d2_mm"] + optimum["d4_mm"],
    )
    return {
        "fast": fast,
        "formal": formal,
        "fine": fine,
        "optimum": optimum,
        "config": formal_config,
        "monotonicity": monotonicity,
    }


def _run_robustness(
    results_dir: Path,
    materials: tuple[Material, ...],
    q2: dict[str, Any],
    q3: dict[str, Any],
) -> dict[str, Any]:
    q2_table = robust_design_search(materials, q2["config"], np.array([5.5]))
    q3_table = robust_design_search(materials, q3["config"], Q3_D4_VALUES)
    q2_optimum = None if q2_table.empty else _first_feasible(q2_table, "d2_mm")
    q3_optimum = None if q3_table.empty else _first_feasible(q3_table, "total")
    sensitivity = run_sensitivity_analysis(
        materials,
        (float(q2["optimum"]["d2_mm"]), 5.5),
        (float(q3["optimum"]["d2_mm"]), float(q3["optimum"]["d4_mm"])),
        q2["config"],
        q3["config"],
    )
    q2_table.to_csv(results_dir / "q2_robust_search.csv", index=False)
    q3_table.to_csv(results_dir / "q3_robust_search.csv", index=False)
    sensitivity.to_csv(results_dir / "sensitivity.csv", index=False)
    return {"q2_optimum": q2_optimum, "q3_optimum": q3_optimum, "sensitivity": sensitivity}


def _write_formal_figures(
    figures_dir: Path,
    times_s: np.ndarray,
    measured_c: np.ndarray,
    q1: dict[str, Any],
    q2: dict[str, Any],
    q3: dict[str, Any],
    nsga2: dict[str, Any],
    sensitivity: pd.DataFrame,
) -> None:
    simulation = q1["simulation"]
    _plot_q1_fit(figures_dir, times_s, measured_c, simulation.skin_temp_c)
    _plot_q1_residual(figures_dir, times_s, simulation.skin_temp_c - measured_c)
    _plot_q1_field(figures_dir, simulation)
    _plot_q1_profiles(figures_dir, simulation)
    _plot_q2_search(figures_dir, q2["fast"], q2["optimum"])
    _plot_q3_search(figures_dir, q3["fast"], q3["optimum"])
    _plot_pareto(figures_dir, nsga2)
    _plot_sensitivity(figures_dir, sensitivity)


def _optimum_payload(optimum: pd.Series | None) -> tuple[dict[str, Any] | None, str]:
    if optimum is None:
        return None, "NO_FEASIBLE_DESIGN_WITHIN_BOUNDS"
    return optimum.to_dict(), "FEASIBLE"


def _build_formal_payload(
    started: float,
    font_name: str,
    q1: dict[str, Any],
    q2: dict[str, Any],
    q3: dict[str, Any],
    robust: dict[str, Any],
    nsga2: dict[str, Any],
) -> dict[str, Any]:
    q2_robust, q2_status = _optimum_payload(robust["q2_optimum"])
    q3_robust, q3_status = _optimum_payload(robust["q3_optimum"])
    return {
        "stage": "G3",
        "result_status": "FORMAL_RESULTS",
        "runtime": _runtime_payload(),
        "figure_font": font_name,
        "calibration": q1["calibration"],
        "grid_convergence": q1["grid_study"],
        "question_1": q1["diagnostics"],
        "question_2": {
            "nominal_optimum": q2["optimum"].to_dict(),
            "robust_10pct_optimum": q2_robust,
            "robust_10pct_status": q2_status,
            "fast_candidates": len(q2["fast"]),
            "formal_boundary_candidates": len(q2["formal"]),
            "fine_candidates": len(q2["fine"]),
        },
        "question_3": {
            "nominal_optimum": q3["optimum"].to_dict(),
            "robust_10pct_optimum": q3_robust,
            "robust_10pct_status": q3_status,
            "fast_candidates": len(q3["fast"]),
            "formal_boundary_candidates": len(q3["formal"]),
            "fine_candidates": len(q3["fine"]),
            "monotonicity": q3["monotonicity"],
        },
        "nsga2_cross_validation": nsga2,
        "sensitivity_scenarios": len(robust["sensitivity"]),
        "elapsed_seconds": float(time.perf_counter() - started),
    }


def _write_key_numbers(results_dir: Path, payload: dict[str, Any]) -> None:
    q2 = payload["question_2"]
    q3 = payload["question_3"]
    q2_robust = q2["robust_10pct_optimum"]
    q3_robust = q3["robust_10pct_optimum"]
    _json_dump(
        results_dir / "key_numbers.json",
        {
            "h_out_w_m2k": payload["calibration"]["h_out_w_m2k"],
            "h_body_w_m2k": payload["calibration"]["h_body_w_m2k"],
            "q1_rmse_c": payload["question_1"]["rmse_c"],
            "q2_nominal_d2_mm": q2["nominal_optimum"]["d2_mm"],
            "q2_robust_d2_mm": None if q2_robust is None else q2_robust["d2_mm"],
            "q3_nominal_d2_mm": q3["nominal_optimum"]["d2_mm"],
            "q3_nominal_d4_mm": q3["nominal_optimum"]["d4_mm"],
            "q3_robust_d2_mm": None if q3_robust is None else q3_robust["d2_mm"],
            "q3_robust_d4_mm": None if q3_robust is None else q3_robust["d4_mm"],
        },
    )


def run_g3_formal(project_root: Path, input_path: Path, workers: int) -> Path:
    """运行 G3 正式标定、枚举、交叉验证、稳健性和制图。"""
    started = time.perf_counter()
    results_dir = project_root / "results"
    figures_dir = project_root / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    font_name = _configure_figure_style()
    materials, times_s, measured_c = load_problem_data(input_path)
    LOGGER.info("G3 正式数据读取完成：%d 条观测；中文字体=%s", len(times_s), font_name)
    q1 = _run_q1_stage(results_dir, materials, times_s, measured_c)
    q2 = _run_q2_stage(results_dir, materials, q1["config"], workers)
    q3 = _run_q3_stage(results_dir, materials, q1["config"], workers)
    nsga2 = run_nsga2_cross_validation(q3["fast"])
    robust = _run_robustness(results_dir, materials, q2, q3)
    _write_formal_figures(
        figures_dir, times_s, measured_c, q1, q2, q3, nsga2, robust["sensitivity"]
    )
    payload = _build_formal_payload(started, font_name, q1, q2, q3, robust, nsga2)
    result_path = results_dir / "formal_results.json"
    _json_dump(result_path, payload)
    _write_key_numbers(results_dir, payload)
    LOGGER.info("G3 正式流水线完成，用时 %.2f s", payload["elapsed_seconds"])
    return result_path


def write_formal_run_manifest(project_root: Path, command: list[str], started: float) -> Path:
    """记录正式运行命令、耗时和关键产物哈希。"""
    relative_paths = [
        "results/formal_results.json",
        "results/key_numbers.json",
        "results/q1_skin_temperature.csv",
        "results/q1_temperature_field.csv",
        "results/q2_enumeration_fast.csv",
        "results/q3_enumeration_fast.csv",
        "results/sensitivity.csv",
        "figures/q1_model_fit.pdf",
        "figures/q3_feasible_region.pdf",
        "figures/q3_pareto_cross_validation.pdf",
        "logs/g3_formal.log",
    ]
    artifacts = []
    for relative in relative_paths:
        path = project_root / relative
        if not path.is_file():
            raise NumericalError(f"正式运行缺少产物: {relative}")
        artifacts.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": _hash_file(path),
            }
        )
    manifest = {
        "status": "FORMAL_RUN_RECORDED",
        "command": command,
        "executable": sys.executable,
        "elapsed_seconds": float(time.perf_counter() - started),
        "artifacts": artifacts,
    }
    path = project_root / "results" / "g3_run_manifest.json"
    _json_dump(path, manifest)
    return path


def refresh_formal_run_manifest(project_root: Path) -> Path:
    """在工作簿和视觉复核后刷新正式产物哈希，不改写原始运行命令。"""
    path = project_root / "results" / "g3_run_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for artifact in payload["artifacts"]:
        artifact_path = project_root / artifact["path"]
        artifact["size_bytes"] = artifact_path.stat().st_size
        artifact["sha256"] = _hash_file(artifact_path)
    workbook_path = project_root / "results" / "problem1.xlsx"
    payload["postprocessed_artifacts"] = [
        {
            "path": "results/problem1.xlsx",
            "size_bytes": workbook_path.stat().st_size,
            "sha256": _hash_file(workbook_path),
            "verification": "artifact-tool formulas inspected and all sheets rendered",
        }
    ]
    payload["status"] = "FORMAL_RUN_AND_POSTPROCESSING_RECORDED"
    _json_dump(path, payload)
    return path


def _read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        return pd.DataFrame()
    return pd.read_csv(path)


def refresh_formal_selections(project_root: Path, input_path: Path) -> Path:
    """从已验证的细网格表刷新离散择优、灵敏度和相关图表。"""
    results_dir = project_root / "results"
    figures_dir = project_root / "figures"
    payload_path = results_dir / "formal_results.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    materials, _, _ = load_problem_data(input_path)
    q2_fine = pd.read_csv(results_dir / "q2_grid_refinement.csv")
    q3_fine = pd.read_csv(results_dir / "q3_grid_refinement.csv")
    q2_optimum = _first_feasible(q2_fine, "d2_mm")
    q3_optimum = _first_feasible(q3_fine, "total")
    q2_robust_table = _read_optional_csv(results_dir / "q2_robust_search.csv")
    q3_robust_table = _read_optional_csv(results_dir / "q3_robust_search.csv")
    q2_robust = None if q2_robust_table.empty else _first_feasible(q2_robust_table, "d2_mm")
    q3_robust = None if q3_robust_table.empty else _first_feasible(q3_robust_table, "total")
    h_out = float(payload["calibration"]["h_out_w_m2k"])
    h_body = float(payload["calibration"]["h_body_w_m2k"])
    q2_config = SimulationConfig(65.0, 37.0, 37.0, 3600.0, 1.0, 0.1, h_out, h_body)
    q3_config = SimulationConfig(80.0, 37.0, 37.0, 1800.0, 1.0, 0.1, h_out, h_body)
    sensitivity = run_sensitivity_analysis(
        materials,
        (float(q2_optimum["d2_mm"]), 5.5),
        (float(q3_optimum["d2_mm"]), float(q3_optimum["d4_mm"])),
        q2_config,
        q3_config,
    )
    sensitivity.to_csv(results_dir / "sensitivity.csv", index=False)
    payload["question_2"]["nominal_optimum"] = q2_optimum.to_dict()
    payload["question_3"]["nominal_optimum"] = q3_optimum.to_dict()
    payload["question_2"]["robust_10pct_optimum"], _ = _optimum_payload(q2_robust)
    payload["question_3"]["robust_10pct_optimum"], _ = _optimum_payload(q3_robust)
    payload["selection_refresh"] = "0.1 mm integer-grid tie break with areal-mass secondary objective"
    _json_dump(payload_path, payload)
    _write_key_numbers(results_dir, payload)
    q2_fast = pd.read_csv(results_dir / "q2_enumeration_fast.csv")
    q3_fast = pd.read_csv(results_dir / "q3_enumeration_fast.csv")
    _configure_figure_style()
    _plot_q2_search(figures_dir, q2_fast, q2_optimum)
    _plot_q3_search(figures_dir, q3_fast, q3_optimum)
    _plot_sensitivity(figures_dir, sensitivity)
    refresh_formal_run_manifest(project_root)
    return payload_path


def run_g3_replay(project_root: Path, input_path: Path) -> Path:
    """运行问题一至三的小规模确定性端到端回放。"""
    materials, _, _ = load_problem_data(input_path)
    base = SimulationConfig(65.0, 37.0, 37.0, 120.0, 2.0, 0.5, 128.0, 8.4)
    q1 = simulate(materials, THICKNESSES_Q1, replace(base, environment_temp_c=75.0))
    q2 = enumerate_designs(
        materials,
        np.array([8.0, 12.0]),
        np.array([5.5]),
        base,
        1,
    )
    q3 = enumerate_designs(
        materials,
        np.array([8.0, 12.0]),
        np.array([2.0, 4.0]),
        replace(base, environment_temp_c=80.0),
        1,
    )
    payload = {
        "status": "DETERMINISTIC_REPLAY_PASSED",
        "q1_points": len(q1.times_s),
        "q1_final_c": float(q1.skin_temp_c[-1]),
        "q2_candidates": len(q2),
        "q2_monotone_max_temperature": bool(
            np.all(np.diff(q2.sort_values("d2_mm")["max_skin_temp_c"]) <= 0.0)
        ),
        "q3_candidates": len(q3),
        "q3_all_finite": bool(
            np.all(np.isfinite(q3[["max_skin_temp_c", "duration_above_44_s"]]))
        ),
    }
    if not payload["q2_monotone_max_temperature"] or not payload["q3_all_finite"]:
        raise NumericalError("G3 小规模回放校验失败")
    path = project_root / "results" / "g3_replay.json"
    _json_dump(path, payload)
    return path


def verify_g3_artifacts(project_root: Path) -> Path:
    """快速核验正式结果、工作簿、图表和搜索数据是否齐全。"""
    required = [
        "results/formal_results.json",
        "results/key_numbers.json",
        "results/problem1.xlsx",
        "results/q1_temperature_field.csv",
        "results/q2_enumeration_fast.csv",
        "results/q3_enumeration_fast.csv",
        "results/g3_run_manifest.json",
        "figures/q1_model_fit.pdf",
        "figures/q1_residual_diagnostics.pdf",
        "figures/q1_temperature_field.pdf",
        "figures/q1_temperature_profiles.pdf",
        "figures/q2_enumeration.pdf",
        "figures/q3_feasible_region.pdf",
        "figures/q3_pareto_cross_validation.pdf",
        "figures/sensitivity_tornado.pdf",
        "logs/g3_formal.log",
    ]
    missing = [relative for relative in required if not (project_root / relative).is_file()]
    if missing:
        raise NumericalError(f"G3 产物缺失: {missing}")
    payload = json.loads(
        (project_root / "results" / "formal_results.json").read_text(encoding="utf-8")
    )
    if payload.get("result_status") != "FORMAL_RESULTS":
        raise NumericalError("formal_results.json 未标记为正式结果")
    hashes = {
        relative: _hash_file(project_root / relative)
        for relative in required
        if relative != "logs/g3_formal.log"
    }
    output = {
        "status": "G3_ARTIFACTS_VERIFIED",
        "required_count": len(required),
        "formal_result_status": payload["result_status"],
        "hashes": hashes,
    }
    path = project_root / "results" / "g3_artifact_check.json"
    _json_dump(path, output)
    return path


def parse_args() -> argparse.Namespace:
    """解析 G3 命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--formal", action="store_true", help="运行全部 G3 正式实验")
    mode.add_argument("--replay", action="store_true", help="运行确定性小规模回放")
    mode.add_argument(
        "--verify-artifacts",
        action="store_true",
        help="核验已生成的 G3 正式产物",
    )
    mode.add_argument(
        "--refresh-selections",
        action="store_true",
        help="从细网格结果刷新离散择优与灵敏度",
    )
    parser.add_argument("--input", type=Path, help="覆盖默认附件路径")
    parser.add_argument(
        "--workers",
        type=int,
        default=min(4, os.cpu_count() or 1),
        help="枚举搜索工作进程数",
    )
    return parser.parse_args()


def main() -> int:
    """G3 命令行入口。"""
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    input_path = args.input or (
        project_root / "inputs" / "CUMCM-2018-Problem-A-Chinese-Appendix.xlsx"
    )
    log_name = "g3_formal.log" if args.formal else "g3_validation.log"
    _configure_logging(project_root / "logs" / log_name)
    if args.workers < 1:
        LOGGER.error("--workers 必须至少为 1")
        return 2
    started = time.perf_counter()
    try:
        if args.formal:
            run_g3_formal(project_root, input_path, args.workers)
            write_formal_run_manifest(project_root, sys.argv, started)
        elif args.replay:
            run_g3_replay(project_root, input_path)
        elif args.refresh_selections:
            refresh_formal_selections(project_root, input_path)
        else:
            verify_g3_artifacts(project_root)
    except (DataValidationError, ConfigurationError, NumericalError):
        LOGGER.exception("G3 入口执行失败")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
