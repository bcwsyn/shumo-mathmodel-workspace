"""Generate the publication figures used by the V8.1-based paper revision."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from main import load_demand_model
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import FuncFormatter, PercentFormatter
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
INPUTS = ROOT / "inputs"
DEFAULT_OUTPUT = ROOT / "figures" / "publication"

NAVY = "#17324D"
BLUE = "#2878B5"
TEAL = "#2A9D8F"
ORANGE = "#E07A5F"
GOLD = "#D4A017"
SLATE = "#64748B"
INK = "#243447"
GRID = "#D8E0E8"
PALE_BLUE = "#EAF2F8"
PALE_TEAL = "#EAF6F3"
PALE_ORANGE = "#FCF2E8"
PALE_GRAY = "#F5F7FA"

FEATURE_ZH = {
    "sales_signed_amount_asinh": "销项净额规模",
    "sales_positive_amount_log": "销项正额规模",
    "sales_recent12_log": "近12月销项规模",
    "sales_top5_share": "前5大客户占比",
    "sales_hhi": "客户集中度 HHI",
    "sales_monthly_cv_log": "销项月度波动",
    "sales_invoice_count_log": "销项发票数量",
    "sales_void_rate": "销项作废率",
    "sales_active_ratio": "销项活跃月份比",
    "sales_counterparty_count_log": "客户数量",
    "purchase_recent12_log": "近12月进项规模",
    "purchase_positive_amount_log": "进项正额规模",
    "purchase_hhi": "供应商集中度 HHI",
    "purchase_top5_share": "前5大供应商占比",
    "sales_avg_abs_amount_log": "销项平均绝对金额",
    "purchase_void_rate": "进项作废率",
    "purchase_trend_norm": "进项趋势",
}


def configure_style() -> None:
    """Apply one restrained academic style to all publication figures."""
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
            "font.family": "sans-serif",
            "font.size": 9.5,
            "axes.labelsize": 10.5,
            "axes.labelcolor": INK,
            "axes.edgecolor": "#94A3B8",
            "axes.linewidth": 0.8,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "xtick.color": INK,
            "ytick.color": INK,
            "legend.fontsize": 9.0,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def style_axes(axis: Axes, grid_axis: str = "y") -> None:
    axis.set_axisbelow(True)
    axis.grid(True, axis=grid_axis, color=GRID, linewidth=0.75, linestyle="--", alpha=0.8)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(direction="out", length=3.5, width=0.8)


def save_figure(fig: Figure, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    common = {"bbox_inches": "tight", "pad_inches": 0.06, "facecolor": "white"}
    fig.savefig(output_dir / f"{stem}.png", dpi=300, **common)
    fig.savefig(output_dir / f"{stem}.pdf", **common)
    fig.savefig(output_dir / f"{stem}.svg", **common)
    plt.close(fig)


def add_box(
    axis: Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    facecolor: str,
    edgecolor: str,
    fontsize: float = 9.0,
) -> None:
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.15,
        facecolor=facecolor,
        edgecolor=edgecolor,
    )
    axis.add_patch(box)
    axis.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=INK,
        linespacing=1.35,
    )


def add_arrow(
    axis: Axes, start: tuple[float, float], end: tuple[float, float], color: str = SLATE
) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=10,
        linewidth=1.15,
        color=color,
        shrinkA=2,
        shrinkB=2,
        connectionstyle="arc3,rad=0",
    )
    axis.add_patch(arrow)


def figure01_method_overview(output_dir: Path) -> None:
    fig, axis = plt.subplots(figsize=(6.3, 3.54))
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")

    headers = [
        (0.03, "数据与风险评价", BLUE),
        (0.355, "策略迁移与组合决策", TEAL),
        (0.68, "压力决策与解释检验", ORANGE),
    ]
    for x, label, color in headers:
        axis.text(x + 0.145, 0.93, label, ha="center", va="center", color=color, weight="bold")
        axis.plot([x, x + 0.29], [0.885, 0.885], color=color, linewidth=2.0)

    add_box(axis, 0.04, 0.58, 0.27, 0.20, "企业信息与进销项发票\n冻结时间窗与数据审计", PALE_BLUE, BLUE)
    add_box(
        axis,
        0.04,
        0.23,
        0.27,
        0.20,
        "32维经营特征\n规模 · 波动 · 集中度\n异常发票与活跃度",
        PALE_BLUE,
        BLUE,
        8.5,
    )
    add_arrow(axis, (0.175, 0.58), (0.175, 0.44), BLUE)

    add_box(axis, 0.365, 0.58, 0.27, 0.20, "Logistic + XGBoost\n折外概率融合与 CRI", PALE_TEAL, TEAL)
    add_box(axis, 0.365, 0.23, 0.27, 0.20, "冻结模型迁移\n利率响应 + 名义 MILP", PALE_TEAL, TEAL)
    add_arrow(axis, (0.50, 0.58), (0.50, 0.44), TEAL)
    add_arrow(axis, (0.31, 0.33), (0.365, 0.33))

    add_box(axis, 0.69, 0.58, 0.27, 0.20, "经营脆弱度\n轻度 · 中度 · 重度压力", PALE_ORANGE, ORANGE)
    add_box(axis, 0.69, 0.23, 0.27, 0.20, "maximin 鲁棒组合\nSHAP解释与敏感性检验", PALE_ORANGE, ORANGE)
    add_arrow(axis, (0.825, 0.58), (0.825, 0.44), ORANGE)
    add_arrow(axis, (0.635, 0.33), (0.69, 0.33))
    axis.text(0.50, 0.08, "问题一评价与定价  →  问题二风险迁移  →  问题三压力调整", ha="center", color=SLATE, fontsize=8.5)
    save_figure(fig, output_dir, "figure01_method_overview")


def figure02_risk_pipeline(output_dir: Path) -> None:
    fig, axis = plt.subplots(figsize=(6.1, 2.81))
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")

    add_box(axis, 0.015, 0.35, 0.16, 0.32, "32维经营特征\n规模 · 活跃度\n波动 · 集中度", PALE_BLUE, BLUE, 8.4)
    add_box(axis, 0.21, 0.35, 0.16, 0.32, "折内预处理\n缺失值填补\n变换与特征选择", PALE_GRAY, SLATE, 8.4)
    add_box(axis, 0.405, 0.59, 0.16, 0.24, "多项 Logistic\n线性基准", PALE_TEAL, TEAL, 8.4)
    add_box(axis, 0.405, 0.18, 0.16, 0.24, "浅层 XGBoost\n非线性交互", PALE_TEAL, TEAL, 8.4)
    add_box(
        axis,
        0.60,
        0.35,
        0.17,
        0.32,
        "5折×5次\n折外概率与\n对数损失选权\n0.80 / 0.20",
        PALE_ORANGE,
        ORANGE,
        7.7,
    )
    add_box(
        axis,
        0.80,
        0.35,
        0.185,
        0.32,
        "融合评级概率\nA / B / C / D\n信用风险指数\nCRI",
        "#F7EEF8",
        "#8E44AD",
        7.9,
    )

    add_arrow(axis, (0.175, 0.51), (0.21, 0.51))
    add_arrow(axis, (0.37, 0.51), (0.405, 0.71))
    add_arrow(axis, (0.37, 0.51), (0.405, 0.30))
    add_arrow(axis, (0.565, 0.71), (0.60, 0.56))
    add_arrow(axis, (0.565, 0.30), (0.60, 0.46))
    add_arrow(axis, (0.77, 0.51), (0.805, 0.51))
    axis.text(0.50, 0.06, "所有预处理参数均在训练折内估计，测试折不参与拟合", ha="center", color=SLATE, fontsize=8.1)
    save_figure(fig, output_dir, "figure02_risk_pipeline")


def figure03_cri_distribution(output_dir: Path) -> None:
    source = pd.read_csv(RESULTS / "problem1_strategy.csv")
    target = pd.read_csv(RESULTS / "problem2_strategy.csv")
    source_values = source["cri_oof"].to_numpy()
    target_values = target["cri"].to_numpy()
    bins = np.linspace(0, 100, 14)

    fig, axis = plt.subplots(figsize=(5.8, 3.75))
    axis.hist(source_values, bins=bins, histtype="stepfilled", color=BLUE, alpha=0.16)
    axis.hist(source_values, bins=bins, histtype="step", color=BLUE, linewidth=1.8, label=f"附件1 折外（n={len(source_values)}）")
    axis.hist(target_values, bins=bins, histtype="stepfilled", color=ORANGE, alpha=0.12)
    axis.hist(target_values, bins=bins, histtype="step", color=ORANGE, linewidth=1.8, linestyle="--", label=f"附件2 迁移（n={len(target_values)}）")
    for values, color in [(source_values, BLUE), (target_values, ORANGE)]:
        axis.axvline(np.median(values), color=color, linewidth=1.2, linestyle=":")
    axis.set_xlim(0, 100)
    axis.set_xlabel("信用风险指数 CRI")
    axis.set_ylabel("企业数")
    style_axes(axis)
    axis.legend(frameon=False, loc="upper right")
    save_figure(fig, output_dir, "figure03_cri_distribution")


def figure04_interest_loss(output_dir: Path) -> None:
    demand = load_demand_model(INPUTS / "附件3：银行贷款年利率与客户流失率关系的统计数据.xlsx")
    colors = [BLUE, TEAL, ORANGE]
    markers = ["o", "s", "^"]

    fig, axis = plt.subplots(figsize=(5.8, 3.75))
    for index, rating in enumerate(["A", "B", "C"]):
        axis.scatter(
            demand.rates,
            demand.raw_loss[index],
            s=22,
            marker=markers[index],
            facecolor="white",
            edgecolor=colors[index],
            linewidth=0.9,
            alpha=0.8,
        )
        axis.plot(
            demand.rates,
            demand.monotone_loss[index],
            color=colors[index],
            linewidth=1.9,
            label=f"{rating}级保序拟合",
        )
    axis.set_xlim(0.039, 0.151)
    axis.set_ylim(-0.02, 1.0)
    axis.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    axis.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    axis.set_xlabel("年利率")
    axis.set_ylabel("客户流失率")
    style_axes(axis)
    axis.legend(frameon=False, loc="upper left", ncol=3, handlelength=2.0, columnspacing=1.0)
    axis.text(0.99, 0.03, "空心点：原始观测　实线：保序拟合", transform=axis.transAxes, ha="right", color=SLATE, fontsize=8.0)
    save_figure(fig, output_dir, "figure04_interest_loss")


def figure05_budget_benefit(output_dir: Path) -> None:
    curve = pd.read_csv(RESULTS / "problem1_budget_curve.csv")
    x = curve["budget_yuan"].to_numpy() / 1e6
    y = curve["expected_benefit_yuan"].to_numpy() / 1e6
    fig, axis = plt.subplots(figsize=(5.8, 3.75))
    axis.plot(x, y, color=BLUE, linewidth=1.9, marker="o", markersize=5.5, markerfacecolor="white", markeredgewidth=1.5)
    for x_value, y_value in zip(x, y, strict=True):
        axis.annotate(f"{y_value:.2f}", (x_value, y_value), xytext=(0, 8), textcoords="offset points", ha="center", color=INK, fontsize=8.5)
    axis.set_xlabel("问题一总额度（百万元）")
    axis.set_ylabel("期望年度效益（百万元）")
    axis.set_xlim(x.min() - 5, x.max() + 5)
    axis.margins(y=0.14)
    style_axes(axis)
    save_figure(fig, output_dir, "figure05_budget_benefit")


def figure06_transfer_shift(output_dir: Path) -> None:
    shift = pd.read_csv(RESULTS / "transfer_feature_shift.csv")
    top = shift.assign(abs_shift=shift["standardized_mean_shift"].abs()).nlargest(6, "abs_shift")
    top = top.sort_values("standardized_mean_shift")
    values = top["standardized_mean_shift"].to_numpy()
    labels = [FEATURE_ZH.get(name, name) for name in top["feature"]]
    colors = np.where(values >= 0, ORANGE, BLUE)

    fig, axis = plt.subplots(figsize=(6.1, 3.29))
    bars = axis.barh(labels, values, color=colors, height=0.58)
    axis.axvline(0, color=INK, linewidth=1.0)
    axis.set_xlabel("标准化均值漂移（目标域 − 源域）")
    axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:+.1f}" if value else "0"))
    for bar, value in zip(bars, values, strict=True):
        offset = 0.007 if value >= 0 else -0.007
        axis.text(value + offset, bar.get_y() + bar.get_height() / 2, f"{value:+.3f}", va="center", ha="left" if value >= 0 else "right", fontsize=8.4, color=INK)
    limit = max(0.25, np.abs(values).max() + 0.06)
    axis.set_xlim(-limit, limit)
    style_axes(axis, grid_axis="x")
    save_figure(fig, output_dir, "figure06_transfer_shift")


def figure07_risk_return(output_dir: Path) -> None:
    curve = pd.read_csv(RESULTS / "problem2_risk_return_curve.csv")
    x = curve["risk_loss_principal_yuan"].to_numpy() / 1e6
    y = curve["expected_benefit_yuan"].to_numpy() / 1e6
    caps = curve["risk_cap_fraction"].to_numpy()
    main_index = int(np.argmin(np.abs(caps - 0.013)))

    fig, axis = plt.subplots(figsize=(5.8, 3.85))
    axis.plot(x, y, color=BLUE, linewidth=1.9, marker="o", markersize=4.8)
    axis.scatter(x[main_index], y[main_index], color=ORANGE, edgecolor="white", linewidth=0.9, s=72, marker="*", zorder=5)
    axis.annotate(
        "1.30% 主方案",
        (x[main_index], y[main_index]),
        xytext=(10, -20),
        textcoords="offset points",
        color=ORANGE,
        fontsize=8.4,
        arrowprops={"arrowstyle": "->", "color": ORANGE, "lw": 0.9},
    )
    axis.annotate(
        "1.34%后进入平台",
        (x[3], y[3]),
        xytext=(-76, 12),
        textcoords="offset points",
        color=SLATE,
        fontsize=8.0,
        arrowprops={"arrowstyle": "->", "color": SLATE, "lw": 0.8},
    )
    axis.set_xlabel("组合风险损失尺度（百万元）")
    axis.set_ylabel("期望年度效益（百万元）")
    axis.margins(x=0.04, y=0.10)
    style_axes(axis)

    detail = inset_axes(axis, width="41%", height="39%", loc="lower right", borderpad=1.0)
    detail.set_facecolor("#FBFCFD")
    detail.plot(x, y, color=BLUE, linewidth=1.4, marker="o", markersize=3.5)
    detail.scatter(x[main_index], y[main_index], color=ORANGE, edgecolor="white", linewidth=0.6, s=34, marker="*", zorder=5)
    detail.set_xlim(1.295, 1.337)
    detail.set_ylim(1.425, 1.452)
    detail.set_title("局部放大：主方案至平台段", fontsize=7.8, color=INK, pad=3)
    detail.grid(True, color=GRID, linewidth=0.55, linestyle="--", alpha=0.75)
    detail.tick_params(labelsize=7.2, direction="out", length=2.5)
    for spine in detail.spines.values():
        spine.set_color("#94A3B8")
        spine.set_linewidth(0.7)
    detail.text(
        0.04,
        0.08,
        "★ 1.30%主方案",
        transform=detail.transAxes,
        color=ORANGE,
        fontsize=6.9,
    )
    save_figure(fig, output_dir, "figure07_risk_return")


def figure08_stress_transmission(output_dir: Path) -> None:
    fig, axis = plt.subplots(figsize=(6.1, 3.61))
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")

    add_box(
        axis,
        0.015,
        0.29,
        0.19,
        0.48,
        "六项经营指标\n销项月度波动\n销售近期下滑\n客户/供应商 HHI\n销项负数率\n低活跃度",
        PALE_BLUE,
        BLUE,
        7.5,
    )
    add_box(axis, 0.235, 0.40, 0.15, 0.26, "百分位排序\n等权平均", PALE_GRAY, SLATE, 8.6)
    add_box(axis, 0.425, 0.40, 0.15, 0.26, "经营脆弱度\n$v_i \\in [0,1]$", PALE_TEAL, TEAL, 9.0)
    add_box(axis, 0.625, 0.61, 0.16, 0.22, "风险通道\n$\\rho_{is}=\\rho_i(1+\\delta_s v_i)$", PALE_ORANGE, GOLD, 8.1)
    add_box(axis, 0.625, 0.25, 0.16, 0.22, "留存通道\n$q_{is}=(1-\\ell_i)(1-\\gamma_s v_i)$", PALE_ORANGE, GOLD, 8.1)
    add_box(
        axis,
        0.825,
        0.41,
        0.16,
        0.29,
        "情景单位效益\n$u_{is}(r)$\n风险与留存\n共同作用",
        "#F7EEF8",
        "#8E44AD",
        7.6,
    )
    add_box(
        axis,
        0.62,
        0.01,
        0.36,
        0.16,
        "同一授信组合面对全部情景\nmaximin 最大化最坏组合效益",
        PALE_TEAL,
        TEAL,
        7.9,
    )

    add_arrow(axis, (0.195, 0.53), (0.235, 0.53))
    add_arrow(axis, (0.385, 0.53), (0.425, 0.53))
    add_arrow(axis, (0.575, 0.53), (0.625, 0.72))
    add_arrow(axis, (0.575, 0.53), (0.625, 0.36))
    add_arrow(axis, (0.785, 0.72), (0.825, 0.58))
    add_arrow(axis, (0.785, 0.36), (0.825, 0.50))
    add_arrow(axis, (0.905, 0.43), (0.80, 0.15))
    axis.text(
        0.705,
        0.92,
        "压力参数：$\\delta_s$、$\\gamma_s$（决策情景，不是观测事实）",
        ha="center",
        color=SLATE,
        fontsize=8.0,
    )
    save_figure(fig, output_dir, "figure08_stress_transmission")


def figure09_robust_scenarios(output_dir: Path) -> None:
    scenario = pd.read_csv(RESULTS / "problem3_scenarios.csv")
    names = {"mild": "轻度", "moderate": "中度", "severe": "重度"}
    labels = [names.get(value, value) for value in scenario["scenario"]]
    values = scenario["portfolio_benefit_yuan"].to_numpy() / 1e6
    colors = [TEAL, BLUE, ORANGE]

    fig, axis = plt.subplots(figsize=(5.8, 3.75))
    bars = axis.bar(labels, values, color=colors, width=0.58)
    for bar, value in zip(bars, values, strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 0.025, f"{value:.2f}", ha="center", va="bottom", fontsize=8.8, color=INK)
    axis.set_ylim(0, max(values) * 1.18)
    axis.set_ylabel("压力情景组合效益（百万元）")
    axis.set_xlabel("压力情景")
    style_axes(axis)
    save_figure(fig, output_dir, "figure09_robust_scenarios")


def figure10_shap_importance(output_dir: Path) -> None:
    shap = pd.read_csv(RESULTS / "shap_global.csv").head(12).copy()
    shap["label"] = shap["feature"].map(lambda value: FEATURE_ZH.get(value, value))
    shap = shap.sort_values("mean_abs_shap_cri_direction")
    values = shap["mean_abs_shap_cri_direction"].to_numpy()
    colors = [BLUE] * len(shap)
    for index in range(max(0, len(colors) - 3), len(colors)):
        colors[index] = TEAL if index < len(colors) - 1 else ORANGE

    fig, axis = plt.subplots(figsize=(5.8, 3.87))
    bars = axis.barh(shap["label"], values, color=colors, height=0.62)
    for bar, value in zip(bars, values, strict=True):
        axis.text(value + max(values) * 0.012, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center", fontsize=7.9, color=INK)
    axis.set_xlim(0, max(values) * 1.14)
    axis.set_xlabel("平均绝对 SHAP 风险方向贡献")
    style_axes(axis, grid_axis="x")
    save_figure(fig, output_dir, "figure10_shap_importance")


def figure11_sensitivity(output_dir: Path) -> None:
    lgd = pd.read_csv(RESULTS / "problem2_lgd_sensitivity.csv")
    stress = pd.read_csv(RESULTS / "problem3_stress_sensitivity.csv")
    fig, axes = plt.subplots(1, 2, figsize=(5.8, 2.65))

    axes[0].plot(lgd["lgd"], lgd["expected_benefit_yuan"] / 1e6, color=BLUE, linewidth=1.8, marker="o", markersize=4.5)
    axes[0].set_xlabel("违约损失率 LGD")
    axes[0].set_ylabel("名义组合效益（百万元）")
    axes[0].set_title("(a)  LGD敏感性", loc="left", fontsize=9.2, weight="bold", color=NAVY, pad=5)
    style_axes(axes[0])

    axes[1].plot(stress["stress_scale"], stress["worst_benefit_yuan"] / 1e6, color=ORANGE, linewidth=1.8, marker="o", markersize=4.5)
    axes[1].set_xlabel("压力强度倍数")
    axes[1].set_ylabel("最坏情景效益（百万元）")
    axes[1].set_title("(b)  压力强度敏感性", loc="left", fontsize=9.2, weight="bold", color=NAVY, pad=5)
    style_axes(axes[1])

    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.22, top=0.97, wspace=0.34)
    save_figure(fig, output_dir, "figure11_sensitivity")


def build_all(output_dir: Path) -> None:
    configure_style()
    figure01_method_overview(output_dir)
    figure02_risk_pipeline(output_dir)
    figure03_cri_distribution(output_dir)
    figure04_interest_loss(output_dir)
    figure05_budget_benefit(output_dir)
    figure06_transfer_shift(output_dir)
    figure07_risk_return(output_dir)
    figure08_stress_transmission(output_dir)
    figure09_robust_scenarios(output_dir)
    figure10_shap_importance(output_dir)
    figure11_sensitivity(output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_all(args.output_dir.resolve())
    print(args.output_dir.resolve())
