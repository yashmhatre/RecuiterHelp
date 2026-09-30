# <ID>: <Title>

**Phase:** <n> · **Est:** <days> · **Blocked by:** nothing

## Owns (no other ticket edits these)
- `path/to/file.py`

## Reads (contract only, never another ticket's code)
- `docs/CONTRACTS.md` §<n>

## Context
Why this exists, in two or three lines.

## Scope
**Do**
- ...

**Do not**
- ...

## Independence
How to build and test this with zero other tickets merged. Name the stub or fixture.

## Acceptance criteria
- [ ] ...

## Done when
`pytest tests/<this ticket's tests>` passes on a clean clone with nothing else merged.
