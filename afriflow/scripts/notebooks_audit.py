import os
import json
import time
from typing import Dict, Any, List, Tuple


NB_OK = "OK"
NB_FAIL = "FAIL"


def list_notebooks(root: str) -> List[str]:
    return [
        os.path.join(root, f)
        for f in sorted(os.listdir(root))
        if f.endswith(".ipynb")
    ]


def load_nb(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_nb(path: str, nb: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)


def clear_outputs(nb: Dict[str, Any]) -> None:
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None


def ensure_structure(nb: Dict[str, Any]) -> None:
    headings = {
        "Notebook Overview": "# Notebook Overview",
        "Imports": "## Imports",
        "Data Loading": "## Data Loading",
        "Analysis": "## Analysis",
        "Results": "## Results",
    }
    existing_h = set()
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            src = "".join(cell.get("source", []))
            for h in headings.values():
                if h in src:
                    existing_h.add(h)
    # Prepend missing headings as markdown cells
    missing = [h for h in headings.values() if h not in existing_h]
    if missing:
        md_cells = [{"cell_type": "markdown", "metadata": {}, "source": [m + "\n\n"]} for m in missing]
        nb["cells"] = md_cells + nb.get("cells", [])


def detect_sensitive_sources(src: str) -> List[str]:
    keys = ["password", "api_key", "apikey", "token", "secret", "private_key"]
    found = []
    low = src.lower()
    for k in keys:
        if k in low:
            found.append(k)
    return found


def sanitize_cell_source(src: str) -> str:
    lines = src.splitlines()
    clean = []
    for ln in lines:
        if ln.strip().startswith(("%", "!", "?")):
            continue
        clean.append(ln)
    return "\n".join(clean)


def exec_notebook(nb: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    g: Dict[str, Any] = {}
    errors: List[Dict[str, Any]] = []
    for idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        sensitive = detect_sensitive_sources(src)
        if sensitive:
            errors.append({"cell": idx, "code": "SENSITIVE", "desc": f"Sensitive keyword(s) detected: {', '.join(sensitive)}"})
        code = sanitize_cell_source(src)
        if not code.strip():
            continue
        try:
            exec(code, g)
        except Exception as e:
            errors.append({"cell": idx, "code": "EXEC_ERROR", "desc": str(e)})
    return (NB_OK if not errors else NB_FAIL), errors


def write_readme(root: str, entries: List[Dict[str, Any]], dependencies: List[str]) -> None:
    p = os.path.join(root, "README.md")
    lines = []
    lines.append("# Notebooks")
    lines.append("")
    lines.append("Guidelines:")
    lines.append("- Keep outputs cleared to reduce repository size")
    lines.append("- Include sections: Notebook Overview, Imports, Data Loading, Analysis, Results")
    lines.append("- Avoid hard-coded secrets; use environment variables or config")
    lines.append("")
    lines.append("## Dependencies")
    lines.append(", ".join(sorted(set(dependencies))) or "None")
    lines.append("")
    lines.append("## Index")
    lines.append("| Notebook | Status | Last Updated | Owner |")
    lines.append("|---|---|---|---|")
    for e in entries:
        lines.append(f"| {e['name']} | {e['status']} | {e['mtime']} | {e.get('owner','Unassigned')} |")
    with open(p, "w", encoding="utf-8") as w:
        w.write("\n".join(lines) + "\n")


def write_summary(root: str, entries: List[Dict[str, Any]]) -> None:
    p = os.path.join(root, "notebooks_summary.md")
    lines = []
    lines.append("# Notebooks Summary")
    lines.append("| Notebook | Path | Status | Last Updated | Owner |")
    lines.append("|---|---|---|---|---|")
    for e in entries:
        lines.append(f"| {e['name']} | {e['path']} | {e['status']} | {e['mtime']} | {e.get('owner','Unassigned')} |")
    with open(p, "w", encoding="utf-8") as w:
        w.write("\n".join(lines) + "\n")


def main() -> int:
    root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "notebooks")
    nbs = list_notebooks(root)
    entries: List[Dict[str, Any]] = []
    deps: List[str] = []
    for nb_path in nbs:
        st = os.stat(nb_path)
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
        nb = load_nb(nb_path)
        # Collect naive dependencies from import statements
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code":
                src = "".join(cell.get("source", []))
                for ln in src.splitlines():
                    ln_s = ln.strip()
                    if ln_s.startswith("import ") or ln_s.startswith("from "):
                        pkg = ln_s.split()[1]
                        deps.append(pkg.split(".")[0])
        ensure_structure(nb)
        clear_outputs(nb)
        status, errs = exec_notebook(nb)
        # Save sanitized notebook
        save_nb(nb_path, nb)
        entry = {
            "name": os.path.basename(nb_path),
            "path": nb_path,
            "mtime": mtime,
            "status": status if status == NB_OK else f"{NB_FAIL} ({len(errs)} issues)",
            "owner": "Unassigned",
        }
        entries.append(entry)
    write_readme(root, entries, deps)
    write_summary(root, entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
