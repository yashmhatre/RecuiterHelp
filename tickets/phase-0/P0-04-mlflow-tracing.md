# P0-04: MLflow server and the tracing module

**Phase:** 0 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `email_agent/tracing.py`
- `scripts/run_mlflow.sh`, `scripts/run_mlflow.ps1`
- `tests/test_tracing.py`
- `docs/setup-mlflow.md`

## Reads
- `docs/CONTRACTS.md` §6

## Context
Six pipeline tickets will call `log_stage(...)`. They must be able to do that without MLflow
installed or running, which is why the contract makes every function a no-op on failure.

## Scope
**Do**
- Implement exactly the §6 surface: `start_email_run`, `log_stage`, `log_metrics`.
- Tag each run `provider`, `intent`, `email_id`. One run per email.
- Wrap every MLflow call so any exception — connection refused, bad URI, server 500 — is caught,
  logged once at WARNING, and swallowed.
- A `MLFLOW_TRACKING_URI` that is unset disables tracing entirely with no warning spam
  (warn once per process, not once per call).
- Redact before logging: no resume text, no full email bodies, no candidate emails or phone
  numbers in params or tags. Log counts, scores, IDs and durations.
- `run_mlflow.sh`: local server on SQLite backend with a local artifact root.

**Do not**
- Add tracing calls to pipeline files. Each pipeline ticket adds its own call.

## Independence
Fully standalone. The central test asserts the no-op behaviour by pointing the tracking URI at a
dead port and checking that nothing raises.

## Acceptance criteria
- [ ] With MLflow down, all three functions return normally and raise nothing
- [ ] The unreachable-server warning is emitted once per process, not per call
- [ ] With MLflow up, one run per `email_id` appears with the three tags set
- [ ] No resume text, email body, candidate email or phone appears in any logged field
- [ ] `log_stage` durations land as metrics named `stage.<name>.ms`

## Done when
`pytest tests/test_tracing.py` passes with no MLflow server running.
