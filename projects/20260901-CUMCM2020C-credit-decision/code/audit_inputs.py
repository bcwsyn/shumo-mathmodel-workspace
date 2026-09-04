"""Audit the four frozen inputs without changing them."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "inputs"
OUTPUT = ROOT / "results" / "input_audit.json"
# All monetary summaries preserve yuan and signed refund entries; the audit never
# rewrites the source workbooks or infers missing business semantics.


def sha256(path: Path) -> str:
    """Return the SHA-256 digest for one immutable input file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop workbook-exported empty columns while preserving every data row."""
    return frame.dropna(axis=1, how="all").copy()


def _duplicate_audit(frame: pd.DataFrame, enterprise: str, number: str) -> dict:
    key_duplicates = frame.duplicated([enterprise, number], keep=False)
    exact_deduplicated = frame.drop_duplicates()
    remaining_key_duplicates = exact_deduplicated.duplicated(
        [enterprise, number], keep=False
    )
    remaining_duplicate_sample = exact_deduplicated.loc[remaining_key_duplicates].head(
        8
    )
    return {
        "exact_duplicate_rows": int(frame.duplicated().sum()),
        "duplicate_key_rows": int(key_duplicates.sum()),
        "duplicate_keys": int(
            frame.loc[key_duplicates, [enterprise, number]].drop_duplicates().shape[0]
        ),
        "remaining_duplicate_key_rows_after_exact_dedup": int(
            remaining_key_duplicates.sum()
        ),
        "remaining_duplicate_keys_after_exact_dedup": int(
            exact_deduplicated.loc[remaining_key_duplicates, [enterprise, number]]
            .drop_duplicates()
            .shape[0]
        ),
        "remaining_duplicate_sample": [
            {
                str(key): (None if pd.isna(value) else str(value))
                for key, value in row.items()
            }
            for row in remaining_duplicate_sample.to_dict(orient="records")
        ],
    }


def _amount_audit(
    amount_values: pd.Series, tax_values: pd.Series, total_values: pd.Series
) -> dict:
    identity_error = (amount_values + tax_values - total_values).abs()
    return {
        "negative_amount_rows": int((amount_values < 0).sum()),
        "negative_amount_rate": float((amount_values < 0).mean()),
        "zero_amount_rows": int((amount_values == 0).sum()),
        "signed_amount_sum_yuan": float(amount_values.sum()),
        "positive_amount_sum_yuan": float(amount_values.clip(lower=0).sum()),
        "negative_amount_sum_yuan": float(amount_values.clip(upper=0).sum()),
        "amount_tax_identity_failures_gt_0_01": int((identity_error > 0.011).sum()),
        "amount_tax_identity_max_abs_error": float(identity_error.max()),
    }


def invoice_audit(frame: pd.DataFrame) -> dict:
    """Audit one invoice table without changing source records on disk."""
    frame = clean_frame(frame)
    enterprise, number, date, _counterparty, amount, tax, total, status = frame.columns[
        :8
    ]
    dates = pd.to_datetime(frame[date], errors="coerce")
    amount_values = pd.to_numeric(frame[amount], errors="coerce")
    result = {
        "rows": len(frame),
        "columns": [str(value) for value in frame.columns],
        "enterprise_count": int(frame[enterprise].nunique(dropna=True)),
        "missing_cells": {
            str(key): int(value) for key, value in frame.isna().sum().items()
        },
        "date_min": None if dates.isna().all() else str(dates.min()),
        "date_max": None if dates.isna().all() else str(dates.max()),
        "invalid_date_rows": int(dates.isna().sum()),
        "status_counts": {
            str(key): int(value)
            for key, value in frame[status].value_counts(dropna=False).items()
        },
        "invoice_number_python_types": sorted(
            {type(value).__name__ for value in frame[number].dropna().head(10000)}
        ),
    }
    result.update(_duplicate_audit(frame, enterprise, number))
    result.update(
        _amount_audit(
            amount_values,
            pd.to_numeric(frame[tax], errors="coerce"),
            pd.to_numeric(frame[total], errors="coerce"),
        )
    )
    return result


def _enterprise_audit(
    info: pd.DataFrame,
    purchase: pd.DataFrame,
    sales: pd.DataFrame,
    expected_enterprises: int,
) -> dict:
    enterprise_col = info.columns[0]
    observed = set(info[enterprise_col].dropna().astype(str).str.strip())
    purchase_ids = set(purchase.iloc[:, 0].dropna().astype(str).str.strip())
    sales_ids = set(sales.iloc[:, 0].dropna().astype(str).str.strip())
    return {
        "rows": len(info),
        "columns": [str(value) for value in info.columns],
        "expected_enterprises": expected_enterprises,
        "unique_enterprises": len(observed),
        "duplicate_enterprise_rows": int(info.duplicated([enterprise_col]).sum()),
        "missing_cells": {
            str(key): int(value) for key, value in info.isna().sum().items()
        },
        "missing_from_purchase": sorted(observed - purchase_ids),
        "missing_from_sales": sorted(observed - sales_ids),
        "purchase_unknown_enterprises": sorted(purchase_ids - observed),
        "sales_unknown_enterprises": sorted(sales_ids - observed),
    }


def _rating_audit(info: pd.DataFrame) -> dict:
    rating_col, default_col = info.columns[2], info.columns[3]
    cross = pd.crosstab(info[rating_col], info[default_col], dropna=False)
    return {
        "rating_counts": {
            str(key): int(value)
            for key, value in info[rating_col].value_counts(dropna=False).items()
        },
        "default_counts": {
            str(key): int(value)
            for key, value in info[default_col].value_counts(dropna=False).items()
        },
        "rating_default_crosstab": {
            str(index): {
                str(column): int(cross.loc[index, column]) for column in cross.columns
            }
            for index in cross.index
        },
    }


def workbook_audit(path: Path, expected_enterprises: int) -> dict:
    """Audit enterprise metadata and semantically identified invoice sheets."""
    book = pd.ExcelFile(path, engine="openpyxl")
    info = clean_frame(pd.read_excel(book, sheet_name=0))
    invoice_frames = [
        clean_frame(pd.read_excel(book, sheet_name=index)) for index in (1, 2)
    ]
    purchase = next(
        frame for frame in invoice_frames if "销方单位代号" in frame.columns
    )
    sales = next(frame for frame in invoice_frames if "购方单位代号" in frame.columns)
    result = {
        "file": path.name,
        "sha256": sha256(path),
        "sheet_names": book.sheet_names,
        "enterprise_info": _enterprise_audit(
            info, purchase, sales, expected_enterprises
        ),
        "purchase_invoices": invoice_audit(purchase),
        "sales_invoices": invoice_audit(sales),
    }
    if info.shape[1] >= 4:
        result.update(_rating_audit(info))
    return result


def interest_audit(path: Path) -> dict:
    """Audit rates and customer-loss observations in attachment 3."""
    frame = clean_frame(
        pd.read_excel(path, sheet_name=0, header=None, engine="openpyxl")
    )
    values = frame.iloc[2:, :4].apply(pd.to_numeric, errors="coerce").dropna(how="all")
    rates = values.iloc[:, 0]
    loss = values.iloc[:, 1:]
    return {
        "file": path.name,
        "sha256": sha256(path),
        "observations": len(values),
        "rate_min": float(rates.min()),
        "rate_max": float(rates.max()),
        "rate_strictly_increasing": bool((rates.diff().dropna() > 0).all()),
        "loss_bounds_valid": bool(((loss >= 0) & (loss <= 1)).all().all()),
        "raw_monotonic_violations": [
            int((loss.iloc[:, index].diff().dropna() < 0).sum())
            for index in range(loss.shape[1])
        ],
        "rates": [float(value) for value in rates],
        "loss_by_rating": {
            rating: [float(value) for value in loss.iloc[:, index]]
            for index, rating in enumerate(["A", "B", "C"])
        },
    }


def main() -> None:
    """Write the reproducible input audit JSON under the project results folder."""
    files = {
        "attachment1": INPUTS / "附件1：123家有信贷记录企业的相关数据.xlsx",
        "attachment2": INPUTS / "附件2：302家无信贷记录企业的相关数据.xlsx",
        "attachment3": INPUTS / "附件3：银行贷款年利率与客户流失率关系的统计数据.xlsx",
    }
    report = {
        "attachment1": workbook_audit(files["attachment1"], 123),
        "attachment2": workbook_audit(files["attachment2"], 302),
        "attachment3": interest_audit(files["attachment3"]),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
