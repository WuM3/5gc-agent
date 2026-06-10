from __future__ import annotations

import os
from pathlib import Path

_LOADED_ENV_VALUES: dict[str, str] = {}
_LOADED_ENV_SOURCES: dict[str, Path] = {}


def load_env_file(path: str | Path | None = None) -> bool:
    if os.getenv("LLM_DISABLE_ENV_FILE", "").strip().lower() in {"1", "true", "yes"}:
        return False

    env_path = _resolve_env_path(path)
    if env_path is None or not env_path.exists():
        return False
    env_path = env_path.resolve()

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _clean_value(value)
        if key and _should_set_env_value(key, env_path):
            os.environ[key] = value
            _LOADED_ENV_VALUES[key] = value
            _LOADED_ENV_SOURCES[key] = env_path

    return True


def _resolve_env_path(path: str | Path | None) -> Path | None:
    if path is not None:
        return Path(path)

    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _clean_value(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned


def _should_set_env_value(key: str, env_path: Path) -> bool:
    if key not in os.environ:
        return True
    if not os.environ[key].strip():
        return True
    return (
        os.environ[key] == _LOADED_ENV_VALUES.get(key)
        and _LOADED_ENV_SOURCES.get(key) == env_path
    )
