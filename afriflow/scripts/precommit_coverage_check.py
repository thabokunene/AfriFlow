import subprocess
import sys
import os


def run(cmd: list[str], cwd: str) -> int:
    p = subprocess.run(cmd, cwd=cwd)
    return p.returncode


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    project = os.path.abspath(os.path.join(root, os.pardir))

    rc = run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--cov=domains",
            "--cov=afriflow",
            "--cov-branch",
            "--cov-report=xml",
            "--cov-report=term",
        ],
        cwd=project,
    )
    if rc != 0:
        return rc

    rc = run(
        [
            sys.executable,
            "scripts/cell_coverage_report.py",
            "--xml",
            "coverage.xml",
            "--json",
            "coverage.json",
            "--include-subpath",
            "domains/forex/ingestion",
            "--line-min",
            "90",
            "--branch-min",
            "0",
            "--func-min",
            "0",
        ],
        cwd=project,
    )
    if rc != 0:
        return rc

    rc = run(
        [
            sys.executable,
            "scripts/cell_coverage_report.py",
            "--xml",
            "coverage.xml",
            "--json",
            "coverage.json",
            "--include-subpath",
            "domains/cib/processing/flink",
            "--include-file-pattern",
            "flow_drift_detector\\.py",
            "--line-min",
            "90",
            "--branch-min",
            "0",
            "--func-min",
            "0",
        ],
        cwd=project,
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
