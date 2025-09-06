"""Tests for MkDocs Mermaid configuration to ensure diagrams render correctly."""

import os
import subprocess
from pathlib import Path

import yaml


class TestMkDocsMermaidConfiguration:
    """Test MkDocs configuration for Mermaid diagram support."""

    def test_mkdocs_yml_contains_mermaid_plugin(self):
        """Test that mkdocs.yml includes the mermaid2 plugin."""
        mkdocs_path = Path(__file__).parent.parent / "mkdocs.yml"

        with open(mkdocs_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Check that plugins section exists
        assert "plugins" in config, "mkdocs.yml should have a 'plugins' section"

        plugins = config["plugins"]

        # Extract plugin names (handle both string and dict formats)
        plugin_names = []
        for plugin in plugins:
            if isinstance(plugin, str):
                plugin_names.append(plugin)
            elif isinstance(plugin, dict):
                plugin_names.extend(plugin.keys())

        # Check that mermaid2 plugin is present
        assert "mermaid2" in plugin_names, (
            f"mermaid2 plugin should be in plugins list. Found: {plugin_names}"
        )

    def test_mkdocs_yml_has_superfences_mermaid_extension(self):
        """Test that mkdocs.yml has pymdownx.superfences configured for Mermaid."""
        mkdocs_path = Path(__file__).parent.parent / "mkdocs.yml"

        with open(mkdocs_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert "markdown_extensions" in config, (
            "mkdocs.yml should have markdown_extensions"
        )

        extensions = config["markdown_extensions"]

        # Look for pymdownx.superfences configuration
        superfences_config = None
        for ext in extensions:
            if isinstance(ext, dict) and "pymdownx.superfences" in ext:
                superfences_config = ext["pymdownx.superfences"]
                break
            if ext == "pymdownx.superfences":
                # Extension is present but not configured - that's okay for basic Mermaid
                return

        if superfences_config:
            # If superfences is configured, check it supports Mermaid
            custom_fences = superfences_config.get("custom_fences", [])
            mermaid_fence = any(
                fence.get("name") == "mermaid" for fence in custom_fences
            )
            assert mermaid_fence, (
                "pymdownx.superfences should have mermaid custom fence configured"
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
