"""FORGE Match™ scoring, implementing the client's own specification.

Taken from `Forge_AI/forge-skills/forge-candidate-matching/SKILL.md` (Agent 3 of the FORGE AI
architecture). That document is client reference material and is never modified; this module is
our implementation of it.

Why adopt it rather than keep our own 0-1 score: downstream FORGE skills consume this by name.
`forge-outreach-agent`'s submission email template literally prints
``FORGE Match™ Score: XX/100`` and branches on the band label, so a score on any other scale
cannot feed it.

What the specification pins down, and what it leaves to us:

    pinned    the six dimensions and their maxima, the four band cutoffs, the signal enum,
              the bridge positioning pairs, and "always find the bridge before calling a gap
              insurmountable"
    open      how points are divided *within* a dimension. No per-skill formula, no partial
              credit rule, no required-versus-preferred multiplier. Those choices are ours and
              are commented where they are made.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "DIMENSIONS",
    "BANDS",
    "MIN_SUBMIT_SCORE",
    "BRIDGE_PAIRS",
    "DimensionScore",
    "MatchReport",
    "score_candidate",
    "band_for",
    "find_bridges",
]

#: Dimension -> maximum points. Sums to 100. Verbatim from the specification's
#: "Dimensions Scored (100 points total)" table.
DIMENSIONS: dict[str, int] = {
    "Core Technical Skills": 40,
    "Experience Depth": 20,
    "Seniority Alignment": 15,
    "Certifications": 10,
    "Soft Skills / Leadership": 10,
    "Location / Work Auth": 5,
}

#: (minimum score, signal, label, recommendation). Ordered high to low.
#: The signal strings are the specification's enum: strong|good|partial|stretch|poor.
BANDS: tuple[tuple[int, str, str, str], ...] = (
    (85, "strong", "Strong Match", "Submit immediately"),
    (70, "good", "Good Match", "Submit with positioning notes"),
    (55, "partial", "Partial Match", "Submit with bridge narrative"),
    (40, "stretch", "Stretch Match", "Develop before submitting"),
    (0, "poor", "Poor Match", "Do not submit"),
)

#: Below this, the specification says "Do not submit". Replaces our old 0-1 MIN_SCORE of 0.30.
MIN_SUBMIT_SCORE = 40

#: Bridge Positioning Protocol, verbatim from the specification. Adjacent technologies where
#: experience in one genuinely transfers to the other. This is client domain knowledge we would
#: not have invented, and the rule attached to it is explicit: "Always find the bridge before
#: calling a gap insurmountable."
BRIDGE_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("azure data factory", "aws glue", "managed ETL bridge"),
    ("aws glue", "azure data factory", "managed ETL bridge"),
    ("databricks", "spark", "Databricks is Spark; transfers to any Spark-on-cloud role"),
    ("spark", "databricks", "Spark experience transfers to Databricks regardless of cloud"),
    ("pyspark", "spark", "PySpark is Spark"),
    ("sql server", "azure sql", "on-prem SQL Server to Azure SQL / Synapse"),
    ("sql server", "synapse", "on-prem SQL Server to Azure SQL / Synapse"),
    ("tensorflow", "pytorch", "deep learning framework bridge"),
    ("pytorch", "tensorflow", "deep learning framework bridge"),
)

#: Seniority ladder, from forge-jd-intelligence's enum. Index distance drives the alignment score.
SENIORITY_LADDER = ("entry", "mid", "senior", "staff", "principal", "executive")

#: Words in a profile summary that evidence leadership. The specification says soft skills are
#: "Inferred from resume language" and gives no list, so this is ours.
_LEADERSHIP_MARKERS = (
    "led", "lead", "mentor", "managed", "manage", "owned", "architect", "stakeholder",
    "cross-functional", "collaborat", "presented", "drove", "coordinated", "principal",
    "spearhead", "championed", "directed", "supervis", "coach",
)


@dataclass(frozen=True)
class DimensionScore:
    name: str
    score: float
    maximum: int
    note: str

    @property
    def fraction(self) -> float:
        return self.score / self.maximum if self.maximum else 0.0


@dataclass
class MatchReport:
    """The object `forge-candidate-matching` specifies, field for field."""

    candidate: str
    role: str
    overall_score: int
    signal: str
    dimension_scores: dict[str, float] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    gaps: list[dict[str, str]] = field(default_factory=list)
    bridge_strategy: str = ""
    recommendation: str = ""
    recruiter_talking_points: list[str] = field(default_factory=list)
    #: Ours, not FORGE's: the per-dimension notes a reviewer needs.
    dimension_detail: list[DimensionScore] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate,
            "role": self.role,
            "overall_score": self.overall_score,
            "signal": self.signal,
            "dimension_scores": self.dimension_scores,
            "strengths": self.strengths,
            "gaps": self.gaps,
            "bridge_strategy": self.bridge_strategy,
            "recommendation": self.recommendation,
            "recruiter_talking_points": self.recruiter_talking_points,
        }


def band_for(score: float) -> tuple[str, str, str]:
    """Return (signal, label, recommendation) for a 0-100 score."""
    for minimum, signal, label, recommendation in BANDS:
        if score >= minimum:
            return signal, label, recommendation
    return BANDS[-1][1], BANDS[-1][2], BANDS[-1][3]


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9+#./ ]", " ", (value or "").lower()).strip()


def _has(skill: str, held: set[str], haystack: str) -> bool:
    """Whether a profile holds a skill, by exact match or by its title and summary text.

    Substring on the haystack is deliberate: a requirement says "data modeling" where a profile
    says "dimensional data modeling", and set equality alone would miss it.
    """
    s = _normalise(skill)
    return bool(s) and (s in held or s in haystack)


def find_bridges(missing: set[str], held: set[str], haystack: str) -> list[str]:
    """Adjacent experience that covers a missing requirement.

    The specification is emphatic that this runs before a gap is called fatal, because a
    candidate with Azure Data Factory is not unqualified for an AWS Glue role.
    """
    bridges: list[str] = []
    for want in sorted(missing):
        w = _normalise(want)
        for source, target, why in BRIDGE_PAIRS:
            if target in w and _has(source, held, haystack):
                bridges.append(f"{want}: has {source} ({why})")
                break
    return bridges


# ---------------------------------------------------------------------------
# The six dimensions
# ---------------------------------------------------------------------------


def _core_technical(must_have, preferred, held, haystack) -> DimensionScore:
    """40 points. The specification fixes the maximum but not the split inside it.

    Ours: must-haves carry 80% of the dimension and preferred the remaining 20%, because a
    client email told us plainly that must-haves decide who may be put forward at all.
    """
    maximum = DIMENSIONS["Core Technical Skills"]
    if not must_have and not preferred:
        return DimensionScore("Core Technical Skills", maximum * 0.5, maximum,
                              "No skills stated in the requirement")

    must_held = {s for s in must_have if _has(s, held, haystack)}
    pref_held = {s for s in preferred if _has(s, held, haystack)}

    must_part = (len(must_held) / len(must_have)) if must_have else 1.0
    pref_part = (len(pref_held) / len(preferred)) if preferred else 1.0
    score = maximum * (0.8 * must_part + 0.2 * pref_part) if must_have else maximum * pref_part

    missing = sorted(set(must_have) - must_held)
    note = f"{len(must_held)}/{len(must_have)} must-have" if must_have else "no must-haves stated"
    if preferred:
        note += f", {len(pref_held)}/{len(preferred)} preferred"
    if missing:
        note += f"; missing {', '.join(missing)}"
    return DimensionScore("Core Technical Skills", round(score, 1), maximum, note)


def _experience_depth(required_years, candidate_years) -> DimensionScore:
    """20 points. Years plus domain relevance, per the specification."""
    maximum = DIMENSIONS["Experience Depth"]
    if required_years is None:
        return DimensionScore("Experience Depth", maximum * 0.7, maximum,
                              f"{candidate_years:g} yrs; no requirement stated")

    ratio = candidate_years / required_years if required_years else 1.0
    if ratio >= 1.0:
        score = maximum
        note = f"{candidate_years:g} yrs meets {required_years:g}+"
    elif ratio >= 0.8:
        # Within a year of the ask is a positioning question, not a disqualification.
        score = maximum * 0.75
        note = f"{candidate_years:g} yrs against {required_years:g}+ (close)"
    else:
        score = maximum * max(0.0, ratio * 0.6)
        note = f"{candidate_years:g} yrs against {required_years:g}+ (short)"
    return DimensionScore("Experience Depth", round(score, 1), maximum, note)


def _seniority_alignment(required: str | None, candidate: str | None) -> DimensionScore:
    """15 points. Distance on the ladder, penalising over-qualification less than under."""
    maximum = DIMENSIONS["Seniority Alignment"]
    r = (required or "").strip().lower()
    c = (candidate or "").strip().lower()
    if r not in SENIORITY_LADDER or c not in SENIORITY_LADDER:
        return DimensionScore("Seniority Alignment", maximum * 0.7, maximum,
                              "Seniority not stated on both sides")

    distance = SENIORITY_LADDER.index(c) - SENIORITY_LADDER.index(r)
    if distance == 0:
        score, note = maximum, f"{c} matches {r}"
    elif distance > 0:
        # Over-qualified: a real concern but not a mismatch.
        score = maximum * (0.8 if distance == 1 else 0.55)
        note = f"{c} above {r} by {distance}"
    else:
        score = maximum * (0.55 if distance == -1 else 0.2)
        note = f"{c} below {r} by {abs(distance)}"
    return DimensionScore("Seniority Alignment", round(score, 1), maximum, note)


def _certifications(required: list[str], held: set[str], haystack: str) -> DimensionScore:
    """10 points. Full marks when none are asked for; absence is not evidence against."""
    maximum = DIMENSIONS["Certifications"]
    if not required:
        return DimensionScore("Certifications", maximum, maximum, "None required")
    got = {c for c in required if _has(c, held, haystack)}
    score = maximum * (len(got) / len(required))
    return DimensionScore("Certifications", round(score, 1), maximum,
                          f"{len(got)}/{len(required)}: {', '.join(sorted(got)) or 'none held'}")


def _soft_skills(summary: str, title: str) -> DimensionScore:
    """10 points, "inferred from resume language" per the specification.

    Weak evidence by nature, so it starts at half marks and climbs. Scoring a profile to zero
    on vocabulary would be unfair to a terse CV.
    """
    maximum = DIMENSIONS["Soft Skills / Leadership"]
    text = f"{title} {summary}".lower()
    hits = {m for m in _LEADERSHIP_MARKERS if m in text}
    score = maximum * min(1.0, 0.5 + 0.125 * len(hits))
    note = f"signals: {', '.join(sorted(hits)[:4])}" if hits else "no leadership language in profile"
    return DimensionScore("Soft Skills / Leadership", round(score, 1), maximum, note)


def _location_auth(compatible: bool, candidate_location, work_auth) -> DimensionScore:
    """5 points. The smallest dimension, because it is usually negotiable."""
    maximum = DIMENSIONS["Location / Work Auth"]
    if not compatible:
        return DimensionScore("Location / Work Auth", 0.0, maximum,
                              f"{candidate_location or 'location unknown'} does not fit")
    score = maximum if work_auth else maximum * 0.8
    note = candidate_location or "no location constraint"
    if work_auth:
        note += f"; {work_auth}"
    return DimensionScore("Location / Work Auth", round(score, 1), maximum, note)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def score_candidate(
    profile: dict,
    requirement: dict,
    *,
    location_compatible: bool = True,
) -> MatchReport:
    """Score one profile against one requirement, producing a FORGE Match report.

    ``requirement`` uses the forge-jd-intelligence field names: role_title, seniority,
    must_have_skills, preferred_skills, certifications, experience_requirements.
    """
    held = {_normalise(s) for s in (profile.get("skills") or []) if s}
    haystack = _normalise(f"{profile.get('title', '')} {profile.get('summary', '')}")

    must_have = [s for s in (requirement.get("must_have_skills") or []) if s]
    preferred = [s for s in (requirement.get("preferred_skills") or []) if s]
    certs = [c for c in (requirement.get("certifications") or []) if c]
    experience = requirement.get("experience_requirements") or {}
    required_years = experience.get("total_years")

    dimensions = [
        _core_technical(must_have, preferred, held, haystack),
        _experience_depth(required_years, float(profile.get("years_experience") or 0)),
        _seniority_alignment(requirement.get("seniority"), profile.get("seniority")),
        _certifications(certs, held, haystack),
        _soft_skills(str(profile.get("summary") or ""), str(profile.get("title") or "")),
        _location_auth(location_compatible, profile.get("location"), profile.get("work_auth")),
    ]

    overall = int(round(sum(d.score for d in dimensions)))
    signal, label, recommendation = band_for(overall)

    must_held = {s for s in must_have if _has(s, held, haystack)}
    missing = set(must_have) - must_held
    bridges = find_bridges(missing, held, haystack)

    strengths = [f"Holds {s}" for s in sorted(must_held)[:4]]
    if not required_years or float(profile.get("years_experience") or 0) >= (required_years or 0):
        strengths.append(f"{float(profile.get('years_experience') or 0):g} years of experience")

    gaps = [
        {"requirement": s, "type": "Required",
         "bridge": next((b for b in bridges if b.startswith(f"{s}:")), "")}
        for s in sorted(missing)
    ]
    gaps += [
        {"requirement": s, "type": "Preferred", "bridge": ""}
        for s in sorted(set(preferred) - {p for p in preferred if _has(p, held, haystack)})[:3]
    ]

    bridge_strategy = "; ".join(bridges) if bridges else (
        "No adjacent experience found for the missing requirements" if missing else
        "Meets every stated must-have"
    )

    talking_points = []
    if strengths:
        talking_points.append(f"Lead with: {strengths[0]}")
    if bridges:
        talking_points.append(f"Gap mitigation: {bridges[0]}")
    elif missing:
        talking_points.append(f"Gap to raise: {', '.join(sorted(missing)[:2])}")
    best = max(dimensions, key=lambda d: d.fraction)
    talking_points.append(f"Differentiator: {best.name} - {best.note}")

    return MatchReport(
        candidate=str(profile.get("name", "")),
        role=str(requirement.get("role_title") or "the role"),
        overall_score=overall,
        signal=signal,
        dimension_scores={d.name: d.score for d in dimensions},
        strengths=strengths,
        gaps=gaps,
        bridge_strategy=bridge_strategy,
        recommendation=f"{label} - {recommendation}",
        recruiter_talking_points=talking_points,
        dimension_detail=dimensions,
    )
