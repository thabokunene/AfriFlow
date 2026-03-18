import os
import json
import time
from typing import List, Dict, Any


def file_info(path: str) -> Dict[str, Any]:
    st = os.stat(path)
    return {
        "name": os.path.basename(path),
        "path": path,
        "size": st.st_size,
        "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
    }


def audit_coverage_dir(root: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"inventory": [], "issues": []}
    for fname in sorted(os.listdir(root)):
        fpath = os.path.join(root, fname)
        if not os.path.isfile(fpath):
            continue
        info = file_info(fpath)
        out["inventory"].append(info)
        if fname.endswith(".json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "rows" in data and isinstance(data["rows"], list) and len(data["rows"]) == 0:
                    out["issues"].append(
                        {
                            "severity": "major",
                            "code": "COVJSON_EMPTY_ROWS",
                            "file": fname,
                            "line": 1,
                            "desc": "Coverage summary JSON contains no rows; likely include-subpath mismatch",
                        }
                    )
            except Exception as e:
                out["issues"].append(
                    {
                        "severity": "critical",
                        "code": "COVJSON_PARSE_ERROR",
                        "file": fname,
                        "line": 1,
                        "desc": f"JSON parse error: {e}",
                    }
                )
        elif fname.endswith(".md"):
            with open(fpath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) < 3:
                out["issues"].append(
                    {
                        "severity": "major",
                        "code": "COVMD_NO_ROWS",
                        "file": fname,
                        "line": 1,
                        "desc": "Markdown table header present but no data rows",
                    }
                )
        else:
            # orphaned formats not expected
            pass
    return out


def write_report(root: str, audit: Dict[str, Any]) -> None:
    path = os.path.join(root, "coverage_audit.md")
    lines: List[str] = []
    lines.append("# Coverage Folder Audit")
    lines.append("")
    lines.append("## Inventory")
    lines.append("| Name | Path | Size (bytes) | Last Modified |")
    lines.append("|---|---|---:|---|")
    for ent in audit["inventory"]:
        lines.append(f"| {ent['name']} | {ent['path']} | {ent['size']} | {ent['mtime']} |")
    lines.append("")
    lines.append("## Issues")
    if not audit["issues"]:
        lines.append("No issues found.")
    else:
        lines.append("| Severity | Code | File | Line | Description |")
        lines.append("|---|---|---|---:|---|")
        for issue in audit["issues"]:
            lines.append(
                f"| {issue['severity']} | {issue['code']} | {issue['file']} | {issue['line']} | {issue['desc']} |"
            )
    with open(path, "w", encoding="utf-8") as w:
        w.write("\n".join(lines) + "\n")


def main() -> int:
    root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "coverage")
    audit = audit_coverage_dir(root)
    write_report(root, audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
