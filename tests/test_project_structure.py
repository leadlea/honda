"""Test project structure and basic imports."""

import sys
from pathlib import Path

import pytest


def test_project_structure():
    """Test that the basic project structure exists."""
    project_root = Path(__file__).parent.parent

    # Check main directories exist
    assert (project_root / "src").exists()
    assert (project_root / "src" / "handlers").exists()
    assert (project_root / "src" / "models").exists()
    assert (project_root / "src" / "services").exists()
    assert (project_root / "src" / "repositories").exists()
    assert (project_root / "src" / "utils").exists()

    # Check test directories exist
    assert (project_root / "tests").exists()
    assert (project_root / "tests" / "unit").exists()
    assert (project_root / "tests" / "integration").exists()

    # Check frontend directory exists
    assert (project_root / "frontend").exists()
    assert (project_root / "frontend" / "src").exists()


def test_python_version():
    """Test that we're running Python 3.12+."""
    assert sys.version_info >= (3, 12), f"Python 3.12+ required, got {sys.version_info}"


def test_src_package_imports():
    """Test that src packages can be imported."""
    # Add src to path for testing
    project_root = Path(__file__).parent.parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Test basic imports work
    try:
        import handlers
        import models
        import repositories
        import services
        import utils
    except ImportError as e:
        pytest.fail(f"Failed to import src packages: {e}")


def test_configuration_files_exist():
    """Test that essential configuration files exist."""
    project_root = Path(__file__).parent.parent

    config_files = [
        "serverless.yml",
        "requirements.txt",
        "requirements-dev.txt",
        "package.json",
        "pyproject.toml",
        ".gitignore",
        "README.md",
        ".pre-commit-config.yaml",
        "Makefile",
        ".env.example",
        "pytest.ini",
    ]

    for config_file in config_files:
        assert (
            project_root / config_file
        ).exists(), f"Missing configuration file: {config_file}"


def test_github_workflow_exists():
    """Test that GitHub Actions workflow exists."""
    project_root = Path(__file__).parent.parent
    workflow_file = project_root / ".github" / "workflows" / "deploy.yml"
    assert workflow_file.exists(), "Missing GitHub Actions workflow file"


def test_frontend_configuration_exists():
    """Test that frontend configuration files exist."""
    project_root = Path(__file__).parent.parent
    frontend_root = project_root / "frontend"

    frontend_files = [
        "package.json",
        "tsconfig.json",
        "public/index.html",
        "src/index.tsx",
        "src/App.tsx",
        "src/App.css",
        "src/index.css",
    ]

    for frontend_file in frontend_files:
        assert (
            frontend_root / frontend_file
        ).exists(), f"Missing frontend file: {frontend_file}"
