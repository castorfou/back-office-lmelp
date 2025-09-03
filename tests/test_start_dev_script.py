"""Test for the start-dev.sh script."""

import os
import stat
import subprocess
from pathlib import Path


class TestStartDevScript:
    """Test suite for the start-dev.sh script."""

    def test_script_exists(self):
        """Test that the start-dev.sh script exists."""
        script_path = Path("/workspaces/back-office-lmelp/scripts/start-dev.sh")
        assert script_path.exists(), "start-dev.sh script should exist"

    def test_script_is_executable(self):
        """Test that the start-dev.sh script is executable."""
        script_path = Path("/workspaces/back-office-lmelp/scripts/start-dev.sh")
        assert script_path.exists(), "Script must exist to test executability"

        # Check if file has execute permissions
        st = os.stat(script_path)
        assert bool(st.st_mode & stat.S_IXUSR), "Script should be executable by user"

    def test_script_syntax(self):
        """Test that the start-dev.sh script has valid bash syntax."""
        script_path = Path("/workspaces/back-office-lmelp/scripts/start-dev.sh")
        assert script_path.exists(), "Script must exist to test syntax"

        # Use bash -n to check syntax without executing
        result = subprocess.run(
            ["bash", "-n", str(script_path)], capture_output=True, text=True
        )
        assert result.returncode == 0, f"Script syntax error: {result.stderr}"

    def test_script_has_shebang(self):
        """Test that the script starts with a proper shebang."""
        script_path = Path("/workspaces/back-office-lmelp/scripts/start-dev.sh")
        assert script_path.exists(), "Script must exist to test shebang"

        with open(script_path) as f:
            first_line = f.readline().strip()

        assert first_line.startswith("#!/"), "Script should start with shebang"
        assert "bash" in first_line, "Script should use bash"

    def test_script_contains_backend_command(self):
        """Test that the script contains the backend launch command."""
        script_path = Path("/workspaces/back-office-lmelp/scripts/start-dev.sh")
        assert script_path.exists(), "Script must exist to test content"

        with open(script_path) as f:
            content = f.read()

        assert 'PYTHONPATH="$PROJECT_ROOT/src"' in content, (
            "Script should set PYTHONPATH for backend"
        )
        assert "python -m back_office_lmelp.app" in content, (
            "Script should launch backend app"
        )

    def test_script_contains_frontend_command(self):
        """Test that the script contains the frontend launch command."""
        script_path = Path("/workspaces/back-office-lmelp/scripts/start-dev.sh")
        assert script_path.exists(), "Script must exist to test content"

        with open(script_path) as f:
            content = f.read()

        assert 'cd "$PROJECT_ROOT/frontend"' in content, (
            "Script should change to frontend directory"
        )
        assert "npm run dev" in content, "Script should run frontend dev server"

    def test_script_handles_signal_trapping(self):
        """Test that the script handles signal trapping for clean shutdown."""
        script_path = Path("/workspaces/back-office-lmelp/scripts/start-dev.sh")
        assert script_path.exists(), "Script must exist to test content"

        with open(script_path) as f:
            content = f.read()

        assert "trap" in content, "Script should use signal trapping"
        assert "SIGINT" in content or "INT" in content, (
            "Script should handle SIGINT (Ctrl+C)"
        )
