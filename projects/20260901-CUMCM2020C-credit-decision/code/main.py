"""2020C credit-risk transfer and robust portfolio optimization pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from sklearn.base import clone
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    f1_score,
    log_loss,
    mean_absolute_error,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))
LOGGER = logging.getLogger(__name__)

RATING_ORDER = ["A", "B", "C", "D"]
RATING_TO_INT = {rating: index for index, rating in enumerate(RATING_ORDER)}
SEVERITY = np.array([0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0])
AMOUNT_UNIT_YUAN = 1_000_000.0


class DataValidationError(ValueError):
    """Raised when a frozen input violates the documented data contract."""


class OptimizationError(RuntimeError):
    """Raised when the portfolio problem is infeasible or fails to converge."""


@dataclass(frozen=True)
class Config:
    """Runtime configuration for one reproducible experiment."""

    seed: int = 42
    cutoff: str = "2020-02-21"
    feature_start: str = "2016-10"
    min_loan_yuan: float = 100_000.0
    max_loan_yuan: float = 1_000_000.0
    problem1_budget_yuan: float = 50_000_000.0
    problem2_budget_yuan: float = 100_000_000.0
    portfolio_risk_cap_fraction: float = 0.013
    lgd: float = 1.0
    cv_repeats: int = 5
    xgb_estimators: int = 160
    selected_features: int = 14
    solver_time_limit: float = 90.0


@dataclass
class ModelBundle:
    """Fitted source-domain models and their validated fusion settings."""

    logistic: Pipeline
    xgboost: Pipeline
    fusion_weight: float
    feature_names: list[str]
    classes: np.ndarray


@dataclass
class DemandModel:
    """Monotone customer-loss curves indexed by rating and interest rate."""

    rates: np.ndarray
    raw_loss: np.ndarray
    monotone_loss: np.ndarray


def safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Divide elementwise while returning zero for a zero denominator.

    Args:
        numerator: Numeric numerator array.
        denominator: Numeric denominator array with the same broadcast shape.

    Returns:
        Finite quotient array.
    """

    numerator = np.asarray(numerator, dtype=float)
    denominator = np.asarray(denominator, dtype=float)
    result = np.zeros(np.broadcast_shapes(numerator.shape, denominator.shape))
    return np.divide(numerator, denominator, out=result, where=denominator != 0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_invoice_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.dropna(axis=1, how="all").copy()
    if frame.shape[1] < 8:
        raise DataValidationError("发票工作表少于 8 个有效字段")
    frame = frame.iloc[:, :8]
    frame.columns = [
        "enterprise_id",
        "invoice_no",
        "date",
        "counterparty",
        "amount",
        "tax",
        "total",
        "status",
    ]
    frame["enterprise_id"] = frame["enterprise_id"].astype(str).str.strip()
    frame["counterparty"] = frame["counterparty"].astype(str).str.strip()
    frame["status"] = frame["status"].astype(str).str.strip()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in ["amount", "tax", "total"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    required = ["enterprise_id", "date", "amount", "status"]
    if frame[required].isna().any().any():
        raise DataValidationError("发票关键字段存在无法解析的空值")
    # 发票号码会跨期复用，因此只去除八字段完全相同的复制行。
    return frame.drop_duplicates().reset_index(drop=True)


def _invoice_direction(columns: pd.Index) -> str:
    names = {str(value).strip() for value in columns}
    if "销方单位代号" in names:
        return "purchase"
    if "购方单位代号" in names:
        return "sales"
    raise DataValidationError("无法依据交易对手字段识别进项或销项")


def _monthly_matrix(
    valid: pd.DataFrame, enterprise_ids: pd.Index, config: Config
) -> np.ndarray:
    months = pd.period_range(
        config.feature_start, pd.Period(config.cutoff, freq="M"), freq="M"
    )
    grouped = (
        valid.assign(month=valid["date"].dt.to_period("M"))
        .groupby(["enterprise_id", "month"], observed=True)["amount"]
        .sum()
        .unstack(fill_value=0.0)
        .reindex(index=enterprise_ids, columns=months, fill_value=0.0)
    )
    return grouped.to_numpy(dtype=float)


def _counterparty_metrics(
    valid: pd.DataFrame, enterprise_ids: pd.Index
) -> pd.DataFrame:
    amounts = valid.assign(abs_amount=valid["amount"].abs())
    by_party = amounts.groupby(["enterprise_id", "counterparty"], observed=True)[
        "abs_amount"
    ].sum()
    totals = by_party.groupby(level=0).sum()
    shares = by_party / totals.replace(0.0, np.nan).reindex(by_party.index, level=0)
    hhi = shares.pow(2).groupby(level=0).sum()
    top5 = (
        shares.sort_values(ascending=False)
        .groupby(level=0, group_keys=False)
        .head(5)
        .groupby(level=0)
        .sum()
    )
    counts = valid.groupby("enterprise_id")["counterparty"].nunique()
    return pd.DataFrame(
        {
            "counterparty_count_log": np.log1p(counts),
            "hhi": hhi,
            "top5_share": top5,
        }
    ).reindex(enterprise_ids, fill_value=0.0)


def _direction_aggregates(
    frame: pd.DataFrame, enterprise_ids: pd.Index
) -> tuple[
    pd.Series, pd.DataFrame, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series
]:
    total_count = (
        frame.groupby("enterprise_id").size().reindex(enterprise_ids, fill_value=0)
    )
    valid = frame.loc[frame["status"] == "有效发票"].copy()
    valid_count = (
        valid.groupby("enterprise_id").size().reindex(enterprise_ids, fill_value=0)
    )
    amount = valid.groupby("enterprise_id")["amount"]
    signed_sum = amount.sum().reindex(enterprise_ids, fill_value=0.0)
    positive_sum = (
        valid.assign(positive=valid["amount"].clip(lower=0.0))
        .groupby("enterprise_id")["positive"]
        .sum()
        .reindex(enterprise_ids, fill_value=0.0)
    )
    negative_rate = (
        valid.assign(is_negative=valid["amount"] < 0)
        .groupby("enterprise_id")["is_negative"]
        .mean()
        .reindex(enterprise_ids, fill_value=0.0)
    )
    mean_abs = (
        valid.assign(abs_amount=valid["amount"].abs())
        .groupby("enterprise_id")["abs_amount"]
        .mean()
        .reindex(enterprise_ids, fill_value=0.0)
    )
    return (
        total_count,
        valid,
        valid_count,
        signed_sum,
        positive_sum,
        negative_rate,
        mean_abs,
    )


def _direction_features(
    frame: pd.DataFrame, enterprise_ids: pd.Index, prefix: str, config: Config
) -> pd.DataFrame:
    aggregates = _direction_aggregates(frame, enterprise_ids)
    (
        total_count,
        valid,
        valid_count,
        signed_sum,
        positive_sum,
        negative_rate,
        mean_abs,
    ) = aggregates
    monthly = _monthly_matrix(valid, enterprise_ids, config)
    t = np.arange(monthly.shape[1], dtype=float)
    t -= t.mean()
    slope = monthly @ t / np.dot(t, t)
    mean_abs_monthly = np.mean(np.abs(monthly), axis=1)
    recent = monthly[:, -12:].sum(axis=1)
    prior = monthly[:, -24:-12].sum(axis=1)
    party = _counterparty_metrics(valid, enterprise_ids)
    features = pd.DataFrame(index=enterprise_ids)
    features["invoice_count_log"] = np.log1p(valid_count)
    features["void_rate"] = safe_divide(total_count - valid_count, total_count)
    features["negative_rate"] = negative_rate
    features["positive_amount_log"] = np.log1p(positive_sum)
    features["signed_amount_asinh"] = np.arcsinh(signed_sum / 100_000.0)
    features["avg_abs_amount_log"] = np.log1p(mean_abs)
    features = features.join(party)
    features["active_ratio"] = np.mean(np.abs(monthly) > 0.01, axis=1)
    features["monthly_cv_log"] = np.log1p(
        safe_divide(monthly.std(axis=1), mean_abs_monthly + 1.0)
    )
    features["trend_norm"] = np.clip(safe_divide(slope, mean_abs_monthly + 1.0), -1, 1)
    features["recent12_log"] = np.arcsinh(recent / 100_000.0)
    features["recent_growth_log"] = np.clip(
        np.arcsinh(recent / 100_000.0) - np.arcsinh(prior / 100_000.0), -10, 10
    )
    features.columns = [f"{prefix}_{column}" for column in features.columns]
    return features


def _load_invoice_directions(book: pd.ExcelFile) -> dict[str, pd.DataFrame]:
    directions: dict[str, pd.DataFrame] = {}
    for sheet in book.sheet_names[1:]:
        raw = pd.read_excel(book, sheet_name=sheet)
        directions[_invoice_direction(raw.columns)] = _normalize_invoice_frame(raw)
    if set(directions) != {"purchase", "sales"}:
        raise DataValidationError("工作簿必须同时包含进项和销项发票")
    return directions


def _combine_direction_features(
    purchase: pd.DataFrame, sales: pd.DataFrame
) -> pd.DataFrame:
    features = purchase.join(sales)
    features["sales_purchase_log_ratio"] = (
        features["sales_positive_amount_log"] - features["purchase_positive_amount_log"]
    )
    signed_sales = np.sinh(features["sales_signed_amount_asinh"]) * 100_000.0
    signed_purchase = np.sinh(features["purchase_signed_amount_asinh"]) * 100_000.0
    features["margin_proxy"] = safe_divide(
        signed_sales - signed_purchase,
        np.abs(signed_sales) + np.abs(signed_purchase) + 1.0,
    )
    features["activity_gap"] = (
        features["sales_active_ratio"] - features["purchase_active_ratio"]
    )
    features["business_scale_log"] = np.logaddexp(
        features["sales_positive_amount_log"], features["purchase_positive_amount_log"]
    )
    return features


def load_enterprise_features(
    path: Path, config: Config
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read one workbook and construct enterprise-level operating features.

    Args:
        path: Frozen attachment 1 or attachment 2 workbook.
        config: Date and numerical settings.

    Returns:
        A pair ``(metadata, features)`` indexed by enterprise code.

    Raises:
        DataValidationError: If sheet direction, dates, or enterprise membership fail.
    """

    book = pd.ExcelFile(path, engine="openpyxl")
    info = pd.read_excel(book, sheet_name=0).dropna(axis=1, how="all")
    info.iloc[:, 0] = info.iloc[:, 0].astype(str).str.strip()
    info = info.set_index(info.columns[0], drop=True)
    info.index.name = "enterprise_id"
    if info.index.has_duplicates:
        raise DataValidationError("企业信息表存在重复企业代号")
    directions = _load_invoice_directions(book)
    enterprise_ids = info.index
    for direction, frame in directions.items():
        unknown = set(frame["enterprise_id"]) - set(enterprise_ids)
        if unknown:
            raise DataValidationError(f"{direction} 表存在未知企业代号")
    purchase = _direction_features(
        directions["purchase"], enterprise_ids, "purchase", config
    )
    sales = _direction_features(directions["sales"], enterprise_ids, "sales", config)
    features = _combine_direction_features(purchase, sales)
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise DataValidationError("企业特征包含非有限数值")
    return info, features


def load_demand_model(path: Path) -> DemandModel:
    """Fit nondecreasing rating-specific loss curves from attachment 3.

    The raw series contain small sampling reversals. Isotonic regression preserves
    the observed rate grid while imposing the economic monotonicity constraint.

    Args:
        path: Frozen attachment 3 workbook.

    Returns:
        Monotone loss curves for A, B and C ratings.
    """

    raw = pd.read_excel(path, sheet_name=0, header=None, engine="openpyxl")
    raw = (
        raw.dropna(axis=1, how="all").iloc[2:, :4].apply(pd.to_numeric, errors="coerce")
    )
    raw = raw.dropna(how="any")
    rates = raw.iloc[:, 0].to_numpy(dtype=float)
    losses = raw.iloc[:, 1:].to_numpy(dtype=float).T
    if len(rates) < 3 or not np.all(np.diff(rates) > 0):
        raise DataValidationError("利率点必须至少有三个且严格递增")
    if np.any((losses < 0) | (losses > 1)):
        raise DataValidationError("客户流失率必须位于 [0, 1]")
    fitted = np.vstack(
        [
            IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True).fit_transform(
                rates, row
            )
            for row in losses
        ]
    )
    return DemandModel(rates=rates, raw_loss=losses, monotone_loss=fitted)


def _make_models(config: Config, feature_count: int) -> tuple[Pipeline, Pipeline]:
    select_count = min(config.selected_features, feature_count)
    logistic = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("select", SelectKBest(f_classif, k=select_count)),
            (
                "model",
                LogisticRegression(
                    C=0.7,
                    max_iter=3000,
                    class_weight="balanced",
                    random_state=config.seed,
                ),
            ),
        ]
    )
    xgboost = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("select", SelectKBest(f_classif, k=select_count)),
            (
                "model",
                XGBClassifier(
                    n_estimators=config.xgb_estimators,
                    max_depth=2,
                    learning_rate=0.04,
                    subsample=0.8,
                    colsample_bytree=0.85,
                    min_child_weight=2.0,
                    reg_lambda=4.0,
                    reg_alpha=0.15,
                    objective="multi:softprob",
                    eval_metric="mlogloss",
                    num_class=4,
                    random_state=config.seed,
                    n_jobs=1,
                ),
            ),
        ]
    )
    return logistic, xgboost


def _normalize_probability(probability: np.ndarray) -> np.ndarray:
    """Clip floating-point noise and enforce row-wise probability normalization."""

    normalized = np.clip(np.asarray(probability, dtype=float), 0.0, 1.0)
    row_sum = normalized.sum(axis=1, keepdims=True)
    if np.any(row_sum <= 0.0):
        raise RuntimeError("分类概率行和非正，无法归一化")
    return normalized / row_sum


def _metric_summary(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    probability = _normalize_probability(probability)
    predicted = probability.argmax(axis=1)
    expected = probability @ np.arange(4, dtype=float)
    summary = {
        "accuracy": float(accuracy_score(y_true, predicted)),
        "macro_f1": float(
            f1_score(y_true, predicted, average="macro", zero_division=0)
        ),
        "ordinal_mae": float(mean_absolute_error(y_true, expected)),
        "quadratic_kappa": float(
            cohen_kappa_score(y_true, predicted, weights="quadratic")
        ),
        "log_loss": float(log_loss(y_true, probability, labels=np.arange(4))),
    }
    return summary


def _oof_probabilities(
    x: np.ndarray,
    y: np.ndarray,
    logistic: Pipeline,
    xgboost: Pipeline,
    config: Config,
) -> tuple[np.ndarray, np.ndarray]:
    splitter = RepeatedStratifiedKFold(
        n_splits=5, n_repeats=config.cv_repeats, random_state=config.seed
    )
    probability_logit = np.zeros((len(x), 4), dtype=float)
    probability_xgb = np.zeros((len(x), 4), dtype=float)
    fold_count = np.zeros(len(x), dtype=int)
    for train, test in splitter.split(x, y):
        probability_logit[test] += (
            clone(logistic).fit(x[train], y[train]).predict_proba(x[test])
        )
        probability_xgb[test] += (
            clone(xgboost).fit(x[train], y[train]).predict_proba(x[test])
        )
        fold_count[test] += 1
    if not np.all(fold_count == config.cv_repeats):
        raise RuntimeError("重复交叉验证的折外预测计数不一致")
    return _normalize_probability(
        probability_logit / fold_count[:, None]
    ), _normalize_probability(probability_xgb / fold_count[:, None])


def _select_fusion_weight(
    y: np.ndarray, probability_logit: np.ndarray, probability_xgb: np.ndarray
) -> tuple[float, dict[float, float]]:
    losses = {
        float(weight): log_loss(
            y,
            _normalize_probability(
                weight * probability_xgb + (1.0 - weight) * probability_logit
            ),
        )
        for weight in np.linspace(0.0, 1.0, 21)
    }
    return min(losses, key=losses.get), losses


def _ensemble_metrics(
    y: np.ndarray,
    defaults: pd.Series,
    probability_logit: np.ndarray,
    probability_xgb: np.ndarray,
    probability: np.ndarray,
    weight: float,
    losses: dict[float, float],
) -> dict[str, Any]:
    default_binary = defaults.astype(str).str.strip().eq("是").to_numpy(dtype=int)
    cri = 100.0 * (probability @ SEVERITY)
    return {
        "logistic": _metric_summary(y, probability_logit),
        "xgboost": _metric_summary(y, probability_xgb),
        "ensemble": _metric_summary(y, probability),
        "selected_xgboost_weight": float(weight),
        "weight_log_loss": {str(key): float(value) for key, value in losses.items()},
        "oof_default_auc": float(roc_auc_score(default_binary, cri)),
        "oof_cri_default_mean_yes": float(cri[default_binary == 1].mean()),
        "oof_cri_default_mean_no": float(cri[default_binary == 0].mean()),
    }


def _source_model_outputs(
    features: pd.DataFrame,
    ratings: pd.Series,
    defaults: pd.Series,
    probability: np.ndarray,
    logistic: Pipeline,
    xgboost: Pipeline,
    weight: float,
) -> tuple[ModelBundle, pd.DataFrame]:
    source = pd.DataFrame(
        probability,
        index=features.index,
        columns=[f"p_{rating}" for rating in RATING_ORDER],
    )
    source["rating_observed"] = ratings
    source["default_observed"] = defaults
    source["cri_oof"] = 100.0 * (probability @ SEVERITY)
    source["rating_predicted"] = [
        RATING_ORDER[value] for value in probability.argmax(axis=1)
    ]
    bundle = ModelBundle(
        logistic=logistic,
        xgboost=xgboost,
        fusion_weight=float(weight),
        feature_names=list(features.columns),
        classes=np.arange(4),
    )
    return bundle, source


def fit_risk_model(
    features: pd.DataFrame, ratings: pd.Series, defaults: pd.Series, config: Config
) -> tuple[ModelBundle, pd.DataFrame, dict[str, Any]]:
    """Fit the ensemble and return strict out-of-fold source predictions."""

    x = features.to_numpy(dtype=float)
    y = ratings.map(RATING_TO_INT).to_numpy(dtype=int)
    if set(np.unique(y)) != {0, 1, 2, 3}:
        raise DataValidationError("源域评级必须包含 A/B/C/D 四类")
    logistic, xgboost = _make_models(config, x.shape[1])
    probability_logit, probability_xgb = _oof_probabilities(
        x, y, logistic, xgboost, config
    )
    weight, loss_by_weight = _select_fusion_weight(
        y, probability_logit, probability_xgb
    )
    probability = _normalize_probability(
        weight * probability_xgb + (1.0 - weight) * probability_logit
    )
    metrics = _ensemble_metrics(
        y,
        defaults,
        probability_logit,
        probability_xgb,
        probability,
        weight,
        loss_by_weight,
    )
    logistic.fit(x, y)
    xgboost.fit(x, y)
    bundle, source = _source_model_outputs(
        features, ratings, defaults, probability, logistic, xgboost, weight
    )
    return bundle, source, metrics


def predict_risk(bundle: ModelBundle, features: pd.DataFrame) -> pd.DataFrame:
    """Apply the frozen source-domain ensemble to a compatible feature table."""

    if list(features.columns) != bundle.feature_names:
        raise DataValidationError("迁移特征列与源域训练特征不一致")
    x = features.to_numpy(dtype=float)
    probability = bundle.fusion_weight * bundle.xgboost.predict_proba(x)
    probability += (1.0 - bundle.fusion_weight) * bundle.logistic.predict_proba(x)
    probability = _normalize_probability(probability)
    result = pd.DataFrame(
        probability, index=features.index, columns=[f"p_{r}" for r in RATING_ORDER]
    )
    result["cri"] = 100.0 * (probability @ SEVERITY)
    result["rating_predicted"] = [
        RATING_ORDER[value] for value in probability.argmax(axis=1)
    ]
    result["prediction_entropy"] = -(
        probability * np.log(np.clip(probability, 1e-12, 1.0))
    ).sum(axis=1)
    return result


def _default_risk_coefficients(ratings: pd.Series, defaults: pd.Series) -> np.ndarray:
    counts = (
        ratings.value_counts().reindex(RATING_ORDER, fill_value=0).to_numpy(dtype=float)
    )
    events = (
        pd.crosstab(ratings, defaults.astype(str).str.strip())
        .reindex(index=RATING_ORDER, columns=["是"], fill_value=0)
        .iloc[:, 0]
        .to_numpy(dtype=float)
    )
    # Jeffreys smoothing avoids a literal zero loss coefficient for the A group.
    return (events + 0.5) / (counts + 1.0)


def _interpolate_loss(demand: DemandModel, probability: np.ndarray) -> np.ndarray:
    return probability[:, :3] @ demand.monotone_loss


def _vulnerability(features: pd.DataFrame) -> pd.Series:
    def _rank(column: str, ascending: bool = True) -> pd.Series:
        return features[column].rank(pct=True, ascending=ascending)

    values = pd.concat(
        [
            _rank("sales_monthly_cv_log"),
            _rank("sales_recent_growth_log", ascending=True).rsub(1.0),
            _rank("sales_hhi"),
            _rank("purchase_hhi"),
            _rank("sales_negative_rate"),
            _rank("sales_active_ratio", ascending=True).rsub(1.0),
        ],
        axis=1,
    )
    return values.mean(axis=1).clip(0.0, 1.0).rename("vulnerability")


def _best_rate_and_value(
    probability: np.ndarray,
    risk_coefficient: np.ndarray,
    demand: DemandModel,
    lgd: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    loss = _interpolate_loss(demand, probability)
    retained = 1.0 - loss
    benefit = (
        demand.rates[None, :] * retained - lgd * risk_coefficient[:, None] * retained
    )
    choice = benefit.argmax(axis=1)
    return (
        demand.rates[choice],
        benefit[np.arange(len(choice)), choice],
        loss[np.arange(len(choice)), choice],
    )


def _portfolio_base(
    n: int,
    risk_weight: np.ndarray,
    eligible: np.ndarray,
    budget_yuan: float,
    risk_cap_yuan: float,
    config: Config,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[float], list[float]]:
    lower = config.min_loan_yuan / AMOUNT_UNIT_YUAN
    upper = config.max_loan_yuan / AMOUNT_UNIT_YUAN
    budget = budget_yuan / AMOUNT_UNIT_YUAN
    risk_cap = risk_cap_yuan / AMOUNT_UNIT_YUAN
    integrality = np.r_[np.zeros(n), np.ones(n)]
    bounds_lower = np.zeros(2 * n)
    bounds_upper = np.r_[np.full(n, upper), eligible.astype(float)]
    # These two blocks encode lower*y <= x <= upper*y in million yuan.
    matrix = [
        np.c_[np.eye(n), -upper * np.eye(n)],
        np.c_[np.eye(n), -lower * np.eye(n)],
        np.r_[np.ones(n), np.zeros(n)][None, :],
        np.r_[risk_weight, np.zeros(n)][None, :],
    ]
    lower_bounds = [-np.inf] * n + [0.0] * n + [budget, -np.inf]
    upper_bounds = [0.0] * n + [np.inf] * n + [budget, risk_cap]
    return (
        integrality,
        bounds_lower,
        bounds_upper,
        np.vstack(matrix),
        lower_bounds,
        upper_bounds,
    )


def _solve_nominal_milp(
    unit_benefit: np.ndarray,
    integrality: np.ndarray,
    bounds_lower: np.ndarray,
    bounds_upper: np.ndarray,
    matrix: np.ndarray,
    lower_bounds: list[float],
    upper_bounds: list[float],
    config: Config,
) -> Any:
    n = len(unit_benefit)
    return milp(
        c=np.r_[-unit_benefit, np.zeros(n)],
        integrality=integrality,
        bounds=Bounds(bounds_lower, bounds_upper),
        constraints=LinearConstraint(matrix, lower_bounds, upper_bounds),
        options={"time_limit": config.solver_time_limit},
    )


def _solve_robust_milp(
    scenario_benefit: np.ndarray,
    integrality: np.ndarray,
    bounds_lower: np.ndarray,
    bounds_upper: np.ndarray,
    matrix: np.ndarray,
    lower_bounds: list[float],
    upper_bounds: list[float],
    config: Config,
) -> Any:
    n = scenario_benefit.shape[1]
    scenario_count = scenario_benefit.shape[0]
    robust_matrix = np.c_[matrix, np.zeros(matrix.shape[0])]
    scenario_rows = [
        np.r_[-scenario_benefit[index], np.zeros(n), 1.0]
        for index in range(scenario_count)
    ]
    return milp(
        c=np.r_[np.zeros(2 * n), -1.0],
        integrality=np.r_[integrality, 0],
        bounds=Bounds(np.r_[bounds_lower, -np.inf], np.r_[bounds_upper, np.inf]),
        constraints=LinearConstraint(
            np.vstack([robust_matrix, scenario_rows]),
            np.r_[lower_bounds, [-np.inf] * scenario_count],
            np.r_[upper_bounds, [0.0] * scenario_count],
        ),
        options={"time_limit": config.solver_time_limit},
    )


def _portfolio_checks(
    result: Any,
    loan_yuan: np.ndarray,
    selected: np.ndarray,
    risk_weight: np.ndarray,
    budget_yuan: float,
    robust: bool,
) -> dict[str, Any]:
    robust_value = float(result.x[-1] * AMOUNT_UNIT_YUAN) if robust else None
    return {
        "solver_message": str(result.message),
        "solver_status": int(result.status),
        "budget_error_yuan": float(loan_yuan.sum() - budget_yuan),
        "max_risk_yuan": float(loan_yuan @ risk_weight),
        "min_selected_loan_yuan": float(loan_yuan[selected].min())
        if selected.any()
        else 0.0,
        "max_selected_loan_yuan": float(loan_yuan[selected].max())
        if selected.any()
        else 0.0,
        "selected_count": int(selected.sum()),
        "robust_min_benefit_yuan": robust_value,
    }


def _portfolio_milp(
    unit_benefit: np.ndarray,
    risk_weight: np.ndarray,
    eligible: np.ndarray,
    budget_yuan: float,
    risk_cap_yuan: float,
    config: Config,
    scenario_benefit: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Solve nominal or maximin portfolio allocation in million-yuan units."""

    n = len(unit_benefit)
    base = _portfolio_base(n, risk_weight, eligible, budget_yuan, risk_cap_yuan, config)
    integrality, bounds_lower, bounds_upper, matrix, lower_bounds, upper_bounds = base
    if scenario_benefit is None:
        result = _solve_nominal_milp(
            unit_benefit,
            integrality,
            bounds_lower,
            bounds_upper,
            matrix,
            lower_bounds,
            upper_bounds,
            config,
        )
    else:
        result = _solve_robust_milp(
            scenario_benefit,
            integrality,
            bounds_lower,
            bounds_upper,
            matrix,
            lower_bounds,
            upper_bounds,
            config,
        )
    if not result.success or result.x is None:
        raise OptimizationError(f"MILP 未求得可行最优解：{result.message}")
    loan_yuan = result.x[:n] * AMOUNT_UNIT_YUAN
    selected = result.x[n : 2 * n] > 0.5
    checks = _portfolio_checks(
        result,
        loan_yuan,
        selected,
        risk_weight,
        budget_yuan,
        scenario_benefit is not None,
    )
    return loan_yuan, selected, checks


def _source_target_shift(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    source_mean = source.mean(axis=0)
    source_std = source.std(axis=0).replace(0.0, 1.0)
    target_mean = target.mean(axis=0)
    standardized = (target_mean - source_mean) / source_std
    return pd.DataFrame(
        {
            "feature": source.columns,
            "source_mean": source_mean.to_numpy(),
            "target_mean": target_mean.to_numpy(),
            "standardized_mean_shift": standardized.to_numpy(),
        }
    ).sort_values(
        "standardized_mean_shift", key=lambda series: series.abs(), ascending=False
    )


def _make_problem_table(
    risk: pd.DataFrame,
    features: pd.DataFrame,
    demand: DemandModel,
    risk_coefficients: np.ndarray,
    lgd: float,
) -> pd.DataFrame:
    probability = risk[[f"p_{rating}" for rating in RATING_ORDER]].to_numpy(dtype=float)
    risk_coefficient = probability @ risk_coefficients
    rate, unit_benefit, loss_rate = _best_rate_and_value(
        probability, risk_coefficient, demand, lgd
    )
    table = risk.copy()
    table["risk_loss_coefficient"] = risk_coefficient
    table["recommended_rate"] = rate
    table["customer_loss_rate"] = loss_rate
    table["unit_expected_benefit"] = unit_benefit
    table["vulnerability"] = _vulnerability(features)
    return table


def _robust_rates(
    probability: np.ndarray,
    risk_coefficients: np.ndarray,
    vulnerability: np.ndarray,
    demand: DemandModel,
    lgd: float,
    stress_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Choose each enterprise's rate by its worst-case unit benefit.

    The scenarios are explicit stress tests, not observed pandemic losses. They
    simultaneously increase risk loss and reduce retained demand according to the
    enterprise's observed invoice-derived vulnerability.
    """

    loss = _interpolate_loss(demand, probability)
    retained = 1.0 - loss
    # Scenario multipliers are assumptions for stress testing, not observed
    # pandemic coefficients. Risk is amplified relatively so that an already
    # low-risk enterprise does not receive an implausible absolute probability
    # jump merely because a stress scenario is activated.
    risk_bump = stress_scale * np.array([0.15, 0.50, 1.00])
    retention_shock = stress_scale * np.array([0.05, 0.15, 0.30])
    scenario_benefits = []
    scenario_risks = []
    for delta, gamma in zip(risk_bump, retention_shock, strict=True):
        stressed_risk = np.clip(
            risk_coefficients * (1.0 + delta * vulnerability), 0.0, 1.0
        )
        stressed_retained = np.clip(
            retained * (1.0 - gamma * vulnerability[:, None]), 0.0, 1.0
        )
        scenario_benefits.append(
            demand.rates[None, :] * stressed_retained
            - lgd * stressed_risk[:, None] * stressed_retained
        )
        scenario_risks.append(stressed_risk[:, None] * stressed_retained)
    benefit_cube = np.stack(scenario_benefits, axis=0)
    risk_cube = np.stack(scenario_risks, axis=0)
    choice = benefit_cube.min(axis=0).argmax(axis=1)
    row = np.arange(len(choice))
    selected_benefit = benefit_cube[:, row, choice]
    selected_risk = risk_cube[:, row, choice]
    return demand.rates[choice], selected_benefit, selected_risk, loss[row, choice]


def _problem1(
    source: pd.DataFrame,
    features: pd.DataFrame,
    demand: DemandModel,
    risk_coefficients: np.ndarray,
    config: Config,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    table = _make_problem_table(source, features, demand, risk_coefficients, config.lgd)
    eligible = ~table["rating_observed"].astype(str).eq("D").to_numpy()
    risk_weight = table["risk_loss_coefficient"].to_numpy() * (
        1.0 - table["customer_loss_rate"].to_numpy()
    )
    unit_benefit = table["unit_expected_benefit"].to_numpy()
    curve_rows = []
    for budget in [20_000_000.0, config.problem1_budget_yuan, 80_000_000.0]:
        if budget > eligible.sum() * config.max_loan_yuan:
            continue
        loan, selected, check = _portfolio_milp(
            unit_benefit,
            risk_weight,
            eligible,
            budget,
            risk_cap_yuan=0.10 * budget,
            config=config,
        )
        curve_rows.append(
            {
                "budget_yuan": budget,
                "expected_benefit_yuan": float((loan * unit_benefit).sum()),
                "risk_loss_principal_yuan": float((loan * risk_weight).sum()),
                **check,
            }
        )
        if np.isclose(budget, config.problem1_budget_yuan):
            table["loan_yuan"] = loan
            table["selected"] = selected
    if "loan_yuan" not in table:
        raise OptimizationError("问题一展示预算未产生策略")
    if (table.loc[~eligible, "loan_yuan"] > 0.01).any():
        raise OptimizationError("问题一违反 D 级企业禁贷约束")
    return table, pd.DataFrame(curve_rows)


def _problem2(
    target: pd.DataFrame, features: pd.DataFrame, demand: DemandModel, config: Config
) -> tuple[pd.DataFrame, pd.DataFrame]:
    risk_coefficients = target["risk_loss_coefficient"].to_numpy()
    risk_weight = risk_coefficients * (1.0 - target["customer_loss_rate"].to_numpy())
    unit_benefit = target["unit_expected_benefit"].to_numpy()
    # A predicted D-like distribution is not an observed D rating. It is managed
    # continuously by the loss coefficient and an explicit portfolio risk budget.
    eligible = np.ones(len(target), dtype=bool)
    curve_rows = []
    for fraction in [0.0128, 0.0130, 0.0132, 0.0134, 0.0140]:
        loan, selected, check = _portfolio_milp(
            unit_benefit,
            risk_weight,
            eligible,
            config.problem2_budget_yuan,
            risk_cap_yuan=fraction * config.problem2_budget_yuan,
            config=config,
        )
        curve_rows.append(
            {
                "risk_cap_fraction": fraction,
                "expected_benefit_yuan": float((loan * unit_benefit).sum()),
                "risk_loss_principal_yuan": float((loan * risk_weight).sum()),
                **check,
            }
        )
        if np.isclose(fraction, config.portfolio_risk_cap_fraction):
            target["loan_yuan"] = loan
            target["selected"] = selected
    if "loan_yuan" not in target:
        raise OptimizationError("问题二主情景未产生策略")
    return target, pd.DataFrame(curve_rows)


def _problem3(
    target: pd.DataFrame, demand: DemandModel, config: Config
) -> tuple[pd.DataFrame, pd.DataFrame]:
    probability = target[[f"p_{rating}" for rating in RATING_ORDER]].to_numpy(
        dtype=float
    )
    rate, scenario_benefit, scenario_risk, loss = _robust_rates(
        probability,
        target["risk_loss_coefficient"].to_numpy(),
        target["vulnerability"].to_numpy(),
        demand,
        config.lgd,
    )
    risk_weight = scenario_risk.max(axis=0)
    loan, selected, check = _portfolio_milp(
        unit_benefit=scenario_benefit.min(axis=0),
        risk_weight=risk_weight,
        eligible=np.ones(len(target), dtype=bool),
        budget_yuan=config.problem2_budget_yuan,
        risk_cap_yuan=(
            config.portfolio_risk_cap_fraction * config.problem2_budget_yuan
        ),
        config=config,
        scenario_benefit=scenario_benefit,
    )
    robust = target.copy()
    robust["robust_rate"] = rate
    robust["robust_customer_loss_rate"] = loss
    robust["robust_loan_yuan"] = loan
    robust["robust_selected"] = selected
    names = ["mild", "moderate", "severe"]
    scenario_table = pd.DataFrame(
        {
            "scenario": names,
            "portfolio_benefit_yuan": [
                float((loan * value).sum()) for value in scenario_benefit
            ],
            "portfolio_risk_yuan": [
                float((loan * value).sum()) for value in scenario_risk
            ],
            "mean_unit_benefit": scenario_benefit.mean(axis=1),
            "mean_risk_weight": scenario_risk.mean(axis=1),
        }
    )
    for key, value in check.items():
        scenario_table[key] = value
    return robust, scenario_table


def _problem2_lgd_sensitivity(
    target: pd.DataFrame, demand: DemandModel, config: Config
) -> pd.DataFrame:
    """Re-optimize the nominal portfolio across documented LGD assumptions."""

    probability = target[[f"p_{rating}" for rating in RATING_ORDER]].to_numpy(
        dtype=float
    )
    risk_coefficient = target["risk_loss_coefficient"].to_numpy(dtype=float)
    rows = []
    for lgd in [0.4, 0.7, 1.0]:
        rate, benefit, loss = _best_rate_and_value(
            probability, risk_coefficient, demand, lgd
        )
        risk_weight = risk_coefficient * (1.0 - loss)
        loan, _selected, check = _portfolio_milp(
            benefit,
            risk_weight,
            np.ones(len(target), dtype=bool),
            config.problem2_budget_yuan,
            config.problem2_budget_yuan,
            config,
        )
        rows.append(
            {
                "lgd": lgd,
                "risk_cap_fraction": 1.0,
                "expected_benefit_yuan": float(loan @ benefit),
                "risk_loss_principal_yuan": float(loan @ risk_weight),
                "loan_weighted_rate": float(loan @ rate / loan.sum()),
                **check,
            }
        )
    return pd.DataFrame(rows)


def _problem3_stress_sensitivity(
    target: pd.DataFrame, demand: DemandModel, config: Config
) -> pd.DataFrame:
    """Re-optimize the maximin portfolio as the stress set is scaled."""

    probability = target[[f"p_{rating}" for rating in RATING_ORDER]].to_numpy(
        dtype=float
    )
    risk_coefficient = target["risk_loss_coefficient"].to_numpy(dtype=float)
    vulnerability = target["vulnerability"].to_numpy(dtype=float)
    rows = []
    for scale in [0.50, 0.75, 1.00, 1.25, 1.50]:
        rate, benefit, risk, _loss = _robust_rates(
            probability,
            risk_coefficient,
            vulnerability,
            demand,
            config.lgd,
            stress_scale=scale,
        )
        loan, _selected, check = _portfolio_milp(
            benefit.min(axis=0),
            risk.max(axis=0),
            np.ones(len(target), dtype=bool),
            config.problem2_budget_yuan,
            config.portfolio_risk_cap_fraction * config.problem2_budget_yuan,
            config,
            scenario_benefit=benefit,
        )
        scenario_totals = np.array([loan @ row for row in benefit])
        rows.append(
            {
                "stress_scale": scale,
                "mild_benefit_yuan": float(scenario_totals[0]),
                "moderate_benefit_yuan": float(scenario_totals[1]),
                "severe_benefit_yuan": float(scenario_totals[2]),
                "worst_benefit_yuan": float(scenario_totals.min()),
                "worst_risk_yuan": float(loan @ risk.max(axis=0)),
                "loan_weighted_rate": float(loan @ rate / loan.sum()),
                **check,
            }
        )
    return pd.DataFrame(rows)


def _shap_summary(
    bundle: ModelBundle, features: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return global and local SHAP summaries for the XGBoost component only."""

    import shap

    imputed = bundle.xgboost.named_steps["impute"].transform(
        features.to_numpy(dtype=float)
    )
    selector = bundle.xgboost.named_steps["select"]
    selected = selector.transform(imputed)
    selected_names = np.asarray(bundle.feature_names)[selector.get_support()]
    estimator = bundle.xgboost.named_steps["model"]
    values = shap.TreeExplainer(estimator).shap_values(selected)
    if isinstance(values, list):
        array = np.stack(values, axis=-1)
    else:
        array = np.asarray(values)
    if array.ndim != 3:
        raise RuntimeError("SHAP 多分类输出形状不符合预期")
    severity_contribution = np.tensordot(array, SEVERITY, axes=([2], [0]))
    global_summary = pd.DataFrame(
        {
            "feature": selected_names,
            "mean_abs_shap_cri_direction": np.abs(severity_contribution).mean(axis=0),
            "mean_shap_cri_direction": severity_contribution.mean(axis=0),
        }
    ).sort_values("mean_abs_shap_cri_direction", ascending=False)
    local = pd.DataFrame(
        severity_contribution, index=features.index, columns=selected_names
    )
    return global_summary, local


def _write_json(path: Path, payload: Any) -> None:
    def _convert(value: Any) -> Any:
        if isinstance(value, (np.floating, np.integer, np.bool_)):
            return value.item()
        if isinstance(value, Path):
            return str(value)
        raise TypeError(f"不可序列化类型: {type(value).__name__}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_convert),
        encoding="utf-8",
    )


def _save_demand_and_risk_plots(
    demand: DemandModel, source: pd.DataFrame, target: pd.DataFrame, figure_dir: Path
) -> None:
    import matplotlib.pyplot as plt

    colors = ["#2A9D8F", "#457B9D", "#E76F51"]
    fig, axis = plt.subplots(figsize=(6.5, 4.2))
    for index, rating in enumerate(["A", "B", "C"]):
        axis.scatter(
            demand.rates, demand.raw_loss[index], s=14, color=colors[index], alpha=0.5
        )
        axis.plot(
            demand.rates,
            demand.monotone_loss[index],
            color=colors[index],
            label=f"{rating} 级",
        )
    axis.set_xlabel("年利率")
    axis.set_ylabel("客户流失率")
    axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_dir / "interest_loss_isotonic.pdf")
    plt.close(fig)
    fig, axis = plt.subplots(figsize=(6.5, 4.2))
    axis.hist(
        source["cri_oof"], bins=16, alpha=0.7, label="附件1（折外）", color="#457B9D"
    )
    axis.hist(
        target["cri"], bins=18, alpha=0.65, label="附件2（迁移）", color="#E76F51"
    )
    axis.set_xlabel("信用风险指数 CRI")
    axis.set_ylabel("企业数")
    axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_dir / "risk_index_distribution.pdf")
    plt.close(fig)


def _save_nominal_plots(
    curve1: pd.DataFrame,
    curve2: pd.DataFrame,
    scenario: pd.DataFrame,
    figure_dir: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(figsize=(6.5, 4.2))
    axis.plot(
        curve1["budget_yuan"] / 1e6, curve1["expected_benefit_yuan"] / 1e6, marker="o"
    )
    axis.set_xlabel("问题一总额度（百万元）")
    axis.set_ylabel("期望年度效益（百万元）")
    fig.tight_layout()
    fig.savefig(figure_dir / "problem1_budget_curve.pdf")
    plt.close(fig)
    fig, axis = plt.subplots(figsize=(6.5, 4.2))
    axis.plot(
        curve2["risk_loss_principal_yuan"] / 1e6,
        curve2["expected_benefit_yuan"] / 1e6,
        marker="o",
    )
    axis.set_xlabel("组合风险损失尺度（百万元）")
    axis.set_ylabel("期望年度效益（百万元）")
    fig.tight_layout()
    fig.savefig(figure_dir / "problem2_risk_return_frontier.pdf")
    plt.close(fig)
    fig, axis = plt.subplots(figsize=(6.5, 4.2))
    axis.bar(scenario["scenario"], scenario["portfolio_benefit_yuan"] / 1e6)
    axis.set_ylabel("压力情景组合效益（百万元）")
    fig.tight_layout()
    fig.savefig(figure_dir / "problem3_robust_scenarios.pdf")
    plt.close(fig)


def _save_sensitivity_plot(
    lgd_sensitivity: pd.DataFrame,
    stress_sensitivity: pd.DataFrame,
    figure_dir: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    axes[0].plot(
        lgd_sensitivity["lgd"],
        lgd_sensitivity["expected_benefit_yuan"] / 1e6,
        marker="o",
    )
    axes[0].set_xlabel("违约损失率 LGD")
    axes[0].set_ylabel("名义组合效益（百万元）")
    axes[1].plot(
        stress_sensitivity["stress_scale"],
        stress_sensitivity["worst_benefit_yuan"] / 1e6,
        marker="o",
        color="#E76F51",
    )
    axes[1].set_xlabel("压力强度倍数")
    axes[1].set_ylabel("最坏情景效益（百万元）")
    fig.tight_layout()
    fig.savefig(figure_dir / "sensitivity_analysis.pdf")
    plt.close(fig)


def _save_shap_plot(shap_global: pd.DataFrame, figure_dir: Path) -> None:
    import matplotlib.pyplot as plt

    top = shap_global.head(12).sort_values("mean_abs_shap_cri_direction")
    fig, axis = plt.subplots(figsize=(7.2, 4.8))
    axis.barh(top["feature"], top["mean_abs_shap_cri_direction"], color="#457B9D")
    axis.set_xlabel("平均绝对 SHAP 风险方向贡献")
    fig.tight_layout()
    fig.savefig(figure_dir / "shap_global_importance.pdf")
    plt.close(fig)


def _plot_results(
    demand: DemandModel,
    source: pd.DataFrame,
    target: pd.DataFrame,
    optimization: tuple[
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
    ],
    shap_global: pd.DataFrame,
) -> None:
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    figure_dir = ROOT / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    curve1, curve2, scenario, lgd_sensitivity, stress_sensitivity = optimization
    _save_demand_and_risk_plots(demand, source, target, figure_dir)
    _save_nominal_plots(curve1, curve2, scenario, figure_dir)
    _save_sensitivity_plot(lgd_sensitivity, stress_sensitivity, figure_dir)
    _save_shap_plot(shap_global, figure_dir)


def _input_paths() -> tuple[Path, Path, Path]:
    input_dir = ROOT / "inputs"
    return (
        input_dir / "附件1：123家有信贷记录企业的相关数据.xlsx",
        input_dir / "附件2：302家无信贷记录企业的相关数据.xlsx",
        input_dir / "附件3：银行贷款年利率与客户流失率关系的统计数据.xlsx",
    )


def _local_shap_rows(source: pd.DataFrame, shap_local: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for enterprise_id in source.sort_values("cri_oof", ascending=False).head(15).index:
        contribution = (
            shap_local.loc[enterprise_id].sort_values(ascending=False).head(3)
        )
        for rank, (feature, value) in enumerate(contribution.items(), start=1):
            rows.append(
                {
                    "enterprise_id": enterprise_id,
                    "rank": rank,
                    "risk_increasing_feature": feature,
                    "shap_risk_direction": float(value),
                }
            )
    return pd.DataFrame(rows)


def _save_result_tables(tables: dict[str, pd.DataFrame]) -> None:
    result_dir = ROOT / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        preserve_index = name in {
            "problem1_strategy.csv",
            "problem2_strategy.csv",
            "problem3_robust_strategy.csv",
        }
        table.to_csv(result_dir / name, index=preserve_index, encoding="utf-8-sig")


def _mark_transfer_confidence(
    target: pd.DataFrame, source_features: pd.DataFrame, target_features: pd.DataFrame
) -> None:
    standardized = (
        target_features - source_features.mean()
    ) / source_features.std().replace(0.0, 1.0)
    target["target_domain_shift_score"] = standardized.abs().mean(axis=1)
    target["transfer_confidence"] = np.where(
        target["target_domain_shift_score"] <= 1.5, "常规", "需人工复核"
    )


def _result_table_map(
    problems: tuple[
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
    ],
    analysis: tuple[
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
    ],
) -> dict[str, pd.DataFrame]:
    source, curve1, target, curve2, robust, scenarios = problems
    shift, shap_global, shap_local, lgd_sensitivity, stress_sensitivity = analysis
    return {
        "problem1_strategy.csv": source,
        "problem1_budget_curve.csv": curve1,
        "problem2_strategy.csv": target,
        "problem2_risk_return_curve.csv": curve2,
        "problem3_robust_strategy.csv": robust,
        "problem3_scenarios.csv": scenarios,
        "problem2_lgd_sensitivity.csv": lgd_sensitivity,
        "problem3_stress_sensitivity.csv": stress_sensitivity,
        "transfer_feature_shift.csv": shift,
        "shap_global.csv": shap_global,
        "shap_local_high_risk.csv": _local_shap_rows(source, shap_local),
    }


def _artifact_hashes() -> dict[str, str]:
    artifacts = sorted(
        [
            path
            for path in (ROOT / "results").glob("*")
            if path.is_file() and path.name != "summary.json"
        ]
        + [path for path in (ROOT / "figures").glob("*.pdf")]
    )
    return {str(path.relative_to(ROOT)): _sha256(path) for path in artifacts}


def _curve_row(curve: pd.DataFrame, column: str, value: float) -> dict[str, Any]:
    mask = np.isclose(curve[column].to_numpy(dtype=float), value)
    if mask.sum() != 1:
        raise RuntimeError(f"结果曲线主情景定位失败: {column}={value}")
    return curve.loc[mask].iloc[0].to_dict()


def _build_run_summary(
    config: Config,
    inputs: tuple[Path, Path, Path],
    feature_tables: tuple[pd.DataFrame, pd.DataFrame],
    risk_coefficients: np.ndarray,
    metrics: dict[str, Any],
    curves: tuple[pd.DataFrame, pd.DataFrame],
    scenarios: pd.DataFrame,
    start: float,
) -> dict[str, Any]:
    feature1, feature2 = feature_tables
    curve1, curve2 = curves
    return {
        "seed": config.seed,
        "python": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "input_hashes": {path.name: _sha256(path) for path in inputs},
        "feature_count": int(feature1.shape[1]),
        "source_enterprises": len(feature1),
        "target_enterprises": len(feature2),
        "rating_default_risk_coefficients": dict(
            zip(RATING_ORDER, risk_coefficients.tolist(), strict=True)
        ),
        "portfolio_risk_cap_fraction": config.portfolio_risk_cap_fraction,
        "model_metrics": metrics,
        "problem1_main": _curve_row(
            curve1, "budget_yuan", config.problem1_budget_yuan
        ),
        "problem2_main": _curve_row(
            curve2, "risk_cap_fraction", config.portfolio_risk_cap_fraction
        ),
        "problem3_worst_benefit_yuan": float(scenarios["portfolio_benefit_yuan"].min()),
        "elapsed_seconds": time.perf_counter() - start,
        "artifact_sha256": _artifact_hashes(),
    }


def _load_experiment_inputs(
    config: Config,
) -> tuple[
    tuple[Path, Path, Path],
    tuple[pd.DataFrame, pd.DataFrame],
    tuple[pd.Series, pd.Series],
    DemandModel,
]:
    attachment1, attachment2, attachment3 = _input_paths()
    info1, feature1 = load_enterprise_features(attachment1, config)
    _info2, feature2 = load_enterprise_features(attachment2, config)
    demand = load_demand_model(attachment3)
    ratings = info1["信誉评级"].astype(str).str.strip()
    defaults = info1["是否违约"].astype(str).str.strip()
    return (
        (attachment1, attachment2, attachment3),
        (feature1, feature2),
        (ratings, defaults),
        demand,
    )


def _fit_experiment_models(
    features: tuple[pd.DataFrame, pd.DataFrame],
    labels: tuple[pd.Series, pd.Series],
    demand: DemandModel,
    config: Config,
) -> tuple[ModelBundle, pd.DataFrame, pd.DataFrame, np.ndarray, dict[str, Any]]:
    feature1, feature2 = features
    ratings, defaults = labels
    bundle, source, metrics = fit_risk_model(feature1, ratings, defaults, config)
    target = predict_risk(bundle, feature2)
    risk_coefficients = _default_risk_coefficients(ratings, defaults)
    source = _make_problem_table(
        source, feature1, demand, risk_coefficients, config.lgd
    )
    target = _make_problem_table(
        target, feature2, demand, risk_coefficients, config.lgd
    )
    return bundle, source, target, risk_coefficients, metrics


def _run_decision_models(
    source: pd.DataFrame,
    target: pd.DataFrame,
    features: tuple[pd.DataFrame, pd.DataFrame],
    demand: DemandModel,
    risk_coefficients: np.ndarray,
    config: Config,
) -> tuple[pd.DataFrame, ...]:
    feature1, feature2 = features
    source1, curve1 = _problem1(source, feature1, demand, risk_coefficients, config)
    target2, curve2 = _problem2(target, feature2, demand, config)
    _mark_transfer_confidence(target2, feature1, feature2)
    robust, scenarios = _problem3(target2, demand, config)
    lgd_sensitivity = _problem2_lgd_sensitivity(target2, demand, config)
    stress_sensitivity = _problem3_stress_sensitivity(target2, demand, config)
    return (
        source1,
        curve1,
        target2,
        curve2,
        robust,
        scenarios,
        lgd_sensitivity,
        stress_sensitivity,
    )


def run_full(config: Config) -> dict[str, Any]:
    """Execute all three questions from frozen inputs and write audited artifacts."""

    start = time.perf_counter()
    inputs, features, labels, demand = _load_experiment_inputs(config)
    bundle, source, target, risk_coefficients, metrics = _fit_experiment_models(
        features, labels, demand, config
    )
    decision = _run_decision_models(
        source, target, features, demand, risk_coefficients, config
    )
    source1, curve1, target2, curve2, robust, scenarios, lgd_sensitivity, stress_sensitivity = decision
    feature1, feature2 = features
    shift = _source_target_shift(feature1, feature2)
    shap_global, shap_local = _shap_summary(bundle, feature1)
    tables = _result_table_map(
        (source1, curve1, target2, curve2, robust, scenarios),
        (
            shift,
            shap_global,
            shap_local,
            lgd_sensitivity,
            stress_sensitivity,
        ),
    )
    _save_result_tables(tables)
    _plot_results(
        demand,
        source1,
        target2,
        (curve1, curve2, scenarios, lgd_sensitivity, stress_sensitivity),
        shap_global,
    )
    summary = _build_run_summary(
        config,
        inputs,
        features,
        risk_coefficients,
        metrics,
        (curve1, curve2),
        scenarios,
        start,
    )
    _write_json(ROOT / "results" / "summary.json", summary)
    LOGGER.info("full run completed in %.2f seconds", summary["elapsed_seconds"])
    return summary


def run_smoke(config: Config) -> dict[str, Any]:
    """Run deterministic mathematical invariants without loading the large inputs."""

    demand = DemandModel(
        rates=np.array([0.04, 0.10, 0.15]),
        raw_loss=np.array([[0.0, 0.3, 0.7], [0.0, 0.4, 0.8], [0.0, 0.5, 0.9]]),
        monotone_loss=np.array([[0.0, 0.3, 0.7], [0.0, 0.4, 0.8], [0.0, 0.5, 0.9]]),
    )
    probability = np.tile(np.array([0.7, 0.2, 0.08, 0.02]), (5, 1))
    risk = probability @ np.array([0.02, 0.04, 0.08, 0.98])
    rates, benefit, loss = _best_rate_and_value(probability, risk, demand, config.lgd)
    loan, selected, checks = _portfolio_milp(
        benefit,
        risk * (1.0 - loss),
        np.ones(5, dtype=bool),
        budget_yuan=500_000.0,
        risk_cap_yuan=500_000.0,
        config=config,
    )
    payload = {
        "rates": rates.tolist(),
        "selected_count": int(selected.sum()),
        "budget_error_yuan": checks["budget_error_yuan"],
        "loan_sum_yuan": float(loan.sum()),
        "status": "ok",
    }
    _write_json(ROOT / "results" / "smoke.json", payload)
    return payload


def _configure_logging() -> None:
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(ROOT / "logs" / "run.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    """Parse CLI options and run either the smoke or full pipeline."""

    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--smoke", action="store_true", help="run deterministic invariant checks"
    )
    group.add_argument(
        "--run", action="store_true", help="run all three problems from frozen inputs"
    )
    args = parser.parse_args()
    _configure_logging()
    config = Config()
    if args.smoke:
        LOGGER.info("smoke result: %s", run_smoke(config))
    else:
        summary = run_full(config)
        LOGGER.info("problem 2 main result: %s", summary["problem2_main"])


if __name__ == "__main__":
    main()
