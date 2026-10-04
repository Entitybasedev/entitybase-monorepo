"""Application version constants."""

import os
import tomllib
from importlib.metadata import version
from pathlib import Path

from typing import Any


def _pyproject_candidates() -> list[Path]:
    """Paths that may hold the backend's pyproject.toml, most specific first.

    A worker's own directory has a pyproject.toml too, so the order matters:
    the backend's file has to win over whatever the current directory holds.
    """
    return [
        Path("/app/pyproject.toml"),
        Path(__file__).parent.parent.parent.parent / "pyproject.toml",
        # Layout of a worker image, which copies the backend next to itself
        Path("/app/entitybase-backend/pyproject.toml"),
        # Layout of a monorepo checkout, when running a worker from its dir
        Path("../entitybase-backend/pyproject.toml"),
        Path.cwd() / "pyproject.toml",
    ]


def get_pyproject_path() -> Path:
    """Get path to pyproject.toml based on environment."""
    possible_paths = _pyproject_candidates()
    for path in possible_paths:
        if path.exists():
            return path
    raise FileNotFoundError(f"pyproject.toml not found in any of: {possible_paths}")


def _read_api_version() -> str | None:
    """Read the api_version from the first pyproject.toml that declares one.

    Returns None when no candidate declares it, rather than blowing up on an
    unrelated pyproject.toml that happens to sit in the working directory.
    """
    for path in _pyproject_candidates():
        if not path.exists():
            continue
        try:
            with open(path, "rb") as f:
                data: Any = tomllib.load(f)
            api_version = data.get("project", {}).get("api_version")
            if api_version:
                return str(api_version)
        except Exception:
            continue
    return None


def get_release_version() -> str:
    """Get release version from pyproject.toml."""
    try:
        return version("entitybase-backend")
    except Exception:
        pass

    try:
        pyproject_path = get_pyproject_path()
        with open(pyproject_path, "rb") as f:
            data: Any = tomllib.load(f)
        raw_version: str = data["project"]["version"]
        return raw_version.lstrip("v")
    except Exception:
        raise RuntimeError(
            "Could not determine release version. "
            "Either install the package ('uv sync') or ensure pyproject.toml is readable."
        )


def get_api_version() -> str:
    """Get full API version (api_version.release_version) from pyproject.toml."""
    api_version = _read_api_version()
    if api_version is None:
        raise RuntimeError(
            "Could not determine API version. Ensure the backend's pyproject.toml "
            "is readable and declares 'api_version' in [project]."
        )
    return f"{api_version}.{get_release_version()}"


def get_entitybase_version() -> str:
    """Get entitybase version from pyproject.toml."""
    return get_release_version()


API_VERSION = get_api_version()
ENTITYBASE_VERSION = get_entitybase_version()
