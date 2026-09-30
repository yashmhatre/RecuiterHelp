# P2-02: Gmail provider

**Phase:** 2 · **Est:** 2 days · **Blocked by:** nothing

## Owns
- `providers/gmail.py`
- `tests/test_gmail_provider.py`
- `tests/fixtures/gmail/*.json` (recorded, anonymised API responses)

## Reads
- `docs/CONTRACTS.md` §1 (`MailProvider`, `RawEmail`), §2 (labels)

## Context
One of the two interchangeable provider implementations. Requirement 7 says the same pipeline must
pass the test set on both, so this ticket's job is to normalise Gmail's shape into `RawEmail` and
nothing more.

## Scope
**Do**
- `fetch_new(cursor)` using `history.list` with the stored history ID; full sync on first run or
  when the history ID has expired (Gmail expires them — handle `404` by falling back to a bounded
  full sync, do not crash).
- Normalise into `RawEmail`: decode base64url bodies, prefer `text/plain` and strip HTML when
  that is all there is, lower-case header names, keep `Authentication-Results` intact for P2-04,
  resolve `threadId`, set `is_from_self` by comparing against the authenticated address.
- `save_draft`: `drafts.create` with `threadId` set and correct `In-Reply-To` and `References`
  so the draft threads properly, with attachments as a MIME multipart.
- `apply_label`: create the label if missing, then apply; idempotent.
- Retry with backoff on `429` and `5xx`; respect `Retry-After`.

**Do not**
- Call `users.messages.send` or `drafts.send`. Not once, not behind a flag.

## Independence
Run **P2-01's contract suite** against this class, plus recorded-response tests using anonymised
fixtures. Do not import `auth/`: take a credentials object as a constructor argument so tests
pass a stub. Mark live-mailbox tests `@pytest.mark.live` and keep them out of the default run.

## Acceptance criteria
- [ ] P2-01's contract suite passes against `GmailProvider`
- [ ] An expired history ID triggers a bounded full sync instead of an exception
- [ ] The saved draft appears in the original thread in a real mailbox, with attachments intact
- [ ] Attachment filenames with spaces and non-ASCII characters survive intact
- [ ] Threading headers are set; the draft is not a new conversation
- [ ] `429` and `5xx` retry with backoff and eventually surface a typed error
- [ ] Only read, compose and label scopes are requested

## Done when
`pytest tests/test_gmail_provider.py` passes offline, and one draft has been verified by hand in Gmail.
