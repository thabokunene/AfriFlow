"""
@file batch_sftp_ingester.py
@description Batch ingester for Cell domain data via SFTP, supporting checksum validation and rotating logs.
@author Thabo Kunene
@created 2026-03-19
"""

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

# Enables postponed evaluation of type annotations for forward references
from __future__ import annotations

# Standard library for generating SHA-256 checksums for file integrity verification
import hashlib
# Standard library for interacting with the file system and environment variables
import os
# Dataclass for structured configuration objects
from dataclasses import dataclass
# Specialized logging handler for rotating log files to prevent disk saturation
from logging.handlers import RotatingFileHandler
# Typing hints for defining strong functional and collection contracts
from typing import Callable, Iterable, List, Optional, Protocol

# AfriFlow logging utility for consistent log formatting
from afriflow.logging_config import get_logger


def _setup_rotating_logger(name: str) -> any:
    """
    Configures a logger with a rotating file handler based on environment settings.
    
    :param name: The name of the logger (usually __name__).
    :return: A configured logger instance.
    """
    logger = get_logger(name)
    # File path for the SFTP ingester logs
    log_file = os.environ.get("AF_CELL_SFTP_LOG_FILE", "logs/cell_sftp_ingester.log")
    # Maximum size of a single log file before rotation (default 1MB)
    max_bytes = int(os.environ.get("AF_CELL_SFTP_LOG_MAX_BYTES", "1048576"))
    # Number of old log files to keep
    backup_count = int(os.environ.get("AF_CELL_SFTP_LOG_BACKUP_COUNT", "5"))
    
    # Ensure the log directory exists
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    
    # Initialize and attach the rotating handler
    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    logger.addHandler(handler)
    # Set logging level (default INFO)
    logger.setLevel(os.environ.get("AF_CELL_SFTP_LOG_LEVEL", "INFO"))
    return logger


@dataclass
class SFTPConfig:
    """
    Configuration container for SFTP connection parameters.
    """
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
        """
        Loads SFTP configuration from environment variables with defaults.
        
        :return: An initialized SFTPConfig instance.
        """
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
    """
    Structural protocol for SFTP transport implementations.
    Allows for easy mocking during unit testing.
    """
    def listdir(self, path: str) -> List[str]: ...
    def get(self, remote_path: str, local_path: str) -> None: ...
    def exists(self, remote_path: str) -> bool: ...


class BatchSFTPIngester:
    """
    Handles the batch downloading and validation of files from a remote SFTP server.
    """
    def __init__(self, config: SFTPConfig, transport: Optional[SFTPTransport] = None) -> None:
        """
        Initializes the ingester with configuration and an optional transport.
        
        :param config: SFTP connection configuration.
        :param transport: Implementation of SFTPTransport (e.g., paramiko wrapper).
        """
        self.config = config
        self.transport = transport
        self._logger = _setup_rotating_logger(__name__)

    def _ensure_transport(self) -> SFTPTransport:
        """
        Verifies that a transport implementation is available.
        
        :return: The SFTP transport instance.
        :raises RuntimeError: If no transport was provided.
        """
        if self.transport:
            return self.transport
        raise RuntimeError("No SFTP transport provided; inject via constructor")

    def _checksum(self, path: str) -> str:
        """
        Calculates the SHA-256 checksum of a local file.
        
        :param path: Path to the local file.
        :return: Hexadecimal string of the checksum.
        """
        h = hashlib.sha256()
        with open(path, "rb") as f:
            # Read in 8KB chunks to handle large files without high memory usage
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _validate_checksum(self, local_path: str, checksum: str) -> bool:
        """
        Compares a file's actual checksum with an expected value.
        
        :param local_path: Path to the downloaded file.
        :param checksum: The expected checksum string.
        :return: True if they match, False otherwise.
        """
        try:
            return self._checksum(local_path) == checksum.lower()
        except Exception:
            # Catch file access errors and treat as validation failure
            return False

    def _download_batch(self, files: Iterable[str], remote_dir: str, local_dir: str) -> List[str]:
        """
        Downloads a list of files from the remote directory to the local directory.
        
        :param files: List of filenames to download.
        :param remote_dir: Path to the remote directory.
        :param local_dir: Path to the local destination directory.
        :return: List of successfully downloaded local file paths.
        """
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
