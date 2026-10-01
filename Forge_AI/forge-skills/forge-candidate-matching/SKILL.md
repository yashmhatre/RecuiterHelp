---
name: forge-candidate-matching
description: >
  FORGE AI™ Candidate Matching Agent (FORGE Match™) — score any candidate profile against a job
  description to produce a structured match report with overall match percentage, skill-by-skill
  breakdown, readiness score, opportunity ranking, and placement recommendation. Use this skill
  whenever a user wants to know how well a candidate fits a role, compare multiple candidates to
  a JD, score a resume against a job posting, or generate a client-ready talent match report for
  Exeliq. Trigger on: "match this candidate to the JD", "how does X fit this role", "score this
  resume", "which candidate is best for this role", "generate a match report", "compare candidates",
  "run a FORGE match", "what's the fit score". Also trigger when a resume and JD are both present
  and the user hasn't explicitly asked for a match — offer to run one. Part of the FORGE AI™
  platform for Exeliq Consulting.
compatibility: "claude.ai, Claude Code, API — all surfaces"
---

# FORGE AI™ — Candidate Matching Agent (FORGE Match™)

Agent 3 of the FORGE AI Multi-Agent Architecture.

---

## Input Requirements

| Input | Required | Source |
|-------|----------|--------|
| Candidate profile / resume | ✅ Yes | Paste, upload, or describe |
| Job description | ✅ Yes | Paste, or use forge-jd-intelligence output |
| Candidate work authorization | Optional | H1B, GC, USC, EAD, etc. |
| Target location | Optional | For geography fit scoring |

---

## FORGE Match™ Scoring Model

### Dimensions Scored (100 points total)

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Core Technical Skills | 40 pts | Must-have tools, platforms, languages |
| Experience Depth | 20 pts | Years + domain relevance |
| Seniority Alignment | 15 pts | Level match (IC, Manager, Director) |
| Certifications | 10 pts | Required and preferred certs |
| Soft Skills / Leadership | 10 pts | Inferred from resume language |
| Location / Work Auth | 5 pts | Geography and authorization fit |

### Score Interpretation

| Score | Signal | Recommendation |
|-------|--------|---------------|
| 85–100 | 🟢 Strong Match | Submit immediately |
| 70–84 | 🟡 Good Match | Submit with positioning notes |
| 55–69 | 🟠 Partial Match | Submit with bridge narrative |
| 40–54 | 🔴 Stretch Match | Develop before submitting |
| <40 | ⛔ Poor Match | Do not submit |

---

## Output Format — FORGE Match Report™

```
## FORGE Match Report™
### Candidate: [Name]
### Role: [Title] at [Company]
### Match Date: [Date]

---

**Overall Match Score: XX/100** 🟢/🟡/🟠/🔴

---

### Score Breakdown

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| Core Technical Skills | XX | 40 | [key matches and gaps] |
| Experience Depth | XX | 20 | [years, domain relevance] |
| Seniority Alignment | XX | 15 | [level match assessment] |
| Certifications | XX | 10 | [matched / missing certs] |
| Soft Skills / Leadership | XX | 10 | [signals found] |
| Location / Work Auth | XX | 5 | [fit assessment] |

---

### ✅ Strengths (Top Matches)
- [Skill/experience that strongly aligns]
- [Skill/experience that strongly aligns]

### ⚠️ Gaps (Missing Requirements)
- [Gap 1 — Required / Preferred]
- [Gap 2 — Required / Preferred]

### 🎯 Bridge Positioning Strategy
[2–3 sentences on how to position the candidate's transferable strengths
to compensate for any gaps. E.g., Azure → GCP bridge language.]

### 📋 Submission Recommendation
[Clear recommendation: Submit / Submit with notes / Develop first / Do not submit]

### 📝 Recruiter Talking Points
- [Point 1: strength to lead with]
- [Point 2: gap mitigation]
- [Point 3: differentiator]
```

---

## Multi-Candidate Comparison

When comparing multiple candidates to one JD, produce a comparison table first:

```
| Candidate | Score | Strengths | Top Gap | Recommendation |
|-----------|-------|-----------|---------|----------------|
| Candidate A | 88 | ... | ... | Submit |
| Candidate B | 71 | ... | ... | Submit with notes |
| Candidate C | 52 | ... | ... | Develop first |
```

Then provide individual full reports on request.

---

## Bridge Positioning Protocol

This is a core FORGE AI™ differentiator. When a candidate has adjacent but not exact skills:

**Examples:**
- Azure Data Factory experience → position for AWS Glue roles (managed ETL bridge)
- Databricks (Spark) → positions for any Spark-on-cloud role regardless of cloud provider
- On-prem SQL Server → positions for Azure SQL / Synapse with cloud migration narrative
- TensorFlow → PyTorch bridge (framework-agnostic ML framing)

Always find the bridge before calling a gap insurmountable.

---

## Multi-Surface Behavior

**Claude.ai:** Full markdown match report in chat.

**Claude Code / API:** JSON output available:
```json
{
  "candidate": "",
  "role": "",
  "overall_score": 0,
  "signal": "strong|good|partial|stretch|poor",
  "dimension_scores": {},
  "strengths": [],
  "gaps": [],
  "bridge_strategy": "",
  "recommendation": "",
  "recruiter_talking_points": []
}
```

---

## Downstream Handoffs

- **→ forge-gap-analysis**: Deep-dive on specific gaps
- **→ forge-resume-intelligence**: Tailor resume based on match gaps
- **→ forge-career-roadmap**: Build development plan for gaps
- **→ forge-outreach-agent**: Draft submission email using talking points
