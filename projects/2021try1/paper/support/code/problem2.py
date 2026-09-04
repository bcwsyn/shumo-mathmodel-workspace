"""问题二最小可行调节基线。

G2 只验证理想目标是否已经满足硬约束；若不满足，则回到严格可行的
基准球面。正式顺序凸化优化留待 G2 批准后的 G3。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from fast_geometry import DirectionFrame, FastData, constraint_summary


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class FeasibleBaseline:
    """保存 G2 选择的可行位移及其来源。"""

    displacement: FloatArray
    source: str
    constraint: dict[str, float | int | bool]
    weighted_mean_square_error: float
    max_abs_target_error_m: float


def choose_feasible_baseline(
    data: FastData,
    frame: DirectionFrame,
    target_displacement: FloatArray,
) -> FeasibleBaseline:
    """选择理想目标或零位移作为 G2 可行基线。

    理想目标通过精确约束回代时直接采用；否则使用基准球面零位移。
    返回值只证明可行性，不代表 G3 的正式最优调节结果。
    """

    target_constraint = constraint_summary(data, frame, target_displacement)
    if target_constraint["feasible"]:
        selected = target_displacement.copy()
        source = "ideal-target-feasible"
        selected_constraint = target_constraint
    else:
        # 零位移保持全部基准几何不变，是目标投影不可行时的确定性安全基线。
        selected = np.zeros_like(target_displacement)
        source = "zero-displacement-feasible"
        selected_constraint = constraint_summary(data, frame, selected)
    errors = selected[frame.active_nodes] - target_displacement[frame.active_nodes]
    return FeasibleBaseline(
        displacement=selected,
        source=source,
        constraint=selected_constraint,
        weighted_mean_square_error=float(np.mean(errors**2)),
        max_abs_target_error_m=float(np.max(np.abs(errors))),
    )
