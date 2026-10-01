"""
FORGE AI (TM) - AI-Powered Career Acceleration, Talent Readiness
and Human Authenticity Platform.

Single-file Streamlit application.
Python only. No external APIs. No database - session_state only.
"""

import re
import io
import os
import json
import hashlib
import random
import string
import datetime as dt

import streamlit as st

# Exeliq integration: the inbound Email Agent page lives in its own module.
import exeliq_email_agent

# --------------------------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="FORGE AI | Career Acceleration Platform",
    page_icon="F",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# CONSTANTS
# --------------------------------------------------------------------------
APP_NAME = "FORGE AI"
APP_TAGLINE = "AI-Powered Career Acceleration, Talent Readiness & Human Authenticity Platform"

# --------------------------------------------------------------------------
# LOCAL PERSISTENCE PATHS (no external APIs / no database - plain JSON + files
# on local disk, so data survives an app restart and follows the user across
# logins)
# --------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forge_ai_data")
RESUME_DIR = os.path.join(DATA_DIR, "resumes")
PHOTO_DIR = os.path.join(DATA_DIR, "photos")
USERS_DB_PATH = os.path.join(DATA_DIR, "users_db.json")
for _d in (DATA_DIR, RESUME_DIR, PHOTO_DIR):
    os.makedirs(_d, exist_ok=True)

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "protonmail.com", "aol.com", "live.com", "rediffmail.com", "msn.com",
}

ACCOUNT_TYPES = [
    "Individual / Job Seeker", "Corporate", "Institution / University",
    "Training Institute", "Staffing Firm",
    # Exeliq integration: an explicit desk account. Recruiter capability previously depended on
    # picking the right role inside a Corporate account, which nobody would discover.
    "HR / Recruitment Desk",
]

DEPARTMENTS = [
    "Not Applicable", "Data & Analytics", "Cloud & DevOps", "Software Engineering",
    "AI / Machine Learning", "Human Resources", "Talent Acquisition / Recruitment",
    "Sales & Business Development", "Marketing", "Finance & Accounting",
    "Operations", "Product Management", "Customer Success", "Legal & Compliance",
    "Academic Affairs", "Career Services", "Training & Curriculum",
    "Client Delivery / Staffing Operations", "Other",
]

ROLES_BY_ACCOUNT_TYPE = {
    "Individual / Job Seeker": [
        "Data Engineer", "Data Analyst", "Data Architect", "Cloud Engineer",
        "DevOps Engineer", "Software Engineer", "Machine Learning Engineer",
        "AI Engineer", "Cybersecurity Professional", "Solution Architect",
        "Engineering Manager", "Technology Leader", "Product Manager",
        "Business Analyst", "Student / Fresher", "Career Changer", "Other",
    ],
    "Corporate": [
        "HR Manager", "Talent Acquisition Lead", "Recruiter", "Engineering Manager",
        "Director of Data & Analytics", "CIO / CTO", "L&D Manager",
        "Team Lead", "Individual Contributor", "Other",
    ],
    "Institution / University": [
        "Career Services Officer", "Placement Coordinator", "Faculty / Professor",
        "Academic Administrator", "Student Counsellor", "Other",
    ],
    "Training Institute": [
        "Training Director", "Program Manager", "Placement Officer",
        "Trainer / Faculty", "Curriculum Designer", "Operations Manager", "Other",
    ],
    "Staffing Firm": [
        "Talent Acquisition Lead", "Recruiter", "Account Manager",
        "Delivery Manager", "Branch Manager", "Business Development Manager", "Other",
    ],
    # Exeliq integration
    "HR / Recruitment Desk": [
        "Recruiter", "HR Manager", "Talent Acquisition Lead", "Recruitment Admin",
        "Delivery Manager", "Account Manager", "Other",
    ],
}

COUNTRIES = [
    "India", "United States", "Canada", "United Kingdom", "Australia",
    "Germany", "United Arab Emirates", "Singapore", "Other",
]

LEARNING_MODES = ["Self-paced (text)", "Video-based", "Live simulation / interactive", "Mixed"]

CERTIFICATION_OPTIONS = [
    "AWS Certified Solutions Architect", "AWS Certified Data Engineer",
    "Azure Data Engineer Associate", "Azure Solutions Architect Expert",
    "Databricks Certified Data Engineer", "Databricks Certified ML Associate",
    "Google Cloud Professional Data Engineer", "Google Cloud Professional Cloud Architect",
    "Certified Kubernetes Administrator (CKA)", "PMP", "CSM (Scrum Master)",
    "CISSP", "CompTIA Security+", "Snowflake SnowPro", "Terraform Associate",
    "None yet", "Other",
]

PROGRAMS_INDIVIDUAL = [
    "Resume Optimization", "Interview Readiness Program", "Career Accelerator Program",
    "Not sure yet / Just exploring",
]

PROGRAMS_ENTERPRISE = [
    "Talent Readiness Platform", "Corporate Training Programs", "Enterprise Licensing",
    "Not sure yet / Just exploring",
]

REFERRAL_SOURCES = [
    "LinkedIn", "Company / Institution invite", "Referral from a colleague",
    "Google search", "Recruiter outreach", "Event / Webinar", "Other",
]

# ==========================================================================
# EXELIQ INTEGRATION - recruiter/HR bifurcation and the inbound Email Agent.
# Added to the client's app; everything in these marked blocks is ours.
# ==========================================================================

#: Roles that run a desk: they receive requirements and supply candidates. The Email Agent is
#: for these people. A job seeker has no inbound recruiter mailbox to screen.
RECRUITER_ROLES = {
    "HR Manager", "Talent Acquisition Lead", "Recruiter", "Recruitment Admin",
    "Account Manager",
    "Delivery Manager", "Branch Manager", "Placement Coordinator", "Career Services Officer",
}

#: Departments that imply the same, whatever the job title says.
RECRUITER_DEPARTMENTS = {"Human Resources", "Talent Acquisition / Recruitment",
                         "Client Delivery / Staffing Operations", "Career Services"}

#: Pages that only make sense for someone managing their own career.
CANDIDATE_ONLY_PAGES = {
    "resume_intelligence", "gap_analysis", "learning_dev", "simulation",
    "performance_eval", "human_authenticity", "linkedin_branding", "career_intelligence",
}

#: Pages that only make sense for someone running a recruitment desk.
RECRUITER_ONLY_PAGES = {"email_agent"}


def is_recruiter_account(prof: dict) -> bool:
    """Whether this account runs a recruitment desk rather than a personal job search.

    Checked three ways because people fill forms inconsistently: an explicit account type, the
    role they picked, or the department. Any one is enough.
    """
    if prof.get("account_type") in ("HR / Recruitment Desk", "Staffing Firm"):
        return True
    if prof.get("role") in RECRUITER_ROLES:
        return True
    return prof.get("department") in RECRUITER_DEPARTMENTS


NAV_ITEMS = [
    ("Sign Up / Login", "auth"),
    ("Profile Setup", "profile"),
    ("Welcome Kit", "welcome"),
    ("Dashboard", "dashboard"),
    ("Job Hunter Agent", "job_hunter"),
    ("JD Intelligence Agent", "jd_intelligence"),
    ("Candidate Matching Agent", "candidate_matching"),
    ("Email Agent", "email_agent"),                      # Exeliq integration
    ("Resume Intelligence Agent", "resume_intelligence"),
    ("Gap Analysis Agent", "gap_analysis"),
    ("Learning & Development Agent", "learning_dev"),
    ("FORGE Simulation Agent", "simulation"),
    ("Performance Evaluator Agent", "performance_eval"),
    ("Human Authenticity Engine", "human_authenticity"),
    ("LinkedIn Branding Agent", "linkedin_branding"),
    ("Outreach Agent", "outreach"),
    ("Success Tracking Agent", "success_tracking"),
    ("Career Intelligence Agent", "career_intelligence"),
    ("Platform Tour (Videos)", "videos"),
    ("FAQs", "faqs"),
    ("My Profile & Settings", "settings"),
]

# --------------------------------------------------------------------------
# SESSION STATE INIT
# --------------------------------------------------------------------------
def init_state():
    defaults = {
        "authenticated": False,
        "users_db": {},          # user_id -> {email, password, account_type}
        "current_user_id": None,
        "profile": {},           # profile fields
        "profile_complete": False,
        "resume_file_name": None,
        "resume_file_bytes": None,
        "photo_file_name": None,
        "active_page": "auth",
        "mock_jobs": None,       # lazily generated, cached per session
        "saved_jobs": set(),
        "applied_jobs": {},      # job_id -> status ("Applied", "Interview", "Offer")
        "job_alerts": [],
        "selected_job_id": None,
        "jd_analysis_result": None,
        "mock_candidates": None,
        "enrolled_courses": set(),
        "reading_list": set(),
        "learning_progress": {},   # skill -> pct complete
        "resume_versions_saved": 0,
        "simulation_results": {},   # scenario_id -> {technical, communication, problem_solving, leadership, overall}
        "active_scenario_id": None,
        "voice_profile_seed": 0,
        "scheduled_posts": [],
        "outreach_campaigns": None,   # lazily generated
        "outreach_message_draft": "",
        "account_settings": {
            "email_notifications": True, "job_alerts": True, "weekly_reports": True,
            "profile_visibility": True, "two_factor_auth": False,
        },
        "integrations": {"LinkedIn": False, "Google Calendar": False, "Slack": False},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# --------------------------------------------------------------------------
# HELPERS / VALIDATION
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,15}$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))


def email_domain(email: str) -> str:
    return email.strip().split("@")[-1].lower() if "@" in email else ""


def is_company_email(email: str) -> bool:
    return email_domain(email) not in FREE_EMAIL_DOMAINS


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_RE.match(phone.strip()))


def password_strength(pwd: str) -> str:
    score = 0
    if len(pwd) >= 8:
        score += 1
    if re.search(r"[A-Z]", pwd):
        score += 1
    if re.search(r"[a-z]", pwd):
        score += 1
    if re.search(r"[0-9]", pwd):
        score += 1
    if re.search(r"[^A-Za-z0-9]", pwd):
        score += 1
    if score <= 2:
        return "Weak"
    if score <= 4:
        return "Medium"
    return "Strong"


def generate_user_id(name: str) -> str:
    base = re.sub(r"[^a-zA-Z]", "", name).lower() or "user"
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{base}{suffix}"


def initials(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "FA"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


# --------------------------------------------------------------------------
# PERSISTENCE LAYER
# Local JSON files on disk (no external APIs, no database). This is what
# makes a candidate's profile and progress survive an app restart and
# reappear exactly as they left it the next time they log in.
# --------------------------------------------------------------------------
def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


def load_users_db() -> dict:
    if not os.path.exists(USERS_DB_PATH):
        return {}
    try:
        with open(USERS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_users_db(db: dict):
    tmp_path = USERS_DB_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
        os.replace(tmp_path, USERS_DB_PATH)
    except OSError:
        pass  # best-effort persistence; never block the UI on a save failure


def _user_data_path(user_id: str) -> str:
    return os.path.join(DATA_DIR, f"user_{user_id}.json")


# Every one of these session_state keys represents the candidate's actual
# progress/work and is written to disk on every rerun, then restored in full
# on their next login.
PERSIST_KEYS = [
    "profile", "profile_complete", "resume_file_name", "photo_file_name",
    "active_page", "saved_jobs", "applied_jobs", "job_alerts",
    "selected_job_id", "jd_analysis_result", "enrolled_courses", "reading_list",
    "learning_progress", "resume_versions_saved", "simulation_results",
    "active_scenario_id", "voice_profile_seed", "scheduled_posts",
    "outreach_campaigns", "outreach_message_draft", "account_settings", "integrations",
]
SET_KEYS = {"saved_jobs", "enrolled_courses", "reading_list"}


def save_user_data(user_id: str):
    if not user_id:
        return
    data = {}
    for key in PERSIST_KEYS:
        val = st.session_state.get(key)
        if key in SET_KEYS and isinstance(val, set):
            val = sorted(val)
        data[key] = val
    tmp_path = _user_data_path(user_id) + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, _user_data_path(user_id))
    except (OSError, TypeError):
        pass  # best-effort; a failed save should never crash the app


def load_user_data(user_id: str) -> bool:
    """Restores a returning candidate's full session exactly as they left it.
    Returns True if saved data was found and loaded, False for a fresh user."""
    path = _user_data_path(user_id)
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    for key in PERSIST_KEYS:
        if key not in data:
            continue
        val = data[key]
        if key in SET_KEYS and isinstance(val, list):
            val = set(val)
        st.session_state[key] = val
    resume_path = os.path.join(RESUME_DIR, f"{user_id}.bin")
    if os.path.exists(resume_path):
        try:
            with open(resume_path, "rb") as f:
                st.session_state.resume_file_bytes = f.read()
        except OSError:
            pass
    return True


def save_uploaded_resume(user_id: str, file_bytes: bytes):
    try:
        with open(os.path.join(RESUME_DIR, f"{user_id}.bin"), "wb") as f:
            f.write(file_bytes)
    except OSError:
        pass


def save_uploaded_photo(user_id: str, file_bytes: bytes):
    try:
        with open(os.path.join(PHOTO_DIR, f"{user_id}.bin"), "wb") as f:
            f.write(file_bytes)
    except OSError:
        pass


# --------------------------------------------------------------------------
# MOCK DATA ENGINE (no external APIs - deterministic, seeded per user)
# --------------------------------------------------------------------------
MOCK_COMPANIES = [
    "TechNova Solutions", "CloudScale Analytics", "MindTree", "InnoTech Systems",
    "Zenith Data Labs", "NexWave Cloud", "Quantum Analytics Co", "BluePeak Systems",
    "Orbit Data Works", "Silverline Technologies", "Vertex Cloud Partners", "Aether AI Labs",
]

MOCK_LOCATIONS = [
    "Bangalore, India (Hybrid)", "Pune, India", "Hyderabad, India", "Remote (India)",
    "Chennai, India", "Gurgaon, India (Hybrid)", "Mumbai, India", "Remote (Global)",
]

MOCK_CANDIDATE_NAMES = [
    "Rahul Sharma", "Neel Patel", "Ananya Reddy", "Vikram Singh", "Priya Nair",
    "Arjun Mehta", "Kavya Iyer", "Rohan Gupta", "Sneha Kulkarni", "Aditya Rao",
]

SKILL_KEYWORDS = {
    "Cloud & Infrastructure": ["aws", "azure", "gcp", "google cloud", "terraform", "kubernetes",
                                "docker", "cloud", "ec2", "s3", "lambda", "devops"],
    "Data Engineering": ["pyspark", "spark", "databricks", "airflow", "kafka", "etl", "elt",
                          "data pipeline", "snowflake", "dbt", "hadoop", "delta lake"],
    "Programming": ["python", "sql", "java", "scala", "javascript", "typescript", "r programming"],
    "AI / Machine Learning": ["machine learning", "ml", "ai", "tensorflow", "pytorch", "nlp",
                               "deep learning", "llm", "generative ai"],
    "Data & Analytics": ["data modelling", "data warehouse", "power bi", "tableau", "analytics",
                          "data governance", "unity catalog"],
}
ALL_SKILL_TERMS = [term for terms in SKILL_KEYWORDS.values() for term in terms]

JOB_TITLE_POOL = [
    "Data Engineer", "Senior Data Engineer", "Data Architect", "Cloud Engineer",
    "DevOps Engineer", "Software Engineer", "Machine Learning Engineer", "AI Engineer",
    "Solution Architect", "Data & AI Architect", "Analytics Engineer", "Platform Engineer",
]

JD_TEMPLATE = (
    "We are hiring a {title} to join {company}. Required skills: {must_have}. "
    "Preferred / nice to have: {nice_have}. You will {responsibility}. "
    "Minimum {years}+ years of experience. This is a {job_type} role based in {location}."
)

RESPONSIBILITY_POOL = [
    "design and implement scalable data pipelines", "build and maintain cloud-native architectures",
    "collaborate with stakeholders to translate requirements into technical solutions",
    "optimize data platforms for performance and cost", "mentor junior engineers on the team",
    "own end-to-end delivery of data products",
]


def get_user_rng():
    seed_str = (
        st.session_state.profile.get("email")
        or st.session_state.profile.get("name")
        or "forge-ai-default"
    )
    seed = sum(ord(c) for c in seed_str) or 42
    return random.Random(seed)


def candidate_skill_set():
    skills = [s.lower() for s in st.session_state.profile.get("key_skills", [])]
    return set(skills) if skills else {"python", "sql"}


def generate_mock_jobs(n=8):
    if st.session_state.mock_jobs is not None:
        return st.session_state.mock_jobs
    rng = get_user_rng()
    cand_skills = candidate_skill_set()
    target_role = st.session_state.profile.get("target_role", "")
    base_role = target_role if target_role and target_role not in ("Not sure yet", "") else \
        st.session_state.profile.get("role", "Data Engineer")

    jobs = []
    for i in range(n):
        title = base_role if i < 2 else rng.choice(JOB_TITLE_POOL)
        company = rng.choice(MOCK_COMPANIES)
        location = rng.choice(MOCK_LOCATIONS)
        years = rng.choice([2, 3, 5, 6, 8, 10, 12])
        job_type = rng.choice(["Full Time", "Full Time", "Full Time", "Contract"])
        posted_days = rng.choice([0, 1, 1, 2, 3, 5, 7, 10])
        must_have = rng.sample(ALL_SKILL_TERMS, k=5)
        nice_have = rng.sample([t for t in ALL_SKILL_TERMS if t not in must_have], k=3)

        overlap = len(set(must_have) & cand_skills)
        base_match = 68 + overlap * 6 + rng.randint(-4, 6)
        match_pct = max(55, min(97, base_match))

        jd_text = JD_TEMPLATE.format(
            title=title, company=company, must_have=", ".join(must_have),
            nice_have=", ".join(nice_have), responsibility=rng.choice(RESPONSIBILITY_POOL),
            years=years, job_type=job_type, location=location,
        )

        jobs.append({
            "id": f"job{i+1:03d}", "title": title, "company": company, "location": location,
            "years": years, "job_type": job_type, "posted_days": posted_days,
            "match_pct": match_pct, "must_have": must_have, "nice_have": nice_have,
            "jd_text": jd_text,
        })
    jobs.sort(key=lambda j: -j["match_pct"])
    st.session_state.mock_jobs = jobs
    return jobs


def analyze_jd_text(jd_text: str):
    """Deterministic keyword-based JD parsing - no external API calls.
    Uses word-boundary regex matching to avoid false positives from short
    terms matching inside unrelated words (e.g. 'ai' inside 'airflow',
    'scala' inside 'scalable')."""
    text_lower = jd_text.lower()

    def term_present(term):
        pattern = r"\b" + re.escape(term) + r"\b"
        return re.search(pattern, text_lower) is not None

    found_skills = [term for term in ALL_SKILL_TERMS if term_present(term)]
    found_skills = sorted(set(found_skills))

    category_counts = {}
    for cat, terms in SKILL_KEYWORDS.items():
        count = sum(1 for t in terms if term_present(t))
        if count:
            category_counts[cat] = count
    top_category = max(category_counts, key=category_counts.get) if category_counts else "General Technology"

    years_match = re.search(r"(\d+)\s*\+?\s*years?", text_lower)
    years = int(years_match.group(1)) if years_match else 3
    if years >= 10:
        seniority = "Principal / Staff"
    elif years >= 6:
        seniority = "Senior"
    elif years >= 3:
        seniority = "Mid"
    else:
        seniority = "Junior"

    job_type = "Contract" if "contract" in text_lower else "Full Time"
    industry = "IT Services"

    cand_skills = candidate_skill_set()
    overlap = len(set(found_skills) & cand_skills)
    match_potential = max(35, min(97, 40 + overlap * 12))

    return {
        "found_skills": found_skills if found_skills else ["No specific skills detected"],
        "top_category": top_category,
        "seniority": seniority,
        "years": years,
        "job_type": job_type,
        "industry": industry,
        "match_potential": match_potential,
        "responsibilities": rng_pick_responsibilities(jd_text),
    }


def rng_pick_responsibilities(jd_text: str):
    rng = random.Random(len(jd_text))
    return rng.sample(RESPONSIBILITY_POOL, k=min(3, len(RESPONSIBILITY_POOL)))


def generate_mock_candidates(job, n=6):
    rng = get_user_rng()
    candidates = []
    for i in range(n):
        overall = rng.randint(58, 97)
        candidates.append({
            "id": f"cand{i+1:03d}",
            "name": MOCK_CANDIDATE_NAMES[i % len(MOCK_CANDIDATE_NAMES)],
            "overall_match": overall,
            "skills_match": max(40, min(99, overall + rng.randint(-8, 8))),
            "experience_match": max(40, min(99, overall + rng.randint(-10, 10))),
            "readiness_score": max(40, min(99, overall + rng.randint(-12, 6))),
        })
    candidates.sort(key=lambda c: -c["overall_match"])
    return candidates


def render_gauge(pct: int, size: int = 84, color: str = "#5B4CF2", label: str = ""):
    pct = max(0, min(100, pct))
    deg = pct * 3.6
    inner = size - 16
    html = f"""
    <div style="width:{size}px;height:{size}px;border-radius:50%;
         background:conic-gradient({color} {deg}deg, #EEF0F7 0deg);
         display:flex;align-items:center;justify-content:center;margin:0 auto;">
        <div style="width:{inner}px;height:{inner}px;border-radius:50%;background:white;
             display:flex;flex-direction:column;align-items:center;justify-content:center;">
            <div style="font-size:{max(14, size//5)}px;font-weight:700;color:#24243B;">{pct}%</div>
        </div>
    </div>
    {f'<div style="text-align:center;font-size:11px;color:#8A8FA3;margin-top:4px;">{label}</div>' if label else ''}
    """
    return html


def get_selected_job():
    jobs = generate_mock_jobs()
    sel_id = st.session_state.get("selected_job_id")
    for j in jobs:
        if j["id"] == sel_id:
            return j
    return jobs[0] if jobs else None


def compute_resume_analysis(job):
    """Deterministic ATS-style resume analysis against a target job."""
    cand_skills = candidate_skill_set()
    must_have = set(job["must_have"]) if job else set()
    overlap = len(must_have & cand_skills)
    missing = list(must_have - cand_skills)

    ats_score = max(45, min(98, 55 + overlap * 9))
    rng = random.Random(len(job["id"]) * 7 + ats_score if job else 42)

    return {
        "ats_score": ats_score,
        "missing_keywords_count": len(missing),
        "missing_keywords": missing,
        "improved_bullets_count": rng.randint(10, 22),
        "skills_enhancement_count": max(1, overlap),
        "formatting_fixes_count": rng.randint(2, 9),
    }


def build_resume_text(job=None):
    prof = st.session_state.profile
    name = prof.get("name", "Candidate")
    role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "Professional")
    years = prof.get("years_experience", 0)
    skills = prof.get("key_skills", [])
    job_skills = job["must_have"] if job else []
    core_competencies = sorted(set([s.title() for s in skills] + [s.title() for s in job_skills]))[:10]

    summary = (
        f"Results-driven {role} with {years}+ years of experience designing and implementing scalable "
        f"solutions across data architecture and cloud platforms. Proven ability to deliver "
        f"high-impact projects, collaborate cross-functionally, and drive measurable business outcomes."
    )

    lines = [
        f"{name.upper()}",
        f"{role}",
        f"{prof.get('email','')} | {prof.get('contact_number','')} | {prof.get('home_address','')}",
        "",
        "PROFESSIONAL SUMMARY",
        summary,
        "",
        "CORE COMPETENCIES",
        ", ".join(core_competencies) if core_competencies else "Add key skills to your profile to populate this section.",
        "",
        "EXPERIENCE",
        f"{years}+ years of professional experience (details pulled from uploaded resume: "
        f"{st.session_state.resume_file_name or 'not uploaded'}).",
    ]
    return "\n".join(lines)


TARGET_ROLE_PRIORITY = {"high": "#C23636", "medium": "#B8790A", "low": "#1E8E4C"}


def compute_gap_analysis(job):
    cand_skills = candidate_skill_set()
    must_have = job["must_have"] if job else []
    nice_have = job["nice_have"] if job else []
    missing_must = [s for s in must_have if s not in cand_skills]
    missing_nice = [s for s in nice_have if s not in cand_skills]

    high_priority = missing_must[:2]
    medium_priority = missing_must[2:] + missing_nice[:1]
    low_priority = missing_nice[1:]

    total_required = len(must_have) + len(nice_have)
    total_missing = len(missing_must) + len(missing_nice)
    gap_score = int(round((total_missing / total_required) * 100)) if total_required else 0
    gap_score = max(5, min(95, gap_score))
    gap_label = "High" if gap_score >= 60 else "Moderate" if gap_score >= 30 else "Low"

    recommendations = []
    if high_priority:
        recommendations.append(f"Complete 2-3 high priority skills: {', '.join(s.title() for s in high_priority)}.")
    recommendations.append("Work on hands-on projects to apply newly learned skills.")
    if medium_priority:
        recommendations.append(f"Earn relevant certifications covering: {', '.join(s.title() for s in medium_priority[:2])}.")
    recommendations.append("Practice in the Interview Simulator to validate readiness.")

    return {
        "gap_score": gap_score, "gap_label": gap_label,
        "high_priority": high_priority, "medium_priority": medium_priority, "low_priority": low_priority,
        "recommendations": recommendations,
    }


COURSE_PROVIDERS = ["FORGE Learning", "Coursera", "Pluralsight", "Udemy", "LinkedIn Learning"]


def generate_course_catalog(skills):
    rng = get_user_rng()
    catalog = []
    for skill in skills:
        catalog.append({
            "id": f"course_{skill.replace(' ', '_')}",
            "title": f"{skill.title()} \u2014 Practical Deep Dive",
            "provider": rng.choice(COURSE_PROVIDERS),
            "duration": f"{rng.choice([3, 4, 6, 8, 10])} hrs",
            "skill": skill,
        })
    return catalog


BOOK_LIST = [
    {"title": "Designing Data-Intensive Applications", "author": "Martin Kleppmann"},
    {"title": "The Staff Engineer's Path", "author": "Tanya Reilly"},
    {"title": "Fundamentals of Data Engineering", "author": "Reis & Housley"},
    {"title": "Cloud Native Patterns", "author": "Cornelia Davis"},
    {"title": "System Design Interview", "author": "Alex Xu"},
]


# --------------------------------------------------------------------------
# FORGE Sim(TM) SCENARIOS
# --------------------------------------------------------------------------
SIMULATION_SCENARIOS = [
    {
        "id": "sim_prod_incident", "title": "Databricks Production Incident",
        "category": "Production Failure Simulation",
        "scenario": ("Your Databricks production job pipeline has suddenly failed, causing delay "
                     "in downstream reports."),
        "business_impact": "Business impact: $1.2M reporting delay.",
        "prompt": "How would you identify the root cause and resolve it?",
        "keywords": ["root cause", "logs", "monitor", "rollback", "cluster", "retry", "alert", "checkpoint"],
    },
    {
        "id": "sim_cloud_arch", "title": "Cloud Architecture Design Challenge",
        "category": "Cloud Architecture Challenge",
        "scenario": ("Your team needs to design a cost-efficient, highly available data platform "
                     "on the cloud for a new product line."),
        "business_impact": "Business impact: platform must support 3x traffic growth within 12 months.",
        "prompt": "Walk through your proposed architecture and the trade-offs you would make.",
        "keywords": ["scalability", "availability", "cost", "trade-off", "redundancy", "region", "auto-scaling"],
    },
    {
        "id": "sim_cloud_failure", "title": "Cloud Failure Response",
        "category": "Incident Response Exercise",
        "scenario": "A critical cloud region outage has taken down part of your production environment.",
        "business_impact": "Business impact: customer-facing services degraded for 40% of users.",
        "prompt": "How do you lead the incident response from detection through resolution?",
        "keywords": ["incident commander", "failover", "postmortem", "communication", "escalate", "runbook"],
    },
    {
        "id": "sim_leadership", "title": "Leadership Challenge",
        "category": "Leadership Simulation",
        "scenario": ("Two senior engineers on your team strongly disagree on a technical approach, "
                     "and the disagreement is stalling delivery."),
        "business_impact": "Business impact: sprint deadline at risk.",
        "prompt": "How would you navigate this conflict and drive a decision?",
        "keywords": ["listen", "align", "decision", "stakeholder", "compromise", "consensus", "escalate"],
    },
    {
        "id": "sim_behavioral", "title": "Behavioral Interview",
        "category": "Technical Deep-Dive Interview",
        "scenario": "Tell us about a time you had to make a difficult trade-off under a tight deadline.",
        "business_impact": "Business impact: evaluating judgment under pressure.",
        "prompt": "Describe the situation, your reasoning, and the outcome.",
        "keywords": ["situation", "task", "action", "result", "outcome", "learned", "impact"],
    },
    {
        "id": "sim_system_design", "title": "System Design Challenge",
        "category": "System Design Challenge",
        "scenario": "Design a real-time data ingestion system that must handle 1M events per second.",
        "business_impact": "Business impact: system underpins a mission-critical analytics product.",
        "prompt": "Outline your end-to-end design, covering scale, reliability and cost.",
        "keywords": ["throughput", "partition", "queue", "latency", "replication", "backpressure", "sla"],
    },
]


def score_simulation_answer(scenario, answer_text):
    """Deterministic scoring heuristic - no external API calls."""
    answer_lower = answer_text.lower()
    word_count = len(answer_text.split())
    keyword_hits = sum(1 for kw in scenario["keywords"] if kw in answer_lower)

    communication = max(35, min(97, 40 + min(word_count, 120) // 2))
    technical = max(30, min(97, 45 + keyword_hits * 9))
    problem_solving = max(30, min(97, 42 + keyword_hits * 8 + (5 if word_count > 60 else 0)))
    leadership = max(30, min(95, 38 + keyword_hits * 6 + (8 if "team" in answer_lower or "stakeholder" in answer_lower else 0)))
    overall = int(round((technical + communication + problem_solving + leadership) / 4))

    return {
        "technical": technical, "communication": communication,
        "problem_solving": problem_solving, "leadership": leadership, "overall": overall,
    }


def get_performance_summary():
    """Aggregate completed simulation results, or fall back to a profile-based estimate."""
    results = list(st.session_state.simulation_results.values())
    if results:
        keys = ["technical", "communication", "problem_solving", "leadership", "overall"]
        avg = {k: int(round(sum(r[k] for r in results) / len(results))) for k in keys}
        avg["source"] = "simulation"
        avg["decision_making"] = int(round((avg["problem_solving"] + avg["leadership"]) / 2))
        return avg
    rng = get_user_rng()
    base = 55 + len(st.session_state.profile.get("key_skills", [])) * 4 + len(st.session_state.profile.get("certifications", [])) * 3
    base = max(45, min(90, base))
    return {
        "technical": base + rng.randint(-5, 8), "communication": base + rng.randint(-8, 5),
        "problem_solving": base + rng.randint(-5, 5), "leadership": base + rng.randint(-10, 3),
        "decision_making": base + rng.randint(-8, 4), "overall": base, "source": "estimate",
    }


VOICE_TAG_POOL = ["Technical", "Professional", "Clear & Concise", "Thought Leader", "Data-driven",
                   "Analytical Expert", "Strategic", "Collaborative", "Detail-Oriented", "Pragmatic"]


def get_voice_profile():
    seed_str = (st.session_state.profile.get("email", "default")
                + str(st.session_state.voice_profile_seed))
    rng = random.Random(sum(ord(c) for c in seed_str))
    tags = rng.sample(VOICE_TAG_POOL, k=5)
    hae_granted = bool(st.session_state.profile.get("hae_consent"))
    consistency = rng.randint(85, 97) if hae_granted else rng.randint(35, 58)

    tonality = {
        "Technical": rng.randint(35, 55),
        "Conversational": rng.randint(15, 30),
    }
    tonality["Formal"] = max(5, 100 - sum(tonality.values()))

    return {"tags": tags, "consistency": consistency, "hae_granted": hae_granted, "tonality": tonality}


def build_sample_post():
    prof = st.session_state.profile
    role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "professional")
    skills = prof.get("key_skills", [])
    skill_line = skills[0] if skills else "data architecture"
    rng = random.Random(st.session_state.voice_profile_seed + len(prof.get("name", "")))
    openers = [
        f"Most teams treat {skill_line} as an afterthought \u2014 until it costs them a production incident.",
        f"The best {role}s I know don't chase every new tool. They master the fundamentals of {skill_line}.",
        f"A hard lesson from working in {skill_line}: scaling is never just a technical problem.",
    ]
    return (
        f"{rng.choice(openers)}\n\n"
        f"Here's what actually moves the needle: clear ownership, measured trade-offs, and "
        f"communicating impact in terms the business understands \u2014 not just the architecture diagram.\n\n"
        f"#{role.replace(' ', '')} #{skill_line.replace(' ', '')} #CareerGrowth"
    )


def get_linkedin_performance():
    rng = random.Random(sum(ord(c) for c in (st.session_state.profile.get("email", "x"))) + st.session_state.voice_profile_seed)
    engagement = rng.randint(8000, 16000)
    views = rng.randint(1200, 2400)
    reactions = rng.randint(600, 1300)
    return {
        "engagement": engagement, "engagement_delta": rng.randint(10, 30),
        "views": views, "views_delta": rng.randint(8, 25),
        "reactions": reactions, "reactions_delta": rng.randint(10, 25),
    }


OUTREACH_CAMPAIGN_NAMES = [
    "{role} Opportunities", "Cloud Architect Roles", "Senior {role} Search",
    "Referral Outreach \u2014 {role}", "Recruiter Network Expansion",
]


def generate_outreach_campaigns():
    if st.session_state.outreach_campaigns is not None:
        return st.session_state.outreach_campaigns
    rng = get_user_rng()
    prof = st.session_state.profile
    role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "Professional")
    campaigns = []
    for i, template in enumerate(rng.sample(OUTREACH_CAMPAIGN_NAMES, k=3)):
        target = rng.choice([100, 120, 150, 200])
        response = int(target * rng.uniform(0.15, 0.32))
        campaigns.append({
            "id": f"camp{i+1:03d}",
            "name": template.format(role=role),
            "target": target, "response": response,
            "response_rate": round(response / target * 100, 1),
            "status": rng.choice(["Active", "Active", "Paused"]),
        })
    st.session_state.outreach_campaigns = campaigns
    return campaigns


def build_outreach_message():
    prof = st.session_state.profile
    role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "your field")
    return (
        f"Hi {{Name}}, I came across your profile and wanted to reach out regarding exciting "
        f"opportunities that match your experience in {role}. Would you be open to a quick "
        f"conversation this week?"
    )


def compute_success_metrics():
    applied = st.session_state.applied_jobs
    n_applications = len(applied)
    n_interviews = sum(1 for s in applied.values() if s in ("Interview", "Offer"))
    n_offers = sum(1 for s in applied.values() if s == "Offer")
    conversion = round((n_interviews / n_applications) * 100, 1) if n_applications else 0

    rng = get_user_rng()
    # Simple simulated weekly trend, anchored so the final week reflects real current counts
    weeks = ["Wk 1", "Wk 2", "Wk 3", "Wk 4"]
    base = max(1, n_applications)
    trend = [max(0, base + rng.randint(-2, 2)) for _ in range(3)] + [n_applications]

    insights = []
    if n_applications == 0:
        insights.append("You haven't applied to any roles yet \u2014 visit Job Hunter Agent to get started.")
    else:
        insights.append(f"Your application activity is at {n_applications} role(s) tracked this period.")
    if conversion >= 20:
        insights.append("Your interview conversion rate is strong compared to typical benchmarks.")
    elif n_applications > 0:
        insights.append("Focus on tailoring applications to roles with higher match scores to improve conversion.")
    insights.append("Complete more Interview Simulator sessions to strengthen your readiness score.")
    insights.append("Keep your LinkedIn presence active \u2014 recruiters engage more with consistent posting.")

    return {
        "applications": n_applications, "interviews": n_interviews, "offers": n_offers,
        "conversion": conversion, "weeks": weeks, "trend": trend, "insights": insights,
    }


ROLE_MARKET_DATA = {
    "Data Architect": {"score": 9.2, "salary_lpa": 24},
    "Data Engineer": {"score": 9.0, "salary_lpa": 18},
    "Cloud Architect": {"score": 8.8, "salary_lpa": 28},
    "Data Analyst": {"score": 7.5, "salary_lpa": 12},
    "Machine Learning Engineer": {"score": 7.2, "salary_lpa": 20},
    "Solution Architect": {"score": 8.6, "salary_lpa": 26},
    "DevOps Engineer": {"score": 8.1, "salary_lpa": 17},
    "AI Engineer": {"score": 8.4, "salary_lpa": 22},
    "Analytics Engineer": {"score": 7.8, "salary_lpa": 14},
}


def get_career_recommendation():
    prof = st.session_state.profile
    role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "your target role")
    years = prof.get("years_experience", 0)
    seniority = "Senior" if years >= 6 else "Mid-level" if years >= 3 else "Early-career"
    return (
        f"You are well positioned for {seniority} {role} roles. Focus on advanced platform design, "
        f"leadership skills, and relevant certifications to maximize your career growth."
    )


# --------------------------------------------------------------------------
# GLOBAL STYLE
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #F5F6FA; }
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E7E9F1;
    }
    .forge-brand {
        display: flex; align-items: center; gap: 10px;
        padding: 6px 2px 18px 2px; border-bottom: 1px solid #EEF0F7;
        margin-bottom: 14px;
    }
    .forge-brand-badge {
        width: 38px; height: 38px; border-radius: 10px;
        background: linear-gradient(135deg, #5B4CF2, #7C6BFA);
        display: flex; align-items: center; justify-content: center;
        color: white; font-weight: 700; font-size: 17px;
    }
    .forge-brand-name { font-size: 17px; font-weight: 700; color: #24243B; line-height:1.1;}
    .forge-brand-sub { font-size: 10px; color: #8A8FA3; letter-spacing: 0.04em; }
    .hero-card {
        background: linear-gradient(135deg, #5B4CF2 0%, #7C6BFA 60%, #9C8CFF 100%);
        border-radius: 16px; padding: 26px 30px; color: white; margin-bottom: 18px;
    }
    .hero-card h1 { color: white; margin-bottom: 4px; font-size: 26px;}
    .hero-card p { color: #EDEBFF; margin: 0; font-size: 14px; }
    .metric-card {
        background: white; border-radius: 14px; padding: 16px 18px;
        border: 1px solid #ECEEF6; box-shadow: 0 1px 2px rgba(20,20,50,0.04);
    }
    .metric-label { font-size: 12px; color: #8A8FA3; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;}
    .metric-value { font-size: 26px; font-weight: 700; color: #24243B; margin-top: 4px;}
    .section-title { font-size: 18px; font-weight: 700; color: #24243B; margin: 6px 0 10px 0;}
    .faq-tag {
        display:inline-block; background:#EEF0FF; color:#5B4CF2; font-size: 11px;
        font-weight: 700; padding: 3px 10px; border-radius: 20px; margin-bottom: 8px;
    }
    .video-card {
        background: white; border-radius: 14px; padding: 16px; border: 1px solid #ECEEF6;
        height: 100%;
    }
    .video-thumb {
        background: linear-gradient(135deg, #EEF0FF, #E3E6FF);
        border-radius: 10px; height: 110px; display:flex; align-items:center; justify-content:center;
        color:#5B4CF2; font-size: 30px; font-weight: 700; margin-bottom: 10px;
    }
    .email-preview {
        background: white; border-radius: 14px; padding: 22px 26px; border: 1px solid #ECEEF6;
    }
    .pill {
        display:inline-block; padding: 4px 12px; border-radius: 20px; font-size: 11px;
        font-weight: 700; margin-right: 6px;
    }
    .pill-strong { background:#E4F7EA; color:#1E8E4C; }
    .pill-medium { background:#FFF4E0; color:#B8790A; }
    .pill-weak { background:#FDE7E7; color:#C23636; }
    .job-card {
        background: white; border-radius: 14px; padding: 16px 18px; border: 1px solid #ECEEF6;
        margin-bottom: 10px;
    }
    .company-badge {
        width: 42px; height: 42px; border-radius: 10px;
        background: linear-gradient(135deg, #EEF0FF, #E3E6FF); color:#5B4CF2;
        display:flex; align-items:center; justify-content:center; font-weight:700; font-size:15px;
    }
    .match-badge {
        display:inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;
    }
    .match-high { background:#E4F7EA; color:#1E8E4C; }
    .match-mid { background:#FFF4E0; color:#B8790A; }
    .match-low { background:#F1F0F7; color:#5A5E73; }
    .status-badge {
        display:inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;
    }
    .status-applied { background:#EEF0FF; color:#5B4CF2; }
    .status-interview { background:#FFF4E0; color:#B8790A; }
    .status-offer { background:#E4F7EA; color:#1E8E4C; }
    .streak-dot {
        width: 20px; height: 20px; border-radius: 6px; display:inline-flex; align-items:center;
        justify-content:center; font-size: 9px; font-weight:700; margin-right:3px;
    }
    .streak-on { background:#22C55E; color:white; }
    .streak-off { background:#EEF0F7; color:#B4B2A9; }
    .cand-row {
        background: white; border-radius: 12px; padding: 12px 16px; border: 1px solid #ECEEF6;
        margin-bottom: 8px; display:flex; align-items:center; justify-content:space-between;
    }
    .gap-tag { display:inline-block; padding:4px 11px; border-radius:20px; font-size:11px; font-weight:700; margin:3px 4px 3px 0; }
    .gap-high { background:#FDE7E7; color:#C23636; }
    .gap-medium { background:#FFF4E0; color:#B8790A; }
    .gap-low { background:#E4F7EA; color:#1E8E4C; }
    .course-card {
        background: white; border-radius: 14px; padding: 14px 16px; border: 1px solid #ECEEF6;
        margin-bottom: 8px;
    }
    .progress-track { background:#EEF0F7; border-radius:6px; height:8px; overflow:hidden; }
    .progress-fill { background:linear-gradient(90deg,#5B4CF2,#7C6BFA); height:100%; border-radius:6px; }
    .scenario-item {
        padding:10px 12px; border-radius:10px; margin-bottom:6px; cursor:pointer;
        border:1px solid #ECEEF6; font-size:12px;
    }
    .scenario-active { background:#EEF0FF; border-color:#5B4CF2; }
    .scenario-done { background:#E4F7EA; border-color:#8CD9A8; }
    .score-bar-row { margin-bottom:10px; }
    .voice-tag {
        display:inline-block; padding:5px 12px; border-radius:20px; font-size:11px; font-weight:700;
        background:#EEF0FF; color:#5B4CF2; margin:3px 4px 3px 0;
    }
    .campaign-row {
        background: white; border-radius: 12px; padding: 12px 16px; border: 1px solid #ECEEF6;
        margin-bottom: 8px; display:flex; align-items:center; justify-content:space-between;
    }
    .market-row {
        display:flex; align-items:center; justify-content:space-between; padding:8px 0;
        border-bottom:1px solid #ECEEF6; font-size:12px;
    }
    .toggle-row {
        display:flex; align-items:center; justify-content:space-between; padding:10px 0;
        border-bottom:1px solid #ECEEF6;
    }
    /* ===== Exeliq integration: auth page and form refinements ===== */

    /* Replaces .hero-card on the auth page. No gradient: the accent is spent on the primary
       action instead, which is the only thing on this page a person came to do. */
    .auth-intro { margin: 2px 0 22px; }
    .auth-intro h1 {
        font-size: 28px; font-weight: 700; color: #24243B;
        margin: 0 0 6px; letter-spacing: -0.02em; line-height: 1.15;
    }
    .auth-intro > p { color: #5A5E73; font-size: 14.5px; margin: 0 0 18px; max-width: 56ch; }
    .auth-paths { display: flex; gap: 12px; flex-wrap: wrap; }
    .auth-path {
        flex: 1 1 260px; background: #FFFFFF; border: 1px solid #E7E9F1;
        border-radius: 14px; padding: 15px 17px;
    }
    /* The left rule carries the one accent, and marks these as the two routes through the
       product rather than decorating them. */
    .auth-path { border-left: 3px solid #5B4CF2; }
    .auth-path-name { font-weight: 650; color: #24243B; font-size: 14.5px; margin-bottom: 3px; }
    .auth-path-detail { color: #8A8FA3; font-size: 12.8px; line-height: 1.45; }

    /* Form fields were grey-on-grey against a grey canvas, so the boundary between a label and
       its input was doing no work. White field, visible border, accent only on focus. */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background: #FFFFFF !important;
        border: 1px solid #DDE1EC !important;
        border-radius: 9px !important;
        color: #24243B !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
        border-color: #5B4CF2 !important;
        box-shadow: 0 0 0 3px rgba(91, 76, 242, 0.12) !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label,
    .stDateInput label, .stMultiSelect label {
        font-size: 12.5px !important; font-weight: 600 !important; color: #5A5E73 !important;
    }
    div[data-baseweb="select"] > div {
        background: #FFFFFF !important; border-color: #DDE1EC !important; border-radius: 9px !important;
    }

    /* Sidebar navigation: twenty undifferentiated radio rows read as a debug menu. Tighten the
       rhythm and let the selected item carry the accent. */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 3px 0 !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label p {
        font-size: 13.5px !important; color: #5A5E73 !important;
    }

    /* The brand subtitle was tracked-out all-caps, which is a styling default rather than a
       choice, and it competes with the product name directly above it. */
    .forge-brand-sub {
        text-transform: none !important; letter-spacing: 0 !important;
        font-size: 11.5px !important;
    }

    /* Primary action: one confident button, matching the brand rather than Streamlit's red. */
    .stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
        background: #5B4CF2 !important; border: none !important;
        border-radius: 10px !important; font-weight: 600 !important;
    }
    .stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover {
        background: #4A3BE0 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="forge-brand">
            <div class="forge-brand-badge">F</div>
            <div>
                <div class="forge-brand-name">FORGE AI&trade;</div>
                <div class="forge-brand-sub">Career acceleration platform</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.authenticated:
        prof = st.session_state.profile
        st.markdown(f"**{prof.get('name', 'Member')}**")
        st.caption(prof.get("role", "") or "Role not set")
        st.divider()

    # Exeliq integration: show each account only the pages that apply to it. Previously every
    # account saw all twenty, so a recruiter was offered interview practice and a job seeker was
    # offered an inbound mailbox neither of them has.
    _recruiter = is_recruiter_account(st.session_state.profile)
    _visible = [
        item for item in NAV_ITEMS
        if not (_recruiter and item[1] in CANDIDATE_ONLY_PAGES)
        and not (not _recruiter and item[1] in RECRUITER_ONLY_PAGES)
    ]
    labels = [item[0] for item in _visible]
    keys = [item[1] for item in _visible]

    # Lock navigation until authenticated / profile complete, mirrors real onboarding flow
    def nav_disabled(key: str) -> bool:
        if key in ("auth",):
            return False
        if key == "profile":
            return not st.session_state.authenticated
        if key in (
            "welcome", "videos", "faqs", "settings",
            "dashboard", "job_hunter", "jd_intelligence", "candidate_matching",
            "resume_intelligence", "gap_analysis", "learning_dev",
            "simulation", "performance_eval", "human_authenticity",
            "linkedin_branding", "outreach", "success_tracking", "career_intelligence",
            "email_agent",
        ):
            return not st.session_state.profile_complete
        return False

    default_index = keys.index(st.session_state.active_page) if st.session_state.active_page in keys else 0
    choice = st.radio("Navigate", labels, index=default_index, label_visibility="collapsed")
    chosen_key = keys[labels.index(choice)]

    if nav_disabled(chosen_key) and chosen_key != st.session_state.active_page:
        st.warning("Please complete the previous step first.")
    else:
        st.session_state.active_page = chosen_key

    st.divider()
    if st.session_state.authenticated:
        if st.button("Log out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user_id = None
            st.session_state.active_page = "auth"
            st.rerun()
    st.caption("Help & Support: support@forgeai.example")

page = st.session_state.active_page

# --------------------------------------------------------------------------
# PAGE: SIGN UP / LOGIN
# --------------------------------------------------------------------------
if page == "auth":
    # Exeliq integration: the gradient banner that used to sit here said "Welcome to FORGE AI"
    # and repeated the tagline already in the sidebar. It occupied the most valuable space on
    # the page and helped nobody decide anything. The one real decision at signup is which kind
    # of account to open, and the two kinds lead to completely different products, so that is
    # what goes here instead.
    st.markdown(
        f"""
        <div class="auth-intro">
            <h1>Create your {APP_NAME}&trade; account</h1>
            <p>Two kinds of account, built for different jobs. You can change this later.</p>
            <div class="auth-paths">
                <div class="auth-path">
                    <div class="auth-path-name">Job seeker</div>
                    <div class="auth-path-detail">Find roles, sharpen your resume, practise
                    interviews, track applications.</div>
                </div>
                <div class="auth-path">
                    <div class="auth-path-name">Recruitment desk</div>
                    <div class="auth-path-detail">Screen inbound job leads, match candidates
                    from your database, draft replies.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_signup, tab_login = st.tabs(["Create Account", "Log In"])

    # ---------------- SIGN UP ----------------
    with tab_signup:
        st.caption(
            "Individuals sign up with a personal email address. Organizational accounts need a "
            "work email."
        )

        account_type = st.selectbox("Account Type *", ACCOUNT_TYPES, key="signup_account_type")
        program_options = PROGRAMS_INDIVIDUAL if account_type == "Individual / Job Seeker" else PROGRAMS_ENTERPRISE

        with st.form("signup_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                full_name_su = st.text_input("Full Name *", placeholder="e.g. Gauri Joshi")
                email = st.text_input(
                    "Email Address *",
                    placeholder="you@personalmail.com or you@company.com",
                )
                program_of_interest = st.selectbox("Program of Interest *", program_options)
            with col2:
                password = st.text_input("Create Password *", type="password")
                confirm_password = st.text_input("Confirm Password *", type="password")
                terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *")

            marketing_opt_in = st.checkbox("Send me onboarding tips and product updates by email", value=True)

            submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

        if submitted:
            errors = []
            if not full_name_su.strip():
                errors.append("Full name is required.")
            if not is_valid_email(email):
                errors.append("Please enter a valid email address.")
            elif account_type != "Individual / Job Seeker" and not is_company_email(email):
                errors.append(
                    "Organizational accounts must use an official work email address, not a "
                    "personal one. You can also sign up as an individual and switch the account "
                    "type later in Profile Setup."
                )
            if len(password) < 8:
                errors.append("Password must be at least 8 characters long.")
            if password != confirm_password:
                errors.append("Passwords do not match.")
            if not terms:
                errors.append("You must accept the Terms of Service and Privacy Policy.")

            existing_db = load_users_db()
            if is_valid_email(email) and any(
                u.get("email", "").lower() == email.strip().lower() for u in existing_db.values()
            ):
                errors.append("An account with this email already exists. Please log in instead.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                user_id = generate_user_id(full_name_su)
                existing_db[user_id] = {
                    "email": email.strip(),
                    "password": hash_password(password),
                    "account_type": account_type,
                    "program_of_interest": program_of_interest,
                    "marketing_opt_in": marketing_opt_in,
                    "created_at": dt.datetime.now().strftime("%d %b %Y, %I:%M %p"),
                }
                save_users_db(existing_db)
                st.session_state.users_db = existing_db
                st.session_state.current_user_id = user_id
                st.session_state.authenticated = True
                st.session_state.profile["name"] = full_name_su.strip()
                st.session_state.profile["email"] = email.strip()
                st.session_state.profile["account_type"] = account_type
                st.session_state.profile["program_of_interest"] = program_of_interest
                st.session_state.active_page = "profile"
                save_user_data(user_id)
                st.success(f"Account created successfully. Your User ID is **{user_id}** (also emailed to you).")
                st.info("Redirecting you to Profile Setup...")
                st.rerun()

    # ---------------- LOG IN ----------------
    with tab_login:
        st.markdown('<div class="section-title">Log in to your account</div>', unsafe_allow_html=True)
        with st.form("login_form"):
            login_id = st.text_input("User ID or Email")
            login_pwd = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Log In", use_container_width=True, type="primary")

        if login_submit:
            db = load_users_db()
            st.session_state.users_db = db
            matched_id = None
            for uid, udata in db.items():
                if login_id == uid or login_id.strip().lower() == udata.get("email", "").lower():
                    matched_id = uid
                    break
            if matched_id and db[matched_id]["password"] == hash_password(login_pwd):
                st.session_state.authenticated = True
                st.session_state.current_user_id = matched_id
                udata = db[matched_id]
                st.session_state.profile.setdefault("name", "")
                st.session_state.profile["email"] = udata["email"]
                st.session_state.profile["account_type"] = udata["account_type"]
                st.session_state.profile["program_of_interest"] = udata.get("program_of_interest", "")
                had_saved_progress = load_user_data(matched_id)
                if not had_saved_progress:
                    st.session_state.active_page = "profile" if not st.session_state.profile_complete else "dashboard"
                    st.success("Logged in successfully.")
                else:
                    st.success("Welcome back! Picking up right where you left off.")
                st.rerun()
            else:
                st.error("Invalid User ID / Email or Password. Please sign up if you do not have an account yet.")

# --------------------------------------------------------------------------
# PAGE: PROFILE SETUP
# --------------------------------------------------------------------------
elif page == "profile":
    st.markdown('<div class="section-title">Complete your profile</div>', unsafe_allow_html=True)
    st.caption("This information personalizes your welcome kit, readiness roadmap and platform experience.")

    account_type = st.session_state.profile.get("account_type", ACCOUNT_TYPES[0])
    role_options = ROLES_BY_ACCOUNT_TYPE.get(account_type, ROLES_BY_ACCOUNT_TYPE["Individual / Job Seeker"])

    with st.form("profile_form"):
        st.markdown("##### Basic Information")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Individual / Employee Name *", value=st.session_state.profile.get("name", ""))
            # Exeliq integration: account type is editable here. It was fixed at signup, so
            # switching between a job-seeker view and a recruitment desk meant creating a whole
            # new account -- which is also how someone who picked wrong got stuck.
            account_type = st.selectbox(
                "Account Type *",
                ACCOUNT_TYPES,
                index=ACCOUNT_TYPES.index(account_type) if account_type in ACCOUNT_TYPES else 0,
                help="A recruitment desk sees the Email Agent. A job seeker sees the career tools.",
            )
            st.session_state.profile["account_type"] = account_type
            role_options = ROLES_BY_ACCOUNT_TYPE.get(
                account_type, ROLES_BY_ACCOUNT_TYPE["Individual / Job Seeker"]
            )

            role = st.selectbox(
                "Role / Designation *",
                role_options,
                index=0,
            )
            role_other = ""
            if role == "Other":
                role_other = st.text_input("Please specify your role / designation")
            department = st.selectbox(
                "Department *",
                DEPARTMENTS,
                index=DEPARTMENTS.index(st.session_state.profile.get("department", "Not Applicable"))
                if st.session_state.profile.get("department") in DEPARTMENTS else 0,
            )
            org_required = account_type != "Individual / Job Seeker"
            organization_name = st.text_input(
                f"Organization / Institution Name{' *' if org_required else ' (optional)'}",
                placeholder="e.g. Exeliq Consulting" if account_type == "Corporate" else "e.g. XYZ University",
            )
        with c2:
            contact_number = st.text_input("Contact Number *", placeholder="+91 98765 43210")
            country = st.selectbox("Country *", COUNTRIES)
            years_experience = st.slider("Years of Experience", 0, 40, 2)

        st.markdown("##### Address")
        home_address = st.text_area("Home Address *", placeholder="Street, City, State, PIN / ZIP Code")

        st.markdown("##### Additional Details")
        c3, c4 = st.columns(2)
        with c3:
            linkedin_url = st.text_input("LinkedIn Profile URL (optional)", placeholder="https://linkedin.com/in/username")
            timezone = st.selectbox(
                "Preferred Timezone",
                ["IST (India)", "GMT (UK)", "EST (US East)", "PST (US West)", "GST (UAE)", "Other"],
            )
        with c4:
            key_skills = st.text_input("Key Skills (comma separated)", placeholder="Python, SQL, Databricks, AWS")
            learning_mode = st.selectbox("Preferred Learning Mode", LEARNING_MODES)

        c5, c6 = st.columns(2)
        with c5:
            target_role_options = ROLES_BY_ACCOUNT_TYPE["Individual / Job Seeker"]
            target_role = st.selectbox(
                "Target Role / Career Goal (what you're working toward)",
                ["Not sure yet"] + target_role_options,
            )
            target_role_other = ""
            if target_role == "Other":
                target_role_other = st.text_input("Please specify your target role")
        with c6:
            certifications = st.multiselect(
                "Certifications (existing or in progress)",
                CERTIFICATION_OPTIONS,
                default=[],
            )
            certifications_other = ""
            if "Other" in certifications:
                certifications_other = st.text_input("Please specify other certification(s)")

        c7, c8 = st.columns(2)
        with c7:
            referral_source = st.selectbox("How did you hear about FORGE AI?", REFERRAL_SOURCES)
        with c8:
            notify_pref = st.multiselect(
                "Notification Preferences",
                ["Email", "SMS", "WhatsApp", "In-app only"],
                default=["Email"],
            )

        st.markdown("##### Documents")
        c9, c10 = st.columns(2)
        with c9:
            resume_file = st.file_uploader("Upload Latest Resume *", type=["pdf", "doc", "docx"])
        with c10:
            photo_file = st.file_uploader("Upload Profile Photo (optional)", type=["png", "jpg", "jpeg"])

        st.markdown("##### Consent")
        data_consent = st.checkbox(
            "I consent to FORGE AI processing my profile and resume data to generate personalized "
            "career readiness insights (Talent Intelligence, Career Readiness and Analytics layers) *"
        )
        hae_consent = st.checkbox(
            "I consent to the Human Authenticity Engine (FORGE VoiceAI\u2122) learning my writing "
            "and communication style from my resume, LinkedIn posts, articles and interview responses, "
            "to generate content in my authentic voice. I can withdraw this consent at any time from "
            "My Profile & Settings *"
        )

        profile_submit = st.form_submit_button("Save Profile & Continue", use_container_width=True, type="primary")

    if profile_submit:
        errors = []
        if not name.strip():
            errors.append("Name is required.")
        if role == "Other" and not role_other.strip():
            errors.append("Please specify your role / designation.")
        if account_type != "Individual / Job Seeker" and department == "Not Applicable":
            errors.append("Please select your department for a Corporate, Institution, Training Institute or Staffing Firm account.")
        if org_required and not organization_name.strip():
            errors.append("Organization / Institution name is required for Corporate, Institution, Training Institute and Staffing Firm accounts.")
        if target_role == "Other" and not target_role_other.strip():
            errors.append("Please specify your target role.")
        if "Other" in certifications and not certifications_other.strip():
            errors.append("Please specify your other certification(s).")
        if not contact_number.strip() or not is_valid_phone(contact_number):
            errors.append("Please enter a valid contact number.")
        if not home_address.strip():
            errors.append("Home address is required.")
        if resume_file is None:
            errors.append("Please upload your latest resume.")
        if not data_consent:
            errors.append("Please provide consent to proceed.")
        if not hae_consent:
            errors.append("Please provide Human Authenticity Engine (voice-learning) consent to proceed.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            resolved_certifications = [c for c in certifications if c != "Other"]
            if certifications_other.strip():
                resolved_certifications.append(certifications_other.strip())

            st.session_state.profile.update(
                {
                    "name": name.strip(),
                    "role": role_other.strip() if role == "Other" else role,
                    "department": department,
                    "organization_name": organization_name.strip(),
                    "contact_number": contact_number.strip(),
                    "home_address": home_address.strip(),
                    "country": country,
                    "years_experience": years_experience,
                    "linkedin_url": linkedin_url.strip(),
                    "timezone": timezone,
                    "key_skills": [s.strip() for s in key_skills.split(",") if s.strip()],
                    "target_role": target_role_other.strip() if target_role == "Other" else target_role,
                    "certifications": resolved_certifications,
                    "learning_mode": learning_mode,
                    "referral_source": referral_source,
                    "notify_pref": notify_pref,
                    "hae_consent": hae_consent,
                }
            )
            st.session_state.resume_file_name = resume_file.name
            st.session_state.resume_file_bytes = resume_file.getvalue()
            save_uploaded_resume(st.session_state.current_user_id, st.session_state.resume_file_bytes)
            if photo_file is not None:
                st.session_state.photo_file_name = photo_file.name
                save_uploaded_photo(st.session_state.current_user_id, photo_file.getvalue())
            st.session_state.profile_complete = True
            save_user_data(st.session_state.current_user_id)
            st.success("Profile saved successfully.")
            st.session_state.active_page = "welcome"
            st.rerun()

# --------------------------------------------------------------------------
# PAGE: WELCOME KIT (Email)
# --------------------------------------------------------------------------
elif page == "welcome":
    prof = st.session_state.profile
    st.markdown('<div class="section-title">Your personalized welcome kit</div>', unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Account Type</div>'
            f'<div class="metric-value" style="font-size:16px;">{prof.get("account_type","-")}</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Role</div>'
            f'<div class="metric-value" style="font-size:16px;">{prof.get("role","-")}</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Department</div>'
            f'<div class="metric-value" style="font-size:16px;">{prof.get("department","-")}</div></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Country</div>'
            f'<div class="metric-value" style="font-size:16px;">{prof.get("country","-")}</div></div>',
            unsafe_allow_html=True,
        )
    with m5:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Program of Interest</div>'
            f'<div class="metric-value" style="font-size:16px;">{prof.get("program_of_interest","-")}</div></div>',
            unsafe_allow_html=True,
        )

    st.write("")

    is_corporate = prof.get("account_type") != "Individual / Job Seeker"
    first_name = prof.get("name", "there").split(" ")[0] if prof.get("name") else "there"
    today_str = dt.date.today().strftime("%d %B %Y")
    org_name = prof.get("organization_name", "").strip()
    target_role = prof.get("target_role", "")
    certifications = prof.get("certifications", [])
    hae_granted = bool(prof.get("hae_consent"))
    program = prof.get("program_of_interest", "")

    skills_line = (
        ", ".join(prof.get("key_skills", [])) if prof.get("key_skills") else "your core skills"
    )
    certs_line = ", ".join(certifications) if certifications else "no certifications listed yet"
    org_clause = f" at {org_name}" if org_name else ""

    if is_corporate:
        body_focus = (
            f"As a {prof.get('role','team member')} in {prof.get('department','your department')}"
            f"{org_clause}, you now have access to the full FORGE AI engine suite to help your team "
            "source, assess and close talent faster - without sacrificing candidate authenticity."
        )
        cta_line = "Set up your first hiring campaign or candidate pipeline from the Dashboard."
        match_desc = (
            f"ranks and prioritizes candidates against your open roles, so your "
            f"{prof.get('department','team')} spends time only on genuinely strong matches."
        )
        sim_desc = (
            "runs production-failure, cloud-architecture, leadership and incident-response "
            "simulations on your candidates - so you validate real-world capability before you hire, "
            "not just resume keywords."
        )
        insights_desc = (
            "gives your team a live dashboard of application, interview and offer conversion - so "
            "you know exactly where your pipeline is winning or stalling."
        )
        growth_desc = (
            "helps your organization and your placed candidates build credible, consistent "
            "professional visibility on LinkedIn - reinforcing your employer brand with every hire."
        )
    else:
        body_focus = (
            f"As a {prof.get('role','professional')} working toward "
            f"{target_role if target_role and target_role != 'Not sure yet' else 'your next role'}, "
            f"FORGE AI will build your Readiness Score, run mock interview simulations, optimize your "
            f"resume for ATS, and match you to roles that fit your skills in "
            f"{prof.get('country', 'your region')}."
        )
        cta_line = "Start with your Resume Intelligence scan, then take your first Interview Simulation."
        match_desc = (
            f"is already scoring opportunities against your profile and your target role of "
            f"{target_role if target_role and target_role != 'Not sure yet' else 'your choice'}, "
            "so you see only genuinely relevant openings."
        )
        sim_desc = (
            "will run scenario-based mock interviews - production incidents, system design, "
            "leadership challenges - so you walk into the real interview already tested."
        )
        insights_desc = (
            "tracks your Readiness Score, application-to-interview conversion and skill-gap closure "
            "over time, so you always know what to work on next."
        )
        growth_desc = (
            "turns your real experience into LinkedIn posts, articles and outreach messages that "
            "sound like you - building visibility that gets you found by recruiters."
        )

    if hae_granted:
        voiceai_desc = (
            "is now learning your natural communication style from your resume, LinkedIn presence "
            "and (as you add them) future interview responses - everything it writes for you will "
            "sound like you, not generic AI output."
        )
    else:
        voiceai_desc = (
            "is ready whenever you are - you have not yet granted voice-learning consent, so all "
            "content will use standard professional templates until you opt in from My Profile & "
            "Settings."
        )

    welcome_email = f"""Subject: Welcome to FORGE AI, {first_name}! Your career acceleration journey starts now.

Dear {prof.get('name', 'Member')},

Welcome to FORGE AI (TM) - your AI-Powered Career Acceleration, Talent Readiness and
Human Authenticity Platform.

Date: {today_str}
Account Type: {prof.get('account_type', '-')}
Organization: {org_name or 'Not applicable'}
Role / Designation: {prof.get('role', '-')}
Department: {prof.get('department', '-')}
Country: {prof.get('country', '-')}
Program of Interest: {program or 'Not specified'}

{body_focus}

We have received your resume ({st.session_state.resume_file_name or 'not uploaded'}), your listed
skills ({skills_line}), and your certifications ({certs_line}). Five proprietary FORGE engines are
already at work on your profile:

1. FORGE Match(TM) (Talent Intelligence) - {match_desc}
2. FORGE Sim(TM) (Interview Simulation) - {sim_desc}
3. FORGE VoiceAI(TM) (Human Authenticity Engine) - {voiceai_desc}
4. FORGE Insights(TM) (Career Analytics) - {insights_desc}
5. FORGE Growth(TM) (Visibility & Branding) - {growth_desc}

What to do next:
1. Explore your Dashboard to see your Readiness Score and Top Matches from FORGE Match(TM).
2. {cta_line}
3. Review your Learning Roadmap for skill gaps to close this week.
4. Watch the short Platform Tour videos to get familiar with every module in under 15 minutes.
5. Visit the FAQs page if you have onboarding questions - most are answered there, including how
   FORGE VoiceAI(TM) and voice-learning consent work.

Your notifications will be sent via: {', '.join(prof.get('notify_pref', ['Email']))}.

If you need help at any time, reach out to support@forgeai.example.

We are glad to have you on board.

Warm regards,
The FORGE AI Team
"""

    st.markdown('<div class="email-preview">', unsafe_allow_html=True)
    st.text(welcome_email)
    st.markdown("</div>", unsafe_allow_html=True)

    st.download_button(
        "Download welcome email (.txt)",
        data=welcome_email,
        file_name=f"FORGE_AI_Welcome_{first_name}.txt",
        mime="text/plain",
        use_container_width=False,
    )

    st.info("Continue to **Dashboard** from the left navigation to enter your career command center.")

# --------------------------------------------------------------------------
# PAGE: DASHBOARD OVERVIEW
# --------------------------------------------------------------------------
elif page == "dashboard":
    prof = st.session_state.profile
    first_name = prof.get("name", "there").split(" ")[0] if prof.get("name") else "there"
    is_corporate = prof.get("account_type") != "Individual / Job Seeker"
    jobs = generate_mock_jobs()
    rng = get_user_rng()

    # Deterministic-but-personalized readiness score
    completeness = sum([
        bool(prof.get("key_skills")), bool(prof.get("certifications")),
        bool(prof.get("target_role") and prof.get("target_role") != "Not sure yet"),
        bool(prof.get("linkedin_url")), bool(prof.get("hae_consent")),
    ])
    readiness = min(97, 62 + completeness * 7 + rng.randint(0, 5))
    readiness_label = "Strong" if readiness >= 80 else "Building" if readiness >= 60 else "Early Stage"

    top1, top2 = st.columns([2.2, 1])
    with top1:
        st.markdown(
            f'<div class="section-title">Welcome back, {first_name}! \U0001F44B</div>'
            f'<div style="color:#8A8FA3;font-size:13px;margin-top:-8px;">'
            f'{"Your talent command center" if is_corporate else "Your career command center"}</div>',
            unsafe_allow_html=True,
        )
    with top2:
        st.markdown(render_gauge(readiness, size=76, color="#22C55E", label=f"Overall Readiness · {readiness_label}"), unsafe_allow_html=True)

    st.write("")
    n_applied = len(st.session_state.applied_jobs)
    n_saved = len(st.session_state.saved_jobs)
    n_interview = sum(1 for s in st.session_state.applied_jobs.values() if s in ("Interview", "Offer"))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Jobs Found</div>'
                     f'<div class="metric-value">{len(jobs)}</div><div style="font-size:11px;color:#1E8E4C;">+{rng.randint(2,6)} this week</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Applications</div>'
                     f'<div class="metric-value">{n_applied}</div><div style="font-size:11px;color:#1E8E4C;">{n_saved} saved</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Interviews</div>'
                     f'<div class="metric-value">{n_interview}</div><div style="font-size:11px;color:#8A8FA3;">this month</div></div>', unsafe_allow_html=True)
    with c4:
        profile_views = 40 + completeness * 20 + rng.randint(0, 30)
        st.markdown(f'<div class="metric-card"><div class="metric-label">Profile Views</div>'
                     f'<div class="metric-value">{profile_views}</div><div style="font-size:11px;color:#1E8E4C;">+{rng.randint(8,25)}% this week</div></div>', unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([1.6, 1])
    with left:
        st.markdown("##### Top Job Matches")
        for job in jobs[:3]:
            match_cls = "match-high" if job["match_pct"] >= 85 else "match-mid" if job["match_pct"] >= 70 else "match-low"
            st.markdown(
                f"""
                <div class="job-card" style="display:flex;align-items:center;justify-content:space-between;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        <div class="company-badge">{job['company'][0]}</div>
                        <div>
                            <div style="font-weight:700;color:#24243B;font-size:13px;">{job['title']}</div>
                            <div style="color:#8A8FA3;font-size:11px;">{job['company']} · {job['location']}</div>
                        </div>
                    </div>
                    <span class="match-badge {match_cls}">{job['match_pct']}% Match</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if st.button("View all jobs \u2192", key="dash_view_all"):
            st.session_state.active_page = "job_hunter"
            st.rerun()

    with right:
        st.markdown("##### Interview Readiness")
        ready_roles = sum(1 for j in jobs if j["match_pct"] >= 80)
        st.markdown(render_gauge(min(97, readiness), size=90, color="#5B4CF2"), unsafe_allow_html=True)
        st.caption(f"You are interview-ready for {ready_roles} roles.")
        if st.button("Start Simulation \u2192", use_container_width=True, key="dash_start_sim"):
            st.session_state.active_page = "simulation" if "simulation" in [k for _, k in NAV_ITEMS] else "job_hunter"
            st.rerun()

    st.write("")
    l2, r2 = st.columns([1.6, 1])
    with l2:
        st.markdown("##### Recent Activity")
        activities = [
            ("Resume optimized for target role", "2 hours ago"),
            ("Completed a platform onboarding step", "5 hours ago"),
            (f"New match found: {jobs[0]['title']} at {jobs[0]['company']}", "1 day ago"),
            (f"Applied to {jobs[1]['title']}" if n_applied else "Profile created", "1 day ago"),
        ]
        for text, when in activities:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:7px 0;'
                f'border-bottom:1px solid #ECEEF6;font-size:12px;color:#5A5E73;">'
                f'<span>{text}</span><span style="color:#B4B2A9;">{when}</span></div>',
                unsafe_allow_html=True,
            )
    with r2:
        st.markdown("##### Learning Streak")
        streak_days = 3 + completeness * 2
        st.markdown(f'<div style="font-size:26px;font-weight:700;color:#24243B;">{streak_days} <span style="font-size:13px;color:#8A8FA3;font-weight:400;">days in a row</span></div>', unsafe_allow_html=True)
        dots_html = "".join(
            f'<span class="streak-dot {"streak-on" if i < min(7, streak_days) else "streak-off"}">{d}</span>'
            for i, d in enumerate(["M", "T", "W", "T", "F", "S", "S"])
        )
        st.markdown(f'<div style="margin-top:8px;">{dots_html}</div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------
# PAGE: JOB HUNTER AGENT
# --------------------------------------------------------------------------
elif page == "job_hunter":
    prof = st.session_state.profile
    jobs = generate_mock_jobs()

    st.markdown('<div class="section-title">Job Intelligence</div>', unsafe_allow_html=True)
    st.caption("Discover relevant opportunities aggregated across multiple sources, powered by FORGE Match(TM).")

    f1, f2, f3 = st.columns(3)
    with f1:
        role_filter = st.selectbox("Role", ["All Roles"] + sorted(set(j["title"] for j in jobs)))
    with f2:
        loc_filter = st.selectbox("Location", ["All Locations"] + sorted(set(j["location"] for j in jobs)))
    with f3:
        sort_by = st.selectbox("Sort by", ["Best Match", "Most Recent"])

    with st.expander("+ Create Job Alert"):
        with st.form("alert_form"):
            alert_role = st.text_input("Role keyword", placeholder="e.g. Data Architect")
            alert_loc = st.selectbox("Preferred location", MOCK_LOCATIONS)
            alert_submit = st.form_submit_button("Create Alert")
        if alert_submit and alert_role.strip():
            st.session_state.job_alerts.append({"role": alert_role.strip(), "location": alert_loc})
            st.success(f"Alert created for '{alert_role.strip()}' in {alert_loc}.")

    tab_opp, tab_saved, tab_applied, tab_alerts = st.tabs(
        ["Opportunities", "Saved Jobs", "Applied Jobs", "Job Alerts"]
    )

    filtered = [j for j in jobs if (role_filter == "All Roles" or j["title"] == role_filter)
                and (loc_filter == "All Locations" or j["location"] == loc_filter)]
    filtered.sort(key=lambda j: (-j["match_pct"]) if sort_by == "Best Match" else j["posted_days"])

    def render_job_card(job, show_actions=True, ctx="opp"):
        match_cls = "match-high" if job["match_pct"] >= 85 else "match-mid" if job["match_pct"] >= 70 else "match-low"
        posted = "Today" if job["posted_days"] == 0 else f"{job['posted_days']}d ago"
        st.markdown(
            f"""
            <div class="job-card">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        <div class="company-badge">{job['company'][0]}</div>
                        <div>
                            <div style="font-weight:700;color:#24243B;font-size:14px;">{job['title']}</div>
                            <div style="color:#8A8FA3;font-size:12px;">{job['company']} · {job['location']}</div>
                            <div style="color:#B4B2A9;font-size:11px;">{job['years']}+ Yrs · {job['job_type']} · Posted {posted}</div>
                        </div>
                    </div>
                    <span class="match-badge {match_cls}">{job['match_pct']}% Match</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(f"View Details \u2014 {job['title']} @ {job['company']}", key=f"exp_{ctx}_{job['id']}"):
            st.write(job["jd_text"])
            st.markdown(f"**Must-have:** {', '.join(job['must_have'])}")
            st.markdown(f"**Nice-to-have:** {', '.join(job['nice_have'])}")
            if show_actions:
                bcol1, bcol2, bcol3 = st.columns(3)
                with bcol1:
                    if st.button("Save Job", key=f"save_{ctx}_{job['id']}"):
                        st.session_state.saved_jobs.add(job["id"])
                        st.rerun()
                with bcol2:
                    already_applied = job["id"] in st.session_state.applied_jobs
                    if st.button("Apply Now" if not already_applied else "Applied \u2713", key=f"apply_{ctx}_{job['id']}", disabled=already_applied):
                        st.session_state.applied_jobs[job["id"]] = "Applied"
                        st.rerun()
                with bcol3:
                    if st.button("Analyze JD \u2192", key=f"analyzejd_{ctx}_{job['id']}"):
                        st.session_state.jd_analysis_result = analyze_jd_text(job["jd_text"])
                        st.session_state.jd_analysis_result["source_job"] = job
                        st.session_state.active_page = "jd_intelligence"
                        st.rerun()

    with tab_opp:
        st.caption(f"{len(filtered)} opportunities found")
        for job in filtered:
            render_job_card(job, ctx="opp")

    with tab_saved:
        saved = [j for j in jobs if j["id"] in st.session_state.saved_jobs]
        if not saved:
            st.info("No saved jobs yet. Save a job from the Opportunities tab.")
        for job in saved:
            render_job_card(job, ctx="saved")

    with tab_applied:
        applied = [j for j in jobs if j["id"] in st.session_state.applied_jobs]
        if not applied:
            st.info("No applications yet. Apply to a job from the Opportunities tab.")
        for job in applied:
            status = st.session_state.applied_jobs[job["id"]]
            status_cls = {"Applied": "status-applied", "Interview": "status-interview", "Offer": "status-offer"}[status]
            st.markdown(
                f'<div class="job-card" style="display:flex;justify-content:space-between;align-items:center;">'
                f'<div><b>{job["title"]}</b> · {job["company"]}</div>'
                f'<span class="status-badge {status_cls}">{status}</span></div>',
                unsafe_allow_html=True,
            )

    with tab_alerts:
        if not st.session_state.job_alerts:
            st.info("No job alerts created yet. Use '+ Create Job Alert' above.")
        for alert in st.session_state.job_alerts:
            st.markdown(f'<div class="job-card">\U0001F514 <b>{alert["role"]}</b> in {alert["location"]}</div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------
# PAGE: JD INTELLIGENCE AGENT
# --------------------------------------------------------------------------
elif page == "jd_intelligence":
    prof = st.session_state.profile
    st.markdown('<div class="section-title">JD Intelligence</div>', unsafe_allow_html=True)
    st.caption("Extracted insights from a job description, powered by FORGE Match(TM).")

    source_job = (st.session_state.jd_analysis_result or {}).get("source_job")
    with st.form("jd_analyze_form"):
        default_text = source_job["jd_text"] if source_job else ""
        jd_input_text = st.text_area("Paste a job description to analyze (or use 'Analyze JD' from Job Hunter Agent)",
                                      value=default_text, height=140)
        analyze_submit = st.form_submit_button("Analyze JD", type="primary")
    if analyze_submit and jd_input_text.strip():
        st.session_state.jd_analysis_result = analyze_jd_text(jd_input_text)

    result = st.session_state.jd_analysis_result
    if not result:
        st.info("Paste a JD above and click 'Analyze JD', or go to Job Hunter Agent and click 'Analyze JD \u2192' on any job.")
    else:
        if source_job:
            h1, h2, h3, h4 = st.columns(4)
            with h1:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Job Title</div><div class="metric-value" style="font-size:15px;">{source_job["title"]}</div></div>', unsafe_allow_html=True)
            with h2:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Company</div><div class="metric-value" style="font-size:15px;">{source_job["company"]}</div></div>', unsafe_allow_html=True)
            with h3:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Experience</div><div class="metric-value" style="font-size:15px;">{source_job["years"]}+ Years</div></div>', unsafe_allow_html=True)
            with h4:
                st.markdown(f'<div class="metric-card"><div class="metric-label">Location</div><div class="metric-value" style="font-size:15px;">{source_job["location"]}</div></div>', unsafe_allow_html=True)
            st.write("")

        tab_summary, tab_skills, tab_resp, tab_qual = st.tabs(
            ["JD Summary", "Skills", "Responsibilities", "Qualifications"]
        )
        with tab_summary:
            colA, colB = st.columns([1.6, 1])
            with colA:
                st.markdown("**Key Skills (Must Have)**")
                for s in result["found_skills"][:8]:
                    st.markdown(f"\u2705 {s.title()}")
                st.markdown("**Key Responsibilities**")
                for r in result["responsibilities"]:
                    st.markdown(f"\u2705 {r.capitalize()}")
            with colB:
                st.markdown("**Job Insights**")
                st.write(f"Top Skill Category: **{result['top_category']}**")
                st.write(f"Experience Level: **{result['seniority']}**")
                st.write(f"Job Type: **{result['job_type']}**")
                st.write(f"Industry: **{result['industry']}**")
                st.markdown(render_gauge(result["match_potential"], size=80, color="#22C55E", label="Match Potential"), unsafe_allow_html=True)
        with tab_skills:
            for s in result["found_skills"]:
                st.markdown(f"- {s.title()}")
        with tab_resp:
            for r in result["responsibilities"]:
                st.markdown(f"- {r.capitalize()}")
        with tab_qual:
            st.write(f"Minimum {result['years']}+ years of relevant experience.")
            st.write(f"Strong grounding in: {', '.join(result['found_skills'][:5]) or 'core technical skills'}.")

# --------------------------------------------------------------------------
# PAGE: CANDIDATE MATCHING AGENT
# --------------------------------------------------------------------------
# ==========================================================================
# PAGE: EMAIL AGENT  (Exeliq integration)
# ==========================================================================
elif page == "email_agent":
    exeliq_email_agent.render(st, render_gauge)

elif page == "candidate_matching":
    prof = st.session_state.profile
    is_corporate = prof.get("account_type") != "Individual / Job Seeker"
    jobs = generate_mock_jobs()

    if is_corporate:
        st.markdown('<div class="section-title">Candidate Matching</div>', unsafe_allow_html=True)
        st.caption("Match candidates for a selected job, powered by FORGE Match(TM).")

        job_titles = [f"{j['title']} \u2014 {j['company']}" for j in jobs]
        selected_idx = st.selectbox("Selected Job", range(len(jobs)), format_func=lambda i: job_titles[i])
        selected_job = jobs[selected_idx]
        candidates = generate_mock_candidates(selected_job)

        st.markdown(f"**{len(candidates)} candidates matched against {selected_job['title']} @ {selected_job['company']}**")
        for c in candidates:
            st.markdown(
                f"""
                <div class="cand-row">
                    <div style="display:flex;align-items:center;gap:10px;">
                        <div class="company-badge" style="background:linear-gradient(135deg,#5B4CF2,#7C6BFA);color:white;">{initials(c['name'])}</div>
                        <div>
                            <div style="font-weight:700;color:#24243B;font-size:13px;">{c['name']}</div>
                            <div style="color:#8A8FA3;font-size:11px;">Skills {c['skills_match']}% · Experience {c['experience_match']}% · Readiness {c['readiness_score']}%</div>
                        </div>
                    </div>
                    <span class="match-badge {'match-high' if c['overall_match']>=85 else 'match-mid' if c['overall_match']>=70 else 'match-low'}">{c['overall_match']}% Match</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown('<div class="section-title">Your Applications & Match Scores</div>', unsafe_allow_html=True)
        st.caption("Match scores for the roles you have saved or applied to, powered by FORGE Match(TM).")

        tracked_ids = set(st.session_state.saved_jobs) | set(st.session_state.applied_jobs.keys())
        tracked_jobs = [j for j in jobs if j["id"] in tracked_ids]
        if not tracked_jobs:
            st.info("You haven't saved or applied to any jobs yet. Visit Job Hunter Agent to get started.")
        for job in tracked_jobs:
            status = st.session_state.applied_jobs.get(job["id"], "Saved")
            status_cls = {"Applied": "status-applied", "Interview": "status-interview",
                          "Offer": "status-offer", "Saved": "status-applied"}[status]
            match_cls = "match-high" if job["match_pct"] >= 85 else "match-mid" if job["match_pct"] >= 70 else "match-low"
            st.markdown(
                f"""
                <div class="cand-row">
                    <div>
                        <div style="font-weight:700;color:#24243B;font-size:13px;">{job['title']}</div>
                        <div style="color:#8A8FA3;font-size:11px;">{job['company']} · {job['location']}</div>
                    </div>
                    <div style="display:flex;gap:8px;align-items:center;">
                        <span class="status-badge {status_cls}">{status}</span>
                        <span class="match-badge {match_cls}">{job['match_pct']}% Match</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# --------------------------------------------------------------------------
# PAGE: RESUME INTELLIGENCE AGENT
# --------------------------------------------------------------------------
elif page == "resume_intelligence":
    prof = st.session_state.profile
    jobs = generate_mock_jobs()

    st.markdown('<div class="section-title">Resume Studio</div>', unsafe_allow_html=True)
    st.caption("ATS resume optimization powered by FORGE VoiceAI(TM).")

    job_titles = [f"{j['title']} \u2014 {j['company']}" for j in jobs]
    default_idx = next((i for i, j in enumerate(jobs) if j["id"] == st.session_state.selected_job_id), 0)
    sel_idx = st.selectbox("Select Job to optimize against", range(len(jobs)),
                            format_func=lambda i: job_titles[i], index=default_idx)
    st.session_state.selected_job_id = jobs[sel_idx]["id"]
    job = jobs[sel_idx]

    tab1, tab2, tab3, tab4 = st.tabs(["1. Select Job", "2. Analyze Resume", "3. Optimize", "4. Generate"])

    with tab1:
        st.markdown(f"**Target role:** {job['title']} at {job['company']}")
        st.markdown(f"**Must-have skills:** {', '.join(job['must_have'])}")
        st.markdown(f"**Nice-to-have skills:** {', '.join(job['nice_have'])}")
        st.info("Selection saved. Move to the 'Analyze Resume' tab.")

    analysis = compute_resume_analysis(job)
    with tab2:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(render_gauge(analysis["ats_score"], size=100, color="#5B4CF2", label="ATS Score"), unsafe_allow_html=True)
        with c2:
            st.markdown("**Improvement Areas**")
            st.markdown(
                f'<div class="dr"><span class="dr-l">Added missing keywords</span><span class="dr-r">{analysis["missing_keywords_count"]}</span></div>'
                f'<div class="dr"><span class="dr-l">Improved bullet points</span><span class="dr-r">{analysis["improved_bullets_count"]}</span></div>'
                f'<div class="dr"><span class="dr-l">Skills enhancement</span><span class="dr-r">{analysis["skills_enhancement_count"]}</span></div>'
                f'<div class="dr"><span class="dr-l">Formatting & structure</span><span class="dr-r">{analysis["formatting_fixes_count"]}</span></div>',
                unsafe_allow_html=True,
            )
        if analysis["missing_keywords"]:
            st.markdown("**Missing keywords to add:**")
            st.write(", ".join(analysis["missing_keywords"]))

    with tab3:
        st.markdown("**Optimized Resume Preview**")
        resume_text = build_resume_text(job)
        st.markdown(f'<div class="email-preview">', unsafe_allow_html=True)
        st.text(resume_text)
        st.markdown("</div>", unsafe_allow_html=True)

    with tab4:
        resume_text = build_resume_text(job)
        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button("Download Resume (.txt)", data=resume_text,
                                file_name=f"{prof.get('name','resume').replace(' ','_')}_Resume.txt", mime="text/plain")
        with d2:
            md_text = resume_text.replace("PROFESSIONAL SUMMARY", "## Professional Summary") \
                                  .replace("CORE COMPETENCIES", "## Core Competencies") \
                                  .replace("EXPERIENCE", "## Experience")
            st.download_button("Download Resume (.md)", data=md_text,
                                file_name=f"{prof.get('name','resume').replace(' ','_')}_Resume.md", mime="text/markdown")
        with d3:
            if st.button("Save & Next \u2192", type="primary"):
                st.session_state.resume_versions_saved += 1
                st.success(f"Resume version saved ({st.session_state.resume_versions_saved} total).")

# --------------------------------------------------------------------------
# PAGE: GAP ANALYSIS AGENT
# --------------------------------------------------------------------------
elif page == "gap_analysis":
    prof = st.session_state.profile
    jobs = generate_mock_jobs()

    st.markdown('<div class="section-title">Gap Analysis</div>', unsafe_allow_html=True)
    st.caption("Identify gaps and opportunities, powered by FORGE Insights(TM).")

    job_titles = [f"{j['title']} \u2014 {j['company']}" for j in jobs]
    default_idx = next((i for i, j in enumerate(jobs) if j["id"] == st.session_state.selected_job_id), 0)
    sel_idx = st.selectbox("Analyze gaps against", range(len(jobs)),
                            format_func=lambda i: job_titles[i], index=default_idx, key="gap_job_select")
    st.session_state.selected_job_id = jobs[sel_idx]["id"]
    job = jobs[sel_idx]

    gap = compute_gap_analysis(job)

    g1, g2, g3 = st.columns([1, 1.4, 1.2])
    with g1:
        st.markdown("**Overall Gap Score**")
        gauge_color = TARGET_ROLE_PRIORITY["high"] if gap["gap_label"] == "High" else \
            TARGET_ROLE_PRIORITY["medium"] if gap["gap_label"] == "Moderate" else TARGET_ROLE_PRIORITY["low"]
        st.markdown(render_gauge(gap["gap_score"], size=100, color=gauge_color, label=gap["gap_label"]), unsafe_allow_html=True)
        st.caption("Focus on high priority gaps to improve readiness.")
    with g2:
        st.markdown("**Skill Gaps**")
        st.markdown("High Priority")
        st.markdown("".join(f'<span class="gap-tag gap-high">{s.title()}</span>' for s in gap["high_priority"]) or "<span style='color:#8A8FA3;font-size:12px;'>None</span>", unsafe_allow_html=True)
        st.markdown("Medium Priority")
        st.markdown("".join(f'<span class="gap-tag gap-medium">{s.title()}</span>' for s in gap["medium_priority"]) or "<span style='color:#8A8FA3;font-size:12px;'>None</span>", unsafe_allow_html=True)
        st.markdown("Low Priority")
        st.markdown("".join(f'<span class="gap-tag gap-low">{s.title()}</span>' for s in gap["low_priority"]) or "<span style='color:#8A8FA3;font-size:12px;'>None</span>", unsafe_allow_html=True)
    with g3:
        st.markdown("**Recommendations**")
        for i, rec in enumerate(gap["recommendations"], 1):
            st.markdown(f"{i}. {rec}")

    st.write("")
    if st.button("View Learning Roadmap \u2192", type="primary"):
        st.session_state.active_page = "learning_dev"
        st.rerun()

# --------------------------------------------------------------------------
# PAGE: LEARNING & DEVELOPMENT AGENT
# --------------------------------------------------------------------------
elif page == "learning_dev":
    prof = st.session_state.profile
    job = get_selected_job()
    gap = compute_gap_analysis(job) if job else {"high_priority": [], "medium_priority": [], "low_priority": []}
    gap_skills = gap["high_priority"] + gap["medium_priority"] + gap["low_priority"]
    all_tracked_skills = list(dict.fromkeys(gap_skills + [s.lower() for s in prof.get("key_skills", [])]))[:6]

    st.markdown('<div class="section-title">Learning & Development</div>', unsafe_allow_html=True)
    st.caption("Personalized learning roadmap, powered by FORGE Insights(TM).")

    tab_my, tab_courses, tab_certs, tab_books = st.tabs(
        ["My Learning", "Recommended Courses", "Certifications", "Books"]
    )

    with tab_my:
        target_role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "Professional")
        rng = get_user_rng()
        overall_pct = int(sum(st.session_state.learning_progress.get(s, rng.randint(45, 75)) for s in all_tracked_skills) / len(all_tracked_skills)) if all_tracked_skills else 0

        st.markdown(f"**Current Path: {target_role} Mastery Path**")
        st.progress(overall_pct / 100, text=f"{overall_pct}% Complete")

        st.markdown("**Skills Progress**")
        for skill in all_tracked_skills:
            pct = st.session_state.learning_progress.get(skill, rng.randint(45, 90))
            st.session_state.learning_progress.setdefault(skill, pct)
            pct = st.session_state.learning_progress[skill]
            st.markdown(
                f'<div style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;'
                f'font-size:12px;color:#5A5E73;"><span>{skill.title()}</span><span>{pct}%</span></div>'
                f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div></div>',
                unsafe_allow_html=True,
            )

        if all_tracked_skills:
            next_skill = min(all_tracked_skills, key=lambda s: st.session_state.learning_progress.get(s, 50))
            st.markdown(f"**Next Up:** {next_skill.title()} \u2014 Advanced Practice (45 min)")
            if st.button("Start Learning \u2192", type="primary", key="start_learning_btn"):
                cur = st.session_state.learning_progress.get(next_skill, 50)
                st.session_state.learning_progress[next_skill] = min(100, cur + 15)
                st.rerun()

    with tab_courses:
        catalog = generate_course_catalog(all_tracked_skills if all_tracked_skills else ["python", "sql"])
        for course in catalog:
            enrolled = course["id"] in st.session_state.enrolled_courses
            st.markdown(
                f'<div class="course-card"><b>{course["title"]}</b><br>'
                f'<span style="color:#8A8FA3;font-size:12px;">{course["provider"]} \u00b7 {course["duration"]}</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("Enrolled \u2713" if enrolled else "Enroll", key=f"enroll_{course['id']}", disabled=enrolled):
                st.session_state.enrolled_courses.add(course["id"])
                st.rerun()

    with tab_certs:
        relevant_certs = [c for c in CERTIFICATION_OPTIONS if c not in ("None yet", "Other")][:6]
        existing = set(prof.get("certifications", []))
        for cert in relevant_certs:
            already = cert in existing
            ccol1, ccol2 = st.columns([3, 1])
            with ccol1:
                st.write(cert)
            with ccol2:
                if st.button("Added \u2713" if already else "Add", key=f"cert_{cert}", disabled=already):
                    st.session_state.profile.setdefault("certifications", [])
                    st.session_state.profile["certifications"].append(cert)
                    st.rerun()

    with tab_books:
        for book in BOOK_LIST:
            in_list = book["title"] in st.session_state.reading_list
            bcol1, bcol2 = st.columns([3, 1])
            with bcol1:
                st.write(f"**{book['title']}** \u2014 {book['author']}")
            with bcol2:
                if st.button("Added \u2713" if in_list else "Add to List", key=f"book_{book['title']}", disabled=in_list):
                    st.session_state.reading_list.add(book["title"])
                    st.rerun()

# --------------------------------------------------------------------------
# PAGE: FORGE SIMULATION AGENT (INTERVIEW SIMULATOR)
# --------------------------------------------------------------------------
elif page == "simulation":
    prof = st.session_state.profile
    st.markdown('<div class="section-title">Interview Simulator</div>', unsafe_allow_html=True)
    st.caption("Live scenario-based simulation, powered by FORGE Sim(TM).")

    if st.session_state.active_scenario_id is None:
        st.session_state.active_scenario_id = SIMULATION_SCENARIOS[0]["id"]

    left, right = st.columns([1, 2.2])
    with left:
        st.markdown("**Select Scenario**")
        for sc in SIMULATION_SCENARIOS:
            done = sc["id"] in st.session_state.simulation_results
            active = sc["id"] == st.session_state.active_scenario_id
            status = "Completed" if done else ("In Progress" if active else "Pending")
            css_cls = "scenario-done" if done else ("scenario-active" if active else "")
            st.markdown(
                f'<div class="scenario-item {css_cls}"><b>{sc["title"]}</b><br>'
                f'<span style="color:#8A8FA3;font-size:11px;">{sc["category"]} \u00b7 {status}</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("Select", key=f"select_{sc['id']}", use_container_width=True):
                st.session_state.active_scenario_id = sc["id"]
                st.rerun()

    scenario = next(sc for sc in SIMULATION_SCENARIOS if sc["id"] == st.session_state.active_scenario_id)
    with right:
        st.markdown(f"### {scenario['title']}")
        st.caption(scenario["category"])
        st.markdown(
            f'<div class="job-card">{scenario["scenario"]}<br><br>'
            f'<b>{scenario["business_impact"]}</b></div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{scenario['prompt']}**")

        answer_key = f"answer_{scenario['id']}"
        answer_text = st.text_area("Your Answer", key=answer_key, height=140,
                                    placeholder="Type your response here...")
        if st.button("Submit Answer", type="primary", key=f"submit_{scenario['id']}"):
            if answer_text.strip():
                st.session_state.simulation_results[scenario["id"]] = score_simulation_answer(scenario, answer_text)
                st.rerun()
            else:
                st.warning("Please type an answer before submitting.")

        st.write("")
        st.markdown("**Evaluation (Live)**")
        result = st.session_state.simulation_results.get(scenario["id"])
        if not result:
            st.info("Submit your answer to see your live evaluation.")
        else:
            ev1, ev2 = st.columns([1.6, 1])
            with ev1:
                for label, key in [("Technical Approach", "technical"), ("Communication", "communication"),
                                    ("Problem Solving", "problem_solving"), ("Leadership", "leadership")]:
                    pct = result[key]
                    st.markdown(
                        f'<div class="score-bar-row"><div style="display:flex;justify-content:space-between;'
                        f'font-size:12px;color:#5A5E73;"><span>{label}</span><span>{pct}%</span></div>'
                        f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div></div>',
                        unsafe_allow_html=True,
                    )
            with ev2:
                score_label = "Excellent" if result["overall"] >= 85 else "Good" if result["overall"] >= 70 else "Needs Work"
                st.markdown(render_gauge(result["overall"], size=90, color="#22C55E" if result["overall"] >= 70 else "#B8790A", label=f"Overall Score \u00b7 {score_label}"), unsafe_allow_html=True)

# --------------------------------------------------------------------------
# PAGE: PERFORMANCE EVALUATOR AGENT
# --------------------------------------------------------------------------
elif page == "performance_eval":
    prof = st.session_state.profile
    st.markdown('<div class="section-title">Performance Evaluation</div>', unsafe_allow_html=True)
    st.caption("Detailed performance assessment, powered by FORGE Insights(TM).")

    summary = get_performance_summary()
    if summary["source"] == "estimate":
        st.info("No simulations completed yet \u2014 scores below are an estimate based on your profile. "
                "Complete a scenario in the Interview Simulator for your actual performance evaluation.")

    p1, p2 = st.columns([1, 1.6])
    with p1:
        score_label = "Excellent" if summary["overall"] >= 85 else "Good" if summary["overall"] >= 70 else "Needs Work"
        st.markdown("**Overall Performance**")
        st.markdown(render_gauge(summary["overall"], size=110, color="#22C55E" if summary["overall"] >= 70 else "#B8790A", label=score_label), unsafe_allow_html=True)
    with p2:
        st.markdown("**Category Scores**")
        for label, key in [("Technical Depth", "technical"), ("Communication", "communication"),
                            ("Problem Solving", "problem_solving"), ("Decision Making", "decision_making"),
                            ("Leadership", "leadership")]:
            pct = summary[key]
            st.markdown(
                f'<div class="score-bar-row"><div style="display:flex;justify-content:space-between;'
                f'font-size:12px;color:#5A5E73;"><span>{label}</span><span>{pct}%</span></div>'
                f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div></div>',
                unsafe_allow_html=True,
            )

    st.write("")
    st.markdown("**Feedback Summary**")
    strongest = max(["technical", "communication", "problem_solving", "leadership"], key=lambda k: summary[k])
    weakest = min(["technical", "communication", "problem_solving", "leadership"], key=lambda k: summary[k])
    label_map = {"technical": "technical depth", "communication": "communication", "problem_solving": "problem-solving", "leadership": "leadership"}
    st.write(
        f"Strong {label_map[strongest]} and consistent delivery. "
        f"Focus on improving {label_map[weakest]} to raise your overall readiness score."
    )

    if st.session_state.simulation_results:
        with st.expander("View Detailed Report \u2192"):
            for sc_id, res in st.session_state.simulation_results.items():
                sc = next((s for s in SIMULATION_SCENARIOS if s["id"] == sc_id), None)
                if sc:
                    st.markdown(f"**{sc['title']}** \u2014 Overall {res['overall']}%")
                    st.caption(f"Technical {res['technical']}% \u00b7 Communication {res['communication']}% \u00b7 "
                               f"Problem Solving {res['problem_solving']}% \u00b7 Leadership {res['leadership']}%")

# --------------------------------------------------------------------------
# PAGE: HUMAN AUTHENTICITY ENGINE (HAE)
# --------------------------------------------------------------------------
elif page == "human_authenticity":
    prof = st.session_state.profile
    st.markdown('<div class="section-title">Human Authenticity Engine</div>', unsafe_allow_html=True)
    st.caption("Your voice profile and content authenticity, powered by FORGE VoiceAI(TM).")

    voice = get_voice_profile()

    h1, h2 = st.columns([1.6, 1])
    with h1:
        st.markdown("**Your Voice Profile**")
        st.markdown("".join(f'<span class="voice-tag">{t}</span>' for t in voice["tags"]), unsafe_allow_html=True)
        st.write("")
        if voice["hae_granted"]:
            st.success("Your content is currently aligned with your authentic voice.")
        else:
            st.warning("Voice-learning consent is not granted, so this profile uses generic defaults. "
                       "Enable it from My Profile & Settings for a personalized voice profile.")
    with h2:
        st.markdown("**Voice Consistency Score**")
        label = "High" if voice["consistency"] >= 80 else "Medium" if voice["consistency"] >= 55 else "Low"
        st.markdown(render_gauge(voice["consistency"], size=90, color="#22C55E" if voice["consistency"] >= 80 else "#B8790A", label=label), unsafe_allow_html=True)

    st.write("")
    tab_tone, tab_brand = st.tabs(["Content Tonality", "Brand Insights"])
    with tab_tone:
        for tone, pct in voice["tonality"].items():
            st.markdown(
                f'<div class="score-bar-row"><div style="display:flex;justify-content:space-between;'
                f'font-size:12px;color:#5A5E73;"><span>{tone}</span><span>{pct}%</span></div>'
                f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div></div>',
                unsafe_allow_html=True,
            )
    with tab_brand:
        role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "your field")
        st.write(f"Your content consistently emphasizes technical depth and practical impact in {role}. "
                 f"Recruiters and peers are most likely to associate your voice with clarity and expertise "
                 f"rather than generic thought-leadership language.")

    st.write("")
    st.markdown("**Sample Output (Humanized)**")
    st.markdown(f'<div class="post-box">{build_sample_post()}</div>', unsafe_allow_html=True)

    st.write("")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Update Voice Profile \u2192", type="primary", use_container_width=True):
            st.session_state.voice_profile_seed += 1
            st.rerun()
    with b2:
        with st.expander("View Authenticity Insights"):
            st.write(f"Voice tags detected: {', '.join(voice['tags'])}.")
            st.write(f"Consistency score: {voice['consistency']}% ({label}).")
            st.write("Regenerate to see how new content samples would be adapted to your voice.")

# --------------------------------------------------------------------------
# PAGE: LINKEDIN BRANDING AGENT
# --------------------------------------------------------------------------
elif page == "linkedin_branding":
    prof = st.session_state.profile
    st.markdown('<div class="section-title">LinkedIn Branding</div>', unsafe_allow_html=True)
    st.caption("Generate posts, articles and content calendars, powered by FORGE Growth(TM).")

    tab_posts, tab_articles, tab_calendar = st.tabs(["Generated Posts", "Articles", "Content Calendar"])

    with tab_posts:
        st.markdown("**Generated Post (Preview)**")
        post_text = build_sample_post()
        edit_mode = st.session_state.get("linkedin_edit_mode", False)
        if edit_mode:
            edited = st.text_area("Edit your post", value=post_text, height=140, key="linkedin_edit_text")
        else:
            st.markdown(f'<div class="post-box">{post_text}</div>', unsafe_allow_html=True)

        perf = get_linkedin_performance()
        st.markdown("**Post Performance (This Month)**")
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Engagement</div>'
                        f'<div class="metric-value">{perf["engagement"]/1000:.1f}K</div>'
                        f'<div style="font-size:11px;color:#1E8E4C;">+{perf["engagement_delta"]}%</div></div>', unsafe_allow_html=True)
        with pc2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Profile Views</div>'
                        f'<div class="metric-value">{perf["views"]/1000:.1f}K</div>'
                        f'<div style="font-size:11px;color:#1E8E4C;">+{perf["views_delta"]}%</div></div>', unsafe_allow_html=True)
        with pc3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Reactions</div>'
                        f'<div class="metric-value">{perf["reactions"]}</div>'
                        f'<div style="font-size:11px;color:#1E8E4C;">+{perf["reactions_delta"]}%</div></div>', unsafe_allow_html=True)

        st.write("")
        e1, e2 = st.columns(2)
        with e1:
            if st.button("Edit Post" if not edit_mode else "Done Editing", use_container_width=True):
                st.session_state.linkedin_edit_mode = not edit_mode
                st.rerun()
        with e2:
            if st.button("Schedule Post", type="primary", use_container_width=True):
                st.session_state.scheduled_posts.append({"text": post_text, "scheduled_at": "Tomorrow, 9:00 AM"})
                st.success("Post scheduled for tomorrow at 9:00 AM.")

        if st.session_state.scheduled_posts:
            with st.expander(f"Scheduled Posts ({len(st.session_state.scheduled_posts)})"):
                for sp in st.session_state.scheduled_posts:
                    st.write(f"\U0001F4C5 {sp['scheduled_at']} \u2014 {sp['text'][:80]}...")

    with tab_articles:
        role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "your field")
        st.markdown(f"**Suggested article topic:** \"What I've learned building resilient systems as a {role}\"")
        st.caption("Long-form thought leadership content, generated in your authentic voice via FORGE VoiceAI(TM).")
        st.info("Article generation follows the same voice profile as your posts \u2014 visit Human Authenticity Engine to review or update it.")

    with tab_calendar:
        st.markdown("**This week's content plan**")
        days = ["Monday", "Wednesday", "Friday"]
        topics = ["Technical insight post", "Industry commentary", "Career milestone update"]
        for d, t in zip(days, topics):
            st.markdown(f'<div class="job-card"><b>{d}</b> \u2014 {t}</div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------
# PAGE: OUTREACH AGENT
# --------------------------------------------------------------------------
elif page == "outreach":
    prof = st.session_state.profile
    is_corporate = prof.get("account_type") != "Individual / Job Seeker"
    st.markdown('<div class="section-title">Outreach</div>', unsafe_allow_html=True)
    st.caption("Recruiter outreach, referral requests and networking, powered by FORGE VoiceAI(TM).")

    tab_camp, tab_msg, tab_tmpl, tab_settings = st.tabs(["Campaigns", "Messages", "Templates", "Settings"])
    campaigns = generate_outreach_campaigns()

    with tab_camp:
        st.markdown(f"**Active Campaigns** ({sum(1 for c in campaigns if c['status']=='Active')} active)")
        for c in campaigns:
            st.markdown(
                f"""
                <div class="campaign-row">
                    <div>
                        <div style="font-weight:700;color:#24243B;font-size:13px;">{c['name']}</div>
                        <div style="color:#8A8FA3;font-size:11px;">Target {c['target']} \u00b7 Response {c['response']} ({c['response_rate']}%)</div>
                    </div>
                    <span class="status-badge {'status-offer' if c['status']=='Active' else 'status-applied'}">{c['status']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with st.expander("+ Create New Campaign"):
            with st.form("new_campaign_form"):
                camp_name = st.text_input("Campaign name", placeholder="e.g. Senior Roles Outreach")
                camp_target = st.number_input("Target outreach count", min_value=10, max_value=1000, value=100, step=10)
                camp_submit = st.form_submit_button("Create Campaign")
            if camp_submit and camp_name.strip():
                st.session_state.outreach_campaigns.append({
                    "id": f"camp{len(campaigns)+1:03d}", "name": camp_name.strip(),
                    "target": camp_target, "response": 0, "response_rate": 0.0, "status": "Active",
                })
                st.success(f"Campaign '{camp_name.strip()}' created.")
                st.rerun()

    with tab_msg:
        st.markdown("**Message Preview**")
        draft = st.session_state.outreach_message_draft or build_outreach_message()
        edited_msg = st.text_area("Outreach message", value=draft, height=120, key="outreach_msg_edit")
        st.session_state.outreach_message_draft = edited_msg
        st.caption(f"Referral requests sent: {len(st.session_state.scheduled_posts) + len(campaigns)}")

    with tab_tmpl:
        st.markdown("**Message Templates**")
        templates = {
            "Recruiter Outreach": build_outreach_message(),
            "Referral Request": "Hi {Name}, I'm exploring new opportunities and would value your perspective. "
                                 "Would you be open to a referral or a quick chat about openings at your company?",
            "Follow-up": "Hi {Name}, following up on my earlier message \u2014 happy to share more about my "
                         "background if it's helpful. Let me know a good time to connect.",
        }
        for name, text in templates.items():
            with st.expander(name):
                st.write(text)
                if st.button("Use Template", key=f"use_tmpl_{name}"):
                    st.session_state.outreach_message_draft = text
                    st.success(f"'{name}' loaded into Messages tab.")

    with tab_settings:
        st.write("Outreach cadence, tone and connected accounts can be configured here.")
        st.checkbox("Auto-follow-up after 5 days of no response", value=True, key="outreach_autofollow")
        st.checkbox("Personalize each message with candidate/company name", value=True, key="outreach_personalize")

# --------------------------------------------------------------------------
# PAGE: SUCCESS TRACKING AGENT (ANALYTICS)
# --------------------------------------------------------------------------
elif page == "success_tracking":
    prof = st.session_state.profile
    st.markdown('<div class="section-title">Success Tracking</div>', unsafe_allow_html=True)
    st.caption("Career progress and conversion analytics, powered by FORGE Insights(TM).")

    metrics = compute_success_metrics()
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Applications</div><div class="metric-value">{metrics["applications"]}</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Interviews</div><div class="metric-value">{metrics["interviews"]}</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Offers</div><div class="metric-value">{metrics["offers"]}</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Conversion Rate</div><div class="metric-value">{metrics["conversion"]}%</div></div>', unsafe_allow_html=True)

    st.write("")
    t1, t2 = st.columns([1.8, 1])
    with t1:
        st.markdown("**Activity Trend**")
        st.line_chart({"Applications": metrics["trend"]})
    with t2:
        st.markdown("**Top Insights**")
        for insight in metrics["insights"]:
            st.markdown(f"\u2022 {insight}")

    with st.expander("View Full Report \u2192"):
        st.write(f"Total tracked applications: {metrics['applications']}")
        st.write(f"Interviews secured: {metrics['interviews']}")
        st.write(f"Offers received: {metrics['offers']}")
        st.write(f"Overall conversion rate: {metrics['conversion']}%")

# --------------------------------------------------------------------------
# PAGE: CAREER INTELLIGENCE AGENT
# --------------------------------------------------------------------------
elif page == "career_intelligence":
    prof = st.session_state.profile
    st.markdown('<div class="section-title">Career Intelligence</div>', unsafe_allow_html=True)
    st.caption("Market trends and career recommendations, powered by FORGE Insights(TM).")

    tab_demand, tab_roles, tab_salary, tab_trends = st.tabs(
        ["Market Demand", "Role Insights", "Salary Insights", "Skill Trends"]
    )

    with tab_demand:
        st.markdown("**Market Demand \u2014 Roles**")
        for role, data in sorted(ROLE_MARKET_DATA.items(), key=lambda kv: -kv[1]["score"]):
            st.markdown(
                f'<div class="market-row"><span>{role}</span>'
                f'<span style="font-weight:700;color:#5B4CF2;">{data["score"]}/10</span></div>',
                unsafe_allow_html=True,
            )

    with tab_roles:
        role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "")
        data = ROLE_MARKET_DATA.get(role, {"score": 7.5, "salary_lpa": 15})
        st.write(f"**{role or 'Your target role'}** currently scores **{data['score']}/10** on market demand.")
        st.write("Top hiring industries: IT Services, Financial Services, Healthcare, Retail & E-commerce.")

    with tab_salary:
        st.markdown("**Average Salary (India)**")
        for role, data in sorted(ROLE_MARKET_DATA.items(), key=lambda kv: -kv[1]["salary_lpa"])[:6]:
            st.markdown(
                f'<div class="market-row"><span>{role}</span>'
                f'<span style="font-weight:700;color:#1E8E4C;">\u20b9{data["salary_lpa"]} LPA</span></div>',
                unsafe_allow_html=True,
            )

    with tab_trends:
        st.write("Rising skills this quarter: GenAI tooling, cloud-native data platforms, data governance, "
                 "cost optimization, and platform reliability engineering.")

    st.write("")
    st.markdown("**Career Recommendation**")
    st.info(get_career_recommendation())
    if st.button("View Detailed Plan \u2192", type="primary"):
        st.session_state.active_page = "learning_dev"
        st.rerun()

# --------------------------------------------------------------------------
# PAGE: PLATFORM TOUR (VIDEOS)
# --------------------------------------------------------------------------
elif page == "videos":
    prof = st.session_state.profile
    is_corporate = prof.get("account_type") != "Individual / Job Seeker"

    st.markdown('<div class="section-title">Platform usage guide (short videos)</div>', unsafe_allow_html=True)
    st.caption(
        "A quick structured tour of every FORGE AI module, powered by the six FORGE intelligence "
        "layers. These placeholders represent the short walkthrough videos available inside the product."
    )

    def render_video_grid(video_list, cols_per_row=3):
        for i in range(0, len(video_list), cols_per_row):
            row_items = video_list[i : i + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, (title, duration, desc) in zip(cols, row_items):
                with col:
                    st.markdown(
                        f"""
                        <div class="video-card">
                            <div class="video-thumb">&#9654;</div>
                            <div style="font-weight:700; color:#24243B; font-size:14px;">{title}</div>
                            <div style="color:#8A8FA3; font-size:11px; margin-bottom:6px;">{duration} watch</div>
                            <div style="color:#5A5E73; font-size:12px;">{desc}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.write("")

    # ---- Core platform tour ----
    common_videos = [
        ("Dashboard Overview", "2 min", "Your command center: jobs found, applications, interviews and readiness score."),
        ("JD Intelligence", "3 min", "See how FORGE Match(TM) extracts skills, certifications, experience requirements and priority keywords from any job description."),
        ("Job Intelligence", "3 min", "Discover relevant roles aggregated across multiple sources, ranked by opportunity score."),
        ("Resume Studio", "4 min", "Optimize your resume for ATS with AI-driven suggestions, powered by FORGE VoiceAI(TM)."),
        ("Interview Simulator", "5 min", "Practice live, role-based mock interviews with instant scoring. See scenario types below."),
        ("Learning Roadmap", "3 min", "Close skill gaps with a personalized learning path and certification plan."),
        ("LinkedIn Branding", "3 min", "Generate posts, articles and content calendars with FORGE Growth(TM)."),
        ("Human Authenticity Engine", "2 min", "Understand your voice-consistency and authenticity score. See the engine deep-dive below."),
    ]

    corporate_videos = [
        ("Candidate Matching", "4 min", "Rank and shortlist candidates against a selected job in seconds, powered by FORGE Match(TM)."),
        ("Gap Analysis", "3 min", "Identify skill, experience and certification gaps across your candidate pool and prioritize action."),
        ("Candidate Performance Reports", "3 min", "Review each candidate's simulation breakdown: technical depth, communication, decision-making and leadership."),
        ("Outreach Campaigns", "4 min", "Create and track candidate outreach campaigns end-to-end, in your organization's authentic voice."),
        ("Success Tracking (Analytics)", "3 min", "Monitor interviews, offers and conversion rate over time with FORGE Insights(TM)."),
        ("Market Intelligence", "3 min", "Technology trend analysis, in-demand skills and salary benchmarks to sharpen your hiring strategy."),
    ]

    individual_videos = [
        ("Career Intelligence", "3 min", "See market demand, role insights, certification guidance and salary trends for your target role."),
        ("Performance Evaluator", "3 min", "Review a detailed breakdown of your simulated interview performance."),
        ("Gap Analysis", "3 min", "See exactly which skills, certifications and experience separate you from your target role."),
        ("Outreach & Networking", "3 min", "Generate personalized recruiter outreach, referral requests and networking messages in your own voice."),
        ("Career Progress Tracking", "3 min", "Track your applications, interviews, offers and Readiness Score trend over time with FORGE Insights(TM)."),
    ]

    videos = common_videos + (corporate_videos if is_corporate else individual_videos)
    render_video_grid(videos)
    st.success(f"{len(videos)} onboarding videos curated for your role: {prof.get('role', '-')}.")

    # ---- FORGE Sim(TM) scenario types ----
    st.markdown(
        '<div class="section-title" style="font-size:15px;margin-top:22px;">'
        'FORGE Sim(TM) — interview simulation scenario types</div>',
        unsafe_allow_html=True,
    )
    st.caption("The FORGE Simulation Framework runs six distinct scenario types to validate real-world capability.")
    simulation_types = [
        ("Production Failure Simulations", "6 min", "Diagnose and resolve a live production incident under time pressure."),
        ("Cloud Architecture Challenges", "6 min", "Design or fix a cloud architecture against a real-world constraint set."),
        ("Leadership Simulations", "5 min", "Navigate a team conflict, prioritization call, or stakeholder escalation."),
        ("Incident Response Exercises", "5 min", "Lead an incident from detection through resolution and postmortem."),
        ("Technical Deep-Dive Interviews", "7 min", "Defend your technical decisions under detailed follow-up questioning."),
        ("System Design Challenges", "7 min", "Design a system end-to-end against scale, cost and reliability constraints."),
    ]
    render_video_grid(simulation_types)

    # ---- FORGE VoiceAI(TM) / Human Authenticity Engine deep dive ----
    st.markdown(
        '<div class="section-title" style="font-size:15px;margin-top:22px;">'
        'FORGE VoiceAI(TM) — inside the Human Authenticity Engine</div>',
        unsafe_allow_html=True,
    )
    if prof.get("hae_consent"):
        st.caption(
            "Your voice-learning consent is granted, so these modules are actively learning your "
            "communication style."
        )
    else:
        st.info(
            "You have not yet granted Human Authenticity Engine consent, so these modules are running "
            "on standard templates. Enable voice learning any time from My Profile & Settings."
        )
    hae_features = [
        ("Humanized Resume Intelligence", "3 min", "Career storytelling, achievement contextualization and leadership voice preservation in your resume."),
        ("Humanized LinkedIn Content Engine", "3 min", "Thought leadership posts, technical insights and industry commentary in your personal brand voice."),
        ("Humanized Article Generation", "4 min", "Long-form technical articles, industry research and executive thought leadership pieces."),
        ("Humanized Outreach Communication", "3 min", "Recruiter messaging, referral requests and follow-up engagement that sounds like you."),
        ("Voice Intelligence Learning", "2 min", "How the engine learns from your LinkedIn posts, articles, blogs, resumes and interview responses."),
    ]
    render_video_grid(hae_features)

# --------------------------------------------------------------------------
# PAGE: FAQs
# --------------------------------------------------------------------------
elif page == "faqs":
    prof = st.session_state.profile
    is_corporate = prof.get("account_type") != "Individual / Job Seeker"

    st.markdown('<div class="section-title">Frequently asked questions</div>', unsafe_allow_html=True)
    st.caption("Answers are tailored to your account type, role and department.")

    st.markdown('<span class="faq-tag">GENERAL</span>', unsafe_allow_html=True)
    general_faqs = [
        ("How do I reset my password?",
         "Go to Log In, select 'Forgot Password' (coming soon), or contact support@forgeai.example "
         "with your registered email for a manual reset."),
        ("Is my resume and personal data secure?",
         "Yes. Your resume and profile data are used only to generate your personalized readiness "
         "insights and are not shared with third parties without your consent."),
        ("Can I update my profile later?",
         "Yes, go to 'My Profile & Settings' from the left navigation at any time to update your "
         "details or re-upload your resume."),
        ("Which file formats are supported for resume upload?",
         "PDF, DOC and DOCX formats are supported, up to standard file size limits."),
    ]
    for q, a in general_faqs:
        with st.expander(q):
            st.write(a)

    if is_corporate:
        st.markdown('<span class="faq-tag">ORGANIZATION ACCOUNTS</span>', unsafe_allow_html=True)
        corp_faqs = [
            ("How many team members can access our account?",
             "Corporate, Institution, Training Institute and Staffing Firm accounts support multiple "
             "team members under one organization profile. Use 'My Profile & Settings' to review your "
             "account type and contact support to add teammates."),
            ("Can we bulk upload candidate resumes for matching?",
             "Yes, the Candidate Matching module supports uploading multiple candidate resumes against "
             "a selected job requirement."),
            (f"Our department is {prof.get('department', '-')}. Which modules are most relevant to us?",
             "Job Intelligence, Candidate Matching, Gap Analysis, Outreach and Success Tracking are the "
             "core modules for hiring and talent readiness teams."),
            ("How is the Overall Gap Score calculated for our candidate pool?",
             "It aggregates skill-gap severity across all shortlisted candidates for a given job, "
             "weighted by how critical each missing skill is to the role."),
        ]
    else:
        st.markdown('<span class="faq-tag">INDIVIDUAL / JOB SEEKER</span>', unsafe_allow_html=True)
        corp_faqs = [
            ("How is my Readiness Score calculated?",
             "Your Readiness Score combines resume strength, skills match against target roles, "
             "interview simulation performance and learning progress."),
            ("How does the Interview Simulator work?",
             "You select a scenario relevant to your target role, respond by voice or text, and "
             "receive live evaluation across technical approach, communication, problem solving and "
             "leadership."),
            (f"I am a {prof.get('role','-')}. What should I do first?",
             "Start with Resume Studio to optimize your resume, then review your Learning Roadmap for "
             "the highest-priority skill gaps for your target role."),
            ("Will FORGE AI apply to jobs on my behalf?",
             "No. FORGE AI surfaces relevant opportunities and prepares you for them; you choose when "
             "and where to apply."),
        ]
    for q, a in corp_faqs:
        with st.expander(q):
            st.write(a)

    st.markdown('<span class="faq-tag">PROPRIETARY FORGE ENGINES</span>', unsafe_allow_html=True)
    ip_faqs = [
        ("What are FORGE Sim(TM), FORGE Match(TM), FORGE VoiceAI(TM), FORGE Insights(TM) and FORGE Growth(TM)?",
         "These are the five proprietary engines that power the platform, each named after the "
         "intelligence layer it drives:\n\n"
         "- FORGE Match(TM) - the Talent Intelligence engine. Powers Job Intelligence, JD Intelligence "
         "and Candidate Matching by scoring opportunities and candidates against each other.\n\n"
         "- FORGE Sim(TM) - the real-world simulation engine behind the Interview Simulator: production "
         "failures, cloud architecture, leadership, incident response, technical deep-dives and system "
         "design challenges.\n\n"
         "- FORGE VoiceAI(TM) - the Human Authenticity Engine. Learns your natural communication style "
         "and keeps your resume, LinkedIn content, articles and outreach messages sounding like you, "
         "not generic AI output.\n\n"
         "- FORGE Insights(TM) - the career analytics platform behind your Readiness Score, progress "
         "tracking and conversion analytics.\n\n"
         "- FORGE Growth(TM) - the professional branding and visibility framework behind LinkedIn "
         "Branding, content calendars and thought-leadership positioning."),
        ("How is FORGE AI different from a typical job board, resume builder or interview prep tool?",
         "Those tools each solve one isolated piece of the career journey. FORGE AI connects all five "
         "engines into a single continuous ecosystem - discovering opportunities, preparing you, "
         "validating your readiness through simulation, building your visibility, and preserving your "
         "authentic voice throughout, rather than treating each step separately."),
    ]
    for q, a in ip_faqs:
        with st.expander(q):
            st.write(a)

    st.markdown('<span class="faq-tag">HUMAN AUTHENTICITY & VOICE LEARNING</span>', unsafe_allow_html=True)
    hae_consent_status = "granted" if prof.get("hae_consent") else "not granted"
    hae_faqs = [
        ("How does FORGE VoiceAI(TM) learn my writing style?",
         "With your consent, it learns from your resume, LinkedIn posts, articles, blogs and interview "
         "responses to build a Voice Profile, Communication Style Profile and Brand Personality Profile "
         "- used only to keep content generated for you in your own authentic voice."),
        ("Can I opt out of voice learning, or change my mind later?",
         "Yes. Voice-learning consent is entirely optional and can be granted or withdrawn at any time "
         "from 'My Profile & Settings'. Without consent, FORGE AI still works - it simply uses standard "
         "professional templates instead of your personal voice."),
        ("Is Human Authenticity Engine consent currently active on my account?",
         f"Based on your profile, voice-learning consent is currently **{hae_consent_status}**. "
         "You can review or change this any time from 'My Profile & Settings'."),
        ("Does voice learning mean FORGE AI posts or sends things on my behalf without asking?",
         "No. FORGE VoiceAI(TM) only generates drafts in your voice - resumes, posts, articles, outreach "
         "messages. You always review and choose to send or publish."),
    ]
    for q, a in hae_faqs:
        with st.expander(q):
            st.write(a)

    st.markdown('<span class="faq-tag">ACCOUNT & BILLING</span>', unsafe_allow_html=True)
    billing_faqs = [
        ("Is FORGE AI free to use?",
         "Core onboarding, profile setup and the welcome kit are free. Premium modules such as advanced "
         "simulations and analytics may be part of a paid plan depending on your organization's agreement."),
        ("Who do I contact for support?",
         "Email support@forgeai.example or use the 'Help & Support' link in the sidebar."),
    ]
    for q, a in billing_faqs:
        with st.expander(q):
            st.write(a)

# --------------------------------------------------------------------------
# PAGE: MY PROFILE & SETTINGS
# --------------------------------------------------------------------------
elif page == "settings":
    prof = st.session_state.profile
    st.markdown('<div class="section-title">My Profile & Settings</div>', unsafe_allow_html=True)

    tab_profile, tab_docs, tab_prefs, tab_account, tab_integrations = st.tabs(
        ["Profile", "Resume & Documents", "Preferences", "Account Settings", "Integrations"]
    )

    # ---- PROFILE ----
    with tab_profile:
        left, right = st.columns([1, 2])
        with left:
            st.markdown(
                f"""
                <div class="metric-card" style="text-align:center;">
                    <div style="width:72px;height:72px;border-radius:50%;background:linear-gradient(135deg,#5B4CF2,#7C6BFA);
                         display:flex;align-items:center;justify-content:center;color:white;font-size:24px;
                         font-weight:700;margin:0 auto 10px auto;">{initials(prof.get('name','FORGE AI'))}</div>
                    <div style="font-weight:700; font-size:16px; color:#24243B;">{prof.get('name','-')}</div>
                    <div style="color:#8A8FA3; font-size:12px;">{prof.get('role','-')}</div>
                    <div style="color:#8A8FA3; font-size:12px;">{prof.get('country','-')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write("")
            st.caption(f"User ID: {st.session_state.current_user_id}")
        with right:
            st.markdown("##### Contact")
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Email", value=prof.get("email", ""), disabled=True)
                st.text_input("Contact Number", value=prof.get("contact_number", ""), disabled=True)
            with c2:
                st.text_input("Location", value=prof.get("country", ""), disabled=True)
                st.text_input("LinkedIn", value=prof.get("linkedin_url", "") or "Not provided", disabled=True)

            years = prof.get("years_experience", 0)
            role = prof.get("target_role") if prof.get("target_role") not in (None, "", "Not sure yet") else prof.get("role", "professional")
            about_me = (
                f"{prof.get('name','')} is a {role} with {years}+ years of experience"
                f"{' at ' + prof['organization_name'] if prof.get('organization_name') else ''}, "
                f"building scalable solutions and driving measurable outcomes."
            )
            st.markdown("##### About Me")
            st.write(about_me)

            st.markdown("##### Skills")
            skills = prof.get("key_skills", [])
            st.markdown("".join(f'<span class="voice-tag">{s}</span>' for s in skills) or "<span style='color:#8A8FA3;font-size:12px;'>No skills listed yet.</span>", unsafe_allow_html=True)

            st.write("")
            if st.button("Edit Profile", type="primary"):
                st.session_state.active_page = "profile"
                st.rerun()

    # ---- RESUME & DOCUMENTS ----
    with tab_docs:
        st.markdown("##### Documents on File")
        st.write(f"Resume: **{st.session_state.resume_file_name or 'Not uploaded'}**")
        st.write(f"Profile photo: **{st.session_state.photo_file_name or 'Not uploaded'}**")

        st.write("")
        st.markdown("##### Generated Resume")
        st.caption(f"Versions saved via Resume Intelligence Agent: {st.session_state.resume_versions_saved}")
        generated = build_resume_text(get_selected_job())
        st.download_button("Download Latest Generated Resume (.txt)", data=generated,
                            file_name=f"{prof.get('name','resume').replace(' ','_')}_Resume.txt", mime="text/plain")

        st.write("")
        if st.button("Upload a new resume \u2192"):
            st.session_state.active_page = "profile"
            st.rerun()

    # ---- PREFERENCES ----
    with tab_prefs:
        st.markdown("##### Learning & Communication Preferences")
        with st.form("prefs_form"):
            new_learning_mode = st.selectbox("Preferred Learning Mode", LEARNING_MODES,
                                              index=LEARNING_MODES.index(prof.get("learning_mode", LEARNING_MODES[0]))
                                              if prof.get("learning_mode") in LEARNING_MODES else 0)
            new_notify = st.multiselect("Notification Preferences", ["Email", "SMS", "WhatsApp", "In-app only"],
                                         default=prof.get("notify_pref", ["Email"]))
            new_timezone = st.selectbox("Preferred Timezone",
                                         ["IST (India)", "GMT (UK)", "EST (US East)", "PST (US West)", "GST (UAE)", "Other"],
                                         index=0)
            prefs_submit = st.form_submit_button("Save Preferences", type="primary")
        if prefs_submit:
            st.session_state.profile["learning_mode"] = new_learning_mode
            st.session_state.profile["notify_pref"] = new_notify
            st.session_state.profile["timezone"] = new_timezone
            st.success("Preferences updated.")

    # ---- ACCOUNT SETTINGS ----
    with tab_account:
        st.markdown("##### Account Settings")
        settings = st.session_state.account_settings
        settings["email_notifications"] = st.toggle("Email Notifications", value=settings["email_notifications"])
        settings["job_alerts"] = st.toggle("Job Alerts", value=settings["job_alerts"])
        settings["weekly_reports"] = st.toggle("Weekly Reports", value=settings["weekly_reports"])
        settings["profile_visibility"] = st.toggle("Profile Visibility (Public)", value=settings["profile_visibility"])
        settings["two_factor_auth"] = st.toggle("Two Factor Authentication", value=settings["two_factor_auth"])

        st.write("")
        hae_status = "Granted" if prof.get("hae_consent") else "Not granted"
        st.markdown("##### Consent")
        st.write(f"Human Authenticity Engine (FORGE VoiceAI\u2122) voice-learning consent: **{hae_status}**")
        if not prof.get("hae_consent"):
            if st.button("Grant Human Authenticity Engine consent"):
                st.session_state.profile["hae_consent"] = True
                st.success("Voice-learning consent granted.")
                st.rerun()
        else:
            if st.button("Withdraw Human Authenticity Engine consent"):
                st.session_state.profile["hae_consent"] = False
                st.info("Voice-learning consent withdrawn.")
                st.rerun()

    # ---- INTEGRATIONS ----
    with tab_integrations:
        st.markdown("##### Connected Accounts")
        for name in ["LinkedIn", "Google Calendar", "Slack"]:
            connected = st.session_state.integrations.get(name, False)
            icol1, icol2 = st.columns([3, 1])
            with icol1:
                st.write(f"**{name}**")
                st.caption("Connected" if connected else "Not connected")
            with icol2:
                if st.button("Disconnect" if connected else "Connect", key=f"integ_{name}"):
                    st.session_state.integrations[name] = not connected
                    st.rerun()

# --------------------------------------------------------------------------
# AUTO-SAVE
# Persists the signed-in candidate's full profile and progress to disk on
# every rerun, so nothing is lost between visits and a restart of the app
# does not clear their work.
# --------------------------------------------------------------------------
if st.session_state.get("authenticated") and st.session_state.get("current_user_id"):
    save_user_data(st.session_state.current_user_id)

st.write("")
st.divider()
st.caption(f"{APP_NAME}(TM) - {APP_TAGLINE}. Your profile and progress are saved automatically and restored the next time you log in.")
