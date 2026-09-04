"""G2 最小实现的正常、边界、失败与端到端测试。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "code" / "main.py"
SPEC = importlib.util.spec_from_file_location("cumcm2018a_main", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)
sys.modules["main"] = MODEL
G3_PATH = PROJECT_ROOT / "code" / "g3.py"
G3_SPEC = importlib.util.spec_from_file_location("cumcm2018a_g3", G3_PATH)
assert G3_SPEC is not None and G3_SPEC.loader is not None
G3 = importlib.util.module_from_spec(G3_SPEC)
sys.modules[G3_SPEC.name] = G3
G3_SPEC.loader.exec_module(G3)


def _uniform_materials() -> tuple[object, ...]:
    return tuple(MODEL.Material(f"L{index}", 1000.0, 1000.0, 1.0) for index in range(4))


def test_thomas_known_solution() -> None:
    lower = np.array([-1.0, -1.0])
    diagonal = np.array([2.0, 2.0, 2.0])
    upper = np.array([-1.0, -1.0])
    factors = MODEL.factorize_tridiagonal(lower, diagonal, upper)
    solution = MODEL.thomas_solve(factors, np.array([0.0, 0.0, 4.0]))
    assert np.allclose(solution, np.array([1.0, 2.0, 3.0]), atol=1e-12)


def test_uniform_temperature_remains_constant() -> None:
    config = MODEL.SimulationConfig(37.0, 37.0, 37.0, 10.0, 1.0, 0.5, 10.0, 8.0)
    result = MODEL.simulate(_uniform_materials(), (1.0, 1.0, 1.0, 1.0), config)
    assert np.allclose(result.skin_temp_c, 37.0, atol=1e-12)


def test_steady_state_formula_matches_manual_value() -> None:
    value = MODEL.steady_skin_temperature(
        _uniform_materials(),
        (1.0, 1.0, 1.0, 1.0),
        57.0,
        37.0,
        10.0,
        5.0,
    )
    assert value == pytest.approx(50.1578947368421, abs=1e-12)


def test_duration_above_threshold_interpolates_crossings() -> None:
    times = np.array([0.0, 1.0, 2.0])
    temperatures = np.array([43.0, 45.0, 43.0])
    duration = MODEL.duration_above_threshold(times, temperatures, 44.0)
    assert duration == pytest.approx(1.0, abs=1e-12)


def test_validate_measurements_rejects_duplicate_time() -> None:
    with pytest.raises(MODEL.DataValidationError, match="1 s"):
        MODEL.validate_measurements(
            np.array([0.0, 1.0, 1.0]),
            np.array([37.0, 37.1, 37.2]),
        )


def test_simulation_rejects_negative_heat_transfer() -> None:
    config = MODEL.SimulationConfig(75.0, 37.0, 37.0, 10.0, 1.0, 0.5, -1.0, 8.0)
    with pytest.raises(MODEL.ConfigurationError, match="必须为正"):
        MODEL.simulate(_uniform_materials(), (1.0, 1.0, 1.0, 1.0), config)


def test_actual_workbook_pipeline() -> None:
    workbook = PROJECT_ROOT / "inputs" / "CUMCM-2018-Problem-A-Chinese-Appendix.xlsx"
    materials, times, temperatures = MODEL.load_problem_data(workbook)
    assert len(materials) == 4
    assert len(times) == 5401
    assert times[-1] == pytest.approx(5400.0)
    assert temperatures[-1] == pytest.approx(48.08)


def test_design_metric_matches_constraint_definition() -> None:
    config = MODEL.SimulationConfig(57.0, 37.0, 37.0, 60.0, 1.0, 0.5, 10.0, 8.0)
    metric = G3.evaluate_design(_uniform_materials(), 2.0, 2.0, config)
    assert metric.max_skin_temp_c == pytest.approx(metric.final_skin_temp_c)
    assert metric.duration_above_44_s == pytest.approx(0.0)
    assert metric.feasible


def test_q2_small_enumeration_is_monotone() -> None:
    config = MODEL.SimulationConfig(65.0, 37.0, 37.0, 120.0, 2.0, 0.5, 20.0, 8.0)
    table = G3.enumerate_designs(
        _uniform_materials(),
        np.array([1.0, 2.0, 3.0]),
        np.array([2.0]),
        config,
        workers=1,
    )
    assert len(table) == 3
    assert np.all(np.diff(table["max_skin_temp_c"]) <= 0.0)


def test_q3_small_double_enumeration_is_finite() -> None:
    config = MODEL.SimulationConfig(80.0, 37.0, 37.0, 120.0, 2.0, 0.5, 20.0, 8.0)
    table = G3.enumerate_designs(
        _uniform_materials(),
        np.array([1.0, 2.0]),
        np.array([1.0, 2.0]),
        config,
        workers=1,
    )
    assert len(table) == 4
    assert np.all(np.isfinite(table["max_skin_temp_c"]))


def test_pareto_mask_removes_dominated_points() -> None:
    objectives = np.array([[1.0, 4.0], [2.0, 3.0], [3.0, 5.0], [4.0, 2.0]])
    mask = G3._pareto_mask(objectives)
    assert mask.tolist() == [True, True, False, True]


def test_total_thickness_tie_breaks_by_areal_mass() -> None:
    table = G3.pd.DataFrame(
        {
            "d2_mm": [19.4, 19.3],
            "d4_mm": [6.3, 6.4],
            "max_skin_temp_c": [44.81, 44.79],
            "duration_above_44_s": [298.0, 294.0],
            "feasible": [True, True],
        }
    )
    optimum = G3._first_feasible(table, "total")
    assert optimum["d2_mm"] == pytest.approx(19.3)
    assert optimum["d4_mm"] == pytest.approx(6.4)
