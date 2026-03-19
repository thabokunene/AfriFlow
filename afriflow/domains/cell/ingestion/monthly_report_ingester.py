"""
@file monthly_report_ingester.py
@description Ingester for Cell domain monthly reports, supporting CSV, Excel, and JSON formats with validation and transformation.
@author Thabo Kunene
@created 2026-03-19
"""

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

# Enables postponed evaluation of type annotations for forward references
from __future__ import annotations

# Standard library for JSON encoding/decoding
import json
# Standard library for interacting with the file system and environment variables
import os
# Regular expression support for file pattern matching
import re
# Dataclass for structured configuration objects
from dataclasses import dataclass
# Datetime utilities for timestamp normalization
from datetime import datetime, timezone
# Specialized logging handler for rotating log files
from logging.handlers import RotatingFileHandler
# Typing hints for defining strong functional and collection contracts
from typing import Callable, Dict, List, Optional, Tuple

# Pandas library for high-performance data manipulation and analysis
import pandas as pd
# AfriFlow logging utility for consistent log formatting
from afriflow.logging_config import get_logger


def _setup_rotating_logger(name: str) -> any:
    """
    Configures a logger with a rotating file handler based on environment settings.
    
    :param name: The name of the logger.
    :return: A configured logger instance.
    """
    logger = get_logger(name)
    # File path for the monthly ingester logs
    log_file = os.environ.get("AF_CELL_MONTHLY_LOG_FILE", "logs/cell_monthly_ingester.log")
    # Maximum size of a single log file before rotation (default 1MB)
    max_bytes = int(os.environ.get("AF_CELL_MONTHLY_LOG_MAX_BYTES", "1048576"))
    # Number of old log files to keep
    backup_count = int(os.environ.get("AF_CELL_MONTHLY_LOG_BACKUP_COUNT", "5"))
    
    # Ensure the log directory exists
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    
    # Initialize and attach the rotating handler
    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    logger.addHandler(handler)
    # Set logging level (default INFO)
    logger.setLevel(os.environ.get("AF_CELL_MONTHLY_LOG_LEVEL", "INFO"))
    return logger


@dataclass
class MonthlyConfig:
    """
    Configuration container for monthly report ingestion parameters.
    """
    required_columns: Tuple[str, ...] = ("country", "timestamp")
    tz_aware: bool = True
    fail_fast: bool = False

    @classmethod
    def from_env(cls) -> "MonthlyConfig":
        """
        Loads monthly ingestion configuration from environment variables.
        
        :return: An initialized MonthlyConfig instance.
        """
        # Retrieve list of required columns from environment, comma-separated
        cols = os.environ.get("AF_CELL_MONTHLY_REQUIRED_COLUMNS", "country,timestamp")
        return cls(
            required_columns=tuple(c.strip() for c in cols.split(",") if c.strip()),
            # Flag to ensure all timestamps are converted to UTC
            tz_aware=os.environ.get("AF_CELL_MONTHLY_TZ_AWARE", "true").lower() in {"1", "true", "yes"},
            # Flag to abort the entire batch if a single file fails validation
            fail_fast=os.environ.get("AF_CELL_MONTHLY_FAIL_FAST", "false").lower() in {"1", "true", "yes"},
        )


class MonthlyReportIngester:
    """
    Handles discovery, parsing, validation, and transformation of monthly reports.
    """
    def __init__(self, config: MonthlyConfig) -> None:
        """
        Initializes the ingester with configuration.
        
        :param config: Ingestion configuration parameters.
        """
        self.config = config
        self._logger = _setup_rotating_logger(__name__)

    def discover(self, input_dir: str, pattern_prefix: str) -> List[str]:
        """
        Identifies files in the input directory that match the expected naming convention.
        
        :param input_dir: Path to the directory containing report files.
        :param pattern_prefix: Prefix to filter files (e.g., 'cell').
        :return: List of absolute file paths matching the pattern.
        """
        # Pattern expects prefix, year (4 digits), month (2 digits), and supported extension
        rx = re.compile(rf"^{re.escape(pattern_prefix)}[-_]\d{{4}}[-_]\d{{2}}[-_].+\.(csv|xlsx|json)$", re.IGNORECASE)
        all_files = sorted(os.listdir(input_dir)) if os.path.isdir(input_dir) else []
        return [os.path.join(input_dir, f) for f in all_files if rx.match(f)]

    def _parse(self, path: str) -> pd.DataFrame:
        """
        Parses a file into a Pandas DataFrame based on its extension.
        
        :param path: Path to the file to be parsed.
        :return: A Pandas DataFrame containing the file's data.
        :raises ValueError: If the file format is not supported.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(path)
        elif ext == ".xlsx":
            df = pd.read_excel(path)
        elif ext == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Handle both list of records and single record JSON formats
            df = pd.DataFrame(data if isinstance(data, list) else [data])
        else:
            raise ValueError(f"unsupported format: {ext}")
        return df

    def _validate(self, df: pd.DataFrame) -> None:
        """
        Ensures the DataFrame contains all mandatory columns.
        
        :param df: The DataFrame to validate.
        :raises ValueError: If required columns are missing.
        """
        missing = [c for c in self.config.required_columns if c not in df.columns]
        if missing:
            raise ValueError(f"missing columns: {missing}")

    def _transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies standard data cleanups and normalizations.
        
        :param df: The raw DataFrame.
        :return: The transformed DataFrame.
        """
        # Normalize country codes to uppercase for consistent mapping
        if "country" in df.columns:
            df["country"] = df["country"].astype(str).str.upper()
        # Ensure timestamps are in UTC format
        if "timestamp" in df.columns:
            def _to_utc(x):
                try:
                    dt = pd.to_datetime(x, utc=True)
                    return dt.dt.tz_convert("UTC")
                except Exception:
                    # Fallback for irregular date strings
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
