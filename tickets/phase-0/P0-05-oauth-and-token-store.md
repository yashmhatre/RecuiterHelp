# P0-05: OAuth app registration and token store

**Phase:** 0 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `email_agent/auth/token_store.py`
- `email_agent/auth/gmail_oauth.py`
- `email_agent/auth/graph_oauth.py`
- `scripts/authorize.py`
- `tests/test_token_store.py`
- `docs/oauth-setup.md`

## Reads
- `.env.example` key names from `docs/CONTRACTS.md` (client id, secret, tenant, mailbox address)

## Context
Requirement 5 is partly an access-control decision, and this is where it is enforced: the app
registration must not carry a send permission. Getting that wrong is not recoverable in code.

## Scope
**Do**
- `docs/oauth-setup.md` with click-by-click registration for both providers:
  - Microsoft Graph: **`Mail.ReadWrite` only**. `Mail.Send` must not be added or consented.
  - Gmail: `gmail.readonly` + `gmail.compose` + `gmail.labels`. **Not** `gmail.send`,
    **not** `mail.google.com`.
- Record the account-type trade-off from the plan: Workspace "Internal" app or Microsoft 365
  avoids the 7-day token expiry that personal Gmail in Testing mode suffers.
- `token_store.py`: read/write refresh tokens to a gitignored local file, `0600` on POSIX and
  a restrictive ACL on Windows, with transparent refresh and a clear error when a refresh token
  has been revoked.
- `authorize.py`: one-time interactive consent for either provider, writing the token file.
- Assert the granted scope set at startup and refuse to run if a send scope is present.

**Do not**
- Fetch mail or save drafts. Providers are P2-02 and P2-03.

## Independence
Token refresh, expiry and file permissions are tested against a mocked token endpoint. The
interactive consent flow is manual and checked off in the doc.

## Acceptance criteria
- [ ] The registration doc grants no send permission on either provider
- [ ] Startup raises if the token's scope set contains `gmail.send` or `Mail.Send`
- [ ] An expired access token refreshes automatically without re-consent
- [ ] A revoked refresh token produces an actionable error naming `scripts/authorize.py`
- [ ] The token file is gitignored and not world-readable
- [ ] Both providers authorised once by hand and the doc corrected against reality

## Done when
`pytest tests/test_token_store.py` passes, and one real mailbox has been authorised end to end.
