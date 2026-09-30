# P2-01: Provider interface, fake provider and the no-send guard

**Phase:** 2 · **Est:** 1 day · **Blocked by:** nothing · **Status:** done

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
- [x] `MailProvider` has no send method and no way to reach one
- [x] The contract suite is importable and passes against `providers/fake.py`
- [x] The no-send guard scans the whole repo and fails on an added send call — proven by
      temporarily adding one in the test
- [x] Fake cursor semantics: fetching with the returned cursor yields zero new messages
- [x] `get_provider("gmail")` does not import the Graph module, and vice versa

## Done when
`pytest tests/test_provider_contract.py tests/test_no_send_path.py` passes.

## Outcome

Done. 63 tests for this ticket, 222 repo-wide, lint clean.

Decisions:

- **The no-send guard parses instead of grepping.** `grep -r "\.send("` cannot tell code from
  prose, and the tickets, CONTRACTS.md and several comments all discuss sending. Worse, P0-05
  *must* contain the literal strings `"Mail.Send"` and `"gmail.send"` in order to reject those
  scopes. A text scan would fire on all of that or be watered down until it caught nothing. The
  guard walks the AST for send-shaped calls, definitions and string literals, so only real code
  counts. A single line may carry `# send-guard: allow`, which is not suppressible file-wide, so
  `grep -rn "send-guard: allow"` always lists every exception.
- **Error types live in `base.py`**, not in each provider: `ProviderError`,
  `TransientProviderError`, `CursorExpiredError`, `AuthorisationError`. Not in the original scope,
  but both P2-02 and P2-03 need to signal a rate limit and a stale cursor, and if base does not
  define them the two providers invent incompatible ones and P2-12 has to know both.
- **`BaseMailProvider.__init_subclass__` refuses a send method at class-creation time**, so the
  mistake fails on import rather than waiting for review or the repo scan.
- **An unusable cursor raises `CursorExpiredError`** rather than returning an empty batch. Silence
  there would mean new mail is never processed again and nothing would look wrong.
- **`FakeMailProvider.expire_cursor()`** simulates a stale Gmail history id or Graph delta token,
  which P2-12 needs to prove the polling loop survives.
- The fake reads only transport fields from a dataset record. A test asserts the ground-truth
  labels do not leak into `RawEmail`, since a provider handing the pipeline the answers would
  make every metric meaningless.

The guard found a real violation on first run: the `Sneaky` class in the contract suite, which
exists to prove the base class refuses a send method. It now carries the allow marker.
