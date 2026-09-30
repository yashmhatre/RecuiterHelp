# P3-03: Prompt, threshold and rule tuning

**Phase:** 3 · **Est:** 3 days · **Blocked by:** nothing (needs P3-01 output to be *useful*)

## Owns
- `eval/sweep.py`
- `docs/tuning-log.md`
- changes to `config/settings.yaml`, `config/prompts/*`, `config/prefilter_rules.yaml`

## Reads
- `docs/CONTRACTS.md` §4 (the tunable keys)

## Context
The only ticket allowed to change threshold values and prompt text. Keeping that permission in one
place means every number in `settings.yaml` has exactly one recorded reason, and a tuning run
that needs a code change becomes a separate ticket instead of drifting into the stage it
touches.

## Scope
**Do**
- `sweep.py`: grid or random search over `classify.min_confidence`, `match.min_score`,
  `match.hybrid_alpha`, `match.max_profiles`, `match.rerank_pool`, reporting every plan metric per
  configuration.
- Split the labelled set into **tune and holdout**. Tune on one, report final numbers on the other,
  and never look at the holdout while tuning. A threshold fitted to the whole set will not survive
  the pilot.
- Record every iteration in `docs/tuning-log.md`: what changed, which metric moved, what was kept.
- Optimise for the asymmetric cost, not for accuracy: a missed recruiter email costs a follow-up,
  a wrong candidate resume costs a client relationship. Prefer `Needs review` over a bad draft and
  say so in the log.
- When a target cannot be reached with the free models, record which stage failed and by how much,
  and quantify the paid-API upgrade for that one step — that is the plan's stated fallback, and
  this ticket produces the evidence for the decision.

**Do not**
- Edit pipeline logic. A tuning run that needs a code change becomes a separate ticket against the
  owning stage.

## Independence
Consumes `run_eval.py` output through the CLI, not by importing it, so it can be developed against
a stub report file.

## Acceptance criteria
- [ ] Sweep runs unattended and ranks configurations by every plan metric
- [ ] Tune/holdout split is fixed, recorded and never mixed
- [ ] Final numbers are reported on the holdout, not the tuning split
- [ ] Every tuning decision is in `docs/tuning-log.md` with its before and after
- [ ] Chosen values are committed in `config/settings.yaml`, none hardcoded elsewhere
- [ ] Adversarial suite still at 100% with the final configuration
- [ ] A written recommendation on free-versus-paid models, with the numbers behind it

## Done when
The holdout run meets every plan target, or the shortfall is documented with a costed upgrade path.
