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

import re
import shutil
from email.message import EmailMessage
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from email_agent.config import load_dotenv_if_present
from prototype import llm, store
from prototype.pipeline import email_from_form, run_pipeline
from prototype.resume_text import extract_profile_hints, parse_resume

load_dotenv_if_present()

STATIC_DIR = Path(__file__).resolve().parent / "static"
ALLOWED_SUFFIXES = {".pdf", ".docx", ".doc", ".txt", ".rtf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

app = FastAPI(title="Recruiter Email Agent - prototype", docs_url="/api/docs")


@app.on_event("startup")
def startup() -> None:
    store.init_db()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


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


@app.get("/api/samples")
def api_samples() -> JSONResponse:
    """The synthetic emails already in the repo, so the demo needs no typing."""
    from prototype.samples import load_samples

    return JSONResponse({"samples": load_samples()})


@app.get("/api/status")
def api_status() -> JSONResponse:
    return JSONResponse(
        {
            "backend": llm.backend_name(),
            "profiles": store.count_profiles(),
            "using_fallback": llm.backend_name().startswith("rules"),
        }
    )


def main() -> None:
    import uvicorn

    store.init_db()
    print("\n  Recruiter Email Agent - prototype")
    print(f"  Model backend: {llm.backend_name()}")
    if llm.backend_name().startswith("rules"):
        print("  No API key found. Using keyword heuristics - add GEMINI_API_KEY or")
        print("  GROQ_API_KEY to .env for real classification.")
    print("  Open http://127.0.0.1:8000\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
