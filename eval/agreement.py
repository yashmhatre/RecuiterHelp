"""Double-labelling agreement check for the evaluation dataset.

P1-05 requires a slice of the dataset to be labelled twice, independently, with the
disagreement rate reported. The reason is narrow and important: the plan targets 95% recruiter
accuracy and 90% intent accuracy. If two human passes over the same emails disagree more than
5% of the time, then a 95% target is inside the noise of the ground truth itself and **cannot
be measured at all**. Finding that out after labelling 300 emails is expensive; finding it out
after 30 is cheap. Run this before bulk labelling.

Workflow::

    # 1. Pin a reproducible 30-email slice from what is already labelled
    python eval/agreement.py --select --size 30

    # 2. Re-label exactly that slice, blind, into a second file
    python eval/label_cli.py --second-pass

    # 3. Report agreement and gate on it
    python eval/agreement.py

Exit code 0 means every gated field agrees at or above the threshold. Exit code 1 means the
label definitions need tightening before labelling continues.

What counts as a disagreement
-----------------------------
**Gated fields** are the ones with accuracy targets in the plan, compared exactly:

- ``is_recruiter`` (95% target)
- ``intent`` (90% target)

**Reported but not gated** are the extraction fields. Free text like ``role`` and ``location``
will differ on wording between two passes for reasons that say nothing about whether the label
definitions are sound, so gating on them would produce noise and hide the signal that matters.
They are printed so a systematic problem is still visible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "DEFAULT_SLICE_SIZE",
    "MAX_DISAGREEMENT",
    "AgreementReport",
    "FieldAgreement",
    "compare_passes",
    "select_slice",
    "load_records",
]

DATASET_DIR = Path(__file__).resolve().parent / "dataset"
PASS1_PATH = DATASET_DIR / "labels.jsonl"
PASS2_PATH = DATASET_DIR / "labels.pass2.jsonl"
SLICE_PATH = DATASET_DIR / "agreement_slice.json"

#: The ticket asks for 30 emails.
DEFAULT_SLICE_SIZE = 30

#: Above this, a 95% accuracy target is not measurable against this ground truth.
MAX_DISAGREEMENT = 0.05

#: Compared exactly and gated. These are the fields with targets in the plan.
GATED_FIELDS = ("is_recruiter", "intent")

#: Compared and reported, never gated. See the module docstring.
REPORTED_FIELDS = (
    "fields.resume_requested",
    "fields.min_years_experience",
    "expected_profile_ids",
    "fields.skills",
    "fields.candidate_names",
    "fields.role",
    "fields.location",
)


# ---------------------------------------------------------------------------
# Slice selection
# ---------------------------------------------------------------------------


def select_slice(ids: list[str], size: int = DEFAULT_SLICE_SIZE, seed: str = "p1-05") -> list[str]:
    """Pick a reproducible pseudo-random subset of record ids.

    Ordering is by hash of ``id + seed`` rather than by file position, so the slice does not
    favour whatever was labelled first — labelling order tends to correlate with how easy an
    email was, and an agreement check run only on easy emails is worthless.

    Deterministic for a given id set and seed, so two people get the same slice.
    """
    if size < 1:
        raise ValueError(f"size must be at least 1, got {size}")

    ranked = sorted(set(ids), key=lambda rid: hashlib.sha256(f"{seed}:{rid}".encode()).hexdigest())
    return ranked[:size]


def write_slice(ids: list[str], path: Path = SLICE_PATH, seed: str = "p1-05") -> None:
    """Pin the chosen slice to disk.

    Pinned rather than recomputed because pass 1 keeps growing. Recomputing would silently
    change which emails are in the slice between selection and the second pass, and the two
    passes would then be over different emails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"seed": seed, "size": len(ids), "ids": ids}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_slice(path: Path = SLICE_PATH) -> list[str]:
    """Read the pinned slice, or raise with instructions if it does not exist yet."""
    if not path.is_file():
        raise FileNotFoundError(
            f"No pinned slice at {path}. Create one first:\n"
            f"  python eval/agreement.py --select --size {DEFAULT_SLICE_SIZE}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload["ids"])


# ---------------------------------------------------------------------------
# Loading and comparison
# ---------------------------------------------------------------------------


def load_records(path: Path) -> dict[str, dict]:
    """Load a JSONL label file keyed by record id. A later line wins on a duplicate id."""
    records: dict[str, dict] = {}
    if not path.is_file():
        return records
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and "id" in record:
                records[record["id"]] = record
    return records


def _get(record: dict, dotted: str):
    """Read a possibly nested field, e.g. ``fields.skills``."""
    value = record
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _values_agree(dotted: str, left, right) -> bool:
    """Whether two labellings of one field count as agreeing.

    Lists of strings are compared as case-insensitive sets, because ordering and casing are
    entry conventions rather than judgements. Everything else is compared exactly.
    """
    if dotted in ("fields.skills", "fields.candidate_names"):
        return _string_set(left) == _string_set(right)
    if dotted == "expected_profile_ids":
        return set(left or []) == set(right or [])
    if dotted in ("fields.role", "fields.location"):
        return _normalise_text(left) == _normalise_text(right)
    return left == right


def _string_set(value) -> set[str]:
    if not value:
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def _normalise_text(value) -> str:
    return " ".join(str(value or "").split()).strip().lower()


@dataclass(frozen=True)
class FieldAgreement:
    """Agreement on one field across the compared records."""

    name: str
    compared: int
    disagreements: int
    gated: bool
    examples: tuple[str, ...] = ()

    @property
    def disagreement_rate(self) -> float:
        return self.disagreements / self.compared if self.compared else 0.0

    @property
    def agreement_rate(self) -> float:
        return 1.0 - self.disagreement_rate

    @property
    def ok(self) -> bool:
        """A non-gated field is always ok; it is informational."""
        return not self.gated or self.disagreement_rate <= MAX_DISAGREEMENT


@dataclass(frozen=True)
class AgreementReport:
    fields: tuple[FieldAgreement, ...]
    compared_ids: tuple[str, ...]
    only_in_pass1: tuple[str, ...] = ()
    only_in_pass2: tuple[str, ...] = ()
    expected_size: int | None = None
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def compared(self) -> int:
        return len(self.compared_ids)

    @property
    def gated_fields(self) -> tuple[FieldAgreement, ...]:
        return tuple(f for f in self.fields if f.gated)

    @property
    def any_primary_disagreement_rate(self) -> float:
        """Fraction of records where at least one gated field differs."""
        return self._combined

    _combined: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.problems and self.compared > 0 and all(f.ok for f in self.fields)


def compare_passes(
    pass1: dict[str, dict],
    pass2: dict[str, dict],
    expected_ids: list[str] | None = None,
) -> AgreementReport:
    """Compare two independent labelling passes over the same emails."""
    problems: list[str] = []

    ids1, ids2 = set(pass1), set(pass2)
    if expected_ids is not None:
        # Restrict to the pinned slice so a partially re-labelled file cannot inflate agreement
        # by quietly comparing only the records that happen to be in both.
        wanted = set(expected_ids)
        ids1 &= wanted
        ids2 &= wanted

    shared = sorted(ids1 & ids2)
    only1 = sorted(ids1 - ids2)
    only2 = sorted(ids2 - ids1)

    if not shared:
        problems.append("No records appear in both passes, so there is nothing to compare.")

    if expected_ids is not None and len(shared) < len(set(expected_ids)):
        problems.append(
            f"Only {len(shared)} of the {len(set(expected_ids))} pinned slice records are in "
            f"both passes. Finish the second pass before reading these numbers: "
            f"python eval/label_cli.py --second-pass"
        )

    results: list[FieldAgreement] = []
    combined_disagreements = 0

    for dotted in GATED_FIELDS + REPORTED_FIELDS:
        disagreements = 0
        examples: list[str] = []
        for rid in shared:
            if not _values_agree(dotted, _get(pass1[rid], dotted), _get(pass2[rid], dotted)):
                disagreements += 1
                if len(examples) < 3:
                    examples.append(
                        f"{rid}: {_get(pass1[rid], dotted)!r} vs {_get(pass2[rid], dotted)!r}"
                    )
        results.append(
            FieldAgreement(
                name=dotted,
                compared=len(shared),
                disagreements=disagreements,
                gated=dotted in GATED_FIELDS,
                examples=tuple(examples),
            )
        )

    for rid in shared:
        if any(
            not _values_agree(dotted, _get(pass1[rid], dotted), _get(pass2[rid], dotted))
            for dotted in GATED_FIELDS
        ):
            combined_disagreements += 1

    report = AgreementReport(
        fields=tuple(results),
        compared_ids=tuple(shared),
        only_in_pass1=tuple(only1),
        only_in_pass2=tuple(only2),
        expected_size=len(set(expected_ids)) if expected_ids is not None else None,
        problems=tuple(problems),
    )
    object.__setattr__(
        report, "_combined", combined_disagreements / len(shared) if shared else 0.0
    )
    return report


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def format_report(report: AgreementReport) -> str:
    lines: list[str] = []
    lines.append(f"Records compared: {report.compared}")
    if report.expected_size is not None:
        lines.append(f"Pinned slice size: {report.expected_size}")
    lines.append(f"Threshold: disagreement must stay at or below {MAX_DISAGREEMENT:.0%}")
    lines.append("")

    lines.append(f"{'field':<34s} {'agree':>7s} {'disagree':>9s}  gate")
    lines.append("-" * 62)
    for item in report.fields:
        gate = "FAIL" if not item.ok else ("gated" if item.gated else "-")
        lines.append(
            f"{item.name:<34s} {item.agreement_rate:>6.1%} "
            f"{item.disagreements:>5d} ({item.disagreement_rate:>4.1%})  {gate}"
        )

    lines.append("")
    lines.append(
        f"Records where any gated field differs: {report.any_primary_disagreement_rate:.1%}"
    )

    disagreeing = [f for f in report.fields if f.disagreements]
    if disagreeing:
        lines.append("")
        lines.append("Examples:")
        for item in disagreeing:
            for example in item.examples:
                lines.append(f"  {item.name}: {example}")

    if report.only_in_pass1 or report.only_in_pass2:
        lines.append("")
        if report.only_in_pass1:
            lines.append(f"Only in pass 1 ({len(report.only_in_pass1)}): "
                         f"{', '.join(report.only_in_pass1[:8])}")
        if report.only_in_pass2:
            lines.append(f"Only in pass 2 ({len(report.only_in_pass2)}): "
                         f"{', '.join(report.only_in_pass2[:8])}")

    lines.append("")
    if report.problems:
        lines.append("FAIL:")
        for problem in report.problems:
            lines.append(f"  - {problem}")
    elif report.ok:
        lines.append("PASS: gated fields agree within the threshold. The 95% target is measurable.")
    else:
        failed = [f.name for f in report.fields if not f.ok]
        lines.append(f"FAIL: {', '.join(failed)} disagree above {MAX_DISAGREEMENT:.0%}.")
        lines.append("")
        lines.append(
            "  A 95% accuracy target cannot be measured against ground truth this noisy. "
            "Tighten the label definitions in eval/dataset/schema.json descriptions and the "
            "P1-05 ticket, re-label the slice, and say so in the PR. Do not label the "
            "remaining emails until this passes."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report double-labelling agreement for the evaluation dataset.",
    )
    parser.add_argument(
        "--select",
        action="store_true",
        help="Pin a reproducible slice from pass 1 and exit, instead of reporting agreement.",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_SLICE_SIZE,
        help=f"Slice size for --select (default: {DEFAULT_SLICE_SIZE}).",
    )
    parser.add_argument("--pass1", type=Path, default=PASS1_PATH, help="First labelling pass.")
    parser.add_argument("--pass2", type=Path, default=PASS2_PATH, help="Second labelling pass.")
    parser.add_argument("--slice", type=Path, default=SLICE_PATH, help="Pinned slice file.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compare every id present in both files, ignoring the pinned slice.",
    )
    args = parser.parse_args(argv)

    if args.select:
        pass1 = load_records(args.pass1)
        if not pass1:
            print(f"No records in {args.pass1}. Label some emails first.", file=sys.stderr)
            return 1
        if len(pass1) < args.size:
            print(
                f"Only {len(pass1)} labelled records available; slice will be "
                f"{len(pass1)} rather than {args.size}.",
                file=sys.stderr,
            )
        chosen = select_slice(list(pass1), size=min(args.size, len(pass1)))
        write_slice(chosen, args.slice)
        print(f"Pinned {len(chosen)} ids to {args.slice}")
        print("Now re-label exactly these, blind:\n  python eval/label_cli.py --second-pass")
        return 0

    expected: list[str] | None = None
    if not args.all:
        try:
            expected = read_slice(args.slice)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    report = compare_passes(load_records(args.pass1), load_records(args.pass2), expected)
    print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
