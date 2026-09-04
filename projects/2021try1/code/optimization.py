"""FAST 工作反射面的正式约束优化。

模块使用 CVXPY 的稀疏顺序凸化子问题，并在每次候选更新后用原始
非线性几何精确回代。输入为目标径向位移，输出严格可行的节点位移。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cvxpy as cp
import numpy as np
from numpy.typing import NDArray
from scipy import sparse

from fast_geometry import (
    DirectionFrame,
    FastData,
    actuator_strokes,
    constraint_summary,
    node_area_weights,
)


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class OptimizationResult:
    """保存正式优化解、精确约束摘要和迭代证据。"""

    displacement: FloatArray
    strokes: FloatArray
    adjusted_nodes: FloatArray
    objective_mse_m2: float
    max_abs_error_m: float
    constraint: dict[str, float | int | bool]
    selected_start: str
    histories: list[dict[str, Any]]
    solver_statuses: list[str]


def _full_displacement(
    frame: DirectionFrame,
    active_values: FloatArray,
) -> FloatArray:
    full = np.zeros(len(frame.active_nodes), dtype=float)
    full[frame.active_nodes] = active_values
    return full


def _objective(
    active_values: FloatArray,
    target: FloatArray,
    weights: FloatArray,
) -> float:
    return float(np.average((active_values - target) ** 2, weights=weights))


def _edge_linearization(
    data: FastData,
    frame: DirectionFrame,
    current_full: FloatArray,
    active_index: NDArray[np.int64],
) -> tuple[FloatArray, sparse.csr_matrix]:
    moved = data.nodes - current_full[:, None] * data.node_units
    edges = data.edges[frame.incident_edges]
    differences = moved[edges[:, 0]] - moved[edges[:, 1]]
    lengths = np.linalg.norm(differences, axis=1)
    index_map = np.full(len(data.node_ids), -1, dtype=np.int64)
    index_map[active_index] = np.arange(len(active_index))
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    for row, (left, right) in enumerate(edges):
        left_column = int(index_map[left])
        right_column = int(index_map[right])
        if left_column >= 0:
            derivative = -float(differences[row] @ data.node_units[left]) / lengths[row]
            rows.append(row)
            columns.append(left_column)
            values.append(derivative)
        if right_column >= 0:
            derivative = float(differences[row] @ data.node_units[right]) / lengths[row]
            rows.append(row)
            columns.append(right_column)
            values.append(derivative)
    jacobian = sparse.coo_matrix(
        (values, (rows, columns)),
        shape=(len(edges), len(active_index)),
    ).tocsr()
    return lengths, jacobian


def _stroke_linearization(
    data: FastData,
    current_full: FloatArray,
    active_index: NDArray[np.int64],
) -> tuple[FloatArray, FloatArray]:
    strokes, reachable = actuator_strokes(data, current_full)
    if not np.all(reachable[active_index]):
        raise RuntimeError("当前迭代点出现不可达下拉索几何")
    delta = data.nodes - data.actuator_upper
    cable_vectors = delta - current_full[:, None] * data.node_units
    cable_vectors += strokes[:, None] * data.actuator_units
    numerator = np.sum(cable_vectors * data.node_units, axis=1)
    denominator = np.sum(cable_vectors * data.actuator_units, axis=1)
    if np.any(np.abs(denominator[active_index]) < 1e-10):
        raise RuntimeError("促动器连续根导数出现奇异分母")
    derivative = numerator / denominator
    return strokes[active_index], derivative[active_index]


def _is_strictly_feasible(
    data: FastData,
    frame: DirectionFrame,
    full_displacement: FloatArray,
) -> bool:
    summary = constraint_summary(data, frame, full_displacement)
    return bool(summary["feasible"])


def maximum_feasible_target_scale(
    data: FastData,
    frame: DirectionFrame,
    target_displacement: FloatArray,
    iterations: int = 60,
) -> float:
    """二分求目标位移射线上仍满足全部精确硬约束的最大比例。"""

    if iterations < 1:
        raise ValueError("二分迭代次数必须为正")
    if _is_strictly_feasible(data, frame, target_displacement):
        return 1.0
    lower, upper = 0.0, 1.0
    for _ in range(iterations):
        middle = 0.5 * (lower + upper)
        if _is_strictly_feasible(data, frame, middle * target_displacement):
            lower = middle
        else:
            upper = middle
    return lower


def _solve_l2_subproblem(
    data: FastData,
    frame: DirectionFrame,
    current: FloatArray,
    target: FloatArray,
    weights: FloatArray,
    trust_radius: float,
) -> tuple[FloatArray, str]:
    active_index = np.flatnonzero(frame.active_nodes)
    current_full = _full_displacement(frame, current)
    lengths, edge_jacobian = _edge_linearization(
        data,
        frame,
        current_full,
        active_index,
    )
    strokes, stroke_derivative = _stroke_linearization(
        data,
        current_full,
        active_index,
    )
    variable = cp.Variable(len(active_index))
    delta = variable - current
    baseline_edges = data.edge_lengths[frame.incident_edges]
    linear_edges = lengths + edge_jacobian @ delta
    linear_strokes = strokes + cp.multiply(stroke_derivative, delta)
    constraints = [
        linear_edges >= baseline_edges * (1.0 - 0.0007) + 1e-7,
        linear_edges <= baseline_edges * (1.0 + 0.0007) - 1e-7,
        linear_strokes >= -0.6 + 1e-7,
        linear_strokes <= 0.6 - 1e-7,
        cp.abs(delta) <= trust_radius,
    ]
    normalized_weights = weights / np.sum(weights)
    objective = cp.Minimize(cp.sum(cp.multiply(normalized_weights, cp.square(variable - target))))
    problem = cp.Problem(objective, constraints)
    problem.solve(
        solver=cp.OSQP,
        eps_abs=1e-10,
        eps_rel=1e-9,
        max_iter=200000,
        polishing=True,
        verbose=False,
    )
    if problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
        raise RuntimeError(f"OSQP 子问题失败：{problem.status}")
    return np.asarray(variable.value, dtype=float), str(problem.status)


def _accept_feasible_step(
    data: FastData,
    frame: DirectionFrame,
    current: FloatArray,
    candidate: FloatArray,
    target: FloatArray,
    weights: FloatArray,
) -> tuple[FloatArray, float]:
    current_objective = _objective(current, target, weights)
    for exponent in range(18):
        fraction = 0.5**exponent
        trial = current + fraction * (candidate - current)
        full_trial = _full_displacement(frame, trial)
        if _is_strictly_feasible(data, frame, full_trial):
            if _objective(trial, target, weights) < current_objective - 1e-15:
                return trial, fraction
    return current.copy(), 0.0


def _accept_linf_step(
    data: FastData,
    frame: DirectionFrame,
    current: FloatArray,
    candidate: FloatArray,
    target: FloatArray,
    weights: FloatArray,
    l2_limit: float,
) -> tuple[FloatArray, float]:
    """在不突破 L2 容差时，回溯接受能降低最大绝对误差的精修步。"""

    current_max = float(np.max(np.abs(current - target)))
    for exponent in range(18):
        fraction = 0.5**exponent
        trial = current + fraction * (candidate - current)
        full_trial = _full_displacement(frame, trial)
        trial_max = float(np.max(np.abs(trial - target)))
        if (
            _is_strictly_feasible(data, frame, full_trial)
            and _objective(trial, target, weights) <= l2_limit + 1e-12
            and trial_max < current_max - 1e-12
        ):
            return trial, fraction
    return current.copy(), 0.0


def _run_l2_scp(
    data: FastData,
    frame: DirectionFrame,
    target: FloatArray,
    weights: FloatArray,
    initial: FloatArray,
    start_name: str,
    max_iterations: int,
) -> tuple[FloatArray, list[dict[str, Any]], list[str]]:
    current = initial.copy()
    trust_radius = 0.08
    history: list[dict[str, Any]] = []
    statuses: list[str] = []
    for iteration in range(max_iterations):
        candidate, status = _solve_l2_subproblem(
            data,
            frame,
            current,
            target,
            weights,
            trust_radius,
        )
        statuses.append(status)
        accepted, fraction = _accept_feasible_step(
            data,
            frame,
            current,
            candidate,
            target,
            weights,
        )
        step = float(np.max(np.abs(accepted - current)))
        previous = _objective(current, target, weights)
        current = accepted
        current_objective = _objective(current, target, weights)
        history.append(
            {
                "start": start_name,
                "stage": "l2",
                "iteration": iteration,
                "objective_mse_m2": current_objective,
                "max_step_m": step,
                "accepted_fraction": fraction,
                "trust_radius_m": trust_radius,
            }
        )
        if fraction == 1.0:
            trust_radius = min(0.2, 1.4 * trust_radius)
        elif fraction > 0:
            trust_radius = max(1e-4, 0.6 * trust_radius)
        else:
            trust_radius = max(1e-4, 0.35 * trust_radius)
        improvement = previous - current_objective
        if step < 1e-7 or improvement <= 1e-12 * max(1.0, previous):
            break
    return current, history, statuses


def _refine_linf(
    data: FastData,
    frame: DirectionFrame,
    target: FloatArray,
    weights: FloatArray,
    initial: FloatArray,
    l2_limit: float,
    max_iterations: int = 12,
) -> tuple[FloatArray, list[dict[str, Any]], list[str]]:
    current = initial.copy()
    active_index = np.flatnonzero(frame.active_nodes)
    normalized_weights = weights / np.sum(weights)
    trust_radius = 0.03
    history: list[dict[str, Any]] = []
    statuses: list[str] = []
    for iteration in range(max_iterations):
        current_full = _full_displacement(frame, current)
        lengths, edge_jacobian = _edge_linearization(
            data,
            frame,
            current_full,
            active_index,
        )
        strokes, stroke_derivative = _stroke_linearization(
            data,
            current_full,
            active_index,
        )
        variable = cp.Variable(len(active_index))
        maximum_error = cp.Variable(nonneg=True)
        delta = variable - current
        baseline_edges = data.edge_lengths[frame.incident_edges]
        constraints = [
            lengths + edge_jacobian @ delta >= baseline_edges * (1.0 - 0.0007) + 1e-7,
            lengths + edge_jacobian @ delta <= baseline_edges * (1.0 + 0.0007) - 1e-7,
            strokes + cp.multiply(stroke_derivative, delta) >= -0.6 + 1e-7,
            strokes + cp.multiply(stroke_derivative, delta) <= 0.6 - 1e-7,
            cp.abs(delta) <= trust_radius,
            cp.abs(variable - target) <= maximum_error,
            cp.sum(cp.multiply(normalized_weights, cp.square(variable - target))) <= l2_limit,
        ]
        problem = cp.Problem(cp.Minimize(maximum_error), constraints)
        problem.solve(solver=cp.CLARABEL, max_iter=300, verbose=False)
        statuses.append(str(problem.status))
        if problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
            break
        candidate = np.asarray(variable.value, dtype=float)
        previous_max = float(np.max(np.abs(current - target)))
        # L∞ 阶段允许均方误差在既定容差内轻微变化，但必须改善最坏节点。
        accepted, fraction = _accept_linf_step(
            data,
            frame,
            current,
            candidate,
            target,
            weights,
            l2_limit,
        )
        step = float(np.max(np.abs(accepted - current)))
        current = accepted
        current_max = float(np.max(np.abs(current - target)))
        history.append(
            {
                "start": "selected-l2",
                "stage": "linf",
                "iteration": iteration,
                "objective_mse_m2": _objective(current, target, weights),
                "max_abs_error_m": current_max,
                "max_step_m": step,
                "accepted_fraction": fraction,
            }
        )
        if step < 1e-7 or previous_max - current_max < 1e-10:
            break
    return current, history, statuses


def optimize_work_surface(
    data: FastData,
    frame: DirectionFrame,
    target_displacement: FloatArray,
    max_iterations: int = 35,
) -> OptimizationResult:
    """执行多起点 L2 顺序凸化和近等价 L∞ 二阶段精修。"""

    active_index = np.flatnonzero(frame.active_nodes)
    target = target_displacement[active_index]
    weights = node_area_weights(data)[active_index]
    scale = maximum_feasible_target_scale(data, frame, target_displacement)
    starts = {
        "zero": np.zeros_like(target),
        "half-scaled-target": 0.5 * scale * target,
        "max-scaled-target": scale * target,
    }
    candidates: list[tuple[str, FloatArray, list[dict[str, Any]], list[str]]] = []
    for name, initial in starts.items():
        solved, history, statuses = _run_l2_scp(
            data,
            frame,
            target,
            weights,
            initial,
            name,
            max_iterations,
        )
        candidates.append((name, solved, history, statuses))
    selected = min(candidates, key=lambda item: _objective(item[1], target, weights))
    selected_name, best_l2, history, statuses = selected
    l2_objective = _objective(best_l2, target, weights)
    l2_limit = l2_objective * (1.0 + 1e-6) + 1e-12
    refined, linf_history, linf_statuses = _refine_linf(
        data,
        frame,
        target,
        weights,
        best_l2,
        l2_limit,
    )
    full = _full_displacement(frame, refined)
    strokes, reachable = actuator_strokes(data, full)
    if not np.all(reachable[active_index]):
        raise RuntimeError("正式解存在不可达促动器")
    summary = constraint_summary(data, frame, full)
    if not summary["feasible"]:
        raise RuntimeError(f"正式解未通过精确硬约束：{summary}")
    return OptimizationResult(
        displacement=full,
        strokes=strokes,
        adjusted_nodes=data.nodes - full[:, None] * data.node_units,
        objective_mse_m2=_objective(refined, target, weights),
        max_abs_error_m=float(np.max(np.abs(refined - target))),
        constraint=summary,
        selected_start=selected_name,
        histories=[entry for item in candidates for entry in item[2]] + linf_history,
        solver_statuses=[status for item in candidates for status in item[3]] + linf_statuses,
    )
