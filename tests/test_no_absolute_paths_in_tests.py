import re
from pathlib import Path


ABS_PATH_PATTERNS = [
    re.compile(r"/workspaces/"),
    re.compile(r"/home/"),
    re.compile(r"/Users/"),
    re.compile(r"[A-Za-z]:\\\\"),  # Windows drive letter like C:\
]


def find_absolute_paths_in_file(path: Path):
    matches = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        # binary or unreadable file
        return matches
    for i, line in enumerate(text.splitlines(), start=1):
        for pat in ABS_PATH_PATTERNS:
            if pat.search(line):
                matches.append((i, line.strip()))
                break
    return matches


def test_no_absolute_paths_in_tests():
    """Fail if any test or fixture file contains hard-coded absolute paths.

    Scans `tests/` and `frontend/tests/` for common absolute path literals that
    break when running in CI or when the workspace root differs.
    """
    repo_root = Path(__file__).resolve().parents[1]
    search_roots = [repo_root / "tests", repo_root / "frontend" / "tests"]
    found = []
    for root in search_roots:
        if not root.exists():
            continue
        for p in (
            list(root.rglob("*.py"))
            + list(root.rglob("*.js"))
            + list(root.rglob("*.ts"))
        ):
            rel = p.relative_to(repo_root)
            # skip this test file itself (it contains the patterns on purpose)
            if rel.name == Path(__file__).name:
                continue
            matches = find_absolute_paths_in_file(p)
            if matches:
                found.append((str(rel), matches))

    if found:
        lines = ["Found hard-coded absolute paths in test files:"]
        for file, matches in found:
            lines.append(f"- {file}")
            for lineno, line_content in matches:
                lines.append(f"    {lineno}: {line_content}")
        raise AssertionError("\n".join(lines))
