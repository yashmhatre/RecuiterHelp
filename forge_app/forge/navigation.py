"""Information architecture for FORGE AI.

The original sidebar was twenty flat rows named after the system's internals: "JD Intelligence
Agent", "Human Authenticity Engine", "Performance Evaluator Agent". Nobody opens an app wanting
the JD Intelligence Agent. They want to know what a job needs. A navigation list that mirrors
the architecture diagram makes the reader translate from the system's vocabulary into their own,
every single time, and gives them no sense of what to do first.

Two changes here:

**Named for the task, not the component.** Each page keeps its internal key, so no page code
changes, but gets a label describing what a person came to do. The FORGE agent names are not
lost -- they appear as the subtitle on each page, which is where a product name belongs.

**Grouped into a journey.** The groups are ordered the way the work actually happens, and they
differ by account type because a recruitment desk and a job seeker are doing genuinely different
jobs, not the same job with different labels.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavEntry:
    key: str          #: internal page key; unchanged, so page code is untouched
    label: str        #: what the person is trying to do
    agent: str = ""   #: the FORGE agent name, shown as the page subtitle


@dataclass(frozen=True)
class NavGroup:
    title: str
    entries: tuple[NavEntry, ...]


# ---------------------------------------------------------------------------
# Getting started: identical for everyone, and the only part that is a sequence
# ---------------------------------------------------------------------------

_ONBOARDING = NavGroup(
    "Get started",
    (
        NavEntry("auth", "Sign in"),
        NavEntry("profile", "Your details"),
        NavEntry("welcome", "Welcome kit"),
    ),
)

_HELP = NavGroup(
    "Help",
    (
        NavEntry("videos", "Tour"),
        NavEntry("faqs", "Questions"),
        NavEntry("settings", "Settings"),
    ),
)


# ---------------------------------------------------------------------------
# Job seeker: find work, get ready, get seen, track it
# ---------------------------------------------------------------------------

SEEKER_NAV: tuple[NavGroup, ...] = (
    _ONBOARDING,
    NavGroup("Overview", (NavEntry("dashboard", "Dashboard"),)),
    NavGroup(
        "Find work",
        (
            NavEntry("job_hunter", "Browse jobs", "Job Hunter Agent"),
            NavEntry("jd_intelligence", "Understand a job", "JD Intelligence Agent"),
            NavEntry("candidate_matching", "My applications", "Candidate Matching Agent"),
        ),
    ),
    NavGroup(
        "Get ready",
        (
            NavEntry("resume_intelligence", "Build my resume", "Resume Intelligence Agent"),
            NavEntry("gap_analysis", "What I'm missing", "Gap Analysis Agent"),
            NavEntry("learning_dev", "Learning plan", "Learning & Development Agent"),
            NavEntry("simulation", "Practise interviews", "FORGE Simulation Agent"),
            NavEntry("performance_eval", "How I'm doing", "Performance Evaluator Agent"),
        ),
    ),
    NavGroup(
        "Get noticed",
        (
            NavEntry("human_authenticity", "My writing voice", "Human Authenticity Engine"),
            NavEntry("linkedin_branding", "LinkedIn posts", "LinkedIn Branding Agent"),
            NavEntry("outreach", "Reach out", "Outreach Agent"),
        ),
    ),
    NavGroup(
        "Track",
        (
            NavEntry("success_tracking", "My progress", "Success Tracking Agent"),
            NavEntry("career_intelligence", "Market insight", "Career Intelligence Agent"),
        ),
    ),
    _HELP,
)


# ---------------------------------------------------------------------------
# Recruitment desk: leads arrive, candidates go out, results come back
# ---------------------------------------------------------------------------

DESK_NAV: tuple[NavGroup, ...] = (
    _ONBOARDING,
    NavGroup("Overview", (NavEntry("dashboard", "Dashboard"),)),
    NavGroup(
        "Incoming work",
        (
            # First in the group on purpose: this is where a desk's day starts.
            NavEntry("email_agent", "Screen the inbox", "Email Agent"),
            NavEntry("job_hunter", "Job leads", "Job Hunter Agent"),
            NavEntry("jd_intelligence", "Understand a job", "JD Intelligence Agent"),
        ),
    ),
    NavGroup(
        "Placing people",
        (
            NavEntry("candidate_matching", "Match candidates", "Candidate Matching Agent"),
            NavEntry("resume_intelligence", "Format a resume", "Resume Intelligence Agent"),
            NavEntry("outreach", "Write to clients", "Outreach Agent"),
        ),
    ),
    NavGroup(
        "Results",
        (
            NavEntry("success_tracking", "Placements", "Success Tracking Agent"),
            NavEntry("career_intelligence", "Market insight", "Career Intelligence Agent"),
        ),
    ),
    _HELP,
)


def nav_for(is_recruiter: bool) -> tuple[NavGroup, ...]:
    return DESK_NAV if is_recruiter else SEEKER_NAV


def entries_for(is_recruiter: bool) -> list[NavEntry]:
    return [entry for group in nav_for(is_recruiter) for entry in group.entries]


def lookup(key: str, is_recruiter: bool) -> NavEntry | None:
    return next((e for e in entries_for(is_recruiter) if e.key == key), None)
