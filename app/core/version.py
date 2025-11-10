"""Version management for the application.

This module provides utilities to retrieve the application version
dynamically from package metadata (managed by Hatch-VCS) or from
environment variables in containerized environments.
"""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version


def get_app_version() -> str:
    """Retrieve the application version from package metadata or environment.

    Priority order:
    1. APP_VERSION environment variable (for Docker/CI environments)
    2. Package metadata via importlib.metadata (derived from Git tags by Hatch-VCS)
    3. Fallback to "0.0.0-dev" for untagged development environments

    Returns:
        str: Semantic version string (e.g., "1.2.3" or "0.0.0-dev")

    Examples:
        >>> get_app_version()  # In a tagged release
        '1.2.3'
        >>> get_app_version()  # In development without tags
        '0.0.0-dev'
    """
    # Check environment variable first (Docker/CI override)
    env_version = os.getenv("APP_VERSION")
    if env_version:
        return env_version

    # Try to get version from package metadata (Hatch-VCS)
    try:
        return version("fastapi-template")
    except PackageNotFoundError:
        # Fallback for dev mode or untagged commits
        return "0.0.0-dev"


__all__ = ["get_app_version"]
