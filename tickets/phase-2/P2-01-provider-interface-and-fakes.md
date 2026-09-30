# P2-01: Provider interface, fake provider and the no-send guard

**Phase:** 2 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `providers/base.py`
- `providers/fake.py`
- `providers/registry.py`
- `tests/test_provider_contract.py`
- `tests/test_no_send_path.py`

## Reads
- `docs/CONTRACTS.md` §1 (`MailProvider`, `RawEmail`, `DraftContent`, `SavedDraft`), §2 (labels)

## Context
This ticket ships the shared provider test suite and the in-memory fake. Both real providers are
then verified by running the same suite, and every other pipeline ticket uses the fake instead of
a mailbox. Deliberately first, deliberately small.

## Scope
**Do**
- `base.py`: the `MailProvider` protocol plus the abstract base, and the label constants from §2.
- `providers/fake.py`: an in-memory provider seeded from a JSONL file
  (`eval/dataset/labels.example.jsonl` format), implementing fetch/save_draft/apply_label with
  cursor semantics that match the real ones — a repeated cursor returns nothing new.
- `tests/test_provider_contract.py`: a **reusable, parameterised** suite any provider is pointed
  at. P2-02 and P2-03 import and run it against their own implementation.
- `tests/test_no_send_path.py`: a repo-wide guard asserting no send capability exists anywhere —
  no `Mail.Send`, no `gmail.send`, no `messages/send`, no `users.messages.send`, no `.send(` on a
  provider object. This is requirement 5 made mechanical.
- `registry.py`: `get_provider(name)` resolving `gmail` / `outlook` / `fake` lazily, so an
  unimported provider module cannot break startup.

**Do not**
- Implement Gmail or Graph calls.

## Independence
The fake is the whole point — it is what makes P2-04 through P2-13 independent of a mailbox.

## Acceptance criteria
- [ ] `MailProvider` has no send method and no way to reach one
- [ ] The contract suite is importable and passes against `providers/fake.py`
- [ ] The no-send guard scans the whole repo and fails on an added send call — proven by
      temporarily adding one in the test
- [ ] Fake cursor semantics: fetching with the returned cursor yields zero new messages
- [ ] `get_provider("gmail")` does not import the Graph module, and vice versa

## Done when
`pytest tests/test_provider_contract.py tests/test_no_send_path.py` passes.
