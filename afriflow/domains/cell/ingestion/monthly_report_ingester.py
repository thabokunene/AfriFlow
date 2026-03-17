"""
Monthly Report Ingester

Usage:
    from afriflow.domains.cell.ingestion.monthly_report_ingester import MonthlyReportIngester, MonthlyConfig

    cfg = MonthlyConfig.from_env()
    service = MonthlyReportIngester(cfg)
    result = service.run(
        input_dir="reports/monthly",
        pattern_prefix="cell",
        loader=lambda df, meta: df,  # inject pipeline loader
    )
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd
from afriflow.logging_config import get_logger


def _setup_rotating_logger(name: str) -> any:
    logger = get_logger(name)
    log_file = os.environ.get("AF_CELL_MONTHLY_LOG_FILE", "logs/cell_monthly_ingester.log")
    max_bytes = int(os.environ.get("AF_CELL_MONTHLY_LOG_MAX_BYTES", "1048576"))
    backup_count = int(os.environ.get("AF_CELL_MONTHLY_LOG_BACKUP_COUNT", "5"))
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    logger.addHandler(handler)
    logger.setLevel(os.environ.get("AF_CELL_MONTHLY_LOG_LEVEL", "INFO"))
    return logger


@dataclass
class MonthlyConfig:
    required_columns: Tuple[str, ...] = ("country", "timestamp")
    tz_aware: bool = True
    fail_fast: bool = False

    @classmethod
    def from_env(cls) -> "MonthlyConfig":
        cols = os.environ.get("AF_CELL_MONTHLY_REQUIRED_COLUMNS", "country,timestamp")
        return cls(
            required_columns=tuple(c.strip() for c in cols.split(",") if c.strip()),
            tz_aware=os.environ.get("AF_CELL_MONTHLY_TZ_AWARE", "true").lower() in {"1", "true", "yes"},
            fail_fast=os.environ.get("AF_CELL_MONTHLY_FAIL_FAST", "false").lower() in {"1", "true", "yes"},
        )


class MonthlyReportIngester:
    def __init__(self, config: MonthlyConfig) -> None:
        self.config = config
        self._logger = _setup_rotating_logger(__name__)

    def discover(self, input_dir: str, pattern_prefix: str) -> List[str]:
        rx = re.compile(rf"^{re.escape(pattern_prefix)}[-_]\d{{4}}[-_]\d{{2}}[-_].+\.(csv|xlsx|json)$", re.IGNORECASE)
        all_files = sorted(os.listdir(input_dir)) if os.path.isdir(input_dir) else []
        return [os.path.join(input_dir, f) for f in all_files if rx.match(f)]

    def _parse(self, path: str) -> pd.DataFrame:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(path)
        elif ext == ".xlsx":
            df = pd.read_excel(path)
        elif ext == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data if isinstance(data, list) else [data])
        else:
            raise ValueError(f"unsupported format: {ext}")
        return df

    def _validate(self, df: pd.DataFrame) -> None:
        missing = [c for c in self.config.required_columns if c not in df.columns]
        if missing:
            raise ValueError(f"missing columns: {missing}")

    def _transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if "country" in df.columns:
            df["country"] = df["country"].astype(str).str.upper()
        if "timestamp" in df.columns:
            def _to_utc(x):
                try:
                    dt = pd.to_datetime(x, utc=True)
                    return dt.dt.tz_convert("UTC")
                except Exception:
                    return pd.to_datetime(x, errors="coerce", utc=True)
            df["timestamp"] = _to_utc(df["timestamp"])
        return df

    def run(
        self,
        input_dir: str,
        pattern_prefix: str,
        loader: Optional[Callable[[pd.DataFrame, Dict[str, str]], None]] = None,
    ) -> Dict[str, int]:
        files = self.discover(input_dir, pattern_prefix)
        processed = 0
        failed = 0
        for path in files:
            try:
                df = self._parse(path)
                self._validate(df)
                df = self._transform(df)
                meta = {
                    "path": path,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                }
                if loader:
                    loader(df, meta)
                processed += 1
                self._logger.info("monthly_ingest_ok", extra={"path": path, "rows": int(df.shape[0])})
            except Exception as e:
                failed += 1
                self._logger.error("monthly_ingest_error", extra={"path": path, "error": str(e)})
                if self.config.fail_fast:
                    raise
        return {"processed": processed, "failed": failed, "discovered": len(files)}
