"""Email Agent page for the FORGE AI app — Exeliq integration.

Kept in its own module rather than inlined into app.py for two reasons: the edit to the
client's 2,900-line file stays small enough to read in a diff, and they can merge our work
back by copying one file and three lines.

It talks to the screening pipeline over HTTP (default http://127.0.0.1:8000), so the two apps
keep separate dependency trees. Streamlit and FastAPI disagree about which starlette they
want, and discovering that by breaking one of them is not an experience worth repeating.
"""

from __future__ import annotations

import os
from typing import Any

import requests

#: Where the screening pipeline listens. Overridable for a different host or port.
EMAIL_ENGINE_URL = os.environ.get("EMAIL_ENGINE_URL", "http://127.0.0.1:8000")

TIMEOUT_SECONDS = 120


def engine_status() -> tuple[bool, dict[str, Any]]:
    """Whether the pipeline is up, and what it reports about itself."""
    try:
        response = requests.get(f"{EMAIL_ENGINE_URL}/api/status", timeout=5)
        response.raise_for_status()
        return True, response.json()
    except requests.RequestException as exc:
        return False, {"detail": str(exc)[:160]}


def screen_email(sender: str, subject: str, body: str) -> dict[str, Any]:
    """Run one email through the full pipeline and return every stage."""
    try:
        response = requests.post(
            f"{EMAIL_ENGINE_URL}/api/run",
            data={"sender": sender, "subject": subject, "body": body, "auth": "", "reply_to": ""},
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            detail = response.json().get("detail", response.text[:200])
            return {"error": f"Screening failed: {detail}"}
        return response.json()
    except requests.RequestException as exc:
        return {"error": f"Could not reach the screening engine: {exc}"}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

VERDICTS = {
    "drafted": ("Draft ready for review", "#22C55E"),
    "needs_review": ("Needs review — no draft", "#F59E0B"),
    "not_recruiter": ("Not a recruiter email", "#8A8FA3"),
    "skipped_bulk": ("Bulk or automated — dropped before the model", "#8A8FA3"),
}

HOW_IT_WORKS = """
Six stages run in order. An email leaves at the first one that rejects it.

1. **Pre-filter** — bulk mail, newsletters, auto-replies and job-board blasts are dropped
   before any model runs, so they cost nothing.
2. **Sender verification** — SPF, DKIM and DMARC must all pass. This runs *before* the model
   deliberately, so a spoofed sender never reaches one.
3. **Classify and extract** — recruiter or not, the intent, and the requirement itself: role,
   must-have skills, preferred skills, years, location.
4. **Match** — hard filters, then FORGE Match™ scoring across six dimensions out of 100.
   At most one profile per candidate, so the same person is never offered twice.
5. **Draft** — written from a template using only facts from the matched profiles, with each
   candidate's current resume attached.
6. **Validate** — nine checks, including that the recipient is the verified sender, that every
   attached resume belongs to the candidate named beside it, and that no salary figure appears.

A draft failing any check is **discarded rather than shown as ready** — a wrong draft is worse
than no draft. Nothing is ever sent: you review and send every reply yourself.
"""


def render(st, render_gauge) -> None:
    """Draw the page. `st` and `render_gauge` are passed in so this module stays importable
    without Streamlit and without reaching back into the client's app for a helper."""
    st.markdown('<div class="section-title">Email Agent</div>', unsafe_allow_html=True)
    st.caption(
        "Inbound job leads: screen the mailbox, read the requirement, match candidates and "
        "draft the reply. Drafts only — nothing is sent automatically."
    )

    ok, info = engine_status()
    if not ok:
        st.error(
            f"Screening engine unreachable at {EMAIL_ENGINE_URL}. {info.get('detail', '')}"
        )
        st.code(".venv\\Scripts\\python.exe -m prototype.app", language="text")
        return

    c1, c2, c3 = st.columns(3)
    for col, label, value in (
        (c1, "Engine", "Connected"),
        (c2, "Model", str(info.get("backend", "-"))),
        (c3, "Candidate profiles", str(info.get("profiles", 0))),
    ):
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value" style="font-size:14px;">{value}</div></div>',
                unsafe_allow_html=True,
            )
    st.write("")

    tab_screen, tab_how = st.tabs(["Screen an email", "How it works"])

    with tab_screen:
        with st.form("exeliq_email_agent_form"):
            left, right = st.columns(2)
            with left:
                sender = st.text_input("From", placeholder="Priya Sharma <priya@agency.com>")
            with right:
                subject = st.text_input("Subject", placeholder="Requirement — Senior Data Engineer")
            body = st.text_area("Email body", height=210,
                                placeholder="Paste the recruiter's email here…")
            submitted = st.form_submit_button("Screen this email", type="primary")

        if submitted:
            if not sender.strip() or not body.strip():
                st.warning("A sender and an email body are both needed.")
            else:
                with st.spinner("Screening…"):
                    st.session_state.exeliq_email_result = screen_email(sender, subject, body)

        result = st.session_state.get("exeliq_email_result")
        if result:
            _render_result(st, render_gauge, result)

    with tab_how:
        st.markdown(HOW_IT_WORKS)


def _render_result(st, render_gauge, result: dict[str, Any]) -> None:
    if result.get("error"):
        st.error(result["error"])
        return

    label, colour = VERDICTS.get(result.get("status"), (str(result.get("status")), "#8A8FA3"))
    st.markdown(
        f'<div class="job-card" style="border-left:4px solid {colour};"><b>{label}</b></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    st.markdown("**Pipeline**")
    for stage in result.get("stages", []):
        mark = "✅" if stage["ok"] else "⛔"
        st.markdown(f"{mark} **{stage['name']}** — {stage['summary']}")

    matches = result.get("matches") or []
    if matches:
        st.write("")
        st.markdown("**FORGE Match™**")
        for match in matches:
            gauge_col, detail_col = st.columns([1, 3])
            with gauge_col:
                st.markdown(
                    render_gauge(int(match["score"]), size=78, color="#22C55E",
                                 label=match.get("signal", "")),
                    unsafe_allow_html=True,
                )
            with detail_col:
                st.markdown(f"**{match['name']}** — {match['title']}")
                st.caption(match["reason"])
                for dim in match.get("dimensions", []):
                    st.markdown(
                        "<span style='font-size:12px;color:#8A8FA3;'>"
                        f"{dim['name']}: {dim['score']}/{dim['max']} — {dim['note']}</span>",
                        unsafe_allow_html=True,
                    )
            st.write("")

    draft = result.get("draft")
    if not draft:
        return

    st.markdown("**Draft reply**")
    if draft.get("discarded"):
        st.warning("This draft failed validation and was not saved. Shown so you can see what "
                   "was rejected.")
        for issue in (draft.get("validation") or {}).get("issues", []):
            st.markdown(f"- `{issue['check']}` — {issue['detail']}")

    st.text_input("To", value=", ".join(draft.get("to", [])), disabled=True, key="exeliq_to")
    st.text_area("Reply", value=draft.get("body_text", ""), height=220, key="exeliq_body")

    attached = [a["filename"] for a in draft.get("attachments", [])]
    if attached:
        st.markdown(f"**Attached:** {', '.join(attached)}")
    st.caption(
        "Review, edit if needed, then send it yourself from your mail client. This system has "
        "no send capability."
    )
