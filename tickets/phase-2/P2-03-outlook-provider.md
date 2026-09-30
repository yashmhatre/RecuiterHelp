# P2-03: Outlook / Microsoft Graph provider

**Phase:** 2 · **Est:** 2 days · **Blocked by:** nothing

## Owns
- `providers/outlook.py`
- `tests/test_outlook_provider.py`
- `tests/fixtures/graph/*.json` (recorded, anonymised API responses)

## Reads
- `docs/CONTRACTS.md` §1 (`MailProvider`, `RawEmail`), §2 (labels → Outlook categories)

## Context
The second interchangeable implementation. Written against the same contract suite as P2-02, so
the two can be built in parallel by different people without coordination.

## Scope
**Do**
- `fetch_new(cursor)` using `/messages/delta`, storing and replaying the `deltaLink`; handle an
  expired delta token (`410 Gone`) with a bounded full resync.
- Normalise into `RawEmail`: `body.content` with `text` preferred, HTML stripped otherwise,
  `internetMessageHeaders` lower-cased with `Authentication-Results` preserved,
  `conversationId` as `thread_id`, `is_from_self` against the authenticated address.
- `save_draft`: create a reply draft via `createReply` then PATCH the body, keeping
  `conversationId`; upload attachments (use an upload session above 3 MB).
- `apply_label`: Outlook **categories**, created in the master list if missing; idempotent.
- Retry with backoff on `429` and `5xx`, respecting `Retry-After`.

**Do not**
- Call `/sendMail` or `/send`, and do not request `Mail.Send`. `Mail.ReadWrite` only.

## Independence
Run **P2-01's contract suite** against this class, plus recorded-response tests. Take a token
provider as a constructor argument so tests pass a stub — do not import `auth/`. Live tests are
marked `@pytest.mark.live`.

## Acceptance criteria
- [ ] P2-01's contract suite passes against `OutlookProvider`
- [ ] A `410 Gone` delta token triggers a bounded resync instead of an exception
- [ ] The draft appears in the original conversation in real Outlook, attachments intact
- [ ] A 5 MB attachment uploads via an upload session
- [ ] Categories are created on first use and applying twice is a no-op
- [ ] The app registration has `Mail.ReadWrite` and no send permission

## Done when
`pytest tests/test_outlook_provider.py` passes offline, and one draft has been verified by hand in Outlook.
