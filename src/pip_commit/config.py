"""Load pip-commit configuration from pyproject.toml or .pip-commit.toml."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - py39/py310 fallback
    import tomli as tomllib  # type: ignore[import-not-found]


@dataclass(frozen=True)
class Config:
    output: str = "requirements.txt"
    exclude: tuple[str, ...] = ()
    require_venv: bool = True
    prompt: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        return cls(
            output=str(data.get("output", "requirements.txt")),
            exclude=tuple(str(x) for x in data.get("exclude", [])),
            require_venv=bool(data.get("require_venv", True)),
            prompt=bool(data.get("prompt", True)),
        )


def _read_toml(path: Path) -> dict:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def load_config(repo_root: Path, overrides: dict | None = None) -> Config:
    """Load config from `.pip-commit.toml` or `[tool.pip-commit]` in pyproject.toml.

    Standalone `.pip-commit.toml` takes precedence. CLI `overrides` win over both.
    """
    data: dict = {}

    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        section = _read_toml(pyproject).get("tool", {}).get("pip-commit", {})
        if isinstance(section, dict):
            data.update(section)

    standalone = repo_root / ".pip-commit.toml"
    if standalone.is_file():
        section = _read_toml(standalone)
        if isinstance(section, dict):
            data.update(section)

    if overrides:
        data.update({k: v for k, v in overrides.items() if v is not None})

    return Config.from_dict(data)


__all__ = ["Config", "load_config"]
