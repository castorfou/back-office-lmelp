"""Tests for MkDocs Mermaid configuration to ensure diagrams render correctly."""

import os
import subprocess
from pathlib import Path


class TestMkDocsMermaidConfiguration:
    """Test MkDocs configuration for Mermaid diagram support."""

    def test_mkdocs_yml_contains_mermaid_plugin(self):
        """Test that mkdocs.yml includes the mermaid2 plugin."""
        mkdocs_path = Path(__file__).parent.parent / "mkdocs.yml"

        with open(mkdocs_path, encoding="utf-8") as f:
            content = f.read()

        # Check for mermaid2 plugin in raw content to avoid YAML parsing issues
        assert "plugins:" in content, "mkdocs.yml should have a 'plugins' section"
        assert "- mermaid2" in content, (
            "mkdocs.yml should include mermaid2 plugin in the plugins list"
        )

    def test_mkdocs_yml_has_superfences_mermaid_extension(self):
        """Test that mkdocs.yml has pymdownx.superfences configured for Mermaid."""
        mkdocs_path = Path(__file__).parent.parent / "mkdocs.yml"

        with open(mkdocs_path, encoding="utf-8") as f:
            content = f.read()

        # Check for superfences with mermaid configuration in raw content
        # since YAML safe_load cannot handle !!python/name: syntax
        assert "pymdownx.superfences:" in content, (
            "mkdocs.yml should have pymdownx.superfences configuration"
        )
        assert "custom_fences:" in content, (
            "pymdownx.superfences should have custom_fences configuration"
        )
        assert "name: mermaid" in content, (
            "custom_fences should have mermaid fence configured"
        )
        assert "markdown_extensions:" in content, (
            "mkdocs.yml should have markdown_extensions"
        )

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
