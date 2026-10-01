"""Prototype web app: add candidates with resumes, then run a recruiter email through the pipeline.

Run it:

    python -m prototype.app          # then open http://127.0.0.1:8000

Two screens:

- **Candidates** - add a candidate's details and upload their resume. Stored in SQLite with the
  file on disk. One person can have several role profiles, each with its own resume.
- **Inbox** - paste a recruiter email, run the pipeline, and see every stage: pre-filter, sender
  verification, classification, matching with scores and reasons, the drafted reply with
  attachments, and the validation gate.

There is no send path. The draft is shown and can be downloaded as an ``.eml`` to open in a mail
client; sending stays a human action, which is requirement 5.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import sys
from contextlib import asynccontextmanager
from email.message import EmailMessage
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from email_agent.config import load_dotenv_if_present
from prototype import gmail_client, llm, store
from prototype.pipeline import email_from_form, run_pipeline
from prototype.resume_text import extract_profile_hints, parse_resume

load_dotenv_if_present()

STATIC_DIR = Path(__file__).resolve().parent / "static"
ALLOWED_SUFFIXES = {".pdf", ".docx", ".doc", ".txt", ".rtf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init_db()
    yield


app = FastAPI(
    title="Recruiter Email Agent - prototype", docs_url="/api/docs", lifespan=lifespan
)


def _build_stamp() -> str:
    """A short hash of the front-end files, shown in the header.

    Exists because "I fixed it, hard-refresh" is not a reliable instruction: a cached app.js
    made a fixed bug look unfixed once already. If the stamp on screen matches the one the
    server prints at startup, the browser is on current code.
    """
    digest = hashlib.sha256()
    for name in ("index.html", "app.js", "gmail.js"):
        path = STATIC_DIR / name
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:8]


BUILD = _build_stamp()


@app.middleware("http")
async def no_store(request, call_next):
    """Never let a browser cache this prototype.

    The front end changes constantly while it is being demoed and fixed, and a stale app.js
    costs more time than the caching saves.
    """
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Build"] = BUILD
    return response


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    # Cache-bust the script the blunt way, so a reload cannot serve yesterday's JavaScript.
    stamp = _build_stamp()
    for name in ("app.js", "gmail.js"):
        html = html.replace(f'src="/static/{name}"', f'src="/static/{name}?v={stamp}"')
    return HTMLResponse(html)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


def _safe_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")[:60] or "resume"


@app.get("/api/profiles")
def api_profiles() -> JSONResponse:
    profiles = store.list_profiles()
    for profile in profiles:
        profile["has_resume"] = bool(profile.get("file_path") and Path(profile["file_path"]).is_file())
    return JSONResponse({"profiles": profiles, "backend": llm.backend_name()})


@app.post("/api/candidates")
async def api_add_candidate(
    name: str = Form(...),
    email: str = Form(...),
    title: str = Form(...),
    skills: str = Form(""),
    years_experience: float = Form(0),
    summary: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    notice_period_days: str = Form(""),
    availability: str = Form(""),
    resume: UploadFile | None = File(None),
) -> JSONResponse:
    """Add a candidate plus one role profile, with an optional resume upload."""
    if not name.strip() or "@" not in email:
        raise HTTPException(400, "A name and a valid email are required.")
    if not title.strip():
        raise HTTPException(400, "A profile title is required - it is what gets matched.")

    try:
        notice = int(notice_period_days) if str(notice_period_days).strip() else None
    except ValueError:
        raise HTTPException(400, "Notice period must be a whole number of days.") from None

    skill_list = [s for s in re.split(r"[,\n;]+", skills) if s.strip()]

    candidate_id, profile_id = store.add_candidate_with_profile(
        name=name,
        email=email,
        phone=phone.strip() or None,
        location=location.strip() or None,
        notice_period_days=notice,
        availability=availability.strip() or None,
        title=title,
        skills=skill_list,
        years_experience=years_experience,
        summary=summary,
    )

    resume_note = "no resume uploaded"
    if resume is not None and resume.filename:
        suffix = Path(resume.filename).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(400, f"Unsupported resume type {suffix!r}. Use PDF, DOCX or TXT.")

        destination = store.RESUME_DIR / f"p{profile_id}_{_safe_stem(name)}{suffix}"
        store.RESUME_DIR.mkdir(parents=True, exist_ok=True)
        size = 0
        with open(destination, "wb") as handle:
            while chunk := await resume.read(1024 * 256):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    handle.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(400, "Resume is larger than 10 MB.")
                handle.write(chunk)

        store.attach_resume(profile_id, destination, resume.filename)
        resume_note = f"resume saved ({size // 1024} KB)"

    return JSONResponse(
        {
            "ok": True,
            "candidate_id": candidate_id,
            "profile_id": profile_id,
            "message": f"Saved {name.strip()} - {title.strip()}; {resume_note}.",
        }
    )


@app.post("/api/parse-resume")
async def api_parse_resume(resume: UploadFile = File(...)) -> JSONResponse:
    """Read an uploaded resume and suggest form values, so the form is not all typing.

    Deliberately a suggestion, not an import: the plan requires every profile to be checked by a
    human, and a form the person edits before saving is the cheapest way to enforce that.
    """
    suffix = Path(resume.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Unsupported resume type {suffix!r}. Use PDF, DOCX or TXT.")

    temp = store.DATA_DIR / f"_upload_tmp{suffix}"
    store.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(temp, "wb") as handle:
        shutil.copyfileobj(resume.file, handle)

    try:
        parsed = parse_resume(temp)
        hints = extract_profile_hints(parsed.text)
    finally:
        temp.unlink(missing_ok=True)

    return JSONResponse({"ok": True, "hints": hints, "warnings": parsed.warnings})


@app.delete("/api/candidates/{candidate_id}")
def api_delete_candidate(candidate_id: int) -> JSONResponse:
    store.delete_candidate(candidate_id)
    return JSONResponse({"ok": True})


@app.get("/api/resume/{profile_id}")
def api_resume(profile_id: int) -> FileResponse:
    profile = store.get_profile(profile_id)
    if not profile or not profile.get("file_path") or not Path(profile["file_path"]).is_file():
        raise HTTPException(404, "No resume on file for that profile.")
    return FileResponse(profile["file_path"], filename=profile["filename"])


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


@app.post("/api/run")
def api_run(
    sender: str = Form(...),
    subject: str = Form(""),
    body: str = Form(...),
    reply_to: str = Form(""),
    auth: str = Form(""),
) -> JSONResponse:
    """Run one email through the whole pipeline and return every stage."""
    if "@" not in sender:
        raise HTTPException(400, "Sender must include an email address.")

    email = email_from_form(
        sender=sender, subject=subject, body=body,
        auth=auth.strip() or None, reply_to=reply_to.strip() or None,
    )
    profiles = store.list_profiles()
    result = run_pipeline(email, profiles)
    payload = result.as_dict()

    run_id = store.save_run(
        subject=email.subject, sender=email.from_email, status=result.status, payload=payload
    )
    payload["run_id"] = run_id
    payload["profile_count"] = len(profiles)
    return JSONResponse(payload)


@app.get("/api/runs")
def api_runs() -> JSONResponse:
    return JSONResponse({"runs": store.list_runs()})


@app.get("/api/runs/{run_id}")
def api_run_detail(run_id: int) -> JSONResponse:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "No such run.")
    return JSONResponse(run)


@app.get("/api/runs/{run_id}/eml")
def api_run_eml(run_id: int) -> Response:
    """Download the draft as an .eml, attachments included, to open in a mail client.

    This is how a draft leaves the prototype: as a file a person opens, reads and sends
    themselves. Nothing here transmits anything.
    """
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "No such run.")
    draft = (run["payload"] or {}).get("draft")
    if not draft:
        raise HTTPException(404, "That run produced no draft.")

    message = EmailMessage()
    message["To"] = ", ".join(draft["to"])
    message["Subject"] = draft["subject"]
    message["In-Reply-To"] = draft["in_reply_to_message_id"]
    message["X-Prototype-Status"] = run["status"]
    message.set_content(draft["body_text"])

    for attachment in draft.get("attachments", []):
        path = Path(attachment["file_path"])
        if not path.is_file():
            continue
        subtype = "pdf" if path.suffix.lower() == ".pdf" else "octet-stream"
        message.add_attachment(
            path.read_bytes(),
            maintype="application",
            subtype=subtype,
            filename=attachment["filename"],
        )

    return Response(
        content=bytes(message),
        media_type="message/rfc822",
        headers={"Content-Disposition": f'attachment; filename="draft-{run_id}.eml"'},
    )


PORT = int(os.environ.get("PROTOTYPE_PORT", "8000"))


def _port_is_taken(port: int) -> bool:
    """Whether something is already listening on the port.

    Checked up front because the failure otherwise looks like success: an older copy of this app
    keeps answering, serving stale code and a stale ``.env``, while the new process dies quietly.
    That cost real debugging time once already.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.4)
        return probe.connect_ex(("127.0.0.1", port)) == 0


@app.get("/api/samples")
def api_samples() -> JSONResponse:
    """The synthetic emails already in the repo, so the demo needs no typing."""
    from prototype.samples import load_samples

    return JSONResponse({"samples": load_samples()})


# ---------------------------------------------------------------------------
# Gmail
# ---------------------------------------------------------------------------


@app.get("/api/gmail/status")
def api_gmail_status() -> JSONResponse:
    state = gmail_client.status()
    return JSONResponse(
        {
            "connected": state.connected,
            "address": state.address,
            "detail": state.detail,
            "has_client_secret": gmail_client.CLIENT_SECRET_PATH.is_file(),
            "scopes": gmail_client.SCOPES,
        }
    )


@app.post("/api/gmail/client-secret")
async def api_gmail_client_secret(credentials: UploadFile = File(...)) -> JSONResponse:
    """Store the OAuth client JSON downloaded from Google Cloud Console."""
    raw = await credentials.read()
    if len(raw) > 64 * 1024:
        raise HTTPException(400, "That file is too large to be an OAuth client JSON.")
    try:
        client_id = gmail_client.save_client_secret(raw)
    except gmail_client.GmailError as exc:
        raise HTTPException(400, str(exc)) from exc
    return JSONResponse({"ok": True, "client_id": client_id})


@app.get("/api/gmail/auth-url")
def api_gmail_auth_url() -> JSONResponse:
    """The URL the page should open for Google sign-in.

    Returned rather than opened server-side: a backgrounded server process cannot reliably open
    a browser, and the previous blocking version hung forever when it could not.
    """
    try:
        return JSONResponse({"ok": True, "url": gmail_client.build_auth_url(PORT)})
    except gmail_client.GmailError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/gmail/callback")
def api_gmail_callback(request: Request) -> HTMLResponse:
    """Where Google sends the browser back. Exchanges the code and stores the token."""
    params = request.query_params

    if error := params.get("error"):
        message = (
            "Google reported: " + error
            + ("<p>If this says access_denied, add yourself under OAuth consent screen &rarr; "
               "Test users, then try again.</p>" if error == "access_denied" else "")
        )
        return HTMLResponse(_callback_page("Sign-in failed", message, ok=False), status_code=400)

    state, code = params.get("state"), params.get("code")
    if not state or not code:
        return HTMLResponse(
            _callback_page("Sign-in failed", "Google sent no authorisation code.", ok=False),
            status_code=400,
        )

    try:
        address = gmail_client.complete_auth(state, str(request.url))
    except gmail_client.GmailError as exc:
        return HTMLResponse(_callback_page("Sign-in failed", str(exc), ok=False), status_code=400)

    return HTMLResponse(
        _callback_page(
            "Connected",
            f"Signed in as <b>{address}</b>. You can close this tab and go back to the app.",
            ok=True,
        )
    )


def _callback_page(title: str, message: str, ok: bool) -> str:
    """A tiny standalone page, because this tab is opened by Google, not by our own UI."""
    colour = "#157f3d" if ok else "#b3261e"
    return (
        f"<!doctype html><meta charset='utf-8'><title>{title}</title>"
        "<style>body{font:15px/1.6 system-ui,sans-serif;margin:0;display:grid;"
        "place-items:center;min-height:100vh;background:#f6f7f9;color:#1a1d21}"
        ".c{background:#fff;border:1px solid #dfe3e8;border-radius:10px;padding:28px 32px;"
        "max-width:480px}h1{font-size:18px;margin:0 0 8px}</style>"
        f"<div class=c><h1 style='color:{colour}'>{title}</h1><p>{message}</p></div>"
    )


@app.post("/api/gmail/disconnect")
def api_gmail_disconnect() -> JSONResponse:
    gmail_client.disconnect()
    return JSONResponse({"ok": True})


@app.get("/api/gmail/messages")
def api_gmail_messages(limit: int = 15, query: str = "in:inbox -category:promotions") -> JSONResponse:
    """Recent messages, with the pre-filter and verification verdicts already attached.

    Those two stages are free -- no model call -- so running them here lets the list show at a
    glance which messages would even reach a model.
    """
    try:
        emails = gmail_client.fetch_recent(limit=limit, query=query)
    except gmail_client.GmailError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Could not read the mailbox: {exc}") from exc

    from email_agent.contracts import AuthResult
    from pipeline.prefilter import prefilter
    from pipeline.verify import verify

    rows = []
    for email in emails:
        pre = prefilter(email)
        ver = verify(email)
        rows.append(
            {
                "id": email.provider_message_id,
                "thread_id": email.thread_id,
                "from_name": email.from_name,
                "from_email": email.from_email,
                "subject": email.subject,
                "received_at": email.received_at.isoformat(),
                "snippet": " ".join(email.body_text.split())[:180],
                "prefilter_keep": pre.keep,
                "prefilter_rule": pre.rule,
                "auth": ver.result.value,
                "auth_reason": ver.reason,
                "auth_flags": list(ver.flags),
                "would_reach_model": pre.keep and ver.result is AuthResult.PASS,
            }
        )
    return JSONResponse({"messages": rows})


@app.post("/api/gmail/run")
def api_gmail_run(message_id: str = Form(...), save: str = Form("no")) -> JSONResponse:
    """Run one real message through the pipeline, and optionally save the draft in Gmail."""
    try:
        email = gmail_client.fetch_one(message_id)
    except gmail_client.GmailError as exc:
        raise HTTPException(400, str(exc)) from exc

    profiles = store.list_profiles()
    result = run_pipeline(email, profiles)
    payload = result.as_dict()
    payload["source"] = {
        "from": f"{email.from_name} <{email.from_email}>".strip(),
        "subject": email.subject,
        "message_id": email.provider_message_id,
    }

    saved = None
    if save == "yes" and result.draft and not result.draft.get("discarded"):
        try:
            saved = gmail_client.save_draft(result.draft, email)
            gmail_client.apply_label(email.provider_message_id, gmail_client.AI_DRAFT_LABEL)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"Draft not saved: {exc}") from exc
    elif save == "yes":
        try:
            gmail_client.apply_label(email.provider_message_id, gmail_client.NEEDS_REVIEW_LABEL)
            saved = {"labelled": gmail_client.NEEDS_REVIEW_LABEL}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"Label not applied: {exc}") from exc

    payload["gmail"] = saved
    payload["run_id"] = store.save_run(
        subject=email.subject, sender=email.from_email, status=result.status, payload=payload
    )
    payload["profile_count"] = len(profiles)
    return JSONResponse(payload)


@app.post("/api/gmail/export")
def api_gmail_export(
    limit: int = Form(200), query: str = Form("in:inbox"), include_bulk: str = Form("no")
) -> JSONResponse:
    """Pull real mail into the labelling queue.

    Labelling is the blocking task for every accuracy number and for the ML classifier, and
    exporting by hand is the kind of friction that stops it getting done. This writes straight
    into the staging file eval/label_cli.py already reads.

    Bulk mail is skipped by default but can be included: a labelled set that is all recruiter
    mail teaches a classifier nothing about the negative class, and the ticket requires at least
    25% non-recruiter.
    """
    from eval.label_cli import LABELS_PATH, STAGING_PATH, _load_labelled_ids, _load_staged_ids
    from pipeline.prefilter import prefilter

    try:
        emails = gmail_client.fetch_recent(limit=limit, query=query)
    except gmail_client.GmailError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Could not read the mailbox: {exc}") from exc

    STAGING_PATH.parent.mkdir(parents=True, exist_ok=True)
    already = _load_staged_ids() | _load_labelled_ids(LABELS_PATH)

    added, skipped_duplicate, skipped_bulk = 0, 0, 0
    with open(STAGING_PATH, "a", encoding="utf-8") as handle:
        for email in emails:
            if include_bulk != "yes" and not prefilter(email).keep:
                skipped_bulk += 1
                continue
            record = gmail_client.staging_record(email)
            if record["id"] in already:
                skipped_duplicate += 1
                continue
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            already.add(record["id"])
            added += 1

    return JSONResponse({
        "ok": True,
        "fetched": len(emails),
        "added": added,
        "skipped_duplicate": skipped_duplicate,
        "skipped_bulk": skipped_bulk,
        "staging_path": str(STAGING_PATH),
        "next": "python eval/label_cli.py",
    })


@app.get("/api/status")
def api_status() -> JSONResponse:
    return JSONResponse(
        {
            "backend": llm.backend_name(),
            "profiles": store.count_profiles(),
            "using_fallback": llm.backend_name().startswith("rules"),
            "build": _build_stamp(),
        }
    )


def main() -> None:
    import uvicorn

    if _port_is_taken(PORT):
        print(
            f"\n  Port {PORT} is already in use, most likely by an older copy of this app.\n"
            f"  That copy would keep serving stale code and a stale .env, so this one will\n"
            f"  not start. Stop it first, or run on another port with PROTOTYPE_PORT=8001.\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    store.init_db()
    backend = llm.backend_name()
    print("\n  Recruiter Email Agent - prototype")
    print(f"  Model: {backend}")
    print(f"  Fallback chain: {', '.join(b.name for b in llm.configured_backends())}")
    if backend.startswith("rules"):
        print("  No API key found. Using keyword heuristics, which have poor recall.")
        print("  Add GEMINI_API_KEY or GROQ_API_KEY to .env for real classification.")
    print(f"  Candidate profiles: {store.count_profiles()}")
    print(f"  Build: {_build_stamp()}   (must match the stamp shown in the page header)")
    print(f"\n  Open http://127.0.0.1:{PORT}\n")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
