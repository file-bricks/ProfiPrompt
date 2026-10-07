"""Read the application version from the project metadata."""

import re
import sys
from pathlib import Path


def _project_metadata_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "pyproject.toml"
    return Path(__file__).resolve().parents[1] / "pyproject.toml"


def get_version() -> str:
    metadata = _project_metadata_path().read_text(encoding="utf-8")
    project_section = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", metadata)
    if project_section is None:
        raise ValueError("pyproject.toml has no [project] section")
    match = re.search(r'^version\s*=\s*"([^\"]+)"\s*$', project_section.group(1), re.MULTILINE)
    if match is None:
        raise ValueError("pyproject.toml has no project version")
    return match.group(1)


__version__ = get_version()
