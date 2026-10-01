"""Tests for eval/validate_dataset.py — the labelled-email-dataset validator.

Covers: schema validation, duplicate ID detection, conditional expected_profile_ids,
intent coverage, non-recruiter share, and count range checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.validate_dataset import load_schema, validate_dataset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent


def _minimal_record(**overrides) -> dict:
    """Return a valid record with sensible defaults, overridable by keyword."""
    base = {
        "id": "test-001",
        "provider": "gmail",
        "headers": {
            "authentication-results": (
                "mx.google.com; spf=pass smtp.mailfrom=recruiter@corp.example.com; "
                "dkim=pass header.d=corp.example.com; dmarc=pass header.from=corp.example.com"
            ),
            "from": "Recruiter <recruiter@corp.example.com>",
        },
        "subject": "Python Developer — Pune",
        "body_text": "We have an opening for a Python Developer, 5+ years.",
        "is_recruiter": True,
        "intent": "new_requirement",
        "fields": {
            "role": "Python Developer",
            "skills": ["python"],
            "min_years_experience": 5.0,
            "location": "Pune",
            "candidate_names": [],
            "resume_requested": False,
        },
        "expected_profile_ids": [1],
        "notes": "",
    }
    base.update(overrides)
    return base


def _write_jsonl(tmp_path: Path, records: list[dict], filename: str = "test.jsonl") -> Path:
    """Write records as JSONL and return the file path."""
    path = tmp_path / filename
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    return path


# ---------------------------------------------------------------------------
# P1-05a: Schema loads and is valid
# ---------------------------------------------------------------------------


class TestSchemaLoading:
    def test_schema_loads(self):
        schema = load_schema()
        assert schema["title"] == "LabelledEmailRecord"
        assert "properties" in schema

    def test_schema_has_required_fields(self):
        schema = load_schema()
        required = set(schema["required"])
        expected = {
            "id", "provider", "headers", "subject", "body_text",
            "is_recruiter", "intent", "fields", "expected_profile_ids", "notes",
        }
        assert required == expected


# ---------------------------------------------------------------------------
# P1-05b: Example dataset validates
# ---------------------------------------------------------------------------


class TestExampleDataset:
    EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "eval" / "dataset" / "labels.example.jsonl"

    def test_example_dataset_validates(self):
        """The committed labels.example.jsonl must pass validation (with count check off)."""
        result = validate_dataset(self.EXAMPLE_PATH, check_count=False)
        assert result.ok, "Example dataset has errors:\n" + "\n".join(result.errors)

    def test_example_dataset_has_all_intents(self):
        result = validate_dataset(self.EXAMPLE_PATH, check_count=False)
        assert not result.missing_intents, (
            f"Example dataset missing intents: {result.missing_intents}"
        )

    def test_example_dataset_has_no_duplicate_ids(self):
        result = validate_dataset(self.EXAMPLE_PATH, check_count=False)
        # If there were duplicates, errors would be present
        dup_errors = [e for e in result.errors if "duplicate id" in e]
        assert not dup_errors

    def test_example_dataset_has_at_least_10_records(self):
        result = validate_dataset(self.EXAMPLE_PATH, check_count=False)
        assert result.total >= 10, f"Expected at least 10 example records, got {result.total}"


# ---------------------------------------------------------------------------
# P1-05c: Validator catches errors
# ---------------------------------------------------------------------------


class TestValidRecord:
    def test_valid_record_passes(self, tmp_path):
        path = _write_jsonl(tmp_path, [_minimal_record()])
        result = validate_dataset(path, check_count=False)
        assert result.ok, result.errors
        assert result.total == 1

    def test_valid_non_recruiter_passes(self, tmp_path):
        rec = _minimal_record(
            id="nr-001",
            is_recruiter=False,
            intent="other",
            expected_profile_ids=[],
            fields={
                "role": None, "skills": [], "min_years_experience": None,
                "location": None, "candidate_names": [], "resume_requested": False,
            },
        )
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert result.ok, result.errors


class TestMissingRequiredField:
    @pytest.mark.parametrize("field", [
        "id", "provider", "headers", "subject", "body_text",
        "is_recruiter", "intent", "fields", "expected_profile_ids", "notes",
    ])
    def test_missing_top_level_field_fails(self, tmp_path, field):
        rec = _minimal_record()
        del rec[field]
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok
        assert any("schema" in e for e in result.errors)

    @pytest.mark.parametrize("field", [
        "role", "skills", "min_years_experience", "location",
        "candidate_names", "resume_requested",
    ])
    def test_missing_fields_subfield_fails(self, tmp_path, field):
        rec = _minimal_record()
        del rec["fields"][field]
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok

    def test_missing_auth_results_header_fails(self, tmp_path):
        rec = _minimal_record()
        del rec["headers"]["authentication-results"]
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok

    def test_missing_from_header_fails(self, tmp_path):
        rec = _minimal_record()
        del rec["headers"]["from"]
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok


class TestDuplicateId:
    def test_duplicate_id_fails(self, tmp_path):
        r1 = _minimal_record(id="dup-001")
        r2 = _minimal_record(id="dup-001", intent="follow_up", expected_profile_ids=[])
        path = _write_jsonl(tmp_path, [r1, r2])
        result = validate_dataset(path, check_count=False)
        assert not result.ok
        assert any("duplicate id" in e for e in result.errors)

    def test_unique_ids_pass(self, tmp_path):
        r1 = _minimal_record(id="u-001")
        r2 = _minimal_record(id="u-002")
        path = _write_jsonl(tmp_path, [r1, r2])
        result = validate_dataset(path, check_count=False)
        dup_errors = [e for e in result.errors if "duplicate id" in e]
        assert not dup_errors


class TestWrongEnumValue:
    def test_invalid_intent_fails(self, tmp_path):
        rec = _minimal_record(intent="unknown_intent")
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok

    def test_invalid_provider_fails(self, tmp_path):
        rec = _minimal_record(provider="yahoo")
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok


class TestExpectedProfileIds:
    def test_a_requirement_without_profile_ids_is_outstanding_work_not_an_error(self, tmp_path):
        """expected_profile_ids is ground truth for MATCH recall, not for classification.

        Deciding it means opening every candidate profile and judging which fit, which is a far
        slower call than "is this a recruiter email". Requiring it per email roughly triples
        labelling time for data the classifier never reads, so it is counted as outstanding
        rather than rejected.
        """
        rec = _minimal_record(
            intent="new_requirement", is_recruiter=True, expected_profile_ids=[]
        )
        path = _write_jsonl(tmp_path, [rec])

        result = validate_dataset(path, check_count=False)

        assert not [e for e in result.errors if "expected_profile_ids" in e]
        assert result.needs_match_labels == 1

    def test_a_resume_request_without_profile_ids_is_also_counted(self, tmp_path):
        rec = _minimal_record(
            intent="resume_request", is_recruiter=True, expected_profile_ids=[]
        )
        path = _write_jsonl(tmp_path, [rec])

        result = validate_dataset(path, check_count=False)

        assert not [e for e in result.errors if "expected_profile_ids" in e]
        assert result.needs_match_labels == 1

    def test_a_requirement_with_profile_ids_is_not_counted_as_outstanding(self, tmp_path):
        rec = _minimal_record(
            intent="new_requirement", is_recruiter=True, expected_profile_ids=[1, 3]
        )
        path = _write_jsonl(tmp_path, [rec])

        assert validate_dataset(path, check_count=False).needs_match_labels == 0

    def test_the_outstanding_count_is_reported(self, tmp_path):
        """A number nobody sees is a number nobody fills in."""
        from eval.validate_dataset import _format_report

        rec = _minimal_record(
            intent="new_requirement", is_recruiter=True, expected_profile_ids=[]
        )
        path = _write_jsonl(tmp_path, [rec])

        report = _format_report(validate_dataset(path, check_count=False), path)

        assert "expected_profile_ids" in report

    def test_follow_up_without_profile_ids_passes(self, tmp_path):
        rec = _minimal_record(
            intent="follow_up",
            expected_profile_ids=[],
        )
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        # The only potential error is missing intents (since we have just 1 record),
        # but no profile_ids error.
        pid_errors = [e for e in result.errors if "expected_profile_ids" in e]
        assert not pid_errors

    def test_non_recruiter_new_requirement_without_profile_ids_passes(self, tmp_path):
        """A non-recruiter email labelled new_requirement (edge case) doesn't need profile IDs."""
        rec = _minimal_record(
            is_recruiter=False,
            intent="new_requirement",
            expected_profile_ids=[],
        )
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        pid_errors = [e for e in result.errors if "expected_profile_ids" in e]
        assert not pid_errors


class TestCountRange:
    def test_too_few_records_fails_with_count_check(self, tmp_path):
        records = [_minimal_record(id=f"c-{i:03d}") for i in range(10)]
        path = _write_jsonl(tmp_path, records)
        result = validate_dataset(path, check_count=True)
        assert not result.ok
        assert any("Too few" in e for e in result.errors)

    def test_too_few_records_passes_without_count_check(self, tmp_path):
        records = [_minimal_record(id=f"c-{i:03d}") for i in range(5)]
        path = _write_jsonl(tmp_path, records)
        result = validate_dataset(path, check_count=False)
        # May still have missing-intent errors, but no count error.
        count_errors = [e for e in result.errors if "Too few" in e or "Too many" in e]
        assert not count_errors

    def test_count_check_skipped_by_flag(self, tmp_path):
        rec = _minimal_record()
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        count_errors = [e for e in result.errors if "Too few" in e]
        assert not count_errors


class TestInvalidJson:
    def test_malformed_json_line_fails(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text('{"id": "ok"}\nNOT VALID JSON\n', encoding="utf-8")
        result = validate_dataset(path, check_count=False)
        assert not result.ok
        assert any("invalid JSON" in e for e in result.errors)

    def test_empty_file_fails(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        result = validate_dataset(path, check_count=False)
        assert not result.ok
        assert any("empty" in e.lower() for e in result.errors)

    def test_file_not_found_fails(self, tmp_path):
        path = tmp_path / "nonexistent.jsonl"
        result = validate_dataset(path, check_count=False)
        assert not result.ok
        assert any("not found" in e.lower() for e in result.errors)


class TestAdditionalProperties:
    def test_extra_top_level_field_fails(self, tmp_path):
        rec = _minimal_record()
        rec["extra_field"] = "should not be here"
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok

    def test_extra_fields_subfield_fails(self, tmp_path):
        rec = _minimal_record()
        rec["fields"]["extra"] = "nope"
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok


class TestTypeValidation:
    def test_skills_must_be_array(self, tmp_path):
        rec = _minimal_record()
        rec["fields"]["skills"] = "python"  # should be array
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok

    def test_is_recruiter_must_be_boolean(self, tmp_path):
        rec = _minimal_record()
        rec["is_recruiter"] = "yes"  # should be bool
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok

    def test_expected_profile_ids_must_be_integers(self, tmp_path):
        rec = _minimal_record(expected_profile_ids=["1", "2"])
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        assert not result.ok

    def test_min_years_experience_accepts_null(self, tmp_path):
        rec = _minimal_record()
        rec["fields"]["min_years_experience"] = None
        path = _write_jsonl(tmp_path, [rec])
        result = validate_dataset(path, check_count=False)
        # No type error for this field
        type_errors = [e for e in result.errors if "min_years_experience" in e]
        assert not type_errors
