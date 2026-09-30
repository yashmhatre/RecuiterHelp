"""Tests for P0-01's settings loader.

Every test passes its own settings path and its own environment dict, so nothing here reads
``os.environ`` or the repo's real ``config/settings.yaml`` unless it says so explicitly.
"""

from __future__ import annotations

import dataclasses
import textwrap
from pathlib import Path

import pytest

from email_agent.config import (
    DEFAULT_SETTINGS_PATH,
    ConfigError,
    Settings,
    known_keys,
    load_settings,
    require_env,
)

# The documented defaults from docs/CONTRACTS.md section 4. If this table and the contract ever
# disagree, the contract wins and this test is the thing that catches the drift.
CONTRACT_DEFAULTS = {
    "classify.min_confidence": 0.75,
    "match.min_score": 0.60,
    "match.max_profiles": 3,
    "match.rerank_pool": 10,
    "match.hybrid_alpha": 0.6,
    "draft.max_words": 200,
    "poll.interval_seconds": 120,
}

VALID_YAML = textwrap.dedent(
    """
    classify:
      min_confidence: 0.75
    match:
      min_score: 0.60
      max_profiles: 3
      rerank_pool: 10
      hybrid_alpha: 0.6
    draft:
      max_words: 200
    poll:
      interval_seconds: 120
    """
)


@pytest.fixture
def settings_file(tmp_path: Path) -> Path:
    path = tmp_path / "settings.yaml"
    path.write_text(VALID_YAML, encoding="utf-8")
    return path


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "settings.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


# ---------- defaults ----------


def test_shipped_settings_file_matches_the_contract_defaults():
    """The committed config/settings.yaml carries exactly the section 4 values."""
    settings = load_settings(DEFAULT_SETTINGS_PATH, environ={})

    for key, expected in CONTRACT_DEFAULTS.items():
        assert settings.get(key) == pytest.approx(expected), f"{key} drifted from the contract"


def test_every_contract_key_is_known_and_nothing_extra_is():
    assert set(known_keys()) == set(CONTRACT_DEFAULTS)


def test_typed_accessors_return_the_declared_types(settings_file: Path):
    settings = load_settings(settings_file, environ={})

    assert isinstance(settings.classify.min_confidence, float)
    assert isinstance(settings.match.max_profiles, int)
    assert isinstance(settings.match.rerank_pool, int)
    assert isinstance(settings.match.hybrid_alpha, float)
    assert isinstance(settings.draft.max_words, int)
    assert isinstance(settings.poll.interval_seconds, int)


def test_as_dict_is_a_flat_snapshot(settings_file: Path):
    """P3-01 logs this alongside each eval run, so it must cover every key."""
    assert load_settings(settings_file, environ={}).as_dict() == pytest.approx(CONTRACT_DEFAULTS)


# ---------- environment overrides ----------


def test_env_override_changes_the_value(settings_file: Path):
    settings = load_settings(settings_file, environ={"EA_MATCH__MIN_SCORE": "0.8"})

    assert settings.match.min_score == pytest.approx(0.8)
    # Untouched keys keep their file values.
    assert settings.match.max_profiles == 3


def test_env_override_is_coerced_to_the_declared_type(settings_file: Path):
    settings = load_settings(settings_file, environ={"EA_POLL__INTERVAL_SECONDS": "300"})

    assert settings.poll.interval_seconds == 300
    assert isinstance(settings.poll.interval_seconds, int)


def test_env_override_is_case_insensitive_in_the_key_part(settings_file: Path):
    settings = load_settings(settings_file, environ={"EA_DRAFT__MAX_WORDS": "150"})

    assert settings.draft.max_words == 150


def test_several_overrides_apply_together(settings_file: Path):
    settings = load_settings(
        settings_file,
        environ={"EA_MATCH__MIN_SCORE": "0.5", "EA_CLASSIFY__MIN_CONFIDENCE": "0.9"},
    )

    assert settings.match.min_score == pytest.approx(0.5)
    assert settings.classify.min_confidence == pytest.approx(0.9)


def test_unknown_env_key_raises_at_startup(settings_file: Path):
    """A silently ignored typo here means running on the wrong threshold and never knowing."""
    with pytest.raises(ConfigError, match="does not match any setting"):
        load_settings(settings_file, environ={"EA_MATCH__MIN_SCOR": "0.8"})


def test_unknown_env_section_raises(settings_file: Path):
    with pytest.raises(ConfigError, match="does not match any setting"):
        load_settings(settings_file, environ={"EA_BOGUS__THING": "1"})


def test_ea_variable_without_a_separator_raises(settings_file: Path):
    with pytest.raises(ConfigError, match="Unrecognised environment variable"):
        load_settings(settings_file, environ={"EA_MATCH": "0.8"})


def test_reserved_non_setting_env_variables_are_left_alone(settings_file: Path):
    """The mailbox address and provider name are EA_ variables but not settings."""
    settings = load_settings(
        settings_file,
        environ={
            "EA_PROVIDER": "gmail",
            "EA_MAILBOX_ADDRESS": "someone@example.com",
            "EA_RESUME_DIR": "resumes",
        },
    )

    assert settings.match.min_score == pytest.approx(0.60)


def test_non_ea_environment_variables_are_ignored(settings_file: Path):
    settings = load_settings(settings_file, environ={"DATABASE_URL": "postgresql://x", "PATH": "/usr/bin"})

    assert settings.match.min_score == pytest.approx(0.60)


def test_env_override_with_the_wrong_type_raises(settings_file: Path):
    with pytest.raises(ConfigError, match="expected float"):
        load_settings(settings_file, environ={"EA_MATCH__MIN_SCORE": "not-a-number"})


def test_fractional_value_for_an_int_key_raises_rather_than_truncating(settings_file: Path):
    with pytest.raises(ConfigError, match="not a whole number"):
        load_settings(settings_file, environ={"EA_MATCH__MAX_PROFILES": "2.5"})


# ---------- malformed files ----------


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "nope.yaml", environ={})


def test_empty_file_raises(tmp_path: Path):
    path = tmp_path / "settings.yaml"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ConfigError, match="empty"):
        load_settings(path, environ={})


def test_unknown_key_in_the_file_raises(tmp_path: Path):
    path = write(
        tmp_path,
        """
        classify:
          min_confidence: 0.75
          temperature: 0.2
        match:
          min_score: 0.6
          max_profiles: 3
          rerank_pool: 10
          hybrid_alpha: 0.6
        draft:
          max_words: 200
        poll:
          interval_seconds: 120
        """,
    )

    with pytest.raises(ConfigError, match="temperature"):
        load_settings(path, environ={})


def test_unknown_section_in_the_file_raises(tmp_path: Path):
    path = write(
        tmp_path,
        """
        classify:
          min_confidence: 0.75
        match:
          min_score: 0.6
          max_profiles: 3
          rerank_pool: 10
          hybrid_alpha: 0.6
        draft:
          max_words: 200
        poll:
          interval_seconds: 120
        mystery:
          thing: 1
        """,
    )

    with pytest.raises(ConfigError, match="mystery"):
        load_settings(path, environ={})


def test_missing_key_raises_and_names_it(tmp_path: Path):
    path = write(
        tmp_path,
        """
        classify:
          min_confidence: 0.75
        match:
          min_score: 0.6
          max_profiles: 3
          rerank_pool: 10
        draft:
          max_words: 200
        poll:
          interval_seconds: 120
        """,
    )

    with pytest.raises(ConfigError, match="hybrid_alpha"):
        load_settings(path, environ={})


def test_missing_section_raises_and_names_it(tmp_path: Path):
    path = write(
        tmp_path,
        """
        classify:
          min_confidence: 0.75
        match:
          min_score: 0.6
          max_profiles: 3
          rerank_pool: 10
          hybrid_alpha: 0.6
        draft:
          max_words: 200
        """,
    )

    with pytest.raises(ConfigError, match="poll"):
        load_settings(path, environ={})


# ---------- range and cross-field validation ----------


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("EA_CLASSIFY__MIN_CONFIDENCE", "1.5"),
        ("EA_CLASSIFY__MIN_CONFIDENCE", "-0.1"),
        ("EA_MATCH__MIN_SCORE", "2"),
        ("EA_MATCH__HYBRID_ALPHA", "1.2"),
    ],
)
def test_out_of_range_probabilities_raise(settings_file: Path, key: str, value: str):
    with pytest.raises(ConfigError, match="between 0.0 and 1.0"):
        load_settings(settings_file, environ={key: value})


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("EA_MATCH__MAX_PROFILES", "0"),
        ("EA_DRAFT__MAX_WORDS", "0"),
        ("EA_POLL__INTERVAL_SECONDS", "0"),
    ],
)
def test_non_positive_counts_raise(settings_file: Path, key: str, value: str):
    with pytest.raises(ConfigError, match="must be at least 1"):
        load_settings(settings_file, environ={key: value})


def test_rerank_pool_smaller_than_max_profiles_raises(settings_file: Path):
    """The re-ranker cannot select more profiles than it is handed."""
    with pytest.raises(ConfigError, match="rerank_pool must be at least"):
        load_settings(settings_file, environ={"EA_MATCH__RERANK_POOL": "2", "EA_MATCH__MAX_PROFILES": "3"})


# ---------- with_overrides, used by the P3-03 sweep ----------


def test_with_overrides_returns_a_new_settings_object(settings_file: Path):
    original = load_settings(settings_file, environ={})
    tuned = original.with_overrides({"match.min_score": 0.85})

    assert tuned.match.min_score == pytest.approx(0.85)
    assert original.match.min_score == pytest.approx(0.60), "the original must not be mutated"


def test_with_overrides_validates_the_result(settings_file: Path):
    original = load_settings(settings_file, environ={})

    with pytest.raises(ConfigError, match="between 0.0 and 1.0"):
        original.with_overrides({"match.min_score": 3.0})


def test_with_overrides_rejects_an_unknown_key(settings_file: Path):
    original = load_settings(settings_file, environ={})

    with pytest.raises(ConfigError, match="Unknown setting"):
        original.with_overrides({"match.nonexistent": 1})


def test_get_rejects_an_unknown_key(settings_file: Path):
    settings = load_settings(settings_file, environ={})

    with pytest.raises(ConfigError, match="Unknown setting"):
        settings.get("match.nope")


def test_settings_are_frozen(settings_file: Path):
    """Nothing may edit a threshold at runtime. P3-03 tunes by loading a new Settings."""
    settings = load_settings(settings_file, environ={})

    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.match.min_score = 0.1  # type: ignore[misc]


# ---------- secrets ----------


def test_require_env_returns_the_value():
    assert require_env("SOME_SECRET", environ={"SOME_SECRET": "abc"}) == "abc"


@pytest.mark.parametrize("value", ["", "   "])
def test_require_env_rejects_missing_or_blank_and_points_at_the_env_file(value: str):
    with pytest.raises(ConfigError, match=r"\.env\.example"):
        require_env("SOME_SECRET", environ={"SOME_SECRET": value})


def test_require_env_rejects_an_absent_variable():
    with pytest.raises(ConfigError, match="not set"):
        require_env("SOME_SECRET", environ={})


# ---------- repo hygiene ----------


def test_env_example_is_committed_and_env_is_ignored():
    """Requirement: secrets never reach the repository."""
    repo_root = DEFAULT_SETTINGS_PATH.parent.parent

    assert (repo_root / ".env.example").is_file()

    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    assert "!.env.example" in gitignore


def test_env_example_documents_every_reserved_ea_variable():
    """A reserved EA_ name that is not in .env.example is invisible to whoever deploys this."""
    from email_agent.config import RESERVED_ENV

    repo_root = DEFAULT_SETTINGS_PATH.parent.parent
    env_example = (repo_root / ".env.example").read_text(encoding="utf-8")

    for name in sorted(RESERVED_ENV):
        assert name in env_example, f"{name} is reserved in config.py but absent from .env.example"


def test_settings_object_is_importable_as_a_type():
    assert isinstance(load_settings(DEFAULT_SETTINGS_PATH, environ={}), Settings)
