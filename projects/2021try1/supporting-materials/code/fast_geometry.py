"""FAST 数据读取与几何约束模块。

输入为附件 1--3 的 CSV 文件，主要输出节点、促动器、三角面板、
主索拓扑、观测方向和可精确回代的硬件约束指标。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

NODE_COLUMNS = ["节点编号", "X坐标（米）", "Y坐标（米）", "Z坐标（米）"]
ACTUATOR_COLUMNS = [
    "对应主索节点编号",
    "下端点X坐标（米）",
    "下端点Y坐标（米）",
    "下端点Z坐标（米）",
    "基准态时上端点X坐标（米）",
    "基准态时上端点Y坐标（米）",
    "基准态时上端点Z坐标（米）",
]
PANEL_COLUMNS = ["主索节点1", "主索节点2", "主索节点3"]


class DataValidationError(ValueError):
    """表示附件字段、编号或数值不符合题面约定。"""


@dataclass(frozen=True)
class FastData:
    """保存 FAST 基准几何和由附件恢复的拓扑。"""

    node_ids: NDArray[np.str_]
    nodes: FloatArray
    actuator_lower: FloatArray
    actuator_upper: FloatArray
    panels: IntArray
    edges: IntArray
    radii: FloatArray
    node_units: FloatArray
    actuator_units: FloatArray
    down_cable_lengths: FloatArray
    edge_lengths: FloatArray

    @property
    def radius(self) -> float:
        """返回附件节点半径的算术均值，单位为米。"""

        return float(np.mean(self.radii))


@dataclass(frozen=True)
class DirectionFrame:
    """保存一个观测方向对应的局部轴线和工作口径掩码。"""

    sky: FloatArray
    axis: FloatArray
    focus: FloatArray
    active_nodes: BoolArray
    incident_edges: BoolArray


def _read_required_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, encoding="gb18030")
    except FileNotFoundError as exc:
        raise DataValidationError(f"缺少输入文件：{path}") from exc
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise DataValidationError(f"{path.name} 缺失字段：{missing}")
    if frame[columns].isna().any().any():
        raise DataValidationError(f"{path.name} 存在缺失值")
    return frame[columns].copy()


def _validate_identifiers(node_frame: pd.DataFrame) -> NDArray[np.str_]:
    identifiers = node_frame[NODE_COLUMNS[0]].astype(str).str.strip()
    if identifiers.duplicated().any():
        duplicates = identifiers[identifiers.duplicated()].unique().tolist()
        raise DataValidationError(f"节点编号重复：{duplicates[:5]}")
    return identifiers.to_numpy(dtype=str)


def _map_panels(panel_frame: pd.DataFrame, index_by_id: dict[str, int]) -> IntArray:
    mapped = np.empty((len(panel_frame), 3), dtype=np.int64)
    for column_index, column in enumerate(PANEL_COLUMNS):
        values = panel_frame[column].astype(str).str.strip()
        unknown = sorted(set(values) - set(index_by_id))
        if unknown:
            raise DataValidationError(f"面板引用未知节点：{unknown[:5]}")
        mapped[:, column_index] = values.map(index_by_id).to_numpy(dtype=np.int64)
    if np.any(np.sort(mapped, axis=1)[:, 1:] == np.sort(mapped, axis=1)[:, :-1]):
        raise DataValidationError("面板存在重复顶点")
    return mapped


def _build_edges(panels: IntArray) -> IntArray:
    # 每块三角面板贡献三条边；按无向端点排序去重，恢复 6525 根主索。
    edge_set: set[tuple[int, int]] = set()
    for first, second, third in panels:
        edge_set.add(tuple(sorted((int(first), int(second)))))
        edge_set.add(tuple(sorted((int(second), int(third)))))
        edge_set.add(tuple(sorted((int(third), int(first)))))
    return np.asarray(sorted(edge_set), dtype=np.int64)


def load_fast_data(data_dir: Path) -> FastData:
    """读取并验证附件 1--3。

    参数:
        data_dir: 包含三个 GB18030 CSV 文件的目录。

    返回:
        可直接用于几何计算的不可变 ``FastData``。

    异常:
        DataValidationError: 字段、编号、形状或几何量不合法。
    """

    node_frame = _read_required_csv(data_dir / "附件1.csv", NODE_COLUMNS)
    node_ids = _validate_identifiers(node_frame)
    index_by_id = {identifier: index for index, identifier in enumerate(node_ids)}
    actuator_frame = _read_required_csv(data_dir / "附件2.csv", ACTUATOR_COLUMNS)
    panel_frame = _read_required_csv(data_dir / "附件3.csv", PANEL_COLUMNS)

    actuator_ids = actuator_frame[ACTUATOR_COLUMNS[0]].astype(str).str.strip()
    if actuator_ids.tolist() != node_ids.tolist():
        raise DataValidationError("附件2的节点顺序或编号与附件1不一致")
    panels = _map_panels(panel_frame, index_by_id)
    edges = _build_edges(panels)

    nodes = node_frame[NODE_COLUMNS[1:]].to_numpy(dtype=float)
    lower = actuator_frame[ACTUATOR_COLUMNS[1:4]].to_numpy(dtype=float)
    upper = actuator_frame[ACTUATOR_COLUMNS[4:7]].to_numpy(dtype=float)
    if nodes.shape != (2226, 3) or panels.shape != (4300, 3):
        raise DataValidationError("附件规模与题面给出的 2226 节点、4300 面板不一致")
    if edges.shape != (6525, 2):
        raise DataValidationError("三角拓扑未恢复出题面规定的 6525 条主索")

    radii = np.linalg.norm(nodes, axis=1)
    upper_radii = np.linalg.norm(upper, axis=1)
    if np.any(radii <= 0) or np.any(upper_radii <= 0):
        raise DataValidationError("节点或促动器顶端出现零半径")
    edge_vectors = nodes[edges[:, 0]] - nodes[edges[:, 1]]
    edge_lengths = np.linalg.norm(edge_vectors, axis=1)
    if np.any(edge_lengths <= 0):
        raise DataValidationError("主索边长度必须为正")

    return FastData(
        node_ids=node_ids,
        nodes=nodes,
        actuator_lower=lower,
        actuator_upper=upper,
        panels=panels,
        edges=edges,
        radii=radii,
        node_units=nodes / radii[:, None],
        actuator_units=upper / upper_radii[:, None],
        down_cable_lengths=np.linalg.norm(nodes - upper, axis=1),
        edge_lengths=edge_lengths,
    )


def build_direction_frame(
    data: FastData,
    alpha_deg: float,
    beta_deg: float,
    aperture_radius: float = 150.0,
) -> DirectionFrame:
    """构造观测轴、物理焦点及基准态工作口径。

    方位角和仰角使用度；口径半径单位为米。活动节点依据其在
    垂直观测轴平面上的投影距离选择。
    """

    if aperture_radius <= 0:
        raise ValueError("口径半径必须为正")
    alpha, beta = np.deg2rad([alpha_deg, beta_deg])
    sky = np.array(
        [
            np.cos(beta) * np.cos(alpha),
            np.cos(beta) * np.sin(alpha),
            np.sin(beta),
        ],
        dtype=float,
    )
    sky /= np.linalg.norm(sky)
    axis = -sky
    axial = data.nodes @ axis
    rho_squared = np.sum(data.nodes**2, axis=1) - axial**2
    active = (axial > 0) & (rho_squared <= aperture_radius**2)
    incident = active[data.edges[:, 0]] | active[data.edges[:, 1]]
    focus_radius = (1.0 - 0.466) * data.radius
    return DirectionFrame(
        sky=sky,
        axis=axis,
        focus=focus_radius * axis,
        active_nodes=active,
        incident_edges=incident,
    )


def paraboloid_target_displacement(
    data: FastData,
    frame: DirectionFrame,
    focal_length: float,
) -> FloatArray:
    """计算节点径向射线与指定理想抛物面的交点位移。

    返回与全部节点等长的数组，口径外节点位移为零；正值表示
    节点朝球心移动。焦距和位移单位均为米。
    """

    if focal_length <= 0:
        raise ValueError("抛物面焦距必须为正")
    focus_radius = float(np.linalg.norm(frame.focus))
    vertex_radius = focus_radius + focal_length
    cosine = data.node_units @ frame.axis
    radial_factor = 1.0 - cosine**2
    root_term = focal_length**2 * cosine**2
    root_term += focal_length * vertex_radius * radial_factor
    roots = -2.0 * focal_length * cosine + 2.0 * np.sqrt(root_term)
    intersection = np.divide(
        roots,
        radial_factor,
        out=np.zeros_like(roots),
        where=np.abs(radial_factor) > 1e-12,
    )
    axial_case = vertex_radius / cosine
    intersection = np.where(np.abs(radial_factor) <= 1e-12, axial_case, intersection)
    displacement = np.zeros_like(data.radii)
    displacement[frame.active_nodes] = (
        data.radii[frame.active_nodes] - intersection[frame.active_nodes]
    )
    return displacement


def actuator_strokes(
    data: FastData,
    displacement: FloatArray,
) -> tuple[FloatArray, BoolArray]:
    """由节点径向位移求保持下拉索定长的促动器伸缩量。

    返回伸缩量和逐节点可达标记。选择在零位移处等于零并连续的
    二次方程根，正伸缩量表示促动器顶端向球心运动。
    """

    if displacement.shape != data.radii.shape:
        raise ValueError("位移数组形状错误")
    delta = data.nodes - data.actuator_upper
    moved_delta = delta - displacement[:, None] * data.node_units
    # 下拉索定长方程关于促动器伸缩量是一元二次式，必须沿零位移根连续取支。
    coefficient = np.sum(data.actuator_units * moved_delta, axis=1)
    constant = np.sum(moved_delta**2, axis=1) - data.down_cable_lengths**2
    discriminant = coefficient**2 - constant
    reachable = discriminant >= -1e-10
    safe_discriminant = np.maximum(discriminant, 0.0)
    baseline_coefficient = np.sum(data.actuator_units * delta, axis=1)
    branch = np.where(baseline_coefficient >= 0.0, 1.0, -1.0)
    strokes = -coefficient + branch * np.sqrt(safe_discriminant)
    strokes[~reachable] = np.nan
    return strokes, reachable


def constraint_summary(
    data: FastData,
    frame: DirectionFrame,
    displacement: FloatArray,
) -> dict[str, float | int | bool]:
    """精确回代促动器和主索约束并返回最坏指标。"""

    strokes, reachable = actuator_strokes(data, displacement)
    moved_nodes = data.nodes - displacement[:, None] * data.node_units
    edges = data.edges[frame.incident_edges]
    baseline = data.edge_lengths[frame.incident_edges]
    moved_edge_vectors = moved_nodes[edges[:, 0]] - moved_nodes[edges[:, 1]]
    relative_changes = np.abs(np.linalg.norm(moved_edge_vectors, axis=1) / baseline - 1.0)
    active_strokes = strokes[frame.active_nodes]
    active_reachable = reachable[frame.active_nodes]
    max_stroke = float(np.nanmax(np.abs(active_strokes)))
    max_edge_change = float(np.max(relative_changes))
    return {
        "active_nodes": int(np.sum(frame.active_nodes)),
        "incident_edges": int(np.sum(frame.incident_edges)),
        "reachable": bool(np.all(active_reachable)),
        "max_abs_stroke_m": max_stroke,
        "max_edge_relative_change": max_edge_change,
        "actuator_utilization": max_stroke / 0.6,
        "edge_utilization": max_edge_change / 0.0007,
        "feasible": bool(
            np.all(active_reachable)
            and max_stroke <= 0.6 + 1e-10
            and max_edge_change <= 0.0007 + 1e-12
        ),
    }


def hardware_utilization(
    data: FastData,
    frame: DirectionFrame,
    focal_length: float,
) -> float:
    """返回理想目标面的最坏归一化硬件占用率。"""

    displacement = paraboloid_target_displacement(data, frame, focal_length)
    summary = constraint_summary(data, frame, displacement)
    if not summary["reachable"]:
        return float("inf")
    return float(max(summary["actuator_utilization"], summary["edge_utilization"]))


def node_area_weights(data: FastData) -> FloatArray:
    """按相邻三角面板面积的三分之一构造节点面积权重。"""

    vertices = data.nodes[data.panels]
    cross = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    weights = np.zeros(len(data.node_ids), dtype=float)
    for corner in range(3):
        np.add.at(weights, data.panels[:, corner], areas / 3.0)
    if np.any(weights <= 0):
        raise DataValidationError("存在未获得正面积权重的节点")
    return weights
