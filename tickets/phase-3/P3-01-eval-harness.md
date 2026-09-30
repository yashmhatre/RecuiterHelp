# P3-01: Evaluation harness and metrics

**Phase:** 3 · **Est:** 2 days · **Blocked by:** nothing

## Owns
- `eval/run_eval.py`
- `eval/metrics.py`
- `eval/report.py`
- `tests/test_metrics.py`

## Reads
- `docs/CONTRACTS.md` §1 (result types), §6 (tracing)
- `eval/dataset/schema.json` shape from P1-05

## Context
Turns the plan targets into a number that can be printed. Written against the dataset *schema*,
not the dataset, so it can be built while labelling is still in progress.

## Scope
**Do**
- `run_eval.py --dataset <path>` replays every labelled email through the pipeline stages under
  test and writes a report.
- `metrics.py` computes exactly the plan targets:

  | Metric | Target |
  |---|---|
  | Recruiter vs not-recruiter accuracy | ≥ 95% |
  | Intent accuracy | ≥ 90% |
  | Correct profile in top matches (recall@3) | ≥ 90% |
  | Wrong candidate resume attached | 0 |
  | Adversarial checks passed | 100% |
  | Time from arrival to draft | < 5 min on CPU |

- Also report the confusion matrix, per-intent breakdown, and precision/recall separately —
  accuracy alone hides the case that matters, a non-recruiter drafted as a recruiter.
- Record per-stage latency, p50 and p95, so the 5-minute target is measured rather than assumed.
- `--compare <previous-run>` diffs two runs and lists every email whose outcome changed. This is
  what makes P3-03 tuning safe.
- Log the run to MLflow with the config snapshot and prompt versions attached, so a result can be
  traced back to what produced it.
- Exit non-zero when any target is missed, so it can gate a release.

**Do not**
- Change any pipeline code to make a number look better. Findings go back as separate fixes.

## Independence
Runs against `labels.example.jsonl` with faked stages during development; swaps to the real
dataset and real stages when both exist. `metrics.py` is pure and unit-tested against
hand-computed expected values.

## Acceptance criteria
- [ ] Every metric in the table computed and printed with its target and pass/fail
- [ ] Hand-computed fixtures confirm each metric function
- [ ] Confusion matrix and per-intent breakdown in the report
- [ ] p50 and p95 latency per stage reported
- [ ] `--compare` lists changed-outcome emails between two runs
- [ ] The run appears in MLflow with config and prompt versions
- [ ] Missing any target exits non-zero

## Done when
`pytest tests/test_metrics.py` passes and `run_eval.py` produces a full report on
`labels.example.jsonl`.
