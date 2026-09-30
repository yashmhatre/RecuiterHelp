# P1-03: Profile extraction from resume text and the review CLI

**Phase:** 1 · **Est:** 2 days · **Blocked by:** nothing

## Owns
- `profiles/import_resumes.py`
- `profiles/review_profiles.py`
- `config/prompts/extract_profile.txt`
- `tests/test_import_resumes.py`

## Reads
- `docs/CONTRACTS.md` §1 (`Candidate`, `Profile`, `Resume`), §3 (JSON model call rules)
- `docs/schema.reference.sql` for the `reviewed` flag

## Context
Populates candidates and profiles from a folder of resumes. The plan requires every imported
profile to be corrected by hand, so import writes `reviewed = false` and the review CLI is the
only thing that flips it.

## Scope
**Do**
- `import_resumes.py --dir resumes/`: for each file, extract `name`, `email`, `phone`,
  `location`, `notice_period_days`, `title`, `skills`, `years_experience`, `summary` into a
  strict JSON schema.
- One candidate per person (matched on email, then on normalised name), many profiles. A resume
  that reads as two distinct role profiles creates two `profiles` rows under one candidate —
  this is requirement 2.
- Every inserted profile gets `reviewed = false`; a resume row is created with `is_current = true`.
- Re-running the importer on the same folder must not duplicate candidates or profiles.
- `review_profiles.py`: terminal review of unreviewed profiles side by side with the resume text,
  editable fields, then `reviewed = true`. Refuse to mark reviewed while required fields are empty.

**Do not**
- Generate embeddings (P1-04) or parse files yourself — take text as input.

## Independence
Take **both** the parser and the model client as injected callables, defaulting to the real ones.
Tests pass a fake parser returning canned text and a fake model returning canned JSON, so this
ticket needs neither P1-02 nor P0-02 merged. DB writes go through an injected session against a
throwaway database, or a fake repo.

## Acceptance criteria
- [ ] One resume describing two roles produces one candidate and two profiles
- [ ] Two resumes for the same person produce one candidate with two profiles
- [ ] Re-running the import is idempotent — no duplicate candidates, profiles or resume rows
- [ ] Every imported profile lands with `reviewed = false`
- [ ] A model response failing the schema skips that file with a named error and continues
- [ ] The review CLI will not set `reviewed = true` with `title` or `skills` empty
- [ ] All real candidate profiles imported and reviewed by hand once

## Done when
`pytest tests/test_import_resumes.py` passes with fake parser and fake model.
