from __future__ import annotations

import os
from typing import List

import pytest

import afriflow.domains.cell.ingestion.batch_sftp_ingester as mod
from afriflow.domains.cell.ingestion.batch_sftp_ingester import BatchSFTPIngester, SFTPConfig, SFTPTransport


class FakeTransport:
    def __init__(self, files: List[str], data: bytes):
        self._files = files
        self._data = data
        self._exists = set()

    def listdir(self, path: str) -> List[str]:
        return list(self._files)

    def get(self, remote_path: str, local_path: str) -> None:
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(self._data)

    def exists(self, remote_path: str) -> bool:
        return remote_path.endswith("checksums.sha256")


def test_sftp_config_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AF_CELL_SFTP_HOST", "sftp.local")
    monkeypatch.setenv("AF_CELL_SFTP_PORT", "2222")
    cfg = SFTPConfig.from_env()
    assert cfg.host == "sftp.local"
    assert cfg.port == 2222


def test_sftp_run_download_and_process(tmp_path, monkeypatch: pytest.MonkeyPatch):
    files = ["a.bin", "b.bin"]
    transport = FakeTransport(files, b"hello-world")
    cfg = SFTPConfig(host="localhost")
    ingester = BatchSFTPIngester(cfg, transport=transport)

    processed = []
    out = ingester.run(
        remote_dir="/remote",
        local_dir=str(tmp_path),
        batch_size=1,
        processor=lambda p: processed.append(p),
    )
    assert sorted(processed) == sorted(out)
    assert len(out) == 2
    for p in out:
        assert os.path.exists(p)


def test_sftp_checksum_mismatch(tmp_path, monkeypatch: pytest.MonkeyPatch):
    files = ["a.bin"]
    transport = FakeTransport(files, b"content")
    cfg = SFTPConfig(host="localhost")
    ingester = BatchSFTPIngester(cfg, transport=transport)

    # Force checksum mapping to require mismatch
    def fake_load(remote_dir):
        return {"a.bin": "deadbeef"}

    monkeypatch.setattr(mod.BatchSFTPIngester, "_load_checksums", lambda self, r: fake_load(r))
    out = ingester.run(remote_dir="/remote", local_dir=str(tmp_path), batch_size=10, processor=None)
    assert out == []
