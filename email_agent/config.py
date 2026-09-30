"""Settings loading: ``config/settings.yaml`` overlaid with environment variables.

Every tunable threshold in the system comes from here. Nothing else may hardcode one — see
``docs/CONTRACTS.md`` section 4 for the frozen key list, and ticket P3-03, which is the only
ticket allowed to change the values.

Environment overrides
---------------------
``EA_`` + the dotted path, upper-cased, with ``.`` written as ``__``::

    EA_MATCH__MIN_SCORE=0.7     -> match.min_score
    EA_POLL__INTERVAL_SECONDS=60 -> poll.interval_seconds

Any ``EA_`` variable containing ``__`` must resolve to a known key, or loading fails. That is
deliberate: a silently ignored ``EA_MATCH__MIN_SCOR`` typo would mean running the pilot on the
wrong threshold and never knowing.

``EA_`` variables that are *not* settings (the mailbox address, the provider name, the resume
directory) are listed in ``RESERVED_ENV`` below. A new one is added there, so the set of
``EA_`` names stays visible in one place instead of accumulating unnoticed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "ConfigError",
    "Settings",
    "ClassifySettings",
    "MatchSettings",
    "DraftSettings",
    "PollSettings",
    "load_settings",
    "get_settings",
    "require_env",
    "REPO_ROOT",
    "DEFAULT_SETTINGS_PATH",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS_PATH = REPO_ROOT / "config" / "settings.yaml"

ENV_PREFIX = "EA_"
PATH_SEPARATOR = "__"

#: ``EA_`` variables that are locations or identifiers rather than tunable settings.
#: Documented in ``.env.example``. Add here when a ticket introduces a new one.
RESERVED_ENV = frozenset(
    {
        "EA_PROVIDER",
        "EA_MAILBOX_ADDRESS",
        "EA_RESUME_DIR",
    }
)


class ConfigError(Exception):
    """Raised at startup for a malformed, missing or unrecognised setting.

    Always raised eagerly during loading. A bad configuration must not survive to the point
    where it silently changes a threshold mid-run.
    """


# ---------- sections ----------


@dataclass(frozen=True)
class ClassifySettings:
    min_confidence: float


@dataclass(frozen=True)
class MatchSettings:
    min_score: float
    max_profiles: int
    rerank_pool: int
    hybrid_alpha: float


@dataclass(frozen=True)
class DraftSettings:
    max_words: int


@dataclass(frozen=True)
class PollSettings:
    interval_seconds: int


@dataclass(frozen=True)
class Settings:
    classify: ClassifySettings
    match: MatchSettings
    draft: DraftSettings
    poll: PollSettings

    def get(self, dotted_key: str) -> Any:
        """Look a setting up by its dotted path, e.g. ``settings.get("match.min_score")``.

        For sweeps and logging. Ordinary code uses the typed attributes.
        """
        section, _, name = dotted_key.partition(".")
        if not _valid_path(section, name):
            raise ConfigError(f"Unknown setting {dotted_key!r}. Known keys: {', '.join(known_keys())}")
        return getattr(getattr(self, section), name)

    def with_overrides(self, overrides: dict[str, Any]) -> Settings:
        """Return a copy with the given dotted keys replaced.

        This exists so P3-03's threshold sweep can vary a configuration without mutating the
        environment, which would leak between runs.
        """
        updated: dict[str, Any] = {}
        for dotted_key, value in overrides.items():
            section, _, name = dotted_key.partition(".")
            if not _valid_path(section, name):
                raise ConfigError(f"Unknown setting {dotted_key!r}")
            current = updated.get(section, getattr(self, section))
            field_type = _field_type(section, name)
            updated[section] = replace(current, **{name: _coerce(value, field_type, dotted_key)})
        candidate = replace(self, **updated)
        _validate(candidate)
        return candidate

    def as_dict(self) -> dict[str, Any]:
        """Flat ``{"match.min_score": 0.6, ...}`` view, for logging a config snapshot."""
        return {key: self.get(key) for key in known_keys()}


_SECTIONS: dict[str, type] = {
    "classify": ClassifySettings,
    "match": MatchSettings,
    "draft": DraftSettings,
    "poll": PollSettings,
}


def known_keys() -> list[str]:
    """Every valid dotted setting key, in declaration order."""
    return [f"{section}.{f.name}" for section, cls in _SECTIONS.items() for f in fields(cls)]


def _valid_path(section: str, name: str) -> bool:
    cls = _SECTIONS.get(section)
    return bool(cls) and name in {f.name for f in fields(cls)}


def _field_type(section: str, name: str) -> type:
    return {f.name: f.type for f in fields(_SECTIONS[section])}[name]


# ---------- coercion and validation ----------


def _coerce(value: Any, field_type: Any, where: str) -> Any:
    """Convert a YAML or environment value to the section field's declared type.

    ``field_type`` may arrive as a string when ``from __future__ import annotations`` is in
    effect, so compare by name rather than identity.
    """
    type_name = (
        field_type if isinstance(field_type, str) else getattr(field_type, "__name__", str(field_type))
    )

    try:
        if type_name == "bool":
            if isinstance(value, bool):
                return value
            lowered = str(value).strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
            raise ValueError(f"{value!r} is not a boolean")
        if type_name == "int":
            # Reject 0.5 rather than silently truncating it to 0.
            as_float = float(value)
            if as_float != int(as_float):
                raise ValueError(f"{value!r} is not a whole number")
            return int(as_float)
        if type_name == "float":
            return float(value)
        return str(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{where}: expected {type_name}, got {value!r} ({exc})") from exc


def _validate(settings: Settings) -> None:
    """Range and cross-field checks. Everything here would otherwise fail much later, in a
    place where the cause is no longer obvious."""
    problems: list[str] = []

    for key in ("classify.min_confidence", "match.min_score", "match.hybrid_alpha"):
        value = settings.get(key)
        if not 0.0 <= value <= 1.0:
            problems.append(f"{key} must be between 0.0 and 1.0, got {value}")

    if settings.match.max_profiles < 1:
        problems.append(f"match.max_profiles must be at least 1, got {settings.match.max_profiles}")
    if settings.match.rerank_pool < 1:
        problems.append(f"match.rerank_pool must be at least 1, got {settings.match.rerank_pool}")
    if settings.match.rerank_pool < settings.match.max_profiles:
        problems.append(
            "match.rerank_pool must be at least match.max_profiles "
            f"({settings.match.rerank_pool} < {settings.match.max_profiles}): the re-ranker "
            "cannot select more profiles than it is given"
        )
    if settings.draft.max_words < 1:
        problems.append(f"draft.max_words must be at least 1, got {settings.draft.max_words}")
    if settings.poll.interval_seconds < 1:
        problems.append(f"poll.interval_seconds must be at least 1, got {settings.poll.interval_seconds}")

    if problems:
        raise ConfigError("Invalid settings:\n  - " + "\n  - ".join(problems))


# ---------- loading ----------


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Settings file not found: {path}")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Could not parse {path}: {exc}") from exc
    if loaded is None:
        raise ConfigError(f"Settings file is empty: {path}")
    if not isinstance(loaded, dict):
        raise ConfigError(f"Settings file must be a mapping, got {type(loaded).__name__}: {path}")
    return loaded


def _collect_env_overrides(environ: dict[str, str]) -> dict[str, str]:
    """Map ``EA_MATCH__MIN_SCORE`` to ``match.min_score``, rejecting anything unrecognised."""
    overrides: dict[str, str] = {}

    for name, value in environ.items():
        if not name.startswith(ENV_PREFIX):
            continue
        if name in RESERVED_ENV:
            continue

        remainder = name[len(ENV_PREFIX) :]
        if PATH_SEPARATOR not in remainder:
            # No separator, and not reserved. Catch the common case of writing EA_MATCH when
            # EA_MATCH__MIN_SCORE was meant, rather than ignoring it.
            raise ConfigError(
                f"Unrecognised environment variable {name!r}. Setting overrides are written "
                f"{ENV_PREFIX}SECTION{PATH_SEPARATOR}KEY, for example EA_MATCH__MIN_SCORE. "
                f"Non-setting {ENV_PREFIX} variables must be listed in RESERVED_ENV."
            )

        section, _, key = remainder.partition(PATH_SEPARATOR)
        dotted_key = f"{section.lower()}.{key.lower()}"
        if not _valid_path(section.lower(), key.lower()):
            raise ConfigError(
                f"Environment variable {name!r} does not match any setting "
                f"(resolved to {dotted_key!r}). Known keys: {', '.join(known_keys())}"
            )
        overrides[dotted_key] = value

    return overrides


def load_settings(
    path: Path | str | None = None,
    environ: dict[str, str] | None = None,
) -> Settings:
    """Load settings from YAML, overlay environment variables, validate, and return.

    Both the path and the environment are arguments so tests never have to mutate global state.
    """
    settings_path = Path(path) if path is not None else DEFAULT_SETTINGS_PATH
    env = dict(os.environ) if environ is None else dict(environ)

    raw = _read_yaml(settings_path)

    unknown_sections = set(raw) - set(_SECTIONS)
    if unknown_sections:
        raise ConfigError(
            f"Unknown section(s) in {settings_path}: {', '.join(sorted(unknown_sections))}. "
            f"Known sections: {', '.join(_SECTIONS)}"
        )

    sections: dict[str, Any] = {}
    for section_name, section_cls in _SECTIONS.items():
        section_raw = raw.get(section_name)
        if section_raw is None:
            raise ConfigError(f"Missing section {section_name!r} in {settings_path}")
        if not isinstance(section_raw, dict):
            raise ConfigError(f"Section {section_name!r} must be a mapping in {settings_path}")

        expected = {f.name for f in fields(section_cls)}
        unknown = set(section_raw) - expected
        if unknown:
            raise ConfigError(
                f"Unknown key(s) in section {section_name!r} of {settings_path}: "
                f"{', '.join(sorted(unknown))}. Known keys: {', '.join(sorted(expected))}"
            )
        missing = expected - set(section_raw)
        if missing:
            raise ConfigError(
                f"Missing key(s) in section {section_name!r} of {settings_path}: "
                f"{', '.join(sorted(missing))}"
            )

        values = {
            f.name: _coerce(section_raw[f.name], f.type, f"{section_name}.{f.name}")
            for f in fields(section_cls)
        }
        sections[section_name] = section_cls(**values)

    settings = Settings(**sections)

    overrides = _collect_env_overrides(env)
    if overrides:
        settings = settings.with_overrides(overrides)
    else:
        _validate(settings)

    return settings


_cached: Settings | None = None


def get_settings(reload: bool = False) -> Settings:
    """Process-wide settings, loaded once.

    Long-running code (the polling loop) uses this. Tests use ``load_settings`` directly with an
    explicit path and environment, so they never touch this cache.
    """
    global _cached
    if _cached is None or reload:
        _cached = load_settings()
    return _cached


def require_env(name: str, environ: dict[str, str] | None = None) -> str:
    """Read a required secret from the environment, or fail with a message naming the file.

    Secrets live in ``.env`` (gitignored); the names are documented in ``.env.example``.
    """
    env = os.environ if environ is None else environ
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"Required environment variable {name!r} is not set. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


def load_dotenv_if_present(path: Path | str | None = None) -> bool:
    """Load ``.env`` into ``os.environ`` if the file and python-dotenv are both available.

    Entry points call this; library code does not. Returns whether anything was loaded.
    """
    env_path = Path(path) if path is not None else REPO_ROOT / ".env"
    if not env_path.is_file():
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dotenv is a declared dependency
        return False
    return bool(load_dotenv(env_path, override=False))
