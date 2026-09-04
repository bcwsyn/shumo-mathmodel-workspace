"""G3 正式优化与确定性射线追踪的独立性质测试。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from fast_geometry import (
    build_direction_frame,
    constraint_summary,
    load_fast_data,
    paraboloid_target_displacement,
)
from optimization import maximum_feasible_target_scale
from raytrace import barycentric_micro_centroids, trace_surface


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"


def test_barycentric_micro_centroids_partition_triangle() -> None:
    """正常路径：m 阶细分应产生 m² 个合法重心且重心和为 1。"""

    coordinates = barycentric_micro_centroids(4)
    assert coordinates.shape == (16, 3)
    assert np.all(coordinates >= 0.0)
    assert np.all(coordinates <= 1.0)
    np.testing.assert_allclose(np.sum(coordinates, axis=1), 1.0, atol=1e-14)


def test_scaled_target_is_exactly_feasible_at_reported_boundary() -> None:
    """边界路径：真实目标的二分缩放结果须通过原始非线性约束复核。"""

    data = load_fast_data(DATA_DIR)
    frame = build_direction_frame(data, 36.795, 78.169)
    target = paraboloid_target_displacement(data, frame, 0.466 * data.radius)
    scale = maximum_feasible_target_scale(data, frame, target, iterations=45)
    assert 0.0 < scale < 1.0
    summary = constraint_summary(data, frame, scale * target)
    assert summary["feasible"] is True


def test_real_surface_raytrace_returns_finite_probability() -> None:
    """正常路径：真实基准面的小规模射线追踪结果应为有限概率。"""

    data = load_fast_data(DATA_DIR)
    frame = build_direction_frame(data, 36.795, 78.169)
    result = trace_surface(data, frame, data.nodes, subdivision=1)
    assert 0.0 <= result.reception_ratio <= 1.0
    assert result.total_weight > 0.0
    assert result.included_samples > 0


def test_invalid_subdivision_is_rejected() -> None:
    """失败路径：非正细分级别必须被明确拒绝。"""

    with pytest.raises(ValueError, match="正整数"):
        barycentric_micro_centroids(0)
