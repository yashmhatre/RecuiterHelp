# P1-05: Labelled email dataset (200-300 emails)

**Phase:** 1 · **Est:** 3 days · **Blocked by:** nothing · **Status:** tooling done, labelling + agreement pass outstanding

## Owns
- `eval/dataset/schema.json`
- `eval/dataset/labels.example.jsonl` (synthetic, committed)
- `eval/dataset/labels.jsonl` (real, **gitignored**)
- `eval/label_cli.py`
- `eval/validate_dataset.py`
- `tests/test_dataset_schema.py`

## Reads
- `docs/CONTRACTS.md` §1 (`Intent`, `ExtractedFields`)

## Context
Every target in the plan is measured against this set. It is the highest-value and slowest item
in Phase 1, it blocks nothing, and it should start on day one and run in parallel with everything
else. Labelling is the bottleneck, not the code.

## Scope
**Do**
- One JSONL record per email: `id`, `provider`, raw headers needed for auth checks, `subject`,
  `body_text`, and the ground truth: `is_recruiter`, `intent`, `fields` (the `ExtractedFields`
  shape), `expected_profile_ids`, plus `notes`.
- `schema.json` validating every record; `validate_dataset.py` fails on a bad or duplicate record.
- `label_cli.py`: export from the mailbox, then label one email at a time with keyboard shortcuts,
  resumable, appending as it goes.
- Compose a set that reflects reality, not just easy cases. Aim for roughly:
  - 100-150 genuine recruiter emails spread across all five intents
  - 50-80 non-recruiter: newsletters, job alerts, auto-replies, vendor spam, own sent mail
  - 20-30 hard cases: vague one-liners, in-house HR, agency spam that reads genuine,
    forwarded requirements, threads where only the third reply carries the requirement
- Label a 30-email slice **twice** and report the disagreement rate. If two passes disagree more
  than 5% of the time, a 95% accuracy target is not measurable — fix the label definitions first
  and say so in the PR.
- `labels.example.jsonl`: ~10 synthetic records, no real senders, for other tickets' tests.

**Do not**
- Commit real emails, real sender addresses or real candidate names. Ship a
  `--anonymise` mode and use it for anything committed.

## Independence
Pure data work. Every other ticket that needs email fixtures uses `labels.example.jsonl` or its
own inline fixtures, never the real file.

## Acceptance criteria
- [ ] 200-300 real emails labelled, all passing `validate_dataset.py`
- [ ] All five intents present; non-recruiter share is at least 25% of the set
- [ ] The 30-email double-labelling pass is reported, with disagreement at or under 5%
- [ ] `labels.jsonl` is gitignored; `labels.example.jsonl` contains no real data
- [ ] `expected_profile_ids` filled for every `new_requirement` and `resume_request` email
- [ ] The label CLI resumes correctly after being interrupted

## Done when
`python eval/validate_dataset.py eval/dataset/labels.jsonl` passes and the count is in range.

## Outcome so far

Tooling built (schema, validator, labelling CLI, 10 synthetic example records). 46 tests.

**Still outstanding:**

- The 200-300 real emails are not labelled. The validator enforces the count window, all five
  intents and the 25% non-recruiter share, so it fails until they are.
- **No double-labelling support.** The ticket requires a 30-email slice labelled twice with the
  disagreement rate reported, and there is no `--second-pass` mode or agreement report. Without
  it the 95% accuracy target is not known to be measurable. Build this before labelling in bulk,
  not after.
