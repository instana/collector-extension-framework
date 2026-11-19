# (c) Copyright IBM Corp. 2026
"""
Tests for FR1: Project Structure and Configuration.

This module validates the Extension Base Library project structure,
pytest configuration, and module imports.

Tests:
- test_project_structure: Validates directory layout
- test_pytest_configuration: Validates pyproject.toml settings
- test_import_extension_base: Verifies module imports work

Spec Reference: docs/specs/extension-base-library.md#library-architecture (lines 96-193)
"""

import sys
from pathlib import Path

import pytest
import tomli


class TestProjectStructure:
    """Test suite for project structure validation (FR1)."""

    def test_project_structure(self):
        """
        Test that project directory structure matches specification.

        Spec Reference: docs/specs/extension-base-library.md#deployment
        - Directory Structure (lines 1368-1383)

        Validates:
        - base_library/ root exists
        - src/extension_base/ source directory exists
        - tests/ test directory exists
        - tests/mocks/ mock objects directory exists
        - pyproject.toml configuration file exists
        - README.md documentation exists

        Expected: All directories and files exist (TDD red phase - will fail)
        """
        # Get project root (base_library/)
        project_root = Path(__file__).parent.parent

        # Validate root directory
        assert project_root.exists(), "Project root directory must exist"
        assert project_root.name == "base_library", (
            "Project root must be named 'base_library'"
        )

        # Validate source directory structure
        src_dir = project_root / "src"
        assert src_dir.exists(), "src/ directory must exist"

        extension_base_dir = src_dir / "extension_base"
        assert extension_base_dir.exists(), (
            "src/extension_base/ directory must exist"
        )
        assert (extension_base_dir / "__init__.py").exists(), (
            "src/extension_base/__init__.py must exist"
        )

        # Validate source module structure
        expected_modules = [
            "core.py",
            "logging.py",
            "exceptions.py",
        ]
        for module in expected_modules:
            module_path = extension_base_dir / module
            assert module_path.exists(), f"Module {module} must exist"

        # Validate source subdirectories
        expected_subdirs = [
            "config",
            "metrics",
            "health",
            "lifecycle",
        ]
        for subdir in expected_subdirs:
            subdir_path = extension_base_dir / subdir
            assert subdir_path.exists(), f"Subdirectory {subdir}/ must exist"
            assert (subdir_path / "__init__.py").exists(), (
                f"{subdir}/__init__.py must exist"
            )

        # Validate test directory structure
        tests_dir = project_root / "tests"
        assert tests_dir.exists(), "tests/ directory must exist"
        assert (tests_dir / "__init__.py").exists(), (
            "tests/__init__.py must exist"
        )

        mocks_dir = tests_dir / "mocks"
        assert mocks_dir.exists(), "tests/mocks/ directory must exist"
        assert (mocks_dir / "__init__.py").exists(), (
            "tests/mocks/__init__.py must exist"
        )

        # Validate mock files
        expected_mocks = [
            "mock_otlp.py",
            "mock_config.py",
            "mock_credentials.py",
        ]
        for mock_file in expected_mocks:
            mock_path = mocks_dir / mock_file
            assert mock_path.exists(), f"Mock file {mock_file} must exist"

        # Validate conftest.py
        conftest_path = tests_dir / "conftest.py"
        assert conftest_path.exists(), "tests/conftest.py must exist"

        # Validate project files
        assert (project_root / "pyproject.toml").exists(), (
            "pyproject.toml must exist"
        )
        assert (project_root / "README.md").exists(), "README.md must exist"

    def test_pytest_configuration(self):
        """
        Test that pytest configuration in pyproject.toml is correct.

        Spec Reference: docs/specs/extension-base-library.md#testing-strategy
        - Test Coverage Requirements (lines 1231-1267)

        Validates:
        - pyproject.toml exists and is valid TOML
        - [tool.pytest.ini_options] section exists
        - testpaths includes "tests"
        - python_files pattern is "test_*.py"
        - python_classes pattern is "Test*"
        - python_functions pattern is "test_*"
        - Coverage settings are configured
        - Minimum coverage threshold is 80%

        Expected: Configuration matches specification (TDD red phase - will fail)
        """
        # Get project root
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / "pyproject.toml"

        # Load pyproject.toml
        assert pyproject_path.exists(), "pyproject.toml must exist"

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)

        # Validate pytest configuration section exists
        assert "tool" in pyproject_data, (
            "pyproject.toml must have [tool] section"
        )
        assert "pytest" in pyproject_data["tool"], (
            "pyproject.toml must have [tool.pytest] section"
        )
        assert "ini_options" in pyproject_data["tool"]["pytest"], (
            "pyproject.toml must have [tool.pytest.ini_options] section"
        )

        pytest_config = pyproject_data["tool"]["pytest"]["ini_options"]

        # Validate test discovery settings
        assert "testpaths" in pytest_config, (
            "pytest config must specify testpaths"
        )
        testpaths = pytest_config["testpaths"]
        if isinstance(testpaths, str):
            testpaths = [testpaths]
        assert "tests" in testpaths, "testpaths must include 'tests' directory"

        assert "python_files" in pytest_config, (
            "pytest config must specify python_files pattern"
        )
        assert "test_*.py" in pytest_config["python_files"], (
            "python_files must include 'test_*.py' pattern"
        )

        assert "python_classes" in pytest_config, (
            "pytest config must specify python_classes pattern"
        )
        assert "Test*" in pytest_config["python_classes"], (
            "python_classes must include 'Test*' pattern"
        )

        assert "python_functions" in pytest_config, (
            "pytest config must specify python_functions pattern"
        )
        assert "test_*" in pytest_config["python_functions"], (
            "python_functions must include 'test_*' pattern"
        )

        # Validate coverage settings
        assert "addopts" in pytest_config, "pytest config must specify addopts"
        addopts = pytest_config["addopts"]

        # Check for coverage options (may be --cov or --cov=<source>)
        has_cov = any(opt.startswith("--cov") for opt in addopts)
        assert has_cov, (
            "pytest must be configured with --cov or --cov=<source>"
        )

        has_cov_report = any(opt.startswith("--cov-report") for opt in addopts)
        assert has_cov_report, "pytest must be configured with --cov-report"

        # Validate coverage configuration
        assert "coverage" in pyproject_data["tool"], (
            "pyproject.toml must have [tool.coverage] section"
        )

        coverage_config = pyproject_data["tool"]["coverage"]

        # Validate coverage report settings
        assert "report" in coverage_config, (
            "coverage config must have report section"
        )
        report_config = coverage_config["report"]

        assert "fail_under" in report_config, (
            "coverage report must specify fail_under threshold"
        )
        fail_under = report_config["fail_under"]
        assert fail_under >= 80, "coverage threshold must be at least 80%"

        # Validate coverage run settings
        assert "run" in coverage_config, (
            "coverage config must have run section"
        )
        run_config = coverage_config["run"]

        assert "source" in run_config, "coverage run must specify source"
        sources = run_config["source"]
        if isinstance(sources, str):
            sources = [sources]
        assert (
            "extension_base" in sources or "src/extension_base" in sources
        ), "coverage source must include extension_base"

    def test_import_extension_base(self):
        """
        Test that extension_base module can be imported.

        Spec Reference: docs/specs/extension-base-library.md#deployment
        - Python Path (lines 1384-1391)
        - Installation (lines 1359-1367)

        Validates:
        - extension_base package is importable
        - src/extension_base is in Python path
        - __init__.py is valid Python
        - No import errors occur

        Expected: Module imports successfully (TDD red phase - will fail if not in path)
        """
        # Get project root and add src to path if needed
        project_root = Path(__file__).parent.parent
        src_dir = project_root / "src"

        # Ensure src is in Python path
        src_str = str(src_dir)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)

        # Attempt to import extension_base
        try:
            import extension_base

            # Validate module has expected attributes
            assert hasattr(extension_base, "__file__"), (
                "extension_base module must have __file__ attribute"
            )
            assert hasattr(extension_base, "__path__"), (
                "extension_base must be a package (have __path__)"
            )

            # Validate module location
            module_file = Path(extension_base.__file__)
            assert module_file.exists(), (
                "extension_base module file must exist"
            )
            assert "extension_base" in str(module_file), (
                "extension_base module must be in extension_base directory"
            )

        except ImportError as e:
            pytest.fail(f"Failed to import extension_base: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing extension_base: {e}")


# Made with Bob
