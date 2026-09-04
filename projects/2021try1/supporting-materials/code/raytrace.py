"""FAST 三角面板确定性细分射线追踪。

输入为基准或调整后的节点坐标，输出 300 米投影口径内的投影面积
加权接收比、收敛记录和面板中心在馈源平面的落点。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from fast_geometry import DirectionFrame, FastData
from problem3 import reflect_directions


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class RayTraceResult:
    """保存一个细分级别的接收比和能量统计。"""

    subdivision: int
    reception_ratio: float
    received_weight: float
    total_weight: float
    included_samples: int


def barycentric_micro_centroids(subdivision: int) -> FloatArray:
    """生成等面积三角细分的全部微三角形重心坐标。"""

    if subdivision < 1:
        raise ValueError("三角细分级别必须为正整数")
    coordinates: list[tuple[float, float, float]] = []
    scale = float(subdivision)
    for first in range(subdivision):
        for second in range(subdivision - first):
            beta = (first + 1.0 / 3.0) / scale
            gamma = (second + 1.0 / 3.0) / scale
            coordinates.append((1.0 - beta - gamma, beta, gamma))
            if first + second <= subdivision - 2:
                beta = (first + 2.0 / 3.0) / scale
                gamma = (second + 2.0 / 3.0) / scale
                coordinates.append((1.0 - beta - gamma, beta, gamma))
    result = np.asarray(coordinates, dtype=float)
    if result.shape != (subdivision**2, 3):
        raise RuntimeError("三角细分重心数量不等于 subdivision²")
    return result


def _face_geometry(
    data: FastData,
    frame: DirectionFrame,
    nodes: FloatArray,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    vertices = nodes[data.panels]
    cross = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    double_area = np.linalg.norm(cross, axis=1)
    if np.any(double_area <= 0):
        raise ValueError("调整后表面存在零面积面板")
    normals = cross / double_area[:, None]
    # 面板顶点顺序不保证统一，法向一律翻到天体侧，确保入射点积为负。
    flip = (normals @ frame.sky) < 0
    normals[flip] *= -1.0
    reflected = reflect_directions(
        np.repeat(frame.axis[None, :], len(normals), axis=0),
        normals,
    )
    return vertices, normals, reflected


def trace_surface(
    data: FastData,
    frame: DirectionFrame,
    nodes: FloatArray,
    subdivision: int,
    aperture_radius: float = 150.0,
    projected_weight: bool = True,
    batch_size: int = 256,
) -> RayTraceResult:
    """计算给定三角面板表面的确定性细分接收比。"""

    if nodes.shape != data.nodes.shape:
        raise ValueError("节点坐标形状必须与附件1一致")
    if aperture_radius <= 0 or batch_size < 1:
        raise ValueError("口径半径和批大小必须为正")
    barycentric = barycentric_micro_centroids(subdivision)
    vertices, normals, reflected = _face_geometry(data, frame, nodes)
    face_areas = 0.5 * np.linalg.norm(
        np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0]),
        axis=1,
    )
    total_weight = 0.0
    received_weight = 0.0
    included_samples = 0
    for start in range(0, len(vertices), batch_size):
        stop = min(len(vertices), start + batch_size)
        points = np.einsum(
            "sk,bkd->bsd",
            barycentric,
            vertices[start:stop],
            optimize=True,
        )
        axial = np.einsum("bsd,d->bs", points, frame.axis)
        radius_squared = np.sum(points**2, axis=2) - axial**2
        in_aperture = (axial > 0) & (radius_squared <= aperture_radius**2)
        directions = reflected[start:stop]
        denominator = directions @ frame.sky
        numerator = np.einsum(
            "bsd,d->bs",
            frame.focus[None, None, :] - points,
            frame.sky,
        )
        forward = np.abs(denominator) > 1e-14
        distance = np.divide(
            numerator,
            denominator[:, None],
            out=np.full_like(numerator, np.nan),
            where=forward[:, None],
        )
        intersections = points + distance[..., None] * directions[:, None, :]
        receiver_distance = np.linalg.norm(
            intersections - frame.focus[None, None, :],
            axis=2,
        )
        hit = in_aperture & (distance > 0) & (receiver_distance <= 0.5)
        if projected_weight:
            face_weight = face_areas[start:stop]
            face_weight *= np.abs(normals[start:stop] @ frame.axis)
        else:
            face_weight = np.ones(stop - start, dtype=float)
        sample_weight = face_weight[:, None] / float(subdivision**2)
        total_weight += float(np.sum(sample_weight * in_aperture))
        received_weight += float(np.sum(sample_weight * hit))
        included_samples += int(np.sum(in_aperture))
    ratio = received_weight / total_weight
    return RayTraceResult(
        subdivision=subdivision,
        reception_ratio=ratio,
        received_weight=received_weight,
        total_weight=total_weight,
        included_samples=included_samples,
    )


def trace_convergence(
    data: FastData,
    frame: DirectionFrame,
    nodes: FloatArray,
    levels: tuple[int, ...] = (2, 4, 8, 16, 32),
    aperture_radius: float = 150.0,
    projected_weight: bool = True,
) -> list[RayTraceResult]:
    """按给定细分级别计算接收比收敛序列。"""

    if not levels or any(level < 1 for level in levels):
        raise ValueError("收敛级别必须全部为正")
    return [
        trace_surface(
            data,
            frame,
            nodes,
            subdivision=level,
            aperture_radius=aperture_radius,
            projected_weight=projected_weight,
        )
        for level in levels
    ]


def panel_centroid_landings(
    data: FastData,
    frame: DirectionFrame,
    nodes: FloatArray,
) -> FloatArray:
    """返回面板中心反射线在馈源平面内的二维正交坐标。"""

    vertices, _, reflected = _face_geometry(data, frame, nodes)
    centroids = np.mean(vertices, axis=1)
    denominator = reflected @ frame.sky
    numerator = (frame.focus[None, :] - centroids) @ frame.sky
    distance = np.divide(
        numerator,
        denominator,
        out=np.full_like(numerator, np.nan),
        where=np.abs(denominator) > 1e-14,
    )
    intersections = centroids + distance[:, None] * reflected
    reference = np.array([1.0, 0.0, 0.0])
    if abs(float(reference @ frame.sky)) > 0.9:
        reference = np.array([0.0, 1.0, 0.0])
    first = np.cross(frame.sky, reference)
    first /= np.linalg.norm(first)
    second = np.cross(frame.sky, first)
    offsets = intersections - frame.focus[None, :]
    return np.column_stack((offsets @ first, offsets @ second))
