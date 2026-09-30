"""Tests for the P1-05 double-labelling agreement check.

The point of the feature is to answer one question before 300 emails get labelled: is the
ground truth consistent enough that a 95% accuracy target means anything? These tests check
that the answer cannot come out falsely reassuring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.agreement import (
    DEFAULT_SLICE_SIZE,
    MAX_DISAGREEMENT,
    compare_passes,
    format_report,
    load_records,
    main,
    read_slice,
    select_slice,
    write_slice,
)


def record(rid: str, *, is_recruiter=True, intent="new_requirement", **overrides) -> dict:
    """A minimal labelled record. Only the compared fields matter here."""
    base = {
        "id": rid,
        "provider": "gmail",
        "headers": {"authentication-results": "spf=pass", "from": f"{rid}@acme.example.com"},
        "subject": "Role",
        "body_text": "Body",
        "is_recruiter": is_recruiter,
        "intent": intent,
        "fields": {
            "role": "Senior Python Engineer",
            "skills": ["python", "fastapi"],
            "min_years_experience": 5.0,
            "location": "Pune",
            "candidate_names": [],
            "resume_requested": False,
        },
        "expected_profile_ids": [1],
        "notes": "",
    }
    fields = overrides.pop("fields", None)
    base.update(overrides)
    if fields:
        base["fields"].update(fields)
    return base


def as_map(records: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in records}


def write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    return path


# ---------------------------------------------------------------------------
# Slice selection
# ---------------------------------------------------------------------------


def test_slice_is_deterministic_for_the_same_ids():
    ids = [f"e-{i:03d}" for i in range(100)]

    assert select_slice(ids, size=30) == select_slice(ids, size=30)


def test_slice_is_independent_of_input_order():
    """Two people must get the same slice regardless of how their file is ordered."""
    ids = [f"e-{i:03d}" for i in range(100)]

    assert select_slice(ids, size=30) == select_slice(list(reversed(ids)), size=30)


def test_slice_does_not_just_take_the_first_n_labelled():
    """Labelling order correlates with how easy an email was. An agreement check run only on
    the emails labelled first would be measuring the easy cases."""
    ids = [f"e-{i:03d}" for i in range(100)]

    assert select_slice(ids, size=30) != ids[:30]


def test_slice_size_is_capped_by_available_ids():
    assert len(select_slice(["a", "b", "c"], size=30)) == 3


def test_slice_deduplicates_ids():
    assert len(select_slice(["a", "a", "b"], size=30)) == 2


def test_different_seeds_give_different_slices():
    ids = [f"e-{i:03d}" for i in range(100)]

    assert select_slice(ids, size=30, seed="x") != select_slice(ids, size=30, seed="y")


def test_slice_size_below_one_is_rejected():
    with pytest.raises(ValueError, match="at least 1"):
        select_slice(["a"], size=0)


def test_default_slice_size_is_the_thirty_the_ticket_asks_for():
    assert DEFAULT_SLICE_SIZE == 30


def test_slice_round_trips_through_disk(tmp_path: Path):
    ids = select_slice([f"e-{i}" for i in range(50)], size=10)
    path = tmp_path / "slice.json"
    write_slice(ids, path)

    assert read_slice(path) == ids


def test_missing_slice_file_explains_how_to_make_one(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="--select"):
        read_slice(tmp_path / "nope.json")


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def test_identical_passes_agree_completely():
    records = [record(f"e-{i}") for i in range(20)]
    report = compare_passes(as_map(records), as_map(records))

    assert report.ok
    assert report.compared == 20
    assert report.any_primary_disagreement_rate == 0.0


def test_is_recruiter_disagreement_is_counted_and_gated():
    """20 records, 2 differ on is_recruiter = 10%, above the 5% threshold."""
    pass1 = as_map([record(f"e-{i}") for i in range(20)])
    pass2 = as_map(
        [record(f"e-{i}", is_recruiter=(i >= 2)) for i in range(20)]
    )

    report = compare_passes(pass1, pass2)
    field = next(f for f in report.fields if f.name == "is_recruiter")

    assert field.disagreements == 2
    assert field.disagreement_rate == pytest.approx(0.10)
    assert not field.ok
    assert not report.ok


def test_disagreement_exactly_at_the_threshold_passes():
    """5% is the limit, not the first failure. 1 of 20 is 5%."""
    pass1 = as_map([record(f"e-{i}") for i in range(20)])
    pass2 = as_map([record(f"e-{i}", is_recruiter=(i != 0)) for i in range(20)])

    report = compare_passes(pass1, pass2)

    assert report.any_primary_disagreement_rate == pytest.approx(MAX_DISAGREEMENT)
    assert report.ok


def test_one_disagreement_just_over_the_threshold_fails():
    """1 of 15 is 6.7%."""
    pass1 = as_map([record(f"e-{i}") for i in range(15)])
    pass2 = as_map([record(f"e-{i}", is_recruiter=(i != 0)) for i in range(15)])

    assert not compare_passes(pass1, pass2).ok


def test_intent_disagreement_is_gated():
    pass1 = as_map([record(f"e-{i}") for i in range(10)])
    pass2 = as_map(
        [record(f"e-{i}", intent="follow_up" if i < 2 else "new_requirement") for i in range(10)]
    )

    report = compare_passes(pass1, pass2)

    assert not next(f for f in report.fields if f.name == "intent").ok
    assert not report.ok


def test_free_text_role_disagreement_is_reported_but_never_fails():
    """Two passes will word a role differently for reasons that say nothing about whether the
    label definitions are sound. Gating on it would bury the signal that matters."""
    pass1 = as_map([record(f"e-{i}") for i in range(10)])
    pass2 = as_map([record(f"e-{i}", fields={"role": f"Totally different {i}"}) for i in range(10)])

    report = compare_passes(pass1, pass2)
    field = next(f for f in report.fields if f.name == "fields.role")

    assert field.disagreements == 10
    assert not field.gated
    assert field.ok
    assert report.ok, "a free-text field must not fail the gate"


def test_skills_compare_as_case_insensitive_sets():
    """Order and casing are entry conventions, not judgements."""
    pass1 = as_map([record("e-1", fields={"skills": ["Python", "FastAPI"]})])
    pass2 = as_map([record("e-1", fields={"skills": ["fastapi", "python"]})])

    report = compare_passes(pass1, pass2)

    assert next(f for f in report.fields if f.name == "fields.skills").disagreements == 0


def test_skills_with_genuinely_different_content_disagree():
    pass1 = as_map([record("e-1", fields={"skills": ["python"]})])
    pass2 = as_map([record("e-1", fields={"skills": ["java"]})])

    report = compare_passes(pass1, pass2)

    assert next(f for f in report.fields if f.name == "fields.skills").disagreements == 1


def test_expected_profile_ids_compare_as_sets():
    pass1 = as_map([record("e-1", expected_profile_ids=[1, 2])])
    pass2 = as_map([record("e-1", expected_profile_ids=[2, 1])])

    report = compare_passes(pass1, pass2)

    assert next(f for f in report.fields if f.name == "expected_profile_ids").disagreements == 0


def test_role_whitespace_and_casing_are_normalised():
    pass1 = as_map([record("e-1", fields={"role": "Senior  Python Engineer"})])
    pass2 = as_map([record("e-1", fields={"role": "senior python engineer"})])

    report = compare_passes(pass1, pass2)

    assert next(f for f in report.fields if f.name == "fields.role").disagreements == 0


def test_examples_are_captured_for_diagnosis():
    pass1 = as_map([record("e-1", intent="interview")])
    pass2 = as_map([record("e-1", intent="follow_up")])

    report = compare_passes(pass1, pass2)
    field = next(f for f in report.fields if f.name == "intent")

    assert field.examples
    assert "e-1" in field.examples[0]


# ---------------------------------------------------------------------------
# The failure modes that would make the check falsely reassuring
# ---------------------------------------------------------------------------


def test_no_overlap_is_a_failure_not_a_perfect_score():
    """Comparing zero records must never report 100% agreement."""
    report = compare_passes(as_map([record("a")]), as_map([record("b")]))

    assert report.compared == 0
    assert not report.ok
    assert any("nothing to compare" in p for p in report.problems)


def test_empty_passes_fail():
    assert not compare_passes({}, {}).ok


def test_a_partial_second_pass_cannot_report_a_pass():
    """Re-labelling only the 3 easy records out of a 30-record slice would otherwise show
    perfect agreement on those 3."""
    slice_ids = [f"e-{i}" for i in range(30)]
    pass1 = as_map([record(rid) for rid in slice_ids])
    pass2 = as_map([record(rid) for rid in slice_ids[:3]])

    report = compare_passes(pass1, pass2, expected_ids=slice_ids)

    assert report.compared == 3
    assert not report.ok
    assert any("pinned slice" in p for p in report.problems)


def test_records_outside_the_pinned_slice_are_ignored():
    slice_ids = [f"e-{i}" for i in range(5)]
    extra = [record("outsider", is_recruiter=False)]
    pass1 = as_map([record(rid) for rid in slice_ids] + extra)
    pass2 = as_map([record(rid) for rid in slice_ids] + [record("outsider", is_recruiter=True)])

    report = compare_passes(pass1, pass2, expected_ids=slice_ids)

    assert report.compared == 5
    assert "outsider" not in report.compared_ids
    assert report.ok


def test_complete_slice_with_full_agreement_passes():
    slice_ids = [f"e-{i}" for i in range(30)]
    records = [record(rid) for rid in slice_ids]

    report = compare_passes(as_map(records), as_map(records), expected_ids=slice_ids)

    assert report.ok
    assert report.expected_size == 30


# ---------------------------------------------------------------------------
# Loading and reporting
# ---------------------------------------------------------------------------


def test_load_records_keys_by_id(tmp_path: Path):
    path = write_jsonl(tmp_path / "l.jsonl", [record("a"), record("b")])

    assert set(load_records(path)) == {"a", "b"}


def test_load_records_tolerates_blank_and_broken_lines(tmp_path: Path):
    path = tmp_path / "l.jsonl"
    path.write_text(
        json.dumps(record("a")) + "\n\nnot json\n" + json.dumps(record("b")) + "\n",
        encoding="utf-8",
    )

    assert set(load_records(path)) == {"a", "b"}


def test_load_records_on_a_missing_file_is_empty(tmp_path: Path):
    assert load_records(tmp_path / "nope.jsonl") == {}


def test_report_states_the_threshold_and_the_verdict():
    records = [record(f"e-{i}") for i in range(20)]
    text = format_report(compare_passes(as_map(records), as_map(records)))

    assert "5%" in text
    assert "PASS" in text


def test_failing_report_says_not_to_keep_labelling():
    pass1 = as_map([record(f"e-{i}") for i in range(10)])
    pass2 = as_map([record(f"e-{i}", is_recruiter=(i >= 3)) for i in range(10)])
    text = format_report(compare_passes(pass1, pass2))

    assert "FAIL" in text
    assert "cannot be measured" in text
    assert "remaining emails" in text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_select_then_report_round_trip(tmp_path: Path):
    records = [record(f"e-{i}") for i in range(40)]
    p1 = write_jsonl(tmp_path / "labels.jsonl", records)
    slice_path = tmp_path / "slice.json"

    assert main(["--select", "--size", "30", "--pass1", str(p1), "--slice", str(slice_path)]) == 0

    slice_ids = read_slice(slice_path)
    assert len(slice_ids) == 30

    p2 = write_jsonl(tmp_path / "pass2.jsonl", [r for r in records if r["id"] in set(slice_ids)])
    assert main(["--pass1", str(p1), "--pass2", str(p2), "--slice", str(slice_path)]) == 0


def test_cli_exits_non_zero_when_agreement_is_too_low(tmp_path: Path):
    ids = [f"e-{i}" for i in range(20)]
    p1 = write_jsonl(tmp_path / "labels.jsonl", [record(rid) for rid in ids])
    p2 = write_jsonl(
        tmp_path / "pass2.jsonl",
        [record(rid, is_recruiter=(i >= 3)) for i, rid in enumerate(ids)],
    )
    slice_path = tmp_path / "slice.json"
    write_slice(ids, slice_path)

    assert main(["--pass1", str(p1), "--pass2", str(p2), "--slice", str(slice_path)]) == 1


def test_cli_select_needs_labelled_records(tmp_path: Path):
    empty = write_jsonl(tmp_path / "labels.jsonl", [])

    assert main(["--select", "--pass1", str(empty), "--slice", str(tmp_path / "s.json")]) == 1


def test_cli_without_a_pinned_slice_fails_with_instructions(tmp_path: Path, capsys):
    p1 = write_jsonl(tmp_path / "labels.jsonl", [record("a")])

    assert main(["--pass1", str(p1), "--slice", str(tmp_path / "missing.json")]) == 1
    assert "--select" in capsys.readouterr().err


def test_cli_all_flag_compares_without_a_slice(tmp_path: Path):
    records = [record(f"e-{i}") for i in range(20)]
    p1 = write_jsonl(tmp_path / "labels.jsonl", records)
    p2 = write_jsonl(tmp_path / "pass2.jsonl", records)

    assert main(["--all", "--pass1", str(p1), "--pass2", str(p2)]) == 0
