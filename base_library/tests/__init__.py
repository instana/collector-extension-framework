# (c) Copyright IBM Corp. 2026
"""
Test suite for Extension Base Library.

This test suite follows Test-Driven Development (TDD) principles:
- Tests are written BEFORE implementation
- All tests initially FAIL (red phase)
- Implementation makes tests PASS (green phase)
- Code is refactored while keeping tests passing (refactor phase)

Test Organization:
- test_project_structure.py: Project setup validation (FR1)
- test_exceptions.py: Exception hierarchy tests (FR10)
- test_config_loader.py: Configuration loading tests (FR2)
- test_credentials_manager.py: Credential handling tests (FR3)
- test_metrics_emitter.py: Metrics emission tests (FR4)
- test_health_reporter.py: Health reporting tests (FR5)
- test_lifecycle_manager.py: Lifecycle management tests (FR6)
- test_extension_base.py: Main API tests (FR7)
- test_integration.py: Integration tests (FR7)
- test_logging.py: Logging module tests (FR9)

Coverage Requirements:
- Overall: 80% line coverage minimum
- Core components: 90% line coverage minimum
- Total test count: 107 test functions
"""

# Made with Bob
