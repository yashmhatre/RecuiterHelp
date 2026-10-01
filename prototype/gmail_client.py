"""Gmail connection for the prototype: read messages, save drafts, apply labels. Never sends.

Scopes are read, compose and labels. ``gmail.send`` is not requested and
``users.messages.send`` is never called — ``tests/test_no_send_path.py`` scans this file too.
Compose is what allows a draft to be created; it does not allow sending.

Tokens live in ``.secrets/`` which is gitignored. A personal ``gmail.com`` account with the
consent screen in Testing mode has its refresh token revoked every 7 days by Google, so expect
to reconnect weekly; a Workspace account with an Internal app does not have that limit.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from email_agent.contracts import RawEmail

REPO_ROOT = Path(__file__).resolve().parent.parent
SECRETS_DIR = REPO_ROOT / ".secrets"
CLIENT_SECRET_PATH = SECRETS_DIR / "gmail_client_secret.json"
TOKEN_PATH = SECRETS_DIR / "gmail_token.json"

#: Read, draft and label. Deliberately no send scope: requirement 5 is enforced at the
#: authorisation boundary as well as in code, so a coding mistake cannot send mail.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.labels",
]

#: Any of these in a granted token means the credentials are too powerful for this app.
FORBIDDEN_SCOPES = (  # send-guard: allow (named here in order to reject them)
    "https://www.googleapis.com/auth/gmail.send",
    "https://mail.google.com/",
)

#: oauthlib environment switches, set only around the token exchange.
#: INSECURE_TRANSPORT: allows the http://localhost redirect Google itself mandates for a
#: Desktop client. RELAX_TOKEN_SCOPE: Google returns openid alongside what was asked for,
#: and oauthlib treats a changed scope set as an error without this.
_OAUTHLIB_SWITCHES = ("OAUTHLIB_INSECURE_TRANSPORT", "OAUTHLIB_RELAX_TOKEN_SCOPE")

AI_DRAFT_LABEL = "AI Draft"
NEEDS_REVIEW_LABEL = "Needs review"


#: Gmail charges quota units per call and enforces a per-user-per-minute ceiling. Pulling a few
#: hundred messages for labelling blows through it in seconds, and the API answers 403
#: rateLimitExceeded -- which is retryable, not fatal. Google's documented remedy is exponential
#: backoff, so that is what this does.
_RETRYABLE_REASONS = {"rateLimitExceeded", "userRateLimitExceeded", "backendError", "quotaExceeded"}
_RETRYABLE_STATUS = {403, 429, 500, 502, 503, 504}

#: Small gap between message fetches. Cheaper than discovering the ceiling and backing off.
THROTTLE_SECONDS = float(os.environ.get("GMAIL_THROTTLE_SECONDS", "0.12"))


def _execute(request, *, attempts: int = 6):
    """Run one Gmail API request, retrying the failures that are worth retrying.

    Raises GmailError with a readable message once the attempts are spent, rather than letting
    an HttpError traceback reach the UI.
    """
    from googleapiclient.errors import HttpError

    delay = 1.0
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return request.execute()
        except HttpError as exc:
            status = getattr(exc.resp, "status", None)
            reason = ""
            try:
                detail = json.loads(exc.content.decode("utf-8"))
                errors = detail.get("error", {}).get("errors") or [{}]
                reason = errors[0].get("reason", "")
            except Exception:  # noqa: BLE001 - the body is not always JSON
                pass

            retryable = status in _RETRYABLE_STATUS and (
                reason in _RETRYABLE_REASONS or status in {429, 500, 502, 503, 504}
            )
            if not retryable or attempt == attempts - 1:
                if status == 403 and reason in _RETRYABLE_REASONS:
                    raise GmailError(
                        "Gmail's rate limit is still refusing requests after several retries. "
                        "Wait a minute, then pull a smaller batch."
                    ) from exc
                raise GmailError(f"Gmail refused the request ({status} {reason})".strip()) from exc

            last = exc
            time.sleep(delay + random.uniform(0, 0.4))
            delay = min(delay * 2, 16.0)

    raise GmailError(f"Gmail request failed after {attempts} attempts: {last}")


class GmailError(RuntimeError):
    """Anything wrong with the connection, phrased for someone reading it in the UI."""


@dataclass
class Connection:
    connected: bool
    address: str = ""
    detail: str = ""


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


def save_client_secret(raw: bytes) -> str:
    """Store the OAuth client JSON downloaded from Google Cloud Console."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GmailError(f"That file is not valid JSON: {exc}") from exc

    block = parsed.get("installed") or parsed.get("web")
    if not block or "client_id" not in block:
        raise GmailError(
            "That JSON has no OAuth client in it. Download the file from "
            "Credentials > OAuth client ID, and choose the 'Desktop app' type."
        )
    if parsed.get("web"):
        raise GmailError(
            "That is a 'Web application' client. This app signs in locally, so create a "
            "'Desktop app' client instead and download that JSON."
        )

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    CLIENT_SECRET_PATH.write_bytes(raw)
    try:
        CLIENT_SECRET_PATH.chmod(0o600)
    except OSError:
        pass  # Windows ACLs; the directory is gitignored either way
    return str(block["client_id"])[:24] + "..."


def _load_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not TOKEN_PATH.is_file():
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    granted = set(creds.scopes or [])
    too_powerful = granted.intersection(FORBIDDEN_SCOPES)
    if too_powerful:
        raise GmailError(
            f"These credentials carry a send scope ({', '.join(sorted(too_powerful))}). "
            f"This app must not be able to send mail. Disconnect and re-authorise."
        )

    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI as a reconnect prompt
            raise GmailError(
                f"The saved Google login has expired and could not be refreshed ({exc}). "
                f"A personal gmail.com account in Testing mode is revoked every 7 days. "
                f"Click Connect to sign in again."
            ) from exc
    return None


#: Where Google sends the browser back to. Must be "localhost", not "127.0.0.1": Google treats
#: them as different origins, and the Desktop client registers "http://localhost".
REDIRECT_PATH = "/api/gmail/callback"

#: The in-flight flow, keyed by OAuth state. One at a time is plenty for a local prototype.
_pending: dict[str, Any] = {}


def build_auth_url(port: int) -> str:
    """Start the consent flow and return the URL for the browser to open.

    Two steps rather than one blocking call. The previous version ran a local server inside the
    request and waited for the redirect, which hung forever whenever the browser failed to open
    -- and a backgrounded server process cannot reliably open one. Here the page opens the URL
    itself, which is a real user gesture, and Google redirects back into this app.
    """
    from google_auth_oauthlib.flow import Flow

    if not CLIENT_SECRET_PATH.is_file():
        raise GmailError("Upload the OAuth client JSON first.")

    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_PATH),
        scopes=SCOPES,
        redirect_uri=f"http://localhost:{port}{REDIRECT_PATH}",
    )
    url, state = flow.authorization_url(
        access_type="offline",       # we need a refresh token, not just an access token
        prompt="consent",            # force it, so a re-connect actually returns a new one
        include_granted_scopes="true",
    )
    _pending.clear()
    _pending[state] = flow
    return url


def complete_auth(state: str, full_callback_url: str) -> str:
    """Exchange the authorisation code for a token. Returns the mailbox address."""
    flow = _pending.pop(state, None)
    if flow is None:
        raise GmailError(
            "That sign-in did not match a pending request. Click Connect Gmail again."
        )

    # oauthlib refuses a non-https redirect by default. Google deliberately allows plain http
    # for loopback redirects from an installed (Desktop) client -- the code never leaves this
    # machine -- so the check is relaxed for this one call and restored immediately, rather than
    # set process-wide where it would also apply to any other OAuth traffic.
    previous = {name: os.environ.get(name) for name in _OAUTHLIB_SWITCHES}
    for name in _OAUTHLIB_SWITCHES:
        os.environ[name] = "1"
    try:
        flow.fetch_token(authorization_response=full_callback_url)
    except Exception as exc:  # noqa: BLE001 - the library raises many types
        raise GmailError(f"Google rejected the sign-in: {exc}") from exc
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    creds = flow.credentials
    granted = set(creds.scopes or [])
    if granted.intersection(FORBIDDEN_SCOPES):
        raise GmailError("Google granted a send scope. Refusing to store those credentials.")
    if not creds.refresh_token:
        raise GmailError(
            "Google returned no refresh token, so the connection would die in an hour. "
            "Remove this app at myaccount.google.com/permissions and connect again."
        )

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    try:
        TOKEN_PATH.chmod(0o600)
    except OSError:
        pass

    return address_of(creds)


def disconnect() -> None:
    TOKEN_PATH.unlink(missing_ok=True)


def _service(creds):
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def address_of(creds) -> str:
    profile = _execute(_service(creds).users().getProfile(userId="me"))
    return profile.get("emailAddress", "")


def status() -> Connection:
    """What the UI shows: whether we are connected, and to which mailbox."""
    if not CLIENT_SECRET_PATH.is_file():
        return Connection(False, detail="No OAuth client JSON uploaded yet.")
    try:
        creds = _load_credentials()
    except GmailError as exc:
        return Connection(False, detail=str(exc))
    if not creds:
        return Connection(False, detail="Client JSON ready. Click Connect to sign in.")
    try:
        return Connection(True, address=address_of(creds), detail="Connected.")
    except Exception as exc:  # noqa: BLE001
        return Connection(False, detail=f"Could not reach Gmail: {exc}")


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _header(payload: dict, name: str) -> str:
    for item in payload.get("headers", []):
        if item.get("name", "").lower() == name.lower():
            return item.get("value", "")
    return ""


def _all_headers(payload: dict) -> dict[str, str]:
    """Lower-cased header map. Repeated headers are joined with a newline, which is how
    ``pipeline/verify.py`` expects to see several Authentication-Results values."""
    out: dict[str, str] = {}
    for item in payload.get("headers", []):
        key = item.get("name", "").lower()
        value = item.get("value", "")
        out[key] = f"{out[key]}\n{value}" if key in out else value
    return out


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")


def _body_text(payload: dict) -> str:
    """Prefer text/plain; fall back to stripping the HTML part."""
    plain, html = "", ""

    def walk(part: dict) -> None:
        nonlocal plain, html
        mime = part.get("mimeType", "")
        data = (part.get("body") or {}).get("data")
        if data:
            if mime == "text/plain" and not plain:
                plain = _decode(data)
            elif mime == "text/html" and not html:
                html = _decode(data)
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    if plain.strip():
        return plain

    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?i)<br\s*/?>|</p>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ").replace("&amp;", "&")
        .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')
    )
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()


def _split_address(raw: str) -> tuple[str, str]:
    raw = (raw or "").strip()
    if "<" in raw and ">" in raw:
        return raw[: raw.index("<")].strip().strip('"'), raw[raw.index("<") + 1 : raw.rindex(">")].strip()
    return "", raw


def to_raw_email(message: dict, self_address: str) -> RawEmail:
    payload = message.get("payload", {})
    headers = _all_headers(payload)
    from_name, from_email = _split_address(_header(payload, "From"))

    received = datetime.now(UTC)
    if date_header := _header(payload, "Date"):
        try:
            received = parsedate_to_datetime(date_header)
            if received.tzinfo is None:
                received = received.replace(tzinfo=UTC)
        except (TypeError, ValueError):
            pass

    to_values = [a.strip() for a in _header(payload, "To").split(",") if a.strip()]

    return RawEmail(
        provider="gmail",
        provider_message_id=message["id"],
        thread_id=message.get("threadId", ""),
        from_name=from_name,
        from_email=from_email,
        reply_to=_split_address(_header(payload, "Reply-To"))[1] or None,
        to=to_values or [self_address],
        subject=_header(payload, "Subject"),
        body_text=_body_text(payload),
        received_at=received,
        headers=headers,
        is_from_self=from_email.lower() == self_address.lower(),
    )


def fetch_one(message_id: str) -> RawEmail:
    """One message by its Gmail id."""
    creds = _load_credentials()
    if not creds:
        raise GmailError("Not connected to Gmail.")
    service = _service(creds)
    try:
        full = _execute(service.users().messages().get(userId="me", id=message_id, format="full"))
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI
        raise GmailError(f"Could not read message {message_id}: {exc}") from exc
    return to_raw_email(full, address_of(creds))


def fetch_recent(limit: int = 15, query: str = "in:inbox -category:promotions") -> list[RawEmail]:
    """Most recent messages, newest first. A query rather than a sync cursor: the prototype is
    for looking at a handful of real emails, not for keeping a mailbox in step."""
    creds = _load_credentials()
    if not creds:
        raise GmailError("Not connected to Gmail.")

    service = _service(creds)
    self_address = address_of(creds)

    wanted = max(1, min(limit, 500))
    stubs: list[dict] = []
    page_token = None
    while len(stubs) < wanted:
        listing = _execute(
            service.users().messages()
            .list(userId="me", maxResults=min(100, wanted - len(stubs)), q=query,
                  pageToken=page_token)
        )
        stubs.extend(listing.get("messages", []))
        page_token = listing.get("nextPageToken")
        if not page_token:
            break

    emails: list[RawEmail] = []
    for index, stub in enumerate(stubs[:wanted]):
        if index and THROTTLE_SECONDS:
            # Stay under the per-minute ceiling rather than discovering it and backing off.
            time.sleep(THROTTLE_SECONDS)
        full = _execute(
            service.users().messages().get(userId="me", id=stub["id"], format="full")
        )
        emails.append(to_raw_email(full, self_address))
    return emails


def staging_record(email: RawEmail) -> dict:
    """One unlabelled record in the shape eval/label_cli.py stages.

    The id is a hash of the RFC822 Message-ID, matching what the .eml importer produces, so the
    same email pulled from Gmail and dropped in as a file resolves to one record rather than two.
    """
    message_id = email.headers.get("message-id", "")
    seed = message_id or f"{email.provider_message_id}:{email.subject}"
    record_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]

    headers = {
        key: email.headers[key]
        for key in ("authentication-results", "from", "reply-to", "list-unsubscribe", "precedence")
        if email.headers.get(key)
    }
    headers.setdefault("from", f"{email.from_name} <{email.from_email}>".strip())
    headers.setdefault("authentication-results", "none")

    return {
        "id": record_id,
        "provider": "gmail",
        "headers": headers,
        "subject": email.subject,
        "body_text": email.body_text,
        "_labelled": False,
    }


# ---------------------------------------------------------------------------
# Writing: drafts and labels only
# ---------------------------------------------------------------------------


def _ensure_label(service, name: str) -> str:
    existing = _execute(service.users().labels().list(userId="me")).get("labels", [])
    for label in existing:
        if label.get("name") == name:
            return label["id"]
    created = _execute(
        service.users().labels()
        .create(userId="me", body={"name": name, "labelListVisibility": "labelShow",
                                   "messageListVisibility": "show"})
    )
    return created["id"]


def apply_label(provider_message_id: str, label: str) -> None:
    creds = _load_credentials()
    if not creds:
        raise GmailError("Not connected to Gmail.")
    service = _service(creds)
    label_id = _ensure_label(service, label)
    _execute(service.users().messages().modify(
        userId="me", id=provider_message_id, body={"addLabelIds": [label_id]}
    ))


def save_draft(draft: dict[str, Any], source: RawEmail) -> dict[str, str]:
    """Create a reply draft in the original thread, with the resumes attached.

    Uses ``drafts().create``. There is no call to ``drafts().send`` or ``messages().send``
    anywhere in this module, and the granted scopes could not perform one.
    """
    creds = _load_credentials()
    if not creds:
        raise GmailError("Not connected to Gmail.")
    service = _service(creds)

    message = EmailMessage()
    message["To"] = ", ".join(draft["to"])
    message["Subject"] = draft["subject"]

    # Threading headers, so the draft lands in the conversation rather than starting a new one.
    original_message_id = source.headers.get("message-id", "")
    if original_message_id:
        message["In-Reply-To"] = original_message_id
        references = source.headers.get("references", "")
        message["References"] = f"{references} {original_message_id}".strip()

    message.set_content(draft["body_text"])

    for attachment in draft.get("attachments", []):
        path = Path(attachment["file_path"])
        if not path.is_file():
            continue
        subtype = "pdf" if path.suffix.lower() == ".pdf" else "octet-stream"
        message.add_attachment(
            path.read_bytes(), maintype="application", subtype=subtype,
            filename=attachment["filename"],
        )

    encoded = base64.urlsafe_b64encode(bytes(message)).decode()
    created = _execute(
        service.users().drafts()
        .create(userId="me", body={"message": {"raw": encoded, "threadId": source.thread_id}})
    )
    return {
        "draft_id": created.get("id", ""),
        "message_id": (created.get("message") or {}).get("id", ""),
        "thread_id": source.thread_id,
    }
