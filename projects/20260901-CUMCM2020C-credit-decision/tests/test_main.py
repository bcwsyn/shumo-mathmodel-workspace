"""Focused tests for the credit decision pipeline's numerical invariants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "code" / "main.py"
SPEC = importlib.util.spec_from_file_location("credit_main", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
credit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = credit
SPEC.loader.exec_module(credit)


def test_safe_divide_handles_zero_denominator() -> None:
    result = credit.safe_divide(np.array([6.0, 4.0]), np.array([3.0, 0.0]))
    assert np.allclose(result, [2.0, 0.0])


def test_normal_models_fit_current_library_api() -> None:
    x = np.tile(np.arange(4, dtype=float), (24, 1))
    x += np.repeat(np.arange(24, dtype=float)[:, None], 4, axis=1) / 10.0
    y = np.tile(np.arange(4), 6)
    logistic, xgboost = credit._make_models(credit.Config(xgb_estimators=2), 4)
    assert logistic.fit(x, y).predict_proba(x).shape == (24, 4)
    assert xgboost.fit(x, y).predict_proba(x).shape == (24, 4)


def test_demand_model_is_monotone_after_isotonic_fit(tmp_path: Path) -> None:
    path = tmp_path / "demand.xlsx"
    frame = pd.DataFrame(
        [
            ["利率", "A", "B", "C"],
            [None, None, None, None],
            [0.04, 0.0, 0.0, 0.0],
            [0.08, 0.5, 0.4, 0.3],
            [0.12, 0.45, 0.6, 0.5],
        ]
    )
    frame.to_excel(path, header=False, index=False)
    model = credit.load_demand_model(path)
    assert np.all(np.diff(model.monotone_loss, axis=1) >= -1e-12)
    assert np.isclose(model.monotone_loss[0, 1], model.monotone_loss[0, 2])


def test_normal_portfolio_honors_budget_bounds_and_ineligible() -> None:
    config = credit.Config(min_loan_yuan=100_000.0, max_loan_yuan=200_000.0)
    loan, selected, check = credit._portfolio_milp(
        unit_benefit=np.array([0.06, 0.05, 0.04]),
        risk_weight=np.array([0.01, 0.02, 0.03]),
        eligible=np.array([True, False, True]),
        budget_yuan=400_000.0,
        risk_cap_yuan=400_000.0,
        config=config,
    )
    assert np.isclose(loan.sum(), 400_000.0)
    assert loan[1] == 0.0
    assert selected.sum() == 2
    assert np.all((loan[selected] >= 100_000.0) & (loan[selected] <= 200_000.0))
    assert abs(check["budget_error_yuan"]) < 1e-6


def test_portfolio_rejects_infeasible_budget() -> None:
    config = credit.Config(min_loan_yuan=100_000.0, max_loan_yuan=100_000.0)
    with pytest.raises(credit.OptimizationError):
        credit._portfolio_milp(
            unit_benefit=np.array([0.03, 0.02]),
            risk_weight=np.array([0.01, 0.01]),
            eligible=np.array([True, False]),
            budget_yuan=200_000.0,
            risk_cap_yuan=200_000.0,
            config=config,
        )


def test_problem1_hard_excludes_observed_d_rating() -> None:
    index = pd.Index(["E1", "E2", "E3", "E4"], name="enterprise_id")
    source = pd.DataFrame(
        {
            "p_A": [0.8, 0.1, 0.1, 0.1],
            "p_B": [0.1, 0.7, 0.1, 0.1],
            "p_C": [0.05, 0.1, 0.7, 0.1],
            "p_D": [0.05, 0.1, 0.1, 0.7],
            "rating_observed": ["A", "B", "C", "D"],
            "default_observed": ["否", "否", "否", "是"],
            "cri_oof": [10.0, 35.0, 60.0, 90.0],
        },
        index=index,
    )
    features = pd.DataFrame(
        {
            "sales_monthly_cv_log": [0.1, 0.2, 0.3, 0.4],
            "sales_recent_growth_log": [0.1, 0.2, 0.3, 0.4],
            "sales_hhi": [0.1, 0.2, 0.3, 0.4],
            "purchase_hhi": [0.1, 0.2, 0.3, 0.4],
            "sales_negative_rate": [0.1, 0.2, 0.3, 0.4],
            "sales_active_ratio": [0.9, 0.8, 0.7, 0.6],
        },
        index=index,
    )
    demand = credit.DemandModel(
        rates=np.array([0.04, 0.1]),
        raw_loss=np.array([[0.0, 0.5], [0.0, 0.5], [0.0, 0.5]]),
        monotone_loss=np.array([[0.0, 0.5], [0.0, 0.5], [0.0, 0.5]]),
    )
    config = credit.Config(
        min_loan_yuan=100_000.0,
        max_loan_yuan=100_000.0,
        problem1_budget_yuan=300_000.0,
    )
    table, _ = credit._problem1(
        source, features, demand, np.array([0.02, 0.04, 0.08, 0.98]), config
    )
    assert table.loc["E4", "loan_yuan"] == 0.0
