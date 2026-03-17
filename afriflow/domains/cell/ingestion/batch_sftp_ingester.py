"""
Batch SFTP Ingester

Usage:
    from afriflow.domains.cell.ingestion.batch_sftp_ingester import BatchSFTPIngester, SFTPConfig

    cfg = SFTPConfig.from_env()
    ingester = BatchSFTPIngester(cfg)
    ingester.run(
        remote_dir="/reports/incoming",
        local_dir="data/incoming",
        batch_size=50,
        processor=lambda p: p,  # replace with pipeline step
    )
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from typing import Callable, Iterable, List, Optional, Protocol

from afriflow.logging_config import get_logger


def _setup_rotating_logger(name: str) -> any:
    logger = get_logger(name)
    log_file = os.environ.get("AF_CELL_SFTP_LOG_FILE", "logs/cell_sftp_ingester.log")
    max_bytes = int(os.environ.get("AF_CELL_SFTP_LOG_MAX_BYTES", "1048576"))
    backup_count = int(os.environ.get("AF_CELL_SFTP_LOG_BACKUP_COUNT", "5"))
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    logger.addHandler(handler)
    logger.setLevel(os.environ.get("AF_CELL_SFTP_LOG_LEVEL", "INFO"))
    return logger


@dataclass
class SFTPConfig:
    host: str
    port: int = 22
    username: Optional[str] = None
    password: Optional[str] = None
    key_path: Optional[str] = None
    known_hosts_path: Optional[str] = None
    max_retries: int = 3
    retry_backoff_ms: int = 300

    @classmethod
    def from_env(cls) -> "SFTPConfig":
        return cls(
            host=os.environ.get("AF_CELL_SFTP_HOST", "localhost"),
            port=int(os.environ.get("AF_CELL_SFTP_PORT", "22")),
            username=os.environ.get("AF_CELL_SFTP_USERNAME"),
            password=os.environ.get("AF_CELL_SFTP_PASSWORD"),
            key_path=os.environ.get("AF_CELL_SFTP_KEY_PATH"),
            known_hosts_path=os.environ.get("AF_CELL_SFTP_KNOWN_HOSTS"),
            max_retries=int(os.environ.get("AF_CELL_SFTP_MAX_RETRIES", "3")),
            retry_backoff_ms=int(os.environ.get("AF_CELL_SFTP_RETRY_BACKOFF_MS", "300")),
        )


class SFTPTransport(Protocol):
    def listdir(self, path: str) -> List[str]: ...
    def get(self, remote_path: str, local_path: str) -> None: ...
    def exists(self, remote_path: str) -> bool: ...


class BatchSFTPIngester:
    def __init__(self, config: SFTPConfig, transport: Optional[SFTPTransport] = None) -> None:
        self.config = config
        self.transport = transport
        self._logger = _setup_rotating_logger(__name__)

    def _ensure_transport(self) -> SFTPTransport:
        if self.transport:
            return self.transport
        raise RuntimeError("No SFTP transport provided; inject via constructor")

    def _checksum(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _validate_checksum(self, local_path: str, checksum: str) -> bool:
        try:
            return self._checksum(local_path) == checksum.lower()
        except Exception:
            return False

    def _download_batch(self, files: Iterable[str], remote_dir: str, local_dir: str) -> List[str]:
        t = self._ensure_transport()
        os.makedirs(local_dir or ".", exist_ok=True)
        downloaded: List[str] = []
        for fname in files:
            rpath = f"{remote_dir.rstrip('/')}/{fname}"
            lpath = os.path.join(local_dir, fname)
            try:
                t.get(rpath, lpath)
                downloaded.append(lpath)
                self._logger.info("sftp_download_ok", extra={"file": fname})
            except Exception as e:
                self._logger.error("sftp_download_error", extra={"file": fname, "error": str(e)})
        return downloaded

    def _load_checksums(self, remote_dir: str) -> dict:
        t = self._ensure_transport()
        mapping = {}
        sumfile = f"{remote_dir.rstrip('/')}/checksums.sha256"
        if t.exists(sumfile):
            try:
                tmp = os.path.join(".tmp", "checksums.sha256")
                os.makedirs(".tmp", exist_ok=True)
                t.get(sumfile, tmp)
                with open(tmp, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            mapping[parts[1]] = parts[0].lower()
                os.remove(tmp)
            except Exception as e:
                self._logger.error("sftp_checksum_parse_error", extra={"error": str(e)})
        return mapping

    def run(
        self,
        remote_dir: str,
        local_dir: str,
        batch_size: int = 100,
        processor: Optional[Callable[[str], None]] = None,
    ) -> List[str]:
        t = self._ensure_transport()
        files = sorted([f for f in t.listdir(remote_dir) if not f.endswith(".sha256")])
        checksums = self._load_checksums(remote_dir)
        processed: List[str] = []
        for i in range(0, len(files), max(1, batch_size)):
            batch = files[i : i + batch_size]
            downloaded = self._download_batch(batch, remote_dir, local_dir)
            for path in downloaded:
                fname = os.path.basename(path)
                target_sum = checksums.get(fname)
                if target_sum and not self._validate_checksum(path, target_sum):
                    self._logger.error("sftp_checksum_mismatch", extra={"file": fname})
                    continue
                try:
                    if processor:
                        processor(path)
                    processed.append(path)
                    self._logger.info("sftp_process_ok", extra={"file": fname})
                except Exception as e:
                    self._logger.error("sftp_process_error", extra={"file": fname, "error": str(e)})
        return processed
