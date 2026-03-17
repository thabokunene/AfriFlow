from __future__ import annotations

import json
import os
from pathlib import Path
import pandas as pd
import pytest

from afriflow.domains.cell.ingestion.monthly_report_ingester import MonthlyReportIngester, MonthlyConfig


def _write_files(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    csv = base / "cell-2026-02-usage.csv"
    js = base / "cell-2026-02-usage.json"
    df = pd.DataFrame([{"country": "za", "timestamp": "2026-02-15T12:00:00Z", "value": 1}])
    df.to_csv(csv, index=False)
    with open(js, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f)
    return str(csv), str(js)


def test_discover_and_parse(tmp_path):
    csv, js = _write_files(tmp_path)
    # Create optional Excel file only if openpyxl is available
    xlsx = tmp_path / "cell-2026-02-usage.xlsx"
    try:
        import openpyxl  # type: ignore
        df = pd.DataFrame([{"country": "za", "timestamp": "2026-02-15T12:00:00Z", "value": 1}])
        with pd.ExcelWriter(xlsx) as w:
            df.to_excel(w, index=False)
        has_xlsx = True
    except Exception:
        has_xlsx = False
    svc = MonthlyReportIngester(MonthlyConfig.from_env())
    found = svc.discover(str(tmp_path), "cell")
    if has_xlsx:
        assert set(found) == {csv, str(xlsx), js}
    else:
        assert set(found) == {csv, js}
    d_csv = svc._parse(csv)
    d_js = svc._parse(js)
    assert d_csv.shape[0] == 1 and d_js.shape[0] == 1
    if has_xlsx:
        d_xlsx = svc._parse(str(xlsx))
        assert d_xlsx.shape[0] == 1


def test_validate_and_transform(tmp_path):
    csv, _ = _write_files(tmp_path)
    svc = MonthlyReportIngester(MonthlyConfig.from_env())
    df = svc._parse(csv)
    svc._validate(df)
    df2 = svc._transform(df)
    assert df2["country"].iloc[0] == "ZA"
    assert str(df2["timestamp"].iloc[0].tz.tzname(None)).upper() in {"UTC", "COORDINATED UNIVERSAL TIME"}


def test_run_loader_called(tmp_path):
    csv, _ = _write_files(tmp_path)
    svc = MonthlyReportIngester(MonthlyConfig.from_env())
    calls = []
    result = svc.run(str(tmp_path), "cell", loader=lambda df, meta: calls.append((len(df), meta["path"])))
    assert result["processed"] >= 2 and result["failed"] == 0
    assert len(calls) == result["processed"]


def test_validation_failure(tmp_path):
    missing = tmp_path / "cell-2026-02-bad.csv"
    with open(missing, "w", encoding="utf-8") as f:
        f.write("x,y\n1,2\n")
    svc = MonthlyReportIngester(MonthlyConfig(required_columns=("country", "timestamp"), fail_fast=False))
    result = svc.run(str(tmp_path), "cell", loader=None)
    assert result["failed"] >= 1
