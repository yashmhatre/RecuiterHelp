"""Email Agent page for the FORGE AI app — Exeliq integration.

Kept in its own module rather than inlined into app.py for two reasons: the edit to the
client's 2,900-line file stays small enough to read in a diff, and they can merge our work back
by copying one file and five lines.

It talks to the screening pipeline over HTTP (default http://127.0.0.1:8000), so the two apps
keep separate dependency trees. Streamlit and FastAPI disagree about which starlette they want,
and discovering that by breaking one of them is not an experience worth repeating.

Design notes
------------
The palette, radii and card treatment are the client's, taken from app.py. This is a page
inside their product, not a standalone identity, so a different look would be wrong however
nice it might be on its own.

Three decisions specific to this page:

1. The verdict is the hero. Someone triaging fifteen to twenty of these a day wants the answer
   before the evidence, so the form sits below the result once there is one.
2. The stage rail is numbered. Numbered markers are usually decoration, but here the content
   genuinely is an ordered sequence and the order carries meaning -- sender verification runs
   before the model deliberately -- so showing where an email stopped is the information a
   reviewer actually needs after a refusal.
3. Match scores are bars, not gauges. Gauges read one at a time; bars let you compare three
   candidates in a glance, which is the real task.
"""

from __future__ import annotations

import os
from typing import Any

import requests

EMAIL_ENGINE_URL = os.environ.get("EMAIL_ENGINE_URL", "http://127.0.0.1:8000")
TIMEOUT_SECONDS = 120

# The client's tokens, from app.py. Not re-chosen here.
INK = "#24243B"
MUTED = "#8A8FA3"
ACCENT = "#5B4CF2"
TINT = "#ECEEF6"
PASS = "#1E8E4C"
PASS_BG = "#E4F7EA"
HOLD = "#B8790A"
HOLD_BG = "#FFF4E0"
STOP = "#C23636"


def engine_status() -> tuple[bool, dict[str, Any]]:
    try:
        response = requests.get(f"{EMAIL_ENGINE_URL}/api/status", timeout=5)
        response.raise_for_status()
        return True, response.json()
    except requests.RequestException as exc:
        return False, {"detail": str(exc)[:160]}


def screen_email(sender: str, subject: str, body: str) -> dict[str, Any]:
    try:
        response = requests.post(
            f"{EMAIL_ENGINE_URL}/api/run",
            data={"sender": sender, "subject": subject, "body": body, "auth": "", "reply_to": ""},
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            return {"error": response.json().get("detail", response.text[:200])}
        return response.json()
    except requests.RequestException as exc:
        return {"error": f"Could not reach the screening engine: {exc}"}


#: status -> (headline, what happens next, colour, tint). Written as outcomes a person acts on,
#: not as internal status names.
VERDICTS: dict[str, tuple[str, str, str, str]] = {
    "drafted": ("Reply ready for you to send", "Read it below, edit if needed, then send it from your mail client.", PASS, PASS_BG),
    "needs_review": ("Held for you to decide", "Something did not meet the bar, so no reply was written. The stage that stopped it is marked below.", HOLD, HOLD_BG),
    "not_recruiter": ("Not a recruiter email", "No reply needed. Nothing was drafted.", MUTED, TINT),
    "skipped_bulk": ("Bulk mail, dropped early", "Caught before any AI ran, so it cost nothing.", MUTED, TINT),
}

#: The six gates, in the order they run. Keyed by the stage names the engine returns.
RAIL = [
    ("Pre-filter", "bulk"),
    ("Sender verification", "spoofing"),
    ("Classify and extract", "the requirement"),
    ("Match profiles", "candidates"),
    ("Compose draft", "the reply"),
    ("Validate", "safety checks"),
]


def render(st, render_gauge) -> None:
    """Draw the page. `render_gauge` is accepted for signature compatibility with the host app
    but unused: bars compare better than gauges when there are several candidates."""
    ok, info = engine_status()

    st.markdown(
        f'<div style="font-size:26px;font-weight:700;color:{INK};margin-bottom:2px;">'
        f'Email Agent</div>'
        f'<div style="color:{MUTED};font-size:14px;margin-bottom:18px;">'
        f'Screens inbound job leads, finds who fits, and writes the reply. '
        f'You send it &mdash; this never sends anything itself.</div>',
        unsafe_allow_html=True,
    )

    if not ok:
        st.markdown(
            f'<div style="background:{HOLD_BG};border-radius:14px;padding:18px 20px;">'
            f'<div style="font-weight:600;color:{HOLD};">Screening engine is not running</div>'
            f'<div style="color:{INK};font-size:13.5px;margin-top:6px;">'
            f'Start it, then reload this page.</div></div>',
            unsafe_allow_html=True,
        )
        st.code(".venv\\Scripts\\python.exe -m prototype.app", language="text")
        return

    result = st.session_state.get("exeliq_email_result")
    if result:
        _render_result(st, result)
        st.write("")

    _render_form(st, info, has_result=bool(result))


def _render_form(st, info: dict, has_result: bool) -> None:
    with st.expander("Screen another email" if has_result else "Screen an email", expanded=not has_result):
        with st.form("exeliq_email_agent_form"):
            left, right = st.columns(2)
            with left:
                sender = st.text_input("From", placeholder="Priya Sharma <priya@agency.com>")
            with right:
                subject = st.text_input("Subject", placeholder="Requirement: Senior Data Engineer")
            body = st.text_area("Email body", height=190,
                                placeholder="Paste the recruiter's email here")
            submitted = st.form_submit_button("Screen this email", type="primary")

        if submitted:
            if not sender.strip() or not body.strip():
                st.warning("Add a sender and the email body, then try again.")
            else:
                with st.spinner("Reading the email, matching candidates, writing the reply"):
                    st.session_state.exeliq_email_result = screen_email(sender, subject, body)
                st.rerun()

    st.markdown(
        f'<div style="color:{MUTED};font-size:12px;margin-top:10px;">'
        f'Reading with {info.get("backend", "the configured model")} '
        f'against {info.get("profiles", 0)} candidate profiles.</div>',
        unsafe_allow_html=True,
    )


def _render_result(st, result: dict[str, Any]) -> None:
    if result.get("error"):
        st.markdown(
            f'<div style="background:#FBEAEA;border-radius:14px;padding:16px 20px;'
            f'color:{STOP};font-weight:600;">Screening failed</div>'
            f'<div style="color:{INK};font-size:13.5px;margin-top:8px;">{result["error"]}</div>',
            unsafe_allow_html=True,
        )
        return

    headline, next_step, colour, tint = VERDICTS.get(
        result.get("status"), (str(result.get("status")), "", MUTED, TINT)
    )

    # Hero: the answer, and what to do about it.
    st.markdown(
        f'<div style="background:{tint};border-radius:16px;padding:22px 26px;margin-bottom:16px;">'
        f'<div style="font-size:21px;font-weight:700;color:{colour};">{headline}</div>'
        f'<div style="color:{INK};font-size:14px;margin-top:6px;max-width:60ch;">{next_step}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    _render_rail(st, result.get("stages", []))

    matches = result.get("matches") or []
    if matches:
        _render_matches(st, matches)

    draft = result.get("draft")
    if draft:
        _render_draft(st, draft)


def _render_rail(st, stages: list[dict]) -> None:
    """Where the email got to. The one place numbered markers earn their place: this is an
    ordered sequence of gates, and which one stopped it is the question every refusal raises."""
    by_name = {s["name"]: s for s in stages}
    cells = []
    stopped = False

    for index, (name, guards) in enumerate(RAIL, start=1):
        stage = by_name.get(name)
        if stage is None:
            state, dot, label_colour = ("not reached", "#D7DBE4", MUTED) if stopped else ("pending", "#D7DBE4", MUTED)
        elif stage["ok"]:
            state, dot, label_colour = "passed", PASS, INK
        else:
            state, dot, label_colour = "stopped here", STOP, STOP
            stopped = True

        cells.append(
            f'<div style="flex:1;min-width:112px;">'
            f'<div style="display:flex;align-items:center;gap:6px;">'
            f'<span style="width:20px;height:20px;border-radius:50%;background:{dot};'
            f'color:white;font-size:11px;font-weight:700;display:inline-flex;'
            f'align-items:center;justify-content:center;">{index}</span>'
            f'<span style="height:2px;background:{dot};flex:1;opacity:.35;"></span></div>'
            f'<div style="font-size:12.5px;font-weight:600;color:{label_colour};margin-top:7px;">{name}</div>'
            f'<div style="font-size:11px;color:{MUTED};">{state if state != "passed" else "catches " + guards}</div>'
            f"</div>"
        )

    st.markdown(
        '<div style="display:flex;gap:8px;flex-wrap:wrap;background:white;border-radius:14px;'
        'padding:18px 20px;margin-bottom:16px;">' + "".join(cells) + "</div>",
        unsafe_allow_html=True,
    )

    failed = [s for s in stages if not s["ok"]]
    if failed:
        st.markdown(
            f'<div style="color:{INK};font-size:13.5px;margin:-6px 0 16px 2px;">'
            f'<b>{failed[0]["name"]}:</b> {failed[0]["summary"]}</div>',
            unsafe_allow_html=True,
        )


def _render_matches(st, matches: list[dict]) -> None:
    st.markdown(
        f'<div style="font-size:15px;font-weight:700;color:{INK};margin-bottom:8px;">'
        f'Who to put forward</div>',
        unsafe_allow_html=True,
    )

    for match in matches:
        score = int(match["score"])
        colour = PASS if score >= 70 else HOLD if score >= 40 else STOP
        st.markdown(
            f'<div style="background:white;border-radius:14px;padding:16px 20px;margin-bottom:10px;">'
            f'<div style="display:flex;align-items:baseline;gap:10px;">'
            f'<span style="font-weight:700;color:{INK};font-size:15px;">{match["name"]}</span>'
            f'<span style="color:{MUTED};font-size:13px;">{match["title"]}</span>'
            f'<span style="flex:1;"></span>'
            f'<span style="font-weight:700;color:{colour};font-size:17px;">{score}</span>'
            f'<span style="color:{MUTED};font-size:12px;">out of 100</span></div>'
            f'<div style="height:6px;background:{TINT};border-radius:3px;margin:10px 0 12px;">'
            f'<div style="height:100%;width:{score}%;background:{colour};border-radius:3px;"></div></div>'
            f'<div style="color:{MUTED};font-size:12.5px;">{match["reason"]}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

        dims = match.get("dimensions", [])
        if dims:
            with st.expander(f"How {match['name'].split()[0]} scored"):
                for d in dims:
                    pct = int(100 * d["score"] / d["max"]) if d["max"] else 0
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:7px;">'
                        f'<span style="width:150px;font-size:12.5px;color:{INK};">{d["name"]}</span>'
                        f'<span style="width:120px;height:5px;background:{TINT};border-radius:3px;">'
                        f'<span style="display:block;height:100%;width:{pct}%;background:{ACCENT};'
                        f'border-radius:3px;"></span></span>'
                        f'<span style="font-size:12px;color:{MUTED};width:58px;">{d["score"]} / {d["max"]}</span>'
                        f'<span style="font-size:12px;color:{MUTED};">{d["note"]}</span></div>',
                        unsafe_allow_html=True,
                    )


def _render_draft(st, draft: dict[str, Any]) -> None:
    discarded = draft.get("discarded")
    st.markdown(
        f'<div style="font-size:15px;font-weight:700;color:{INK};margin:18px 0 8px;">'
        f'{"Rejected draft" if discarded else "Your reply"}</div>',
        unsafe_allow_html=True,
    )

    if discarded:
        issues = (draft.get("validation") or {}).get("issues", [])
        st.markdown(
            f'<div style="background:#FBEAEA;border-radius:14px;padding:16px 20px;margin-bottom:12px;">'
            f'<div style="color:{STOP};font-weight:600;">This reply was thrown away, not saved</div>'
            f'<div style="color:{INK};font-size:13.5px;margin-top:6px;">'
            f'It failed {len(issues)} safety check{"s" if len(issues) != 1 else ""}. '
            f'Shown so you can see what was wrong.</div></div>',
            unsafe_allow_html=True,
        )
        for issue in issues:
            st.markdown(f"- **{issue['check'].replace('_', ' ')}** &mdash; {issue['detail']}")

    st.text_input("To", value=", ".join(draft.get("to", [])), disabled=True, key="exeliq_to")
    st.text_area("Message", value=draft.get("body_text", ""), height=210, key="exeliq_body")

    attached = [a["filename"] for a in draft.get("attachments", [])]
    if attached:
        st.markdown(
            f'<div style="color:{INK};font-size:13px;">Attached: {", ".join(attached)}</div>',
            unsafe_allow_html=True,
        )
    if not discarded:
        st.markdown(
            f'<div style="color:{MUTED};font-size:12.5px;margin-top:8px;">'
            f'Copy this into your mail client to send it. The agent has no send capability, '
            f'so nothing leaves here on its own.</div>',
            unsafe_allow_html=True,
        )
