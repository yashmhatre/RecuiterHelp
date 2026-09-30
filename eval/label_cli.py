"""Interactive CLI for labelling emails into the evaluation dataset.

Usage::

    # Import raw emails from .eml files into a staging file
    python eval/label_cli.py --import-dir path/to/eml/files

    # Import from a JSONL of unlabelled raw emails
    python eval/label_cli.py --import-jsonl path/to/raw.jsonl

    # Start (or resume) the labelling session
    python eval/label_cli.py

    # Anonymise a labelled file for committing
    python eval/label_cli.py --anonymise eval/dataset/labels.jsonl --output eval/dataset/labels.anon.jsonl

The labelling workflow is:
1. Import emails into a staging file (``eval/dataset/staging.jsonl``)
2. Run the labeller — it presents one email at a time, you label it
3. Labelled records are appended to ``eval/dataset/labels.jsonl``
4. Resume at any time — already-labelled IDs are skipped

Each record is validated against ``eval/dataset/schema.json`` before being written.
"""

from __future__ import annotations

import argparse
import email
import hashlib
import json
import re
import sys
import textwrap
from email import policy
from pathlib import Path

import jsonschema

try:
    from eval.validate_dataset import load_schema
except ModuleNotFoundError:
    # Running as a script: python eval/label_cli.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from eval.validate_dataset import load_schema

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATASET_DIR = Path(__file__).resolve().parent / "dataset"
STAGING_PATH = DATASET_DIR / "staging.jsonl"
LABELS_PATH = DATASET_DIR / "labels.jsonl"
SCHEMA_PATH = DATASET_DIR / "schema.json"
# Second, independent pass over a pinned slice. Kept in its own file so the first pass is
# never edited, and so the second pass cannot see the first.
PASS2_PATH = DATASET_DIR / "labels.pass2.jsonl"

INTENT_CHOICES = {
    "1": "new_requirement",
    "2": "resume_request",
    "3": "follow_up",
    "4": "interview",
    "5": "other",
}

PROVIDER_CHOICES = {"1": "gmail", "2": "outlook"}

# ---------------------------------------------------------------------------
# Import: .eml directory → staging JSONL
# ---------------------------------------------------------------------------


def _parse_eml(eml_path: Path) -> dict | None:
    """Parse a single .eml file into an unlabelled staging record."""
    try:
        with open(eml_path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
    except Exception as exc:
        print(f"  SKIP {eml_path.name}: {exc}", file=sys.stderr)
        return None

    # Extract plain-text body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        if msg.get_content_type() == "text/plain":
            body = msg.get_content()

    # Collect headers (lower-cased keys)
    headers: dict[str, str] = {}
    for key in ("authentication-results", "from", "reply-to", "list-unsubscribe", "precedence"):
        val = msg.get(key)
        if val:
            headers[key] = str(val)

    # Ensure minimum required headers
    if "from" not in headers:
        from_val = msg.get("from", "")
        if from_val:
            headers["from"] = str(from_val)

    # Generate a stable ID from the Message-ID or filename
    message_id = msg.get("message-id", "")
    if message_id:
        record_id = hashlib.sha256(message_id.encode()).hexdigest()[:12]
    else:
        record_id = hashlib.sha256(eml_path.name.encode()).hexdigest()[:12]

    return {
        "id": record_id,
        "provider": "gmail",  # default, can be changed during labelling
        "headers": headers,
        "subject": str(msg.get("subject", "")),
        "body_text": body if isinstance(body, str) else str(body),
        "_labelled": False,
    }


def import_eml_dir(eml_dir: Path) -> int:
    """Import .eml files from a directory into the staging file. Returns count imported."""
    eml_files = sorted(eml_dir.glob("*.eml"))
    if not eml_files:
        print(f"No .eml files found in {eml_dir}", file=sys.stderr)
        return 0

    # Load existing staging IDs to avoid duplicates
    existing_ids = _load_staged_ids()

    count = 0
    with open(STAGING_PATH, "a", encoding="utf-8") as f:
        for eml_path in eml_files:
            record = _parse_eml(eml_path)
            if record is None:
                continue
            if record["id"] in existing_ids:
                continue
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            existing_ids.add(record["id"])
            count += 1

    print(f"Imported {count} emails from {eml_dir} -> {STAGING_PATH}")
    return count


def import_raw_jsonl(jsonl_path: Path) -> int:
    """Import from a JSONL of raw unlabelled emails into staging. Returns count imported."""
    existing_ids = _load_staged_ids()
    count = 0

    with open(jsonl_path, encoding="utf-8") as src, \
         open(STAGING_PATH, "a", encoding="utf-8") as dst:
        for line_num, raw_line in enumerate(src, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                print(f"  SKIP line {line_num}: invalid JSON: {exc}", file=sys.stderr)
                continue

            # Ensure minimum fields for staging
            if "id" not in record:
                record["id"] = hashlib.sha256(raw_line.encode()).hexdigest()[:12]
            if record["id"] in existing_ids:
                continue

            record.setdefault("provider", "gmail")
            record.setdefault("headers", {})
            record.setdefault("subject", "")
            record.setdefault("body_text", "")
            record["_labelled"] = False

            dst.write(json.dumps(record, ensure_ascii=False) + "\n")
            existing_ids.add(record["id"])
            count += 1

    print(f"Imported {count} records from {jsonl_path} -> {STAGING_PATH}")
    return count


def _load_staged_ids() -> set[str]:
    """Return all IDs already in the staging file."""
    ids: set[str] = set()
    if STAGING_PATH.is_file():
        with open(STAGING_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ids.add(rec.get("id", ""))
                except json.JSONDecodeError:
                    pass
    return ids


# ---------------------------------------------------------------------------
# Load already-labelled IDs (from labels.jsonl)
# ---------------------------------------------------------------------------


def _load_labelled_ids(labels_path: Path) -> set[str]:
    """Return IDs already present in the labelled output file."""
    ids: set[str] = set()
    if labels_path.is_file():
        with open(labels_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ids.add(rec.get("id", ""))
                except json.JSONDecodeError:
                    pass
    return ids


# ---------------------------------------------------------------------------
# Interactive labelling
# ---------------------------------------------------------------------------


def _prompt(message: str, valid: set[str] | None = None, allow_empty: bool = False) -> str:
    """Prompt the user for input, retrying on invalid values."""
    while True:
        try:
            value = input(message).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return "q"
        if not value and allow_empty:
            return ""
        if not value:
            continue
        if valid is not None and value not in valid:
            print(f"  Invalid choice. Options: {', '.join(sorted(valid))}")
            continue
        return value


def _prompt_yes_no(message: str) -> bool:
    """Prompt for a yes/no answer."""
    val = _prompt(f"{message} (y/n): ", valid={"y", "n", "yes", "no", "q"})
    if val == "q":
        raise KeyboardInterrupt
    return val in ("y", "yes")


def _prompt_list(message: str) -> list[str]:
    """Prompt for a comma-separated list of strings (or empty)."""
    raw = input(f"{message} (comma-separated, or empty): ").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _display_email(record: dict, index: int, total: int) -> None:
    """Print an email for labelling."""
    sep = "=" * 72
    print(f"\n{sep}")
    print(f"  Email {index}/{total}  |  ID: {record['id']}  |  Provider: {record.get('provider', '?')}")
    print(sep)
    print(f"  From:    {record.get('headers', {}).get('from', '(unknown)')}")
    print(f"  Subject: {record.get('subject', '(no subject)')}")
    print("-" * 72)

    body = record.get("body_text", "")
    # Truncate very long bodies for display
    lines = body.split("\n")
    if len(lines) > 40:
        for line in lines[:35]:
            print(f"  {line}")
        print(f"  ... ({len(lines) - 35} more lines)")
    else:
        for line in lines:
            print(f"  {line}")

    print("-" * 72)

    # Show relevant headers
    headers = record.get("headers", {})
    auth = headers.get("authentication-results")
    if auth:
        # Truncate long auth headers
        if len(auth) > 120:
            auth = auth[:117] + "..."
        print(f"  Auth: {auth}")
    if headers.get("list-unsubscribe"):
        print(f"  List-Unsubscribe: {headers['list-unsubscribe']}")
    if headers.get("precedence"):
        print(f"  Precedence: {headers['precedence']}")
    if headers.get("reply-to"):
        print(f"  Reply-To: {headers['reply-to']}")
    print()


def _label_one(record: dict, schema: dict, validator: jsonschema.Draft202012Validator,
               index: int, total: int) -> dict | None:
    """Present one email and collect labels. Returns a labelled record, or None to skip/quit."""
    _display_email(record, index, total)

    print("  Commands: [s]kip  [q]uit")
    print()

    # --- is_recruiter ---
    answer = _prompt("  Is this from a recruiter? (y/n/s/q): ",
                     valid={"y", "n", "yes", "no", "s", "q"})
    if answer == "q":
        return None
    if answer == "s":
        print("  >> Skipped.")
        return "SKIP"
    is_recruiter = answer in ("y", "yes")

    # --- intent ---
    print("\n  Intent:")
    print("    1 = new_requirement    2 = resume_request    3 = follow_up")
    print("    4 = interview          5 = other")
    intent_key = _prompt("  Intent (1-5): ", valid=set(INTENT_CHOICES) | {"s", "q"})
    if intent_key == "q":
        return None
    if intent_key == "s":
        print("  >> Skipped.")
        return "SKIP"
    intent = INTENT_CHOICES[intent_key]

    # --- fields ---
    print("\n  Extracted fields (press Enter to skip optional fields):")

    role = input("  Role/title: ").strip() or None
    skills = _prompt_list("  Skills")
    exp_raw = input("  Min years experience (number or empty): ").strip()
    min_years_experience = float(exp_raw) if exp_raw else None
    location = input("  Location: ").strip() or None
    candidate_names = _prompt_list("  Candidate names mentioned")
    resume_requested = _prompt_yes_no("  Resume explicitly requested?")

    fields = {
        "role": role,
        "skills": skills,
        "min_years_experience": min_years_experience,
        "location": location,
        "candidate_names": candidate_names,
        "resume_requested": resume_requested,
    }

    # --- expected_profile_ids ---
    expected_profile_ids: list[int] = []
    if is_recruiter and intent in ("new_requirement", "resume_request"):
        ids_raw = input("  Expected profile IDs (comma-separated integers): ").strip()
        if ids_raw:
            try:
                expected_profile_ids = [int(x.strip()) for x in ids_raw.split(",") if x.strip()]
            except ValueError:
                print("  WARNING: Could not parse profile IDs. Enter them as comma-separated integers.")
                expected_profile_ids = []

        if not expected_profile_ids:
            print(f"  WARNING: expected_profile_ids is required for recruiter + {intent}.")
            ids_raw = input("  Expected profile IDs (required): ").strip()
            if ids_raw:
                try:
                    expected_profile_ids = [int(x.strip()) for x in ids_raw.split(",") if x.strip()]
                except ValueError:
                    pass
    else:
        ids_raw = input("  Expected profile IDs (comma-separated, or empty): ").strip()
        if ids_raw:
            try:
                expected_profile_ids = [int(x.strip()) for x in ids_raw.split(",") if x.strip()]
            except ValueError:
                pass

    # --- notes ---
    notes = input("  Notes (free text, or empty): ").strip()

    # --- provider ---
    provider = record.get("provider", "gmail")

    # --- build the labelled record ---
    labelled = {
        "id": record["id"],
        "provider": provider,
        "headers": record.get("headers", {}),
        "subject": record.get("subject", ""),
        "body_text": record.get("body_text", ""),
        "is_recruiter": is_recruiter,
        "intent": intent,
        "fields": fields,
        "expected_profile_ids": expected_profile_ids,
        "notes": notes,
    }

    # Ensure required headers exist (fill stubs if missing)
    if "authentication-results" not in labelled["headers"]:
        labelled["headers"]["authentication-results"] = "none"
    if "from" not in labelled["headers"]:
        labelled["headers"]["from"] = "(unknown)"

    # --- validate before accepting ---
    errors = list(validator.iter_errors(labelled))
    if errors:
        print("\n  VALIDATION ERRORS:")
        for err in errors:
            path = ".".join(str(p) for p in err.absolute_path) if err.absolute_path else "(root)"
            print(f"    {path}: {err.message}")
        retry = _prompt_yes_no("  Record has errors. Save anyway?")
        if not retry:
            print("  >> Discarded. You can re-label this email next time.")
            return "SKIP"

    return labelled


def run_labelling_session(
    labels_path: Path | None = None,
    only_ids: list[str] | None = None,
    banner: str = "LABELLING SESSION",
) -> int:
    """Run the interactive labelling session. Returns count of labels written.

    ``only_ids`` restricts the session to those staged records, which is how the second
    agreement pass re-labels exactly the pinned slice. Records are always read from staging,
    never from an existing labels file, so a second pass cannot see the first pass's answers.
    """
    labels_path = labels_path or LABELS_PATH

    if not STAGING_PATH.is_file():
        print(
            "No staging file found. Import emails first:\n"
            "  python eval/label_cli.py --import-dir path/to/eml/files\n"
            "  python eval/label_cli.py --import-jsonl path/to/raw.jsonl",
            file=sys.stderr,
        )
        return 0

    # Load staging records
    staging: list[dict] = []
    with open(STAGING_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                staging.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not staging:
        print("Staging file is empty.", file=sys.stderr)
        return 0

    if only_ids is not None:
        wanted = set(only_ids)
        staging = [r for r in staging if r["id"] in wanted]
        missing = wanted - {r["id"] for r in staging}
        if missing:
            print(
                f"WARNING: {len(missing)} slice id(s) are not in staging and will be skipped: "
                f"{', '.join(sorted(missing)[:8])}",
                file=sys.stderr,
            )
        if not staging:
            print(
                "None of the pinned slice ids are in the staging file. The slice was pinned "
                "from labels.jsonl, so staging must still hold those raw emails.",
                file=sys.stderr,
            )
            return 0

    # Load already-labelled IDs to skip
    labelled_ids = _load_labelled_ids(labels_path)
    unlabelled = [r for r in staging if r["id"] not in labelled_ids]

    if not unlabelled:
        print(f"All {len(staging)} emails have been labelled. Nothing to do.")
        return 0

    print(f"\n{'=' * 72}")
    print(f"  {banner}")
    print(
        f"  Total staged: {len(staging)}  |  Already labelled: {len(labelled_ids)}"
        f"  |  Remaining: {len(unlabelled)}"
    )
    print(f"  Output: {labels_path}")
    print(f"{'=' * 72}")

    schema = load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    count = 0

    for i, record in enumerate(unlabelled, start=1):
        result = _label_one(record, schema, validator, i, len(unlabelled))

        if result is None:
            # User quit
            print(f"\n  Session ended. Labelled {count} emails this session.")
            print(f"  Total labelled: {len(labelled_ids) + count}/{len(staging)}")
            break

        if result == "SKIP":
            continue

        # Append to labels file
        with open(labels_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        count += 1
        labelled_ids.add(record["id"])
        print(f"  >> Saved. ({len(labelled_ids)}/{len(staging)} total)")

    else:
        print(f"\n  All emails labelled! {count} new labels written this session.")

    return count


# ---------------------------------------------------------------------------
# Anonymise
# ---------------------------------------------------------------------------

# Patterns for emails, names, domains
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_DOMAIN_RE = re.compile(r"@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")

# Synthetic replacements
_SYNTH_DOMAINS = [
    "acme.example.com", "globex.example.com", "initech.example.com",
    "umbrella.example.com", "cyberdyne.example.com", "soylent.example.com",
    "weyland.example.com", "tyrell.example.com", "oscorp.example.com",
    "stark.example.com",
]

_SYNTH_NAMES = [
    "Alex Morgan", "Sam Chen", "Jordan Patel", "Riley Kumar", "Casey Singh",
    "Drew Sharma", "Robin Das", "Avery Gupta", "Charlie Reddy", "Pat Nair",
    "Taylor Rao", "Morgan Iyer", "Jamie Desai", "Kai Mehta", "Quinn Shah",
]


def anonymise_dataset(input_path: Path, output_path: Path) -> int:
    """Replace real emails, names and domains with synthetic equivalents.

    Uses deterministic hashing so the same input always maps to the same output,
    preserving consistency within a record.
    """
    domain_map: dict[str, str] = {}
    email_map: dict[str, str] = {}
    record_count = 0

    with open(input_path, encoding="utf-8") as src, \
         open(output_path, "w", encoding="utf-8") as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Anonymise the record as a JSON string for simplicity
            text = json.dumps(record, ensure_ascii=False)

            # Find and replace all email addresses
            for addr in set(_EMAIL_RE.findall(text)):
                if addr not in email_map:
                    idx = len(email_map) % len(_SYNTH_NAMES)
                    name_part = _SYNTH_NAMES[idx].lower().replace(" ", ".")
                    domain_match = _DOMAIN_RE.search(addr)
                    domain = domain_match.group(1) if domain_match else "example.com"
                    if domain not in domain_map:
                        domain_map[domain] = _SYNTH_DOMAINS[len(domain_map) % len(_SYNTH_DOMAINS)]
                    email_map[addr] = f"{name_part}@{domain_map[domain]}"
                text = text.replace(addr, email_map[addr])

            # Re-parse and write
            try:
                anon_record = json.loads(text)
                dst.write(json.dumps(anon_record, ensure_ascii=False) + "\n")
                record_count += 1
            except json.JSONDecodeError:
                # If anonymisation broke the JSON, write original
                dst.write(line + "\n")
                record_count += 1

    print(f"Anonymised {record_count} records -> {output_path}")
    print(f"  {len(email_map)} email addresses replaced")
    print(f"  {len(domain_map)} domains mapped")
    return record_count


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Label emails for the evaluation dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Workflow:
              1. Import:   python eval/label_cli.py --import-dir path/to/eml/files
                      or:  python eval/label_cli.py --import-jsonl path/to/raw.jsonl
              2. Label:    python eval/label_cli.py
              3. Validate: python eval/validate_dataset.py eval/dataset/labels.jsonl --no-count-check
              4. Anonymise: python eval/label_cli.py --anonymise eval/dataset/labels.jsonl -o anon.jsonl

            Agreement check (run after ~30 labels, BEFORE labelling the rest):
              a. Pin slice:  python eval/agreement.py --select --size 30
              b. Re-label:   python eval/label_cli.py --second-pass
              c. Report:     python eval/agreement.py
        """),
    )
    parser.add_argument(
        "--import-dir",
        type=Path,
        metavar="DIR",
        help="Import .eml files from this directory into the staging file.",
    )
    parser.add_argument(
        "--import-jsonl",
        type=Path,
        metavar="FILE",
        help="Import raw unlabelled emails from a JSONL file into staging.",
    )
    parser.add_argument(
        "--anonymise",
        type=Path,
        metavar="FILE",
        help="Anonymise a labelled dataset: replace real emails/domains with synthetic ones.",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        metavar="FILE",
        help="Output path for --anonymise (default: <input>.anon.jsonl).",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=None,
        help=f"Path to the labels output file (default: {LABELS_PATH}).",
    )
    parser.add_argument(
        "--second-pass",
        action="store_true",
        help=(
            "Re-label the pinned agreement slice, blind, into labels.pass2.jsonl. "
            "Pin the slice first with: python eval/agreement.py --select"
        ),
    )

    args = parser.parse_args(argv)

    # --- Import mode ---
    if args.import_dir:
        if not args.import_dir.is_dir():
            print(f"Not a directory: {args.import_dir}", file=sys.stderr)
            return 1
        import_eml_dir(args.import_dir)
        return 0

    if args.import_jsonl:
        if not args.import_jsonl.is_file():
            print(f"File not found: {args.import_jsonl}", file=sys.stderr)
            return 1
        import_raw_jsonl(args.import_jsonl)
        return 0

    # --- Anonymise mode ---
    if args.anonymise:
        if not args.anonymise.is_file():
            print(f"File not found: {args.anonymise}", file=sys.stderr)
            return 1
        output = args.output
        if output is None:
            output = args.anonymise.with_suffix(".anon.jsonl")
        anonymise_dataset(args.anonymise, output)
        return 0

    # --- Second agreement pass ---
    if args.second_pass:
        try:
            from eval.agreement import read_slice
        except ModuleNotFoundError:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from eval.agreement import read_slice
        try:
            slice_ids = read_slice()
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        run_labelling_session(
            args.labels or PASS2_PATH,
            only_ids=slice_ids,
            banner=f"SECOND PASS (agreement slice, {len(slice_ids)} emails) - label blind",
        )
        return 0

    # --- Label mode (default) ---
    labels_path = args.labels or LABELS_PATH
    run_labelling_session(labels_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
