"""FAST 几何模块的正常、边界和失败输入测试。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fast_geometry import (
    DataValidationError,
    actuator_strokes,
    build_direction_frame,
    constraint_summary,
    load_fast_data,
    paraboloid_target_displacement,
)
from problem3 import receiver_hits


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"


def test_normal_real_data_baseline_counts_and_constraints() -> None:
    """正常路径：真实附件应恢复固定规模且零位移严格可行。"""

    data = load_fast_data(DATA_DIR)
    frame1 = build_direction_frame(data, 0.0, 90.0)
    frame2 = build_direction_frame(data, 36.795, 78.169)
    assert len(data.edges) == 6525
    assert int(np.sum(frame1.active_nodes)) == 706
    assert int(np.sum(frame2.active_nodes)) == 692
    summary = constraint_summary(data, frame2, np.zeros(len(data.node_ids)))
    assert summary["feasible"] is True
    assert summary["max_abs_stroke_m"] == pytest.approx(0.0, abs=1e-12)
    assert summary["max_edge_relative_change"] == pytest.approx(0.0, abs=1e-12)


def test_boundary_axis_node_intersects_vertex() -> None:
    """边界路径：位于抛物面轴线的节点应落在顶点半径。"""

    data = load_fast_data(DATA_DIR)
    frame = build_direction_frame(data, 0.0, 90.0)
    focal_length = 0.466 * data.radius
    displacement = paraboloid_target_displacement(data, frame, focal_length)
    center_index = int(np.argmin(np.linalg.norm(data.nodes[:, :2], axis=1)))
    expected = data.radii[center_index] - (
        np.linalg.norm(frame.focus) + focal_length
    )
    assert displacement[center_index] == pytest.approx(expected, abs=1e-10)
    strokes, reachable = actuator_strokes(data, np.zeros(len(data.node_ids)))
    assert bool(np.all(reachable))
    assert float(np.max(np.abs(strokes))) == pytest.approx(0.0, abs=1e-12)


def test_failure_missing_column_raises_validation_error(tmp_path: Path) -> None:
    """失败路径：附件1缺失坐标列时必须明确抛出字段错误。"""

    incomplete = pd.DataFrame(
        {"节点编号": ["A0"], "X坐标（米）": [0.0], "Y坐标（米）": [0.0]}
    )
    incomplete.to_csv(tmp_path / "附件1.csv", index=False, encoding="gb18030")
    with pytest.raises(DataValidationError, match="缺失字段"):
        load_fast_data(tmp_path)


def test_failure_duplicate_node_ids_are_invalid(tmp_path: Path) -> None:
    """失败边界：重复节点编号不能进入几何映射。"""

    duplicate = pd.DataFrame(
        {
            "节点编号": ["A0", "A0"],
            "X坐标（米）": [0.0, 0.0],
            "Y坐标（米）": [0.0, 0.0],
            "Z坐标（米）": [-300.4, -300.4],
        }
    )
    duplicate.to_csv(tmp_path / "附件1.csv", index=False, encoding="gb18030")
    with pytest.raises(DataValidationError, match="节点编号重复"):
        load_fast_data(tmp_path)


def test_normal_receiver_hit_and_miss() -> None:
    """正常射线：轴向射线命中圆盘，横向偏移射线不命中。"""

    points = np.array([[0.0, 0.0, -300.0], [1.0, 0.0, -300.0]])
    directions = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]])
    hits = receiver_hits(
        points,
        directions,
        focus=np.array([0.0, 0.0, -160.0]),
        sky=np.array([0.0, 0.0, 1.0]),
    )
    assert hits.tolist() == [True, False]
