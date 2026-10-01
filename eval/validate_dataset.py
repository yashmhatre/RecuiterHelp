"""Validate a labelled email dataset against the JSON schema.

Usage::

    python eval/validate_dataset.py eval/dataset/labels.example.jsonl
    python eval/validate_dataset.py eval/dataset/labels.jsonl
    python eval/validate_dataset.py eval/dataset/labels.example.jsonl --no-count-check

Exit code 0 means every record is valid and all acceptance criteria are met.
Exit code 1 means at least one check failed — details are printed to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import jsonschema

__all__ = ["validate_dataset", "load_schema", "ValidationResult"]

SCHEMA_PATH = Path(__file__).resolve().parent / "dataset" / "schema.json"

# Acceptance criteria from P1-05
MIN_COUNT = 200
MAX_COUNT = 300
MIN_NON_RECRUITER_SHARE = 0.25
REQUIRED_INTENTS = frozenset(
    {"new_requirement", "resume_request", "follow_up", "interview", "other"}
)


class ValidationResult:
    """Collects errors and statistics from a validation run."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.total: int = 0
        self.intent_counts: Counter[str] = Counter()
        self.recruiter_count: int = 0
        self.non_recruiter_count: int = 0
        self.ids_seen: set[str] = set()
        self.needs_match_labels: int = 0

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    @property
    def non_recruiter_share(self) -> float:
        return self.non_recruiter_count / self.total if self.total else 0.0

    @property
    def missing_intents(self) -> set[str]:
        return REQUIRED_INTENTS - set(self.intent_counts)

    def add_error(self, line: int, message: str) -> None:
        self.errors.append(f"line {line}: {message}")

    def add_global_error(self, message: str) -> None:
        self.errors.append(message)


def load_schema(path: Path | None = None) -> dict:
    """Load and return the JSON schema for dataset records."""
    schema_path = path or SCHEMA_PATH
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def validate_record(
    record: dict,
    schema: dict,
    validator: jsonschema.Draft202012Validator,
    line_num: int,
    result: ValidationResult,
) -> None:
    """Validate a single parsed record, appending any errors to *result*."""

    # -- schema validation --
    schema_errors = list(validator.iter_errors(record))
    for err in schema_errors:
        path = ".".join(str(p) for p in err.absolute_path) if err.absolute_path else "(root)"
        result.add_error(line_num, f"schema: {path}: {err.message}")

    if schema_errors:
        # Don't run semantic checks on a structurally invalid record.
        return

    record_id = record["id"]

    # -- duplicate ID --
    if record_id in result.ids_seen:
        result.add_error(line_num, f"duplicate id: {record_id!r}")
    result.ids_seen.add(record_id)

    # -- conditional: expected_profile_ids for recruiter + new_requirement / resume_request --
    intent = record["intent"]
    is_recruiter = record["is_recruiter"]
    profile_ids = record["expected_profile_ids"]

    # Not an error. expected_profile_ids is ground truth for MATCH recall, which is a separate
    # and much slower judgement than "is this a recruiter email" -- it means opening every
    # profile and deciding which fit. Requiring it per email roughly triples labelling time for
    # data the classifier never reads. Counted here so the outstanding work stays visible.
    if is_recruiter and intent in ("new_requirement", "resume_request") and not profile_ids:
        result.needs_match_labels += 1

    # -- accumulate stats --
    result.total += 1
    result.intent_counts[intent] += 1
    if is_recruiter:
        result.recruiter_count += 1
    else:
        result.non_recruiter_count += 1


def validate_dataset(
    path: Path,
    *,
    check_count: bool = True,
    schema_path: Path | None = None,
) -> ValidationResult:
    """Validate an entire JSONL dataset file.

    Parameters
    ----------
    path:
        Path to the ``.jsonl`` file to validate.
    check_count:
        If ``True``, enforce the 200–300 record count window.
        Set to ``False`` for the example file or during partial labelling.
    schema_path:
        Override the default schema location (for testing).
    """
    result = ValidationResult()
    schema = load_schema(schema_path)
    validator = jsonschema.Draft202012Validator(schema)

    if not path.is_file():
        result.add_global_error(f"File not found: {path}")
        return result

    with open(path, encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                result.add_error(line_num, f"invalid JSON: {exc}")
                continue
            validate_record(record, schema, validator, line_num, result)

    # -- global checks --
    if result.total == 0:
        result.add_global_error("Dataset is empty (0 records)")

    if check_count and result.total > 0:
        if result.total < MIN_COUNT:
            result.add_global_error(
                f"Too few records: {result.total} (minimum {MIN_COUNT})"
            )
        elif result.total > MAX_COUNT:
            result.add_global_error(
                f"Too many records: {result.total} (maximum {MAX_COUNT})"
            )

        if result.missing_intents:
            result.add_global_error(
                f"Missing intents: {', '.join(sorted(result.missing_intents))}. "
                f"All five intents must be represented."
            )

        if result.non_recruiter_share < MIN_NON_RECRUITER_SHARE:
            result.add_global_error(
                f"Non-recruiter share is {result.non_recruiter_share:.1%}, "
                f"minimum is {MIN_NON_RECRUITER_SHARE:.0%}"
            )

    return result


def _format_report(result: ValidationResult, path: Path) -> str:
    """Build a human-readable summary of the validation run."""
    lines: list[str] = []
    lines.append(f"Dataset: {path}")
    lines.append(f"Records: {result.total}")
    lines.append("")

    # Intent distribution table
    lines.append("Intent distribution:")
    for intent in sorted(REQUIRED_INTENTS):
        count = result.intent_counts.get(intent, 0)
        pct = (count / result.total * 100) if result.total else 0.0
        marker = "  " if count > 0 else "!!"
        lines.append(f"  {marker} {intent:<20s} {count:>4d}  ({pct:5.1f}%)")

    lines.append("")
    lines.append(
        f"Recruiter:     {result.recruiter_count:>4d}  "
        f"({result.recruiter_count / result.total * 100 if result.total else 0:.1f}%)"
    )
    lines.append(
        f"Non-recruiter: {result.non_recruiter_count:>4d}  "
        f"({result.non_recruiter_share:.1%})"
    )
    if result.needs_match_labels:
        lines.append("")
        lines.append(
            f"Still need expected_profile_ids: {result.needs_match_labels}  "
            f"(only required to measure match recall, not classification)"
        )
    lines.append("")

    if result.ok:
        lines.append("PASS: All checks passed.")
    else:
        lines.append(f"FAIL: {len(result.errors)} error(s):")
        for err in result.errors:
            lines.append(f"  - {err}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a labelled email dataset against the JSON schema.",
    )
    parser.add_argument(
        "dataset",
        type=Path,
        help="Path to the JSONL dataset file to validate.",
    )
    parser.add_argument(
        "--no-count-check",
        action="store_true",
        help="Skip the 200-300 record count requirement (for example files or partial progress).",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Override the default schema.json path.",
    )
    args = parser.parse_args(argv)

    result = validate_dataset(
        args.dataset,
        check_count=not args.no_count_check,
        schema_path=args.schema,
    )

    report = _format_report(result, args.dataset)
    print(report)

    if not result.ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
