"""2018 CUMCM A 题高温防护服传热模型的可复现实现。"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
import math
import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"),
)

import matplotlib
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

matplotlib.use("Agg")
import matplotlib.pyplot as plt

LOGGER = logging.getLogger("cumcm2018a")


# 配置与数据结构
@dataclass(frozen=True)
class Material:
    """单层材料的热物性参数。"""

    name: str
    density: float
    specific_heat: float
    conductivity: float


@dataclass(frozen=True)
class Mesh:
    """界面对齐的一维有限体积网格。"""

    centers_m: np.ndarray
    widths_m: np.ndarray
    density: np.ndarray
    specific_heat: np.ndarray
    conductivity: np.ndarray
    layer_ids: np.ndarray


@dataclass(frozen=True)
class SimulationConfig:
    """单次传热仿真的边界和离散配置。"""

    environment_temp_c: float
    body_temp_c: float
    initial_temp_c: float
    duration_s: float
    dt_s: float
    target_dx_mm: float
    h_out: float
    h_body: float


@dataclass(frozen=True)
class ThomasFactors:
    """三对角矩阵的 Thomas 预消元结果。"""

    pivots: np.ndarray
    multipliers: np.ndarray
    upper: np.ndarray


@dataclass(frozen=True)
class ImplicitSystem:
    """全隐式时间步的常量系数。"""

    factors: ThomasFactors
    mass_over_dt: np.ndarray
    boundary_rhs: np.ndarray
    body_conductance: float


@dataclass(frozen=True)
class SimulationResult:
    """单场景仿真的时间序列与可选温度场。"""

    times_s: np.ndarray
    skin_temp_c: np.ndarray
    mesh: Mesh
    temperature_field_c: np.ndarray | None


# 自定义异常
class DataValidationError(ValueError):
    """附件数据不满足建模要求。"""


class ConfigurationError(ValueError):
    """模型配置或物理参数非法。"""


class NumericalError(RuntimeError):
    """数值求解出现奇异或非物理解。"""


# 数据层
def validate_measurements(times_s: np.ndarray, temperatures_c: np.ndarray) -> None:
    """验证一秒间隔的皮肤温度观测。

    Args:
        times_s: 一维时间数组，单位 s。
        temperatures_c: 同长度温度数组，单位 °C。

    Raises:
        DataValidationError: 形状、缺失、重复或单位范围异常。
    """
    if times_s.ndim != 1 or temperatures_c.ndim != 1:
        raise DataValidationError("时间和温度必须是一维数组")
    if len(times_s) != len(temperatures_c) or len(times_s) < 2:
        raise DataValidationError("时间与温度长度不一致或样本不足")
    if not np.all(np.isfinite(times_s)) or not np.all(np.isfinite(temperatures_c)):
        raise DataValidationError("观测包含缺失或非有限值")
    if not np.isclose(times_s[0], 0.0):
        raise DataValidationError("观测必须从 t=0 开始")
    if not np.allclose(np.diff(times_s), 1.0):
        raise DataValidationError("时间必须严格递增且为 1 s 等间隔")
    if np.any((temperatures_c < -50.0) | (temperatures_c > 200.0)):
        raise DataValidationError("温度超出摄氏温标的合理检查范围")


def load_problem_data(
    workbook_path: Path,
) -> tuple[tuple[Material, ...], np.ndarray, np.ndarray]:
    """读取材料参数和皮肤温度观测。

    Args:
        workbook_path: 题目附件 XLSX 路径。

    Returns:
        四层材料、时间数组和温度数组。

    Raises:
        DataValidationError: 工作表结构或数值字段异常。
    """
    if not workbook_path.is_file():
        raise DataValidationError(f"附件不存在: {workbook_path}")
    material_raw = pd.read_excel(workbook_path, sheet_name="附件1", header=None)
    measurement_raw = pd.read_excel(workbook_path, sheet_name="附件2", header=None)
    if material_raw.shape[0] < 6 or material_raw.shape[1] < 5:
        raise DataValidationError("附件1结构不足 A1:E6")
    values = material_raw.iloc[2:6, 1:4].to_numpy(dtype=float)
    names = material_raw.iloc[2:6, 0].astype(str).tolist()
    if values.shape != (4, 3) or not np.all(np.isfinite(values)):
        raise DataValidationError("附件1材料参数无法解析")
    materials = tuple(
        Material(name, float(row[0]), float(row[1]), float(row[2]))
        for name, row in zip(names, values, strict=True)
    )
    observations = measurement_raw.iloc[2:, :2].to_numpy(dtype=float)
    times_s, temperatures_c = observations[:, 0], observations[:, 1]
    validate_measurements(times_s, temperatures_c)
    return materials, times_s, temperatures_c


# 网格与数值内核
def build_mesh(
    materials: tuple[Material, ...],
    thicknesses_mm: tuple[float, ...],
    target_dx_mm: float,
) -> Mesh:
    """生成层间界面对齐的非均匀网格。

    每层至少四个控制体，避免最薄 0.6 mm 层退化成单节点。
    """
    if len(materials) != 4 or len(thicknesses_mm) != 4:
        raise ConfigurationError("模型必须恰好包含四层")
    if target_dx_mm <= 0 or any(value <= 0 for value in thicknesses_mm):
        raise ConfigurationError("网格宽度和各层厚度必须为正")
    arrays: dict[str, list[np.ndarray]] = {
        "width": [],
        "density": [],
        "heat": [],
        "conductivity": [],
        "layer": [],
    }
    for index, (material, thickness_mm) in enumerate(
        zip(materials, thicknesses_mm, strict=True)
    ):
        count = max(4, math.ceil(thickness_mm / target_dx_mm))
        width = thickness_mm * 1e-3 / count
        arrays["width"].append(np.full(count, width))
        arrays["density"].append(np.full(count, material.density))
        arrays["heat"].append(np.full(count, material.specific_heat))
        arrays["conductivity"].append(np.full(count, material.conductivity))
        arrays["layer"].append(np.full(count, index + 1, dtype=int))
    widths = np.concatenate(arrays["width"])
    centers = np.cumsum(widths) - widths / 2.0
    return Mesh(
        centers,
        widths,
        np.concatenate(arrays["density"]),
        np.concatenate(arrays["heat"]),
        np.concatenate(arrays["conductivity"]),
        np.concatenate(arrays["layer"]),
    )


def factorize_tridiagonal(
    lower: np.ndarray,
    diagonal: np.ndarray,
    upper: np.ndarray,
) -> ThomasFactors:
    """预分解三对角矩阵，供多个时间步重复求解。

    Raises:
        NumericalError: 形状不符或主元接近零。
    """
    diagonal = np.asarray(diagonal, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    size = len(diagonal)
    if size == 0 or lower.shape != (size - 1,) or upper.shape != (size - 1,):
        raise NumericalError("三对角数组形状不一致")
    pivots = diagonal.copy()
    multipliers = np.empty(max(size - 1, 0), dtype=float)
    tolerance = np.finfo(float).eps * max(1.0, float(np.max(np.abs(diagonal))))
    if abs(pivots[0]) <= tolerance:
        raise NumericalError("Thomas 分解首主元接近零")
    for index in range(1, size):
        multipliers[index - 1] = lower[index - 1] / pivots[index - 1]
        pivots[index] -= multipliers[index - 1] * upper[index - 1]
        if abs(pivots[index]) <= tolerance:
            raise NumericalError(f"Thomas 分解第 {index} 个主元接近零")
    return ThomasFactors(pivots, multipliers, upper.copy())


def thomas_solve(factors: ThomasFactors, rhs: np.ndarray) -> np.ndarray:
    """用已分解的三对角矩阵求解一个右端向量。"""
    rhs = np.asarray(rhs, dtype=float)
    size = len(factors.pivots)
    if rhs.shape != (size,):
        raise NumericalError("Thomas 求解右端形状错误")
    work = rhs.copy()
    for index in range(1, size):
        work[index] -= factors.multipliers[index - 1] * work[index - 1]
    solution = np.empty(size, dtype=float)
    solution[-1] = work[-1] / factors.pivots[-1]
    for index in range(size - 2, -1, -1):
        numerator = work[index] - factors.upper[index] * solution[index + 1]
        solution[index] = numerator / factors.pivots[index]
    return solution


def _validate_config(config: SimulationConfig) -> int:
    values = (
        config.duration_s,
        config.dt_s,
        config.target_dx_mm,
        config.h_out,
        config.h_body,
    )
    if any(value <= 0 for value in values):
        raise ConfigurationError("时长、步长、网格和换热系数必须为正")
    step_count = round(config.duration_s / config.dt_s)
    if not np.isclose(step_count * config.dt_s, config.duration_s):
        raise ConfigurationError("总时长必须是时间步长的整数倍")
    if config.environment_temp_c < config.body_temp_c:
        raise ConfigurationError("本题高温环境不应低于人体热库温度")
    return step_count


def assemble_implicit_system(
    mesh: Mesh,
    config: SimulationConfig,
) -> ImplicitSystem:
    """装配守恒型全隐式三对角系统。"""
    capacity = mesh.density * mesh.specific_heat * mesh.widths_m
    face_resistance = (
        mesh.widths_m[:-1] / (2.0 * mesh.conductivity[:-1])
        + mesh.widths_m[1:] / (2.0 * mesh.conductivity[1:])
    )
    face_conductance = 1.0 / face_resistance
    outer = 1.0 / (
        1.0 / config.h_out + mesh.widths_m[0] / (2.0 * mesh.conductivity[0])
    )
    body = 1.0 / (
        mesh.widths_m[-1] / (2.0 * mesh.conductivity[-1])
        + 1.0 / config.h_body
    )
    diagonal = capacity / config.dt_s
    diagonal[:-1] += face_conductance
    diagonal[1:] += face_conductance
    diagonal[0] += outer
    diagonal[-1] += body
    boundary_rhs = np.zeros_like(diagonal)
    boundary_rhs[0] = outer * config.environment_temp_c
    boundary_rhs[-1] = body * config.body_temp_c
    factors = factorize_tridiagonal(
        -face_conductance,
        diagonal,
        -face_conductance,
    )
    return ImplicitSystem(factors, capacity / config.dt_s, boundary_rhs, body)


def _skin_surface_temperature(
    last_center_temp_c: float,
    body_temp_c: float,
    h_body: float,
    body_conductance: float,
) -> float:
    heat_flux = body_conductance * (last_center_temp_c - body_temp_c)
    return body_temp_c + heat_flux / h_body


def simulate(
    materials: tuple[Material, ...],
    thicknesses_mm: tuple[float, ...],
    config: SimulationConfig,
    *,
    store_field: bool = False,
) -> SimulationResult:
    """求解一个厚度和边界场景。

    Args:
        materials: 四层材料参数。
        thicknesses_mm: 四层厚度，单位 mm。
        config: 温度、时长、网格和换热参数。
        store_field: 是否保存全部单元温度场。

    Returns:
        时间、皮肤外侧温度、网格和可选全温度场。
    """
    step_count = _validate_config(config)
    mesh = build_mesh(materials, thicknesses_mm, config.target_dx_mm)
    system = assemble_implicit_system(mesh, config)
    state = np.full(len(mesh.centers_m), config.initial_temp_c)
    times = np.linspace(0.0, config.duration_s, step_count + 1)
    skin = np.empty(step_count + 1)
    field = np.empty((step_count + 1, len(state))) if store_field else None
    skin[0] = _skin_surface_temperature(
        state[-1], config.body_temp_c, config.h_body, system.body_conductance
    )
    if field is not None:
        field[0] = state
    for step in range(1, step_count + 1):
        rhs = system.mass_over_dt * state + system.boundary_rhs
        state = thomas_solve(system.factors, rhs)
        skin[step] = _skin_surface_temperature(
            state[-1], config.body_temp_c, config.h_body, system.body_conductance
        )
        if field is not None:
            field[step] = state
    if not np.all(np.isfinite(skin)):
        raise NumericalError("仿真产生非有限温度")
    return SimulationResult(times, skin, mesh, field)


# 评价与参数标定
def steady_skin_temperature(
    materials: tuple[Material, ...],
    thicknesses_mm: tuple[float, ...],
    environment_temp_c: float,
    body_temp_c: float,
    h_out: float,
    h_body: float,
) -> float:
    """用串联热阻闭式解计算稳态皮肤外侧温度。"""
    resistance = 1.0 / h_out + 1.0 / h_body
    for material, thickness_mm in zip(materials, thicknesses_mm, strict=True):
        resistance += thickness_mm * 1e-3 / material.conductivity
    heat_flux = (environment_temp_c - body_temp_c) / resistance
    return body_temp_c + heat_flux / h_body


def duration_above_threshold(
    times_s: np.ndarray,
    temperatures_c: np.ndarray,
    threshold_c: float,
) -> float:
    """按分段线性插值计算严格超过阈值的总时长。"""
    if times_s.ndim != 1 or temperatures_c.shape != times_s.shape:
        raise DataValidationError("阈值积分数组形状错误")
    if len(times_s) < 2 or np.any(np.diff(times_s) <= 0):
        raise DataValidationError("阈值积分时间必须严格递增")
    total = 0.0
    for left_t, right_t, left_y, right_y in zip(
        times_s[:-1],
        times_s[1:],
        temperatures_c[:-1],
        temperatures_c[1:],
        strict=True,
    ):
        width = right_t - left_t
        left_above, right_above = left_y > threshold_c, right_y > threshold_c
        if left_above and right_above:
            total += width
        elif left_above != right_above and not np.isclose(left_y, right_y):
            crossing = (threshold_c - left_y) / (right_y - left_y)
            total += width * (crossing if right_above else 1.0 - crossing)
    return float(total)


def _phase_weights(times_s: np.ndarray) -> np.ndarray:
    weights = np.empty_like(times_s, dtype=float)
    masks = (
        times_s <= 600.0,
        (times_s > 600.0) & (times_s <= 1800.0),
        times_s > 1800.0,
    )
    for mask in masks:
        count = int(np.count_nonzero(mask))
        weights[mask] = 1.0 / math.sqrt(3.0 * count)
    return weights


def _jacobian_diagnostics(jacobian: np.ndarray) -> tuple[float | None, float | None]:
    singular_values = np.linalg.svd(jacobian, compute_uv=False)
    if singular_values[-1] <= np.finfo(float).eps:
        return None, None
    condition = float(singular_values[0] / singular_values[-1])
    try:
        covariance = np.linalg.inv(jacobian.T @ jacobian)
    except np.linalg.LinAlgError:
        return condition, None
    denominator = math.sqrt(covariance[0, 0] * covariance[1, 1])
    correlation = float(covariance[0, 1] / denominator)
    return condition, correlation


def fit_exchange_coefficients(
    materials: tuple[Material, ...],
    times_s: np.ndarray,
    measured_c: np.ndarray,
) -> dict[str, float | int | None]:
    """用 G2 粗网格标定两个等效换热系数。

    本函数只用于最小可行性验证，正式参数需在 G3 网格收敛后重算。
    """
    stride = 10
    fit_times = times_s[::stride]
    fit_measured = measured_c[::stride]
    weights = _phase_weights(fit_times)
    thicknesses = (0.6, 6.0, 3.6, 5.0)

    def residual(log_coefficients: np.ndarray) -> np.ndarray:
        """返回阶段平衡并保证换热系数为正的拟合残差。"""
        h_out, h_body = np.exp(log_coefficients)
        config = SimulationConfig(75.0, 37.0, 37.0, 5400.0, 10.0, 0.5, h_out, h_body)
        prediction = simulate(materials, thicknesses, config).skin_temp_c
        return (prediction - fit_measured) * weights

    starts = ((10.0, 6.0), (30.0, 8.0), (100.0, 10.0))
    bounds = (np.log((1.0, 1.0)), np.log((500.0, 100.0)))
    candidates = [
        least_squares(
            residual,
            np.log(start),
            bounds=bounds,
            max_nfev=60,
            xtol=1e-8,
            ftol=1e-8,
            gtol=1e-8,
        )
        for start in starts
    ]
    best = min(candidates, key=lambda item: item.cost)
    h_out, h_body = np.exp(best.x)
    condition, correlation = _jacobian_diagnostics(best.jac)
    return {
        "h_out_w_m2k": float(h_out),
        "h_body_w_m2k": float(h_body),
        "weighted_least_squares_cost": float(best.cost),
        "function_evaluations": int(sum(item.nfev for item in candidates)),
        "jacobian_condition": condition,
        "parameter_correlation": correlation,
    }


def _verify_nsga2_interface() -> dict[str, object]:
    """在标准玩具问题上验证本机 pymoo NSGA-II 接口。"""
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.optimize import minimize
    from pymoo.problems import get_problem

    result = minimize(
        get_problem("zdt1"),
        NSGA2(pop_size=12),
        ("n_gen", 2),
        seed=42,
        verbose=False,
    )
    if result.F is None or result.F.ndim != 2 or result.F.shape[1] != 2:
        raise NumericalError("pymoo NSGA-II 最小接口未返回二维目标")
    return {
        "package_version": importlib.metadata.version("pymoo"),
        "toy_problem": "zdt1",
        "objective_columns": int(result.F.shape[1]),
        "returned_solutions": int(result.F.shape[0]),
        "evidence_scope": "仅验证软件接口，不是本题正式优化结果",
    }


# G2 产物与 CLI
def _configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(stream_handler)


def _package_versions() -> dict[str, str]:
    names = ("numpy", "scipy", "pandas", "matplotlib", "openpyxl", "pytest", "ruff")
    return {name: importlib.metadata.version(name) for name in names}


def _write_diagnostic_plot(result_path: Path, figure_path: Path) -> None:
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    series = payload["diagnostic_series"]
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    axis.plot(series["time_s"], series["measured_c"], label="Measured", linewidth=1.4)
    axis.plot(series["time_s"], series["modeled_c"], label="G2 model", linewidth=1.3)
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Skin temperature (deg C)")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    figure.savefig(figure_path)
    plt.close(figure)


def _g2_simulation_payload(
    materials: tuple[Material, ...],
    measured_c: np.ndarray,
    fitted: dict[str, float | int | None],
) -> dict[str, object]:
    config = SimulationConfig(
        75.0,
        37.0,
        37.0,
        5400.0,
        10.0,
        0.5,
        float(fitted["h_out_w_m2k"]),
        float(fitted["h_body_w_m2k"]),
    )
    simulation = simulate(materials, (0.6, 6.0, 3.6, 5.0), config)
    observed = measured_c[::10]
    residual = simulation.skin_temp_c - observed
    steady_closed = steady_skin_temperature(
        materials, (0.6, 6.0, 3.6, 5.0), 75.0, 37.0, config.h_out, config.h_body
    )
    return {
        "diagnostics": {
            "rmse_c": float(np.sqrt(np.mean(residual**2))),
            "mae_c": float(np.mean(np.abs(residual))),
            "max_abs_error_c": float(np.max(np.abs(residual))),
            "modeled_final_c": float(simulation.skin_temp_c[-1]),
            "steady_closed_form_c": float(steady_closed),
            "final_to_steady_gap_c": float(simulation.skin_temp_c[-1] - steady_closed),
            "duration_above_44_s": duration_above_threshold(
                simulation.times_s, simulation.skin_temp_c, 44.0
            ),
            "mesh_cells": len(simulation.mesh.centers_m),
            "dt_s": config.dt_s,
            "target_dx_mm": config.target_dx_mm,
        },
        "diagnostic_series": {
            "time_s": simulation.times_s.tolist(),
            "measured_c": observed.tolist(),
            "modeled_c": simulation.skin_temp_c.tolist(),
        },
    }


def _build_g2_payload(
    input_path: Path,
    started: float,
) -> dict[str, object]:
    materials, times_s, measured_c = load_problem_data(input_path)
    LOGGER.info("成功读取附件：%d 条温度观测", len(times_s))
    fitted = fit_exchange_coefficients(materials, times_s, measured_c)
    simulation_payload = _g2_simulation_payload(materials, measured_c, fitted)
    return {
        "stage": "G2",
        "result_status": "MINIMAL_VALIDATION_NOT_FORMAL",
        "runtime": {
            "executable": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "packages": _package_versions(),
        },
        "data": {
            "observation_count": len(times_s),
            "time_start_s": float(times_s[0]),
            "time_end_s": float(times_s[-1]),
            "temperature_start_c": float(measured_c[0]),
            "temperature_end_c": float(measured_c[-1]),
        },
        "coarse_fit": fitted,
        **simulation_payload,
        "nsga2_interface": _verify_nsga2_interface(),
        "elapsed_seconds": float(time.perf_counter() - started),
        "limitations": [
            "G2 使用 10 s 时间步和 0.5 mm 目标网格，仅证明模型链路可行",
            "换热参数及误差不是 G3 正式论文结果",
            "NSGA-II 仅执行 zdt1 玩具接口探测，未运行本题优化",
        ],
    }


def run_g2_smoke(project_root: Path, input_path: Path) -> Path:
    """运行 G2 最小验证并写入 JSON、日志和诊断图。"""
    started = time.perf_counter()
    result_path = project_root / "results" / "g2_baseline.json"
    figure_path = project_root / "figures" / "g2_skin_temperature_diagnostic.pdf"
    payload = _build_g2_payload(input_path, started)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_diagnostic_plot(result_path, figure_path)
    LOGGER.info("G2 最小验证完成：RMSE=%.4f °C", payload["diagnostics"]["rmse_c"])
    return result_path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="运行 G2 最小验证")
    parser.add_argument("--input", type=Path, help="覆盖默认附件路径")
    return parser.parse_args()


def main() -> int:
    """命令行入口。"""
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    input_path = args.input or (
        project_root / "inputs" / "CUMCM-2018-Problem-A-Chinese-Appendix.xlsx"
    )
    _configure_logging(project_root / "logs" / "g2_smoke.log")
    if not args.smoke:
        LOGGER.error("G2 仅开放 --smoke 入口")
        return 2
    try:
        run_g2_smoke(project_root, input_path)
    except (DataValidationError, ConfigurationError, NumericalError):
        LOGGER.exception("G2 最小验证失败")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
