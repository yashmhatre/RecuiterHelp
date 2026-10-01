"""SQLite store for the prototype.

Column names deliberately mirror ``docs/schema.reference.sql`` so that moving to real Postgres
later (ticket P1-01) is a migration rather than a rewrite. What is left out compared to the
reference DDL: the ``embedding`` vector column, since the prototype matches by skill overlap and
an optional model re-rank rather than a vector index. At a couple of dozen profiles, brute force
over everything beats an index and needs no embedding model.

One candidate has many profiles, and each profile has its own current resume. That is
requirement 2, and it is the part of the data model worth getting right even in a prototype.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

PROTOTYPE_DIR = Path(__file__).resolve().parent
DATA_DIR = PROTOTYPE_DIR / "data"
DB_PATH = DATA_DIR / "prototype.db"
RESUME_DIR = DATA_DIR / "resumes"

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT    NOT NULL,
    email              TEXT    NOT NULL UNIQUE,
    phone              TEXT,
    location           TEXT,
    notice_period_days INTEGER,
    availability       TEXT,
    -- Drives the profile cap below. Entry/Mid/Senior/Staff/Principal/Executive, matching the
    -- enum in forge-jd-intelligence so both sides of a match speak the same ladder.
    seniority          TEXT,
    active             INTEGER NOT NULL DEFAULT 1,
    created_at         TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id     INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    title            TEXT    NOT NULL,
    skills           TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    years_experience REAL    NOT NULL DEFAULT 0,
    summary          TEXT    NOT NULL DEFAULT '',
    reviewed         INTEGER NOT NULL DEFAULT 1,
    active           INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS resumes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    file_path   TEXT    NOT NULL,
    filename    TEXT    NOT NULL,
    version     INTEGER NOT NULL DEFAULT 1,
    uploaded_at TEXT    NOT NULL,
    is_current  INTEGER NOT NULL DEFAULT 1
);

-- One current resume per profile, same invariant as the reference DDL.
CREATE UNIQUE INDEX IF NOT EXISTS resumes_one_current
    ON resumes (profile_id) WHERE is_current = 1;

CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    subject      TEXT,
    sender       TEXT,
    status       TEXT    NOT NULL,
    payload      TEXT    NOT NULL,   -- the whole pipeline result, as JSON
    created_at   TEXT    NOT NULL
);

-- One classification verdict per mailbox message, so the inbox queue pays for a model call
-- once per email rather than once per page refresh. Keyed on the provider's message id, which
-- is stable for the life of the message.
CREATE TABLE IF NOT EXISTS triage (
    message_id   TEXT    PRIMARY KEY,
    verdict      TEXT    NOT NULL,   -- recruiter | not_recruiter | needs_review
    is_recruiter INTEGER NOT NULL,
    confidence   REAL    NOT NULL,
    intent       TEXT,
    role         TEXT,
    fields       TEXT    NOT NULL,   -- the full extraction, as JSON
    backend      TEXT,
    classified_at TEXT   NOT NULL
);
"""


#: Maximum profiles per candidate, from the client: "Max 5 to 6 profiles per candidate for
#: experience resources and max 3 profiles for Jr and Mid level experience candidates."
#: Enforced at insert rather than left as guidance, because the reason for the cap is that a
#: candidate with nine near-identical CVs makes matching worse, not better.
PROFILE_CAP_SENIOR = 6
PROFILE_CAP_JUNIOR = 3

#: Which seniorities count as junior or mid for the cap.
JUNIOR_SENIORITIES = frozenset({"entry", "junior", "jr", "mid", "mid-level", "intermediate"})


class ProfileCapReached(ValueError):
    """Raised when a candidate already holds the maximum number of profiles allowed."""


def profile_cap_for(seniority: str | None) -> int:
    """The cap that applies to this candidate.

    Unknown or unset seniority gets the senior cap: refusing a profile because nobody recorded
    a level would be a worse failure than allowing one too many.
    """
    level = (seniority or "").strip().lower()
    return PROFILE_CAP_JUNIOR if level in JUNIOR_SENIORITIES else PROFILE_CAP_SENIOR


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def connect(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """A connection with foreign keys on and rows as dicts."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


#: Columns added after the first release. CREATE TABLE IF NOT EXISTS silently skips an existing
#: table, so a new column never appears on a database that already has rows -- which is every
#: database anyone is actually using.
_ADDED_COLUMNS = (
    ("candidates", "seniority", "TEXT"),
)


def init_db(db_path: Path | str | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        for table, column, column_type in _ADDED_COLUMNS:
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


# ---------------------------------------------------------------------------
# Candidates and profiles
# ---------------------------------------------------------------------------


def add_candidate_with_profile(
    *,
    name: str,
    email: str,
    phone: str | None,
    location: str | None,
    notice_period_days: int | None,
    availability: str | None,
    title: str,
    seniority: str | None = None,
    skills: list[str],
    years_experience: float,
    summary: str,
    db_path: Path | str | None = None,
) -> tuple[int, int]:
    """Create or reuse a candidate, then add a profile under them.

    Reuse rather than reject on a duplicate email, because the natural way to add a second role
    profile for someone is to submit the form again with the same person and a different title.
    """
    with connect(db_path) as conn:
        row = conn.execute("SELECT id FROM candidates WHERE email = ?", (email.strip().lower(),)).fetchone()
        if row:
            candidate_id = row["id"]
            conn.execute(
                """UPDATE candidates SET name = ?, phone = ?, location = ?,
                   notice_period_days = ?, availability = ?,
                   seniority = COALESCE(?, seniority) WHERE id = ?""",
                (name.strip(), phone, location, notice_period_days, availability,
                 seniority, candidate_id),
            )
        else:
            cursor = conn.execute(
                """INSERT INTO candidates
                   (name, email, phone, location, notice_period_days, availability,
                    seniority, active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    name.strip(),
                    email.strip().lower(),
                    phone,
                    location,
                    notice_period_days,
                    availability,
                    seniority,
                    now(),
                ),
            )
            candidate_id = int(cursor.lastrowid or 0)

        # Cap check, after the candidate exists so the error can name their level.
        level = conn.execute(
            "SELECT seniority FROM candidates WHERE id = ?", (candidate_id,)
        ).fetchone()["seniority"]
        held = conn.execute(
            "SELECT COUNT(*) AS n FROM profiles WHERE candidate_id = ? AND active = 1",
            (candidate_id,),
        ).fetchone()["n"]
        cap = profile_cap_for(level)
        if held >= cap:
            raise ProfileCapReached(
                f"{name.strip()} already has {held} profiles. The limit is {cap} for "
                f"{level or 'unspecified seniority'} candidates. Remove or deactivate one first."
            )

        cursor = conn.execute(
            """INSERT INTO profiles
               (candidate_id, title, skills, years_experience, summary, reviewed, active, created_at)
               VALUES (?, ?, ?, ?, ?, 1, 1, ?)""",
            (
                candidate_id,
                title.strip(),
                json.dumps([s.strip().lower() for s in skills if s.strip()]),
                float(years_experience or 0),
                summary.strip(),
                now(),
            ),
        )
        return candidate_id, int(cursor.lastrowid or 0)


def attach_resume(
    profile_id: int, file_path: Path | str, filename: str, db_path: Path | str | None = None
) -> int:
    """Store a resume against a profile, demoting any previous current one."""
    with connect(db_path) as conn:
        previous = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS v FROM resumes WHERE profile_id = ?", (profile_id,)
        ).fetchone()["v"]
        conn.execute("UPDATE resumes SET is_current = 0 WHERE profile_id = ?", (profile_id,))
        cursor = conn.execute(
            """INSERT INTO resumes (profile_id, file_path, filename, version, uploaded_at, is_current)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (profile_id, str(file_path), filename, previous + 1, now()),
        )
        return int(cursor.lastrowid or 0)


def list_profiles(db_path: Path | str | None = None) -> list[dict]:
    """Every active profile with its candidate and current resume, for matching and the UI."""
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT p.id AS profile_id, p.title, p.skills, p.years_experience, p.summary,
                   c.id AS candidate_id, c.name, c.email, c.phone, c.location,
                   c.notice_period_days, c.availability, c.seniority,
                   r.id AS resume_id, r.file_path, r.filename
            FROM profiles p
            JOIN candidates c ON c.id = p.candidate_id
            LEFT JOIN resumes r ON r.profile_id = p.id AND r.is_current = 1
            WHERE p.active = 1 AND c.active = 1
            ORDER BY c.name, p.title
            """
        ).fetchall()

    profiles = []
    for row in rows:
        item = dict(row)
        item["skills"] = json.loads(item["skills"] or "[]")
        profiles.append(item)
    return profiles


def get_profile(profile_id: int, db_path: Path | str | None = None) -> dict | None:
    return next((p for p in list_profiles(db_path) if p["profile_id"] == profile_id), None)


def delete_candidate(candidate_id: int, db_path: Path | str | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))


def count_profiles(db_path: Path | str | None = None) -> int:
    with connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM profiles WHERE active = 1").fetchone()["n"]


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


def save_run(
    *, subject: str, sender: str, status: str, payload: dict, db_path: Path | str | None = None
) -> int:
    with connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO runs (subject, sender, status, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (subject, sender, status, json.dumps(payload, default=str), now()),
        )
        return int(cursor.lastrowid or 0)


def list_runs(limit: int = 30, db_path: Path | str | None = None) -> list[dict]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, subject, sender, status, created_at FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_run(run_id: int, db_path: Path | str | None = None) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item


# ---------------------------------------------------------------------------
# Triage cache
#
# The inbox queue classifies every message that survives the two free stages, so it can show
# only genuine recruiter mail. That is a model call per email, and a page refresh must not
# repeat it: fifteen leads a day is comfortably inside a free tier, fifteen leads re-read on
# every rerender is not.
# ---------------------------------------------------------------------------


def save_triage(
    *,
    message_id: str,
    verdict: str,
    fields: dict,
    backend: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    """Record one classification verdict. Re-classifying a message replaces the old verdict."""
    with connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO triage (message_id, verdict, is_recruiter, confidence, "
            "intent, role, fields, backend, classified_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                message_id,
                verdict,
                1 if fields.get("is_recruiter") else 0,
                float(fields.get("confidence") or 0.0),
                fields.get("intent"),
                fields.get("role"),
                json.dumps(fields, default=str),
                backend,
                now(),
            ),
        )


def get_triage(message_ids: Sequence[str], db_path: Path | str | None = None) -> dict[str, dict]:
    """Cached verdicts for these message ids, keyed by id. Missing ids are simply absent."""
    ids = list(message_ids)
    if not ids:
        return {}
    with connect(db_path) as conn:
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT * FROM triage WHERE message_id IN ({placeholders})", ids
        ).fetchall()
    out = {}
    for row in rows:
        item = dict(row)
        item["fields"] = json.loads(item["fields"])
        item["is_recruiter"] = bool(item["is_recruiter"])
        out[item["message_id"]] = item
    return out


def clear_triage(db_path: Path | str | None = None) -> int:
    """Forget every cached verdict, so the next fetch re-classifies. For when the prompt changes."""
    with connect(db_path) as conn:
        cursor = conn.execute("DELETE FROM triage")
        return cursor.rowcount or 0
