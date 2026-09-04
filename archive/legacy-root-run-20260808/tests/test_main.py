"""G2 tests for exact sampling boundaries and the minimum production-state solver."""

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "code" / "main.py"
SPEC = importlib.util.spec_from_file_location("cumcm_b_main", MODULE_PATH)
assert SPEC and SPEC.loader
main = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = main
SPEC.loader.exec_module(main)


def test_exact_confidence_edge_cases() -> None:
    """All-good and all-bad samples meet the independently checkable G1 limits."""
    lower_bad, _ = main.one_sided_bounds(2, 2)
    _, upper_good = main.one_sided_bounds(0, 22)
    assert lower_bad > 0.10
    assert upper_good <= 0.10
    assert main.confidence_decision(2, 2) == "reject"
    assert main.confidence_decision(0, 22) == "accept"


def test_sprt_extreme_streams_stop_in_expected_directions() -> None:
    """Extreme sequences should cross the precomputed likelihood boundaries."""
    config = main.SamplingConfig()
    assert main.sprt_decision(0, 100, config) == "accept"
    assert main.sprt_decision(20, 20, config) == "reject"


def test_zero_defect_production_prefers_no_inspection() -> None:
    """When defects vanish, positive inspection costs cannot improve expected profit."""
    scenario = main.Scenario((0, 0), (4, 18), (2, 3), 0, 6, 3, 56, 6, 5)
    best = main.evaluate_scenario(scenario)[0]
    assert best.feasible
    assert best.policy == main.Policy(False, False, False, False)
    assert best.expected_profit == pytest.approx(28.0)


def test_uninspected_bad_component_with_disassembly_is_nonabsorbing() -> None:
    """A preserved known-bad component cannot escape a recycle loop without inspection."""
    scenario = main.Scenario((0.1, 0.1), (4, 18), (2, 3), 0.1, 6, 3, 56, 6, 5)
    result = main.evaluate_policy(scenario, main.Policy(False, False, True, True))
    assert not result.feasible
    assert result.expected_profit is None


def test_invalid_probability_fails_explicitly() -> None:
    """Invalid external inputs must raise a model-specific error, not silently clip."""
    with pytest.raises(main.ModelInputError):
        main.confidence_decision(0, 22, nominal_rate=1.0)


def test_problem3_restricted_policy_comparison_has_expected_order() -> None:
    """The table-2 all-inspected candidate family should favor final reuse here."""
    best = main.all_inspected_tree_cost(False, False, True)
    discard = main.all_inspected_tree_cost(False, False, False)
    assert best == pytest.approx(62.2222222222)
    assert best > discard


def test_sprt_simulation_reports_a_normalised_probability_partition() -> None:
    """Monte Carlo operating-characteristic output must account for every run."""
    result = main.simulate_sprt(0.05, main.SamplingConfig(), runs=500, maximum=400)
    assert sum(result[key] for key in ("accept_rate", "reject_rate", "undecided_rate")) == pytest.approx(1.0)
    assert result["accept_rate"] > result["reject_rate"]
