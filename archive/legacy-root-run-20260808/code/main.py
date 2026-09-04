"""2024 CUMCM B 题的 G2 最小可行实现。

当前版本验证精确抽样判定及问题 2 的策略评价。问题 3、4 的完整网络与
不确定性实验留待 G3；本文件不会把 G2 小规模结果当成正式结论。
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import matplotlib
import numpy as np
from scipy.stats import beta

matplotlib.use("Agg")
import matplotlib.pyplot as plt

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"

# 状态用 -1/0/1 保留“缺件/已知(或潜在)次品/合格”三种情形；这样拆解
# 后的潜在次品不会被误当作新品，线性方程才能识别不可吸收的回收循环。


class ModelInputError(ValueError):
    """Raised when a probability or cost violates the model domain."""


Decision = Literal["accept", "reject", "continue"]


@dataclass(frozen=True)
class SamplingConfig:
    """Configuration for exact confidence bounds and the SPRT.

    Args:
        nominal_rate: Supplier's claimed defect probability, in (0, 1).
        delta: Indifference-zone half width, smaller than the nominal rate.
        alpha: Maximum reject-side type-I error.
        beta_error: Maximum accept-side type-II error.
    """

    nominal_rate: float = 0.10
    delta: float = 0.02
    alpha: float = 0.05
    beta_error: float = 0.10


@dataclass(frozen=True)
class Scenario:
    """One problem-2 cost and conditional-defect-rate scenario (yuan per item)."""

    part_defects: tuple[float, float]
    part_costs: tuple[float, float]
    part_test_costs: tuple[float, float]
    assembly_defect: float
    assembly_cost: float
    assembly_test_cost: float
    sale_price: float
    exchange_loss: float
    disassembly_cost: float


@dataclass(frozen=True)
class Policy:
    """Binary inspection and disassembly choices for problem 2."""

    inspect_part_1: bool
    inspect_part_2: bool
    inspect_product: bool
    disassemble_bad_product: bool


@dataclass(frozen=True)
class PolicyResult:
    """Expected value of a policy, measured per finally delivered qualified item."""

    policy: Policy
    expected_profit: float | None
    condition_number: float | None
    feasible: bool
    reason: str


SCENARIOS: dict[int, Scenario] = {
    1: Scenario((0.10, 0.10), (4, 18), (2, 3), 0.10, 6, 3, 56, 6, 5),
    2: Scenario((0.20, 0.20), (4, 18), (2, 3), 0.20, 6, 3, 56, 6, 5),
    3: Scenario((0.10, 0.10), (4, 18), (2, 3), 0.10, 6, 3, 56, 30, 5),
    4: Scenario((0.20, 0.20), (4, 18), (1, 1), 0.20, 6, 2, 56, 30, 5),
    5: Scenario((0.10, 0.20), (4, 18), (8, 1), 0.10, 6, 2, 56, 10, 5),
    6: Scenario((0.05, 0.05), (4, 18), (2, 3), 0.05, 6, 3, 56, 10, 40),
}


def validate_probability(value: float, name: str, *, allow_zero: bool = True) -> None:
    """Validate a probability supplied to the statistical or production model."""
    lower_ok = value >= 0 if allow_zero else value > 0
    if not lower_ok or value >= 1 or not np.isfinite(value):
        raise ModelInputError(f"{name} must be in {'(0, 1)' if not allow_zero else '[0, 1)'}." )


def validate_sampling(config: SamplingConfig) -> None:
    """Validate an SPRT configuration before computing likelihood boundaries."""
    validate_probability(config.nominal_rate, "nominal_rate", allow_zero=False)
    if not 0 < config.delta < min(config.nominal_rate, 1 - config.nominal_rate):
        raise ModelInputError("delta must keep both SPRT reference rates in (0, 1).")
    for name, value in (("alpha", config.alpha), ("beta_error", config.beta_error)):
        if not 0 < value < 1:
            raise ModelInputError(f"{name} must be in (0, 1).")


def one_sided_bounds(defects: int, sample_size: int) -> tuple[float, float]:
    """Return 95% lower and 90% upper exact Clopper-Pearson bounds.

    Args:
        defects: Observed number of defective items.
        sample_size: Positive number of inspected items.

    Returns:
        Lower and upper bounds for the unknown binomial defect probability.
    """
    if sample_size <= 0 or not 0 <= defects <= sample_size:
        raise ModelInputError("defects must satisfy 0 <= defects <= positive sample_size.")
    lower = 0.0 if defects == 0 else float(beta.ppf(0.05, defects, sample_size - defects + 1))
    upper = 1.0 if defects == sample_size else float(beta.ppf(0.90, defects + 1, sample_size - defects))
    return lower, upper


def confidence_decision(defects: int, sample_size: int, nominal_rate: float = 0.10) -> Decision:
    """Classify a sample by the approved exact one-sided confidence rules."""
    validate_probability(nominal_rate, "nominal_rate", allow_zero=False)
    lower, upper = one_sided_bounds(defects, sample_size)
    if lower > nominal_rate:
        return "reject"
    if upper <= nominal_rate:
        return "accept"
    return "continue"


def sprt_decision(defects: int, sample_size: int, config: SamplingConfig) -> Decision:
    """Apply the approved SPRT rule to cumulative binary inspection results."""
    validate_sampling(config)
    if sample_size <= 0 or not 0 <= defects <= sample_size:
        raise ModelInputError("defects must satisfy 0 <= defects <= positive sample_size.")
    p_accept = config.nominal_rate - config.delta
    p_reject = config.nominal_rate + config.delta
    log_ratio = defects * np.log(p_reject / p_accept)
    log_ratio += (sample_size - defects) * np.log((1 - p_reject) / (1 - p_accept))
    if log_ratio >= np.log((1 - config.beta_error) / config.alpha):
        return "reject"
    if log_ratio <= np.log(config.beta_error / (1 - config.alpha)):
        return "accept"
    return "continue"


def all_policies() -> list[Policy]:
    """Enumerate the 16 transparent policy combinations of problem 2."""
    return [Policy(*choices) for choices in itertools.product((False, True), repeat=4)]


def state_index(state: tuple[int, int]) -> int:
    """Map component qualities -1 (missing), 0 (bad), 1 (good) to a matrix index."""
    return (state[0] + 1) * 3 + (state[1] + 1)


def fill_missing_transition(
    state: tuple[int, int], scenario: Scenario, policy: Policy
) -> tuple[np.ndarray, float]:
    """Return transition row and immediate cash flow when acquiring one missing part."""
    row = np.zeros(9)
    missing_index = 0 if state[0] == -1 else 1
    defect = scenario.part_defects[missing_index]
    cost = scenario.part_costs[missing_index]
    inspected = (policy.inspect_part_1, policy.inspect_part_2)[missing_index]
    row[state_index(state)] = defect if inspected else 0.0
    good_state = list(state)
    good_state[missing_index] = 1
    row[state_index(tuple(good_state))] += 1 - defect
    if not inspected:
        bad_state = list(state)
        bad_state[missing_index] = 0
        row[state_index(tuple(bad_state))] += defect
    test_cost = scenario.part_test_costs[missing_index] if inspected else 0.0
    return row, -(cost + test_cost)


def assembly_transition(
    state: tuple[int, int], scenario: Scenario, policy: Policy
) -> tuple[np.ndarray, float, float]:
    """Return transition row, cost and immediate delivery reward for a full component pair."""
    row = np.zeros(9)
    parts_good = state[0] == 1 and state[1] == 1
    good_probability = (1 - scenario.assembly_defect) if parts_good else 0.0
    bad_probability = 1 - good_probability
    reset_state = state if policy.disassemble_bad_product else (-1, -1)
    row[state_index(reset_state)] = bad_probability
    inspection_cost = scenario.assembly_test_cost if policy.inspect_product else 0.0
    bad_cost = scenario.disassembly_cost if policy.disassemble_bad_product else 0.0
    if not policy.inspect_product:
        bad_cost += scenario.exchange_loss
    return row, -(scenario.assembly_cost + inspection_cost + bad_probability * bad_cost), good_probability * scenario.sale_price


def reachable_states(transition: np.ndarray, start: int) -> list[int]:
    """Return states reachable with positive probability from the production start.

    The full 9-state encoding includes latent bad parts that inspection policies can
    never reach. Excluding only those unreachable states avoids false singularity
    while retaining every physically possible recycle path.
    """
    reached = {start}
    frontier = [start]
    while frontier:
        current = frontier.pop()
        for candidate in np.flatnonzero(transition[current] > 1e-14):
            if int(candidate) not in reached:
                reached.add(int(candidate))
                frontier.append(int(candidate))
    return sorted(reached)


def evaluate_policy(scenario: Scenario, policy: Policy) -> PolicyResult:
    """Evaluate one policy through a finite absorbing Markov reward equation."""
    for index, value in enumerate((*scenario.part_defects, scenario.assembly_defect)):
        validate_probability(value, f"defect_rate_{index}")
    transition = np.zeros((9, 9))
    reward = np.zeros(9)
    for first, second in itertools.product((-1, 0, 1), repeat=2):
        state = (first, second)
        index = state_index(state)
        if -1 in state:
            transition[index], reward[index] = fill_missing_transition(state, scenario, policy)
        else:
            row, cost, delivery = assembly_transition(state, scenario, policy)
            transition[index], reward[index] = row, cost + delivery
    start = state_index((-1, -1))
    reachable = reachable_states(transition, start)
    reduced_transition = transition[np.ix_(reachable, reachable)]
    system = np.eye(len(reachable)) - reduced_transition
    condition = float(np.linalg.cond(system))
    if not np.isfinite(condition) or condition > 1e12:
        return PolicyResult(policy, None, condition, False, "循环无法稳定吸收或矩阵严重病态")
    try:
        values = np.linalg.solve(system, reward[reachable])
    except np.linalg.LinAlgError as error:
        return PolicyResult(policy, None, condition, False, f"线性方程不可解: {error}")
    return PolicyResult(policy, float(values[reachable.index(start)]), condition, True, "ok")


def evaluate_scenario(scenario: Scenario) -> list[PolicyResult]:
    """Evaluate all policies and sort feasible options from highest profit to lowest."""
    results = [evaluate_policy(scenario, policy) for policy in all_policies()]
    return sorted(results, key=lambda item: item.expected_profit if item.feasible else -np.inf, reverse=True)


def serialise_policy_result(result: PolicyResult) -> dict[str, object]:
    """Convert a policy result to JSON-safe data while preserving feasibility evidence."""
    payload = asdict(result)
    payload["policy"] = asdict(result.policy)
    return payload


def run_smoke() -> dict[str, object]:
    """Run the approved G2 minimum path and save reproducible baseline artifacts."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    baseline = {
        "zero_defects_n22": {"bounds": one_sided_bounds(0, 22), "decision": confidence_decision(0, 22)},
        "two_defects_n2": {"bounds": one_sided_bounds(2, 2), "decision": confidence_decision(2, 2)},
        "sprt_config": asdict(SamplingConfig()),
        "sprt_examples": {"all_good_100": sprt_decision(0, 100, SamplingConfig()), "all_bad_20": sprt_decision(20, 20, SamplingConfig())},
    }
    results = {str(number): [serialise_policy_result(item) for item in evaluate_scenario(data)] for number, data in SCENARIOS.items()}
    (RESULTS_DIR / "problem1_baseline.json").write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS_DIR / "problem2_g2.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("G2 smoke run completed for six problem-2 scenarios.")
    return {"problem1": baseline, "problem2": results}


def simulate_sprt(true_rate: float, config: SamplingConfig, seed: int = 42, runs: int = 10_000, maximum: int = 1_000) -> dict[str, float]:
    """Estimate SPRT operating characteristics with fixed-seed Bernoulli streams."""
    validate_probability(true_rate, "true_rate")
    generator = np.random.default_rng(seed)
    totals = np.zeros(runs, dtype=int)
    active = np.ones(runs, dtype=bool)
    decisions = np.full(runs, "continue", dtype="U8")
    p_a, p_r = config.nominal_rate - config.delta, config.nominal_rate + config.delta
    upper, lower = np.log((1 - config.beta_error) / config.alpha), np.log(config.beta_error / (1 - config.alpha))
    stopped_at = np.full(runs, maximum, dtype=int)
    for step in range(1, maximum + 1):
        totals[active] += generator.binomial(1, true_rate, active.sum())
        log_ratio = totals * np.log(p_r / p_a) + (step - totals) * np.log((1 - p_r) / (1 - p_a))
        reject, accept = active & (log_ratio >= upper), active & (log_ratio <= lower)
        decisions[reject], decisions[accept] = "reject", "accept"
        stopped_at[reject | accept] = step
        active &= ~(reject | accept)
        if not active.any():
            break
    return {"true_rate": true_rate, "accept_rate": float(np.mean(decisions == "accept")), "reject_rate": float(np.mean(decisions == "reject")), "undecided_rate": float(np.mean(decisions == "continue")), "mean_samples": float(np.mean(stopped_at))}


def all_inspected_tree_cost(dismantle_internal: bool, inspect_final: bool, dismantle_final: bool) -> float:
    """Evaluate the figure-1 tree under a transparent all-input-inspected policy family."""
    leaf_costs = [(cost + test) / 0.9 for cost, test in zip((2, 8, 12, 2, 8, 12, 8, 12), (1, 1, 2, 1, 1, 2, 1, 2))]
    node_costs = []
    for group in ((0, 1, 2), (3, 4, 5), (6, 7)):
        children = sum(leaf_costs[index] for index in group)
        node_costs.append(children + ((8 + 4 + 0.1 * 6) / 0.9 if dismantle_internal else (8 + 4) / 0.9))
    children = sum(node_costs)
    if inspect_final:
        final_cost = children + ((8 + 6 + 0.1 * 10) / 0.9 if dismantle_final else (8 + 6) / 0.9)
    elif dismantle_final:
        final_cost = children + (8 + 0.1 * (40 + 10)) / 0.9
    else:
        final_cost = (children + 8 + 0.1 * 40) / 0.9
    return 200 - final_cost


def save_figure(figure: plt.Figure, stem: str) -> None:
    """Save a data-derived figure in vector and preview formats."""
    FIGURES_DIR = ROOT / "figures"
    FIGURES_DIR.mkdir(exist_ok=True)
    for suffix in ("pdf", "svg", "png"):
        figure.savefig(FIGURES_DIR / f"{stem}.{suffix}", dpi=300, bbox_inches="tight")
    plt.close(figure)


def run_full() -> dict[str, object]:
    """Run G3 analyses, save result data and generate paper-ready data figures."""
    start = time.perf_counter()
    RESULTS_DIR.mkdir(exist_ok=True)
    plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"], "axes.unicode_minus": False, "font.size": 10})
    config = SamplingConfig()
    sprt = [simulate_sprt(rate, config, seed=42 + index) for index, rate in enumerate((0.05, 0.08, 0.10, 0.12, 0.15))]
    x = [item["true_rate"] for item in sprt]
    fig, axis = plt.subplots(figsize=(6.3, 3.6)); axis.plot(x, [item["accept_rate"] for item in sprt], "o-", label="接收"); axis.plot(x, [item["reject_rate"] for item in sprt], "s-", label="拒收"); axis.plot(x, [item["mean_samples"] / 1000 for item in sprt], "^-", label="平均样本量/1000"); axis.set(xlabel="真实次品率", ylabel="比例或归一化样本量"); axis.legend(); axis.grid(alpha=0.25); save_figure(fig, "sprt_operating_characteristics")
    sensitivity = []
    base = SCENARIOS[1]
    for name, factors in {"次品率": (0.8, 1.0, 1.2), "检测成本": (0.8, 1.0, 1.2), "拆解费": (0.8, 1.0, 1.2), "调换损失": (0.8, 1.0, 1.2)}.items():
        for factor in factors:
            altered = Scenario(tuple(min(0.99, value * factor) for value in base.part_defects) if name == "次品率" else base.part_defects, base.part_costs, tuple(value * factor for value in base.part_test_costs) if name == "检测成本" else base.part_test_costs, min(0.99, base.assembly_defect * factor) if name == "次品率" else base.assembly_defect, base.assembly_cost, base.assembly_test_cost * factor if name == "检测成本" else base.assembly_test_cost, base.sale_price, base.exchange_loss * factor if name == "调换损失" else base.exchange_loss, base.disassembly_cost * factor if name == "拆解费" else base.disassembly_cost)
            best = evaluate_scenario(altered)[0]; sensitivity.append({"parameter": name, "factor": factor, "profit": best.expected_profit, "policy": asdict(best.policy)})
    fig, axis = plt.subplots(figsize=(6.3, 3.6)); [axis.plot([row["factor"] for row in sensitivity if row["parameter"] == name], [row["profit"] for row in sensitivity if row["parameter"] == name], marker="o", label=name) for name in ("次品率", "检测成本", "拆解费", "调换损失")]; axis.set(xlabel="相对系数", ylabel="情况 1 最优期望净收益（元）"); axis.legend(); axis.grid(alpha=0.25); save_figure(fig, "problem2_sensitivity")
    tree = [{"internal_disassembly": a, "final_inspection": b, "final_disassembly": c, "profit": all_inspected_tree_cost(a, b, c)} for a, b, c in itertools.product((False, True), repeat=3)]
    tree.sort(key=lambda row: row["profit"], reverse=True)
    labels = [f"半拆{'是' if row['internal_disassembly'] else '否'}\n终检{'是' if row['final_inspection'] else '否'}\n终拆{'是' if row['final_disassembly'] else '否'}" for row in tree]
    fig, axis = plt.subplots(figsize=(6.3, 3.8)); axis.bar(range(len(tree)), [row["profit"] for row in tree], color="#4C78A8"); axis.set(xlabel="全检策略组合（按收益降序）", ylabel="期望净收益（元/最终合格品）"); axis.set_xticks(range(len(tree)), labels, fontsize=8); axis.grid(axis="y", alpha=0.25); save_figure(fig, "problem3_policy_comparison")
    summary = {"sprt": sprt, "problem2_sensitivity": sensitivity, "problem3_all_inspected_candidates": tree, "seed": 42, "elapsed_seconds": time.perf_counter() - start}
    (RESULTS_DIR / "g3_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def configure_logging() -> None:
    """Configure deterministic console logging for the reproducible smoke entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    """Parse CLI options and run only the declared G2 smoke entry point."""
    parser = argparse.ArgumentParser(description="CUMCM 2024 B G2 minimum verification")
    parser.add_argument("--smoke", action="store_true", help="generate G2 baseline JSON artifacts")
    parser.add_argument("--full", action="store_true", help="run approved G3 analyses and figures")
    args = parser.parse_args()
    configure_logging()
    if args.smoke == args.full:
        parser.error("choose exactly one of --smoke or --full")
    if args.smoke:
        run_smoke()
    else:
        run_full()


if __name__ == "__main__":
    main()
