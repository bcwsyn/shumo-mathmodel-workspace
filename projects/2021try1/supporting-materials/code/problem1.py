"""问题一和问题二共享的理想抛物面一维搜索。

输入为已验证的 FAST 几何和观测方向，输出最小硬件占用率对应的
焦距、目标位移、约束摘要以及可审计的搜索网格。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize_scalar

from fast_geometry import (
    DirectionFrame,
    FastData,
    constraint_summary,
    hardware_utilization,
    node_area_weights,
    paraboloid_target_displacement,
)


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class FocalSearchResult:
    """保存 G2 一维焦距搜索的结果与诊断网格。"""

    focal_length: float
    displacement: FloatArray
    constraint: dict[str, float | int | bool]
    grid_focal_lengths: FloatArray
    grid_utilizations: FloatArray
    optimizer_success: bool
    optimizer_message: str


@dataclass(frozen=True)
class FocalModelComparison:
    """保存几何基线、最小二乘和硬件友好三种理想面。"""

    geometric_focal_length: float
    least_squares_focal_length: float
    hardware_result: FocalSearchResult
    metrics: dict[str, dict[str, float | int | bool]]


def search_hardware_friendly_focal_length(
    data: FastData,
    frame: DirectionFrame,
    half_width: float = 0.8,
    grid_size: int = 65,
) -> FocalSearchResult:
    """执行 G2 有界网格加局部精化的最小焦距搜索。

    参数:
        data: FAST 基准几何。
        frame: 当前观测方向。
        half_width: 以 ``F=0.466R`` 为中心的 G2 搜索半宽，单位米。
        grid_size: 确定性搜索网格点数。

    返回:
        搜索结果、目标位移和精确约束回代摘要。
    """

    if half_width <= 0 or grid_size < 5:
        raise ValueError("搜索半宽必须为正且网格点数至少为 5")
    baseline_focal = 0.466 * data.radius
    grid = np.linspace(
        baseline_focal - half_width,
        baseline_focal + half_width,
        grid_size,
    )
    utilization = np.array(
        [hardware_utilization(data, frame, value) for value in grid],
        dtype=float,
    )
    best_index = int(np.argmin(utilization))
    left_index = max(0, best_index - 1)
    right_index = min(grid_size - 1, best_index + 1)

    # G2 先用一维有界精化验证目标可计算；G3 再执行自动扩张与完整对照。
    optimized = minimize_scalar(
        lambda value: hardware_utilization(data, frame, float(value)),
        bounds=(float(grid[left_index]), float(grid[right_index])),
        method="bounded",
        options={"xatol": 1e-10, "maxiter": 200},
    )
    focal_length = float(optimized.x if optimized.success else grid[best_index])
    displacement = paraboloid_target_displacement(data, frame, focal_length)
    return FocalSearchResult(
        focal_length=focal_length,
        displacement=displacement,
        constraint=constraint_summary(data, frame, displacement),
        grid_focal_lengths=grid,
        grid_utilizations=utilization,
        optimizer_success=bool(optimized.success),
        optimizer_message=str(optimized.message),
    )


def _weighted_movement_error(
    data: FastData,
    frame: DirectionFrame,
    focal_length: float,
) -> float:
    displacement = paraboloid_target_displacement(data, frame, focal_length)
    active = frame.active_nodes
    weights = node_area_weights(data)[active]
    return float(np.average(displacement[active] ** 2, weights=weights))


def compare_focal_models(
    data: FastData,
    frame: DirectionFrame,
    initial_half_width: float = 0.2,
) -> FocalModelComparison:
    """比较 G1 批准的三种理想抛物面并自动扩张搜索区间。"""

    if initial_half_width <= 0:
        raise ValueError("初始搜索半宽必须为正")
    half_width = initial_half_width
    baseline_focal = 0.466 * data.radius
    hardware = search_hardware_friendly_focal_length(
        data,
        frame,
        half_width=half_width,
        grid_size=65,
    )
    while half_width < 3.2:
        grid = hardware.grid_utilizations
        boundary_is_competitive = min(grid[0], grid[-1]) <= 1.05 * float(np.min(grid))
        if not boundary_is_competitive:
            break
        half_width *= 2.0
        hardware = search_hardware_friendly_focal_length(
            data,
            frame,
            half_width=half_width,
            grid_size=129,
        )

    bounds = (baseline_focal - half_width, baseline_focal + half_width)
    least_squares = minimize_scalar(
        lambda value: _weighted_movement_error(data, frame, float(value)),
        bounds=bounds,
        method="bounded",
        options={"xatol": 1e-10, "maxiter": 300},
    )
    if not least_squares.success:
        raise RuntimeError(f"最小二乘焦距搜索失败：{least_squares.message}")

    candidates = {
        "geometric": baseline_focal,
        "least_squares": float(least_squares.x),
        "hardware_friendly": hardware.focal_length,
    }
    metrics: dict[str, dict[str, float | int | bool]] = {}
    for name, focal_length in candidates.items():
        displacement = paraboloid_target_displacement(data, frame, focal_length)
        summary = constraint_summary(data, frame, displacement)
        summary["movement_mse_m2"] = _weighted_movement_error(
            data,
            frame,
            focal_length,
        )
        metrics[name] = summary
    return FocalModelComparison(
        geometric_focal_length=baseline_focal,
        least_squares_focal_length=float(least_squares.x),
        hardware_result=hardware,
        metrics=metrics,
    )
