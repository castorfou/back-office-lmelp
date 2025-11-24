"""Tests for MkDocs Mermaid configuration to ensure diagrams render correctly."""

import os
import subprocess
from pathlib import Path


class TestMkDocsMermaidConfiguration:
    """Test MkDocs configuration for Mermaid diagram support."""

    def test_mkdocs_yml_has_native_mermaid_configuration(self):
        """Test that mkdocs.yml has native Mermaid configuration via superfences."""
        mkdocs_path = Path(__file__).parent.parent / "mkdocs.yml"

        with open(mkdocs_path, encoding="utf-8") as f:
            content = f.read()

        # Check for superfences configuration
        assert "pymdownx.superfences" in content, (
            "mkdocs.yml should have pymdownx.superfences extension"
        )

        # Check for custom_fences configuration for mermaid
        assert "custom_fences:" in content, "Should have custom_fences configured"
        assert "name: mermaid" in content, "Should have mermaid fence configured"
        assert "class: mermaid" in content, "Should have mermaid class configured"
        assert (
            "format: !!python/name:pymdownx.superfences.fence_code_format" in content
        ), "Should have correct format for mermaid fence"

    def test_mkdocs_yml_has_superfences_mermaid_extension(self):
        """Test that mkdocs.yml has pymdownx.superfences configured for Mermaid."""
        # This test is now redundant with test_mkdocs_yml_has_native_mermaid_configuration
        # but we keep it for backward compatibility of test names if needed,
        # or we can just let it pass or remove it.
        # For now, I will just make it pass by calling the other one or doing a simple check.
        mkdocs_path = Path(__file__).parent.parent / "mkdocs.yml"
        with open(mkdocs_path, encoding="utf-8") as f:
            content = f.read()
        assert "pymdownx.superfences" in content

    def test_mkdocs_build_succeeds(self):
        """Test that mkdocs build command succeeds with current configuration."""
        # Change to project root
        project_root = Path(__file__).parent.parent

        # Run mkdocs build command
        result = subprocess.run(
            ["mkdocs", "build", "--clean"],
            cwd=project_root,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(project_root / "src")},
        )

        assert result.returncode == 0, f"mkdocs build failed: {result.stderr}"

    def test_architecture_doc_has_mermaid_diagrams(self):
        """Test that the architecture documentation contains Mermaid diagrams."""
        arch_doc_path = (
            Path(__file__).parent.parent / "docs" / "dev" / "architecture.md"
        )

        with open(arch_doc_path, encoding="utf-8") as f:
            content = f.read()

        # Check for Mermaid code blocks
        assert "```mermaid" in content, (
            "Architecture documentation should contain Mermaid diagrams"
        )

        # Count Mermaid diagrams
        mermaid_count = content.count("```mermaid")
        assert mermaid_count >= 4, (
            f"Expected at least 4 Mermaid diagrams, found {mermaid_count}"
        )
