-- Frozen reference DDL for v1. Column names are final.
--
-- This file is a CONTRACT, not a migration. Ticket P1-01 turns it into numbered
-- migrations under db/migrations/. Every other ticket reads shapes from here and
-- builds its own fixtures, so no ticket waits on P1-01 to be testable.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------------------------------------------------------------- candidates

CREATE TABLE candidates (
    id                 SERIAL PRIMARY KEY,
    name               TEXT        NOT NULL,
    email              TEXT        NOT NULL UNIQUE,
    phone              TEXT,
    location           TEXT,
    notice_period_days INTEGER,
    availability       TEXT,
    -- Entry/Mid/Senior/Staff/Principal/Executive, matching forge-jd-intelligence's enum so a
    -- candidate and a requirement are scored against the same ladder.
    seniority          TEXT,
    active             BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One candidate, many role profiles. Requirement 2.
CREATE TABLE profiles (
    id               SERIAL PRIMARY KEY,
    candidate_id     INTEGER     NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    title            TEXT        NOT NULL,
    skills           TEXT[]      NOT NULL DEFAULT '{}',
    years_experience NUMERIC(4,1) NOT NULL DEFAULT 0,
    summary          TEXT        NOT NULL DEFAULT '',
    embedding        VECTOR(768),            -- nomic-embed-text; 1024 if bge-m3
    reviewed         BOOLEAN     NOT NULL DEFAULT FALSE,  -- human-checked after import
    active           BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX profiles_embedding_idx ON profiles
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX profiles_skills_idx    ON profiles USING gin (skills);
CREATE INDEX profiles_candidate_idx ON profiles (candidate_id);

CREATE TABLE resumes (
    id          SERIAL PRIMARY KEY,
    profile_id  INTEGER     NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    file_path   TEXT        NOT NULL,
    version     INTEGER     NOT NULL DEFAULT 1,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_current  BOOLEAN     NOT NULL DEFAULT TRUE
);

-- At most one current resume per profile.
CREATE UNIQUE INDEX resumes_one_current_idx ON resumes (profile_id)
    WHERE is_current;

-- Profile cap per candidate, from the client: "Max 5 to 6 profiles per candidate for experience
-- resources and max 3 profiles for Jr and Mid level experience candidates."
--
-- Enforced in application code rather than as a CHECK constraint, because the limit depends on
-- a column in another table (candidates.seniority) and the message needs to name the person and
-- their level to be actionable. See prototype/store.py: PROFILE_CAP_SENIOR, PROFILE_CAP_JUNIOR.
-- The reason for the cap is that a candidate with nine near-identical CVs makes matching worse,
-- not better.

-- ---------------------------------------------------------------- mailbox

CREATE TABLE mailbox_state (
    provider     TEXT        NOT NULL,   -- 'gmail' | 'outlook'
    address      TEXT        NOT NULL,
    sync_cursor  TEXT,                   -- Gmail history id or Graph delta link
    last_run_at  TIMESTAMPTZ,
    PRIMARY KEY (provider, address)
);

CREATE TABLE emails (
    id                  SERIAL PRIMARY KEY,
    provider            TEXT        NOT NULL,
    provider_message_id TEXT        NOT NULL,
    thread_id           TEXT        NOT NULL,
    sender              TEXT        NOT NULL,
    subject             TEXT,
    received_at         TIMESTAMPTZ NOT NULL,
    auth_result         TEXT        NOT NULL,   -- AuthResult
    auth_flags          TEXT[]      NOT NULL DEFAULT '{}',
    status              TEXT        NOT NULL,   -- EmailStatus
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_message_id)      -- idempotent re-fetch
);

CREATE INDEX emails_thread_idx ON emails (thread_id);

-- ---------------------------------------------------------------- pipeline output

CREATE TABLE classifications (
    id           SERIAL PRIMARY KEY,
    email_id     INTEGER     NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    is_recruiter BOOLEAN     NOT NULL,
    intent       TEXT        NOT NULL,   -- Intent
    fields       JSONB       NOT NULL DEFAULT '{}',
    confidence   NUMERIC(4,3) NOT NULL,
    model        TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE matches (
    id         SERIAL PRIMARY KEY,
    email_id   INTEGER     NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    profile_id INTEGER     NOT NULL REFERENCES profiles(id),
    score      NUMERIC(4,3) NOT NULL,
    reason     TEXT        NOT NULL DEFAULT '',
    stage      TEXT        NOT NULL,     -- 'hybrid' | 'rerank'
    selected   BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX matches_email_idx ON matches (email_id);

CREATE TABLE drafts (
    id                SERIAL PRIMARY KEY,
    email_id          INTEGER     NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    provider_draft_id TEXT,
    profiles_used     INTEGER[]   NOT NULL DEFAULT '{}',
    attachments       JSONB       NOT NULL DEFAULT '[]',
    validation        JSONB       NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- pilot feedback (Phase 4)

CREATE TABLE draft_feedback (
    id          SERIAL PRIMARY KEY,
    draft_id    INTEGER     NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    outcome     TEXT        NOT NULL,   -- 'sent_as_is' | 'edited' | 'discarded'
    wrong_match BOOLEAN     NOT NULL DEFAULT FALSE,
    notes       TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
