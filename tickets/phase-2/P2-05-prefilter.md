# P2-05: Pre-filter

**Phase:** 2 · **Est:** 1 day · **Blocked by:** nothing · **Status:** done

## Owns
- `pipeline/prefilter.py`
- `config/prefilter_rules.yaml`
- `tests/test_prefilter.py`

## Reads
- `docs/CONTRACTS.md` §1 (`RawEmail`, `PrefilterResult`)

## Context
Cheap deterministic rules that drop obvious non-mail before a model is ever loaded. Every drop
must name its rule so a wrongly dropped email can be diagnosed from the log alone.

## Scope
**Do**
- `prefilter(email: RawEmail) -> PrefilterResult`, dropping on:
  - `List-Unsubscribe` or `List-Id` present
  - `Precedence: bulk` / `list` / `junk`
  - `Auto-Submitted` other than `no`, or `X-Autoreply`
  - out-of-office and delivery-failure patterns
  - job-alert and newsletter senders (`noreply@`, `jobs-listings@`, `alerts@`, configurable list)
  - `email.is_from_self`
- Rules live in `config/prefilter_rules.yaml` so P3-03 can tune them without a code change.
- Every drop sets `rule` to the rule name. A kept email has `rule = None`.
- Order rules cheapest-first and stop at the first match.

**Do not**
- Try to decide recruiter-or-not. That is the model's job in P2-06. When in doubt, keep.

## Independence
Pure function over inline `RawEmail` fixtures. No dependencies at all.

## Acceptance criteria
- [x] Each rule has a test that trips it and one that does not
- [x] A genuine recruiter email that happens to contain the word "unsubscribe" in the body but
      has no `List-Unsubscribe` header is kept
- [x] Our own sent mail is dropped as `is_from_self`
- [x] Rules load from YAML; adding a sender to the list needs no code change
- [x] **Zero false drops** across the recruiter emails in the labelled set — this is the metric
      that matters, since a dropped email is silently lost

## Done when
`pytest tests/test_prefilter.py` passes, including the zero-false-drop check against
`labels.example.jsonl`.

## Outcome

Done. 63 tests, lint clean.

Decisions:

- **Sender keywords match whole segments, not bare substrings.** `jobs-listings@` and
  `linkedin-jobalert@` are robots; `jobsmith@`, `alerta@` and `newsletterexpert@` are people.
  A substring match would drop all of them, and a dropped email leaves no trace at all.
- **The domain is not the signal; the sending mailbox is.** `priya.sharma@jobboard.example.com`
  is kept while `jobs-listings@jobboard.example.com` is dropped.
- **Only the `List-Unsubscribe` header counts, never the word in the body.** Plenty of genuine
  signatures mention unsubscribing.
- **Substring matching on subjects is deliberate**, not regex: these patterns are hand-edited
  during P3-03 tuning, and a broken regex there would be a silent behaviour change.

Fixed during the work: `allowed: [no]` in the YAML parsed as the boolean `false`, so every
`Auto-Submitted` check crashed. Now quoted, and list values are coerced with `str()` so another
bare `no`, `null` or number in a hand-edited rule file cannot crash the pipeline.

The zero-false-drop check runs against `labels.example.jsonl`. Re-run it against the real
labelled set when P1-05 lands.
