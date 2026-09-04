"""问题三的反射定律与馈源命中判据。

G2 通过解析理想抛物面聚焦残差验证符号、法向和馈源平面求交；
完整三角面板细分及正式接收比留待 G3。
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from fast_geometry import DirectionFrame


FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


def reflect_directions(incident: FloatArray, normals: FloatArray) -> FloatArray:
    """按镜面反射定律计算单位反射方向。"""

    if incident.shape != normals.shape or incident.ndim != 2 or incident.shape[1] != 3:
        raise ValueError("入射方向和法向必须是相同形状的 N×3 数组")
    unit_incident = incident / np.linalg.norm(incident, axis=1)[:, None]
    unit_normals = normals / np.linalg.norm(normals, axis=1)[:, None]
    # 镜面反射只改变法向分量，切向分量保持不变。
    projections = np.sum(unit_incident * unit_normals, axis=1)
    reflected = unit_incident - 2.0 * projections[:, None] * unit_normals
    return reflected / np.linalg.norm(reflected, axis=1)[:, None]


def receiver_hits(
    points: FloatArray,
    directions: FloatArray,
    focus: FloatArray,
    sky: FloatArray,
    receiver_radius: float = 0.5,
) -> BoolArray:
    """判断反射线是否正向命中馈源平面的有效圆盘。"""

    if points.shape != directions.shape or points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("射线起点和方向必须是相同形状的 N×3 数组")
    if receiver_radius <= 0:
        raise ValueError("馈源有效半径必须为正")
    denominator = directions @ sky
    numerator = (focus[None, :] - points) @ sky
    valid = np.abs(denominator) > 1e-14
    distance = np.full(len(points), np.nan, dtype=float)
    distance[valid] = numerator[valid] / denominator[valid]
    intersections = points + distance[:, None] * directions
    radial_distance = np.linalg.norm(intersections - focus[None, :], axis=1)
    return valid & (distance > 0) & (radial_distance <= receiver_radius)


def ideal_paraboloid_focus_error(
    frame: DirectionFrame,
    focal_length: float,
    aperture_radius: float = 150.0,
) -> float:
    """计算解析理想抛物面测试射线到焦点的最大残差，单位米。"""

    if focal_length <= 0 or aperture_radius <= 0:
        raise ValueError("焦距和口径半径必须为正")
    reference = np.array([1.0, 0.0, 0.0])
    if abs(float(reference @ frame.axis)) > 0.9:
        reference = np.array([0.0, 1.0, 0.0])
    first = np.cross(frame.axis, reference)
    first /= np.linalg.norm(first)
    second = np.cross(frame.axis, first)
    radii = np.linspace(0.0, aperture_radius, 7)
    angles = np.linspace(0.0, 2.0 * np.pi, 13, endpoint=False)
    rho, angle = np.meshgrid(radii, angles, indexing="ij")
    transverse = np.cos(angle)[..., None] * first
    transverse += np.sin(angle)[..., None] * second
    focus_radius = float(np.linalg.norm(frame.focus))
    vertex_radius = focus_radius + focal_length
    axial = vertex_radius - rho**2 / (4.0 * focal_length)
    points = axial[..., None] * frame.axis + rho[..., None] * transverse
    gradient = 2.0 * rho[..., None] * transverse + 4.0 * focal_length * frame.axis
    normals = -gradient / np.linalg.norm(gradient, axis=2)[..., None]
    flat_points = points.reshape(-1, 3)
    flat_normals = normals.reshape(-1, 3)
    incident = np.repeat(frame.axis[None, :], len(flat_points), axis=0)
    reflected = reflect_directions(incident, flat_normals)
    line_parameter = np.sum(
        (frame.focus[None, :] - flat_points) * reflected,
        axis=1,
    )
    closest = flat_points + line_parameter[:, None] * reflected
    return float(np.max(np.linalg.norm(closest - frame.focus[None, :], axis=1)))
