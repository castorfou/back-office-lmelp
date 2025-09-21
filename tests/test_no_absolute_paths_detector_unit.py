from pathlib import Path

from tests.test_no_absolute_paths_in_tests import find_absolute_paths_in_file


def test_detector_finds_absolute_path(tmp_path: Path):
    p = tmp_path / "sample.py"
    # build the absolute path at runtime so the source file doesn't contain
    # the literal absolute-path substring
    parts = ["", "workspaces", "back-office-lmelp", "src"]
    abs_path = "/".join(parts)
    p.write_text(f"env_path = {abs_path!r}\\n")
    matches = find_absolute_paths_in_file(p)
    assert matches, f"Detector did not find absolute path in {p}"
