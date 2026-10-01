# FORGE AI (TM)

AI-Powered Career Acceleration, Talent Readiness & Human Authenticity Platform.

A single-file Streamlit application covering the full candidate journey: account
creation, profile setup, a personalized onboarding welcome kit, and 14 live,
functional FORGE agent pages plus a tabbed profile/settings center — matching
the FORGE AI product wireframe.

## Features

### Onboarding
- **Sign Up / Login** — 5 account types (Individual, Corporate, Institution,
  Training Institute, Staffing Firm) with company-domain email validation for
  organizational accounts, and a Program of Interest field tied to the actual
  revenue-tier offerings.
- **Profile Setup** — role, target role, certifications, organization name,
  resume upload, and a dedicated Human Authenticity Engine (voice-learning)
  consent checkbox.
- **Welcome Kit** — a personalized welcome email naming all 5 proprietary
  FORGE engines (Match/Sim/VoiceAI/Insights/Growth), downloadable as `.txt`.
- **Platform Tour (Videos)** and **FAQs** — role-aware, including dedicated
  sections on the proprietary engines and voice-learning consent.

### Career Command Center (14 live agent pages)
1. **Dashboard** — readiness score, job matches, activity feed, learning streak
2. **Job Hunter Agent** — searchable job feed with Save / Apply / Analyze JD
3. **JD Intelligence Agent** — deterministic keyword-based JD parser (word-boundary
   matching, no external API), skill/seniority/match extraction
4. **Candidate Matching Agent** — candidate ranking table (org accounts) or
   personal application tracker (individual accounts)
5. **Resume Intelligence Agent** — 4-step ATS optimization workflow with
   downloadable generated resume
6. **Gap Analysis Agent** — prioritized skill-gap breakdown against a selected job
7. **Learning & Development Agent** — skills progress tracking, course
   enrollment, certification and reading-list management
8. **FORGE Simulation Agent** — 6 scenario types with real answer scoring
   (keyword + depth heuristic)
9. **Performance Evaluator Agent** — aggregated simulation performance report
10. **Human Authenticity Engine** — voice profile, consistency score (driven by
    consent status), sample generated content
11. **LinkedIn Branding Agent** — post generation, performance metrics, scheduling
12. **Outreach Agent** — campaign management, message templates, drafting
13. **Success Tracking Agent** — real application/interview/offer conversion analytics
14. **Career Intelligence Agent** — market demand, salary benchmarks, career
    recommendations

### My Profile & Settings
Tabbed layout: Profile, Resume & Documents, Preferences, Account Settings
(toggles), Integrations (Connect/Disconnect).

All logic is conditional on **account type**, **role**, and **department** — no
external APIs or a database server are used. All mock data (jobs, candidates,
market data, simulation scoring) is generated deterministically from the
signed-in user's own profile, so results are consistent across reruns without
needing a backend.

## Data persistence

Candidate accounts and progress are **not** session-only — they are saved to
local JSON files on disk and restored automatically on the next login, even
after the app process has been fully restarted:

- `forge_ai_data/users_db.json` — account credentials (passwords are SHA-256
  hashed, never stored in plain text) and account metadata.
- `forge_ai_data/user_<user_id>.json` — that candidate's full profile and
  in-progress work: applications, saved jobs, learning progress, simulation
  results, resume versions, outreach campaigns, account settings, and
  **which page they were last working on**.
- `forge_ai_data/resumes/<user_id>.bin` and `forge_ai_data/photos/<user_id>.bin`
  — the actual uploaded resume/photo file bytes.

On every rerun, the app auto-saves the signed-in candidate's current state.
On login, it restores that state in full and takes them straight back to the
exact page they were last working on — so returning to the app feels like
picking up mid-task, not starting over. Duplicate sign-ups against an email
already on file are rejected with a prompt to log in instead.

The `forge_ai_data/` folder is created automatically next to `app.py` the
first time the app runs, and is safe to delete if you want to reset all data.

## Requirements

- Python 3.9+
- Streamlit

## Setup

```bash
pip install streamlit
```

## Run

```bash
streamlit run app.py
```

Then open the URL Streamlit prints in your terminal (typically
`http://localhost:8501`).

## Notes

- This is a self-contained demo: no external APIs, no database server. Data is
  persisted to local JSON/binary files under `forge_ai_data/` (see "Data
  persistence" above) rather than an in-memory-only session.
- Corporate/Institution/Training Institute/Staffing Firm sign-up blocks common
  free email providers to enforce use of an official organizational email domain.
- The JD Intelligence parser uses word-boundary regex matching (not raw
  substring matching) specifically to avoid false positives like "ai" matching
  inside "airflow" or "scala" matching inside "scalable".
- Simulation scoring is a deterministic heuristic based on answer length and
  relevant-keyword presence — it rewards detailed, specific answers over short
  or vague ones, but is not a real NLP/AI evaluation.
- Video cards on the Platform Tour page are structural placeholders representing
  the short onboarding videos that would be served from a media library in
  production.

