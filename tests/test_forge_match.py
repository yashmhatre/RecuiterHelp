"""Tests for FORGE Match™ scoring.

The specification lives in `Forge_AI/forge-skills/forge-candidate-matching/SKILL.md`, which is
client reference material and is never modified. These tests encode what that document pins
down, so a change to our implementation that drifts from the client's contract fails here.

What the specification fixes, and therefore what is asserted strictly:
    the six dimensions and their maxima summing to 100
    the four band cutoffs (85 / 70 / 55 / 40) and the signal enum
    the bridge positioning pairs
    "Always find the bridge before calling a gap insurmountable"

What it leaves open, and is therefore asserted only for sane behaviour rather than exact value:
    how points divide *within* a dimension.
"""

from __future__ import annotations

import pytest

from prototype.forge_match import (
    BANDS,
    DIMENSIONS,
    MIN_SUBMIT_SCORE,
    band_for,
    find_bridges,
    score_candidate,
)


def requirement(**overrides) -> dict:
    base = {
        "role_title": "Business Intelligence Consultant",
        "seniority": "senior",
        "must_have_skills": ["Power BI", "Databricks", "SQL", "AI/LLM Prompting"],
        "preferred_skills": ["DAX", "Power Query", "Spark"],
        "certifications": [],
        "experience_requirements": {"total_years": 5},
    }
    base.update(overrides)
    return base


def profile(**overrides) -> dict:
    base = {
        "name": "Test Candidate", "title": "Data Engineer", "seniority": "senior",
        "skills": ["power bi", "databricks", "sql", "ai/llm prompting"],
        "years_experience": 6.0, "location": "Pune", "summary": "Builds data platforms.",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# The parts the specification pins down
# ---------------------------------------------------------------------------


def test_the_six_dimensions_sum_to_one_hundred():
    assert sum(DIMENSIONS.values()) == 100


def test_the_dimension_maxima_are_the_specified_ones():
    assert DIMENSIONS == {
        "Core Technical Skills": 40,
        "Experience Depth": 20,
        "Seniority Alignment": 15,
        "Certifications": 10,
        "Soft Skills / Leadership": 10,
        "Location / Work Auth": 5,
    }


@pytest.mark.parametrize(
    ("score", "signal"),
    [
        (100, "strong"), (85, "strong"),
        (84, "good"), (70, "good"),
        (69, "partial"), (55, "partial"),
        (54, "stretch"), (40, "stretch"),
        (39, "poor"), (0, "poor"),
    ],
)
def test_band_cutoffs_match_the_specification(score: int, signal: str):
    """The cutoffs are 85 / 70 / 55 / 40 and the boundaries are inclusive from below."""
    assert band_for(score)[0] == signal


def test_the_signal_enum_is_exactly_the_specified_five():
    assert {signal for _, signal, _, _ in BANDS} == {
        "strong", "good", "partial", "stretch", "poor"
    }


def test_the_submission_floor_is_forty():
    """The specification's "Do not submit" band is below 40."""
    assert MIN_SUBMIT_SCORE == 40
    assert band_for(MIN_SUBMIT_SCORE - 1)[0] == "poor"


def test_every_dimension_is_scored_and_reported():
    """The specification: "All 6 dimensions always scored with notes"."""
    report = score_candidate(profile(), requirement())

    assert set(report.dimension_scores) == set(DIMENSIONS)
    assert all(d.note for d in report.dimension_detail), "every dimension needs a note"


def test_no_dimension_can_exceed_its_maximum():
    generous = profile(
        skills=["power bi", "databricks", "sql", "ai/llm prompting", "dax", "power query", "spark"],
        years_experience=25.0,
        summary="Led, mentored, managed, architected, drove, coordinated, spearheaded teams.",
    )

    for d in score_candidate(generous, requirement()).dimension_detail:
        assert d.score <= d.maximum, f"{d.name} scored {d.score} over {d.maximum}"


def test_the_report_carries_every_field_the_contract_names():
    """forge-candidate-matching's JSON block, key for key."""
    data = score_candidate(profile(), requirement()).as_dict()

    assert set(data) == {
        "candidate", "role", "overall_score", "signal", "dimension_scores", "strengths",
        "gaps", "bridge_strategy", "recommendation", "recruiter_talking_points",
    }


# ---------------------------------------------------------------------------
# Dimensions behave sensibly
# ---------------------------------------------------------------------------


def test_holding_every_must_have_beats_holding_none():
    full = score_candidate(profile(), requirement()).overall_score
    none = score_candidate(profile(skills=["cobol"]), requirement()).overall_score

    assert full > none
    assert full >= 85, "a complete technical match should reach Strong"


def test_a_candidate_with_no_relevant_skills_lands_below_the_submission_floor():
    """The five non-technical dimensions must not float an unqualified candidate into
    submittable territory on their own."""
    irrelevant = profile(
        skills=["cobol", "fortran"], seniority="entry", years_experience=0.5,
        location="Reykjavik", summary="",
    )

    report = score_candidate(irrelevant, requirement())

    assert report.overall_score < MIN_SUBMIT_SCORE, report.dimension_scores
    assert report.signal == "poor"


def test_meeting_the_year_requirement_scores_full_experience_depth():
    report = score_candidate(profile(years_experience=7.0), requirement())

    assert report.dimension_scores["Experience Depth"] == DIMENSIONS["Experience Depth"]


def test_being_slightly_short_on_years_is_not_treated_as_a_failure():
    """4.5 years against "5+" is a positioning question, not a disqualification."""
    short = score_candidate(profile(years_experience=4.5), requirement())
    very_short = score_candidate(profile(years_experience=1.0), requirement())

    assert short.dimension_scores["Experience Depth"] > very_short.dimension_scores["Experience Depth"]
    assert short.dimension_scores["Experience Depth"] >= DIMENSIONS["Experience Depth"] * 0.7


def test_seniority_exactly_matching_scores_full():
    report = score_candidate(profile(seniority="senior"), requirement(seniority="senior"))

    assert report.dimension_scores["Seniority Alignment"] == DIMENSIONS["Seniority Alignment"]


@pytest.mark.parametrize(
    ("over_level", "under_level", "distance"),
    [("staff", "mid", 1), ("principal", "entry", 2)],
)
def test_being_under_level_costs_more_than_being_over_level(over_level, under_level, distance):
    """At the SAME distance from the target. Over-qualification is a conversation; being two
    levels short is a different matter.
    """
    key = "Seniority Alignment"
    over = score_candidate(profile(seniority=over_level), requirement(seniority="senior"))
    under = score_candidate(profile(seniority=under_level), requirement(seniority="senior"))

    assert over.dimension_scores[key] > under.dimension_scores[key], (
        f"{over_level} (+{distance}) should beat {under_level} (-{distance})"
    )


def test_certifications_score_full_when_none_are_required():
    """Absence of a certification nobody asked for is not evidence against a candidate."""
    report = score_candidate(profile(), requirement(certifications=[]))

    assert report.dimension_scores["Certifications"] == DIMENSIONS["Certifications"]


def test_a_required_certification_the_candidate_lacks_costs_points():
    without = score_candidate(profile(), requirement(certifications=["DP-203", "AZ-900"]))
    with_it = score_candidate(
        profile(skills=[*profile()["skills"], "dp-203", "az-900"]),
        requirement(certifications=["DP-203", "AZ-900"]),
    )

    assert with_it.dimension_scores["Certifications"] > without.dimension_scores["Certifications"]


def test_leadership_language_raises_the_soft_skills_score():
    """The specification says soft skills are "inferred from resume language"."""
    plain = score_candidate(profile(summary="Wrote ETL jobs."), requirement())
    leaderly = score_candidate(
        profile(summary="Led the platform team, mentored engineers, drove stakeholder alignment."),
        requirement(),
    )

    key = "Soft Skills / Leadership"
    assert leaderly.dimension_scores[key] > plain.dimension_scores[key]


def test_a_terse_profile_is_not_scored_to_zero_on_soft_skills():
    """Weak evidence by nature; a short CV should not be punished as though it proved absence."""
    report = score_candidate(profile(summary=""), requirement())

    assert report.dimension_scores["Soft Skills / Leadership"] > 0


def test_an_incompatible_location_zeroes_only_that_dimension():
    report = score_candidate(profile(), requirement(), location_compatible=False)

    assert report.dimension_scores["Location / Work Auth"] == 0
    assert report.overall_score > 0, "one bad dimension must not zero the whole score"


# ---------------------------------------------------------------------------
# Bridge positioning, the client's own IP
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("missing", "held", "expect"),
    [
        ("AWS Glue", "azure data factory", "managed ETL"),
        ("Databricks", "spark", "Spark"),
        ("Azure SQL", "sql server", "SQL Server"),
        ("PyTorch", "tensorflow", "framework"),
    ],
)
def test_the_documented_adjacency_pairs_are_found(missing: str, held: str, expect: str):
    bridges = find_bridges({missing}, {held}, "")

    assert bridges, f"no bridge from {held} to {missing}"
    assert expect.lower() in bridges[0].lower()


def test_an_unrelated_skill_is_not_bridged():
    """A bridge that fires on anything is worse than no bridge: it hides real gaps."""
    assert find_bridges({"Kubernetes"}, {"microsoft word"}, "") == []


def test_a_bridge_is_attempted_before_a_gap_is_called_fatal():
    """The specification: "Always find the bridge before calling a gap insurmountable"."""
    report = score_candidate(
        profile(skills=["azure data factory", "sql", "power bi", "ai/llm prompting"]),
        requirement(must_have_skills=["AWS Glue", "SQL", "Power BI", "AI/LLM Prompting"]),
    )

    assert "managed ETL" in report.bridge_strategy
    aws_gap = next((g for g in report.gaps if "glue" in g["requirement"].lower()), None)
    assert aws_gap is not None
    assert aws_gap["bridge"], "the gap should carry its bridge, not just be listed"


def test_a_full_match_says_so_rather_than_inventing_a_bridge():
    report = score_candidate(profile(), requirement())

    assert "Meets every stated must-have" in report.bridge_strategy


# ---------------------------------------------------------------------------
# Recruiter-facing output
# ---------------------------------------------------------------------------


def test_talking_points_are_produced_for_a_real_match():
    """forge-outreach-agent consumes these in submission emails."""
    report = score_candidate(profile(), requirement())

    assert len(report.recruiter_talking_points) >= 2
    assert all(p.strip() for p in report.recruiter_talking_points)


def test_a_poor_match_recommendation_is_unambiguous():
    """The specification: "Poor match recommendations are clear and never buried"."""
    report = score_candidate(
        profile(skills=["cobol"], seniority="entry", years_experience=0.5, summary=""),
        requirement(),
    )

    assert "Do not submit" in report.recommendation


def test_gaps_record_whether_they_were_required_or_preferred():
    report = score_candidate(profile(skills=["sql"]), requirement())

    types = {g["type"] for g in report.gaps}
    assert "Required" in types
