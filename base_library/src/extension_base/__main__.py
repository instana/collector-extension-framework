# (c) Copyright IBM Corp. 2026
"""
Main entry point for the extension base library.

Allows the package to be run as a module for smoke-testing and container
startup verification::

    python -m extension_base
"""

import sys

from extension_base.logging import setup_logging

logger = setup_logging()


def main() -> int:
    """Verify imports and log basic runtime info."""
    from extension_base import __version__

    logger.info("Instana Collector Extension Base Library")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Extension Base Library version: {__version__}")
    logger.info("All imports successful — extension base library is ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
