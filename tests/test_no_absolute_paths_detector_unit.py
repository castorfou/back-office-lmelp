from pathlib import Path

from tests.test_no_absolute_paths_in_tests import find_absolute_paths_in_file


def test_detector_finds_absolute_path(tmp_path: Path):
    p = tmp_path / "sample.py"
    p.write_text('env_path = "/workspaces/back-office-lmelp/src"\n')
    matches = find_absolute_paths_in_file(p)
    assert matches, f"Detector did not find absolute path in {p}"
