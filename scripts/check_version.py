"""Assert the version in ``pyproject.toml`` matches ``__version__`` in the package.

Run from the repository root::

    python scripts/check_version.py

Exits 0 when the two versions agree, 1 (with a diagnostic on stderr) when they
diverge. Used by CI to stop a release where the packaging metadata and the runtime
``mcp_cassette.__version__`` have drifted apart.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
INIT = ROOT / "src" / "mcp_cassette" / "__init__.py"

_VERSION_RE = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.MULTILINE)


def pyproject_version() -> str:
    """Return ``project.version`` from ``pyproject.toml``."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def package_version() -> str:
    """Return ``__version__`` declared in the package ``__init__``."""
    match = _VERSION_RE.search(INIT.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"no __version__ assignment found in {INIT}")
    return match.group(1)


def main() -> int:
    """Compare the two versions and report the outcome."""
    pyproject = pyproject_version()
    package = package_version()
    if pyproject != package:
        sys.stderr.write(
            "version mismatch:\n"
            f"  pyproject.toml           -> {pyproject}\n"
            f"  mcp_cassette.__version__ -> {package}\n"
            "Update both to the same value before releasing.\n"
        )
        return 1
    print(f"version OK: {pyproject}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
