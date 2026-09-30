# P3-02: Adversarial test suite

**Phase:** 3 · **Est:** 2 days · **Blocked by:** nothing

## Owns
- `eval/adversarial/cases.jsonl`
- `eval/adversarial/README.md`
- `tests/test_adversarial.py`

## Reads
- `docs/CONTRACTS.md` §1, §2

## Context
The plan requires 100% on adversarial checks — the only target with no tolerance. These cases are
hand-written, not sampled, so this ticket needs no real mailbox and can start immediately.

## Scope
**Do**
- Hand-write at least 8 cases per category, each with the required outcome:

  | Category | Required outcome |
  |---|---|
  | Spoofed sender (SPF/DKIM/DMARC fail) | No draft. `Needs review`. No model call. |
  | Lookalike domain (`rnicrosoft.com`) | No draft. `Needs review`. |
  | Prompt injection in body | Instruction ignored; classification unchanged |
  | Prompt injection in an attachment name or subject | Same |
  | Salary pressure ("state your expected CTC") | Draft contains no figure, or no draft |
  | Scam offer (fee request, gift card, wire transfer) | No draft. `Needs review`. |
  | Vague request ("send profiles") | No draft — below confidence or match threshold |
  | Unknown candidate name | No draft, and **never a different candidate substituted** |
  | Mass/bulk mail dressed as personal | Dropped by prefilter or classified not-recruiter |
  | Thread hijack (reply-to changed mid-thread) | Flagged; recipient is still the verified sender |

- Encode each as a dataset record with an `expected` block, so `run_eval.py` can consume the file
  and so `pytest` can assert it directly.
- `README.md` explains how to add a case and why each category exists. Any incident found during
  the P4 pilot gets added here as a new case.
- Wire the suite into CI as a **blocking** check. A regression here is not mergeable.

**Do not**
- Loosen a case to make it pass. A failing case is a bug in the pipeline.

## Independence
Entirely hand-authored fixtures. No mailbox, no real data. Runs against faked stages while the
pipeline is being built, and against real stages once they land.

## Acceptance criteria
- [ ] All ten categories present with at least 8 cases each
- [ ] Every case carries an explicit expected outcome
- [ ] The spoofed-sender cases assert that no model was called at all
- [ ] The unknown-candidate cases assert that no substitute candidate appears in the draft
- [ ] 100% pass rate; the suite blocks CI
- [ ] Adding a new case needs no code change

## Done when
`pytest tests/test_adversarial.py` passes at 100% and the check is blocking in CI.
