---
name: forge-gap-analysis
description: >
  FORGE AI™ Gap Analysis Agent — identify and prioritize skill gaps, experience gaps, and
  certification gaps between a candidate's current profile and their target role or career goal.
  Produces a structured gap report with severity ratings, bridge strategies, and a prioritized
  action plan. Use this skill whenever a user wants to know what's missing, what to learn next,
  how to close the gap for a specific role, or what's blocking their career progression. Trigger
  on: "what skills am I missing", "what's the gap", "gap analysis", "what do I need to learn",
  "what's blocking me from this role", "how do I get to the next level", "what certifications do
  I need", "what experience am I lacking". Also trigger after a forge-candidate-matching score
  below 85 to deep-dive on specific gaps. Part of the FORGE AI™ platform for Exeliq Consulting.
compatibility: "claude.ai, Claude Code, API — all surfaces"
---

# FORGE AI™ — Gap Analysis Agent

Agent 5 of the FORGE AI Multi-Agent Architecture.

---

## Purpose

Identify exactly what separates a candidate from their target role and build a prioritized,
actionable remediation plan — not just a list of gaps.

---

## Gap Categories

### 1. Technical Skill Gaps
Tools, platforms, languages, or frameworks the candidate lacks or has insufficient depth in.

**Severity ratings:**
- 🔴 **Critical** — Required in JD, candidate has no exposure
- 🟠 **Significant** — Required in JD, candidate has adjacent experience only
- 🟡 **Moderate** — Preferred in JD, candidate has some exposure
- 🟢 **Minor** — Nice-to-have, candidate can self-learn quickly

### 2. Experience Gaps
Years, domain, or context gaps between candidate history and role requirements.

Examples:
- "Role requires 8 years, candidate has 5"
- "Role requires financial services domain, candidate has retail"
- "Role requires US project experience, candidate has India-based projects only"

### 3. Certification Gaps
Missing certifications that are required or strongly preferred.

### 4. Leadership/Scope Gaps
For senior/management roles: team size, budget ownership, cross-functional leadership, strategic planning experience.

### 5. Visibility Gaps
Missing portfolio items, GitHub activity, conference talks, LinkedIn presence, publications.

---

## Output Format — FORGE Gap Report™

```
## FORGE Gap Analysis Report™
### Candidate: [Name]
### Target Role: [Title] at [Company / Role Type]
### Analysis Date: [Date]

---

### 📊 Gap Summary
- Total Gaps Identified: X
- Critical Gaps: X
- Significant Gaps: X
- Moderate Gaps: X
- Minor Gaps: X
- Estimated Readiness Timeline: [X weeks/months to role-ready]

---

### 🔴 Critical Gaps (Must Address Before Applying)
| Gap | Type | Severity | Bridge Path | Timeline |
|-----|------|----------|-------------|----------|
| [Missing skill] | Technical | Critical | [How to close] | [Time] |

### 🟠 Significant Gaps (Address Within 30–60 Days)
| Gap | Type | Severity | Bridge Path | Timeline |

### 🟡 Moderate Gaps (Address Within 90 Days)
| Gap | Type | Severity | Bridge Path | Timeline |

### 🟢 Minor Gaps (Nice to Have — Low Priority)
| Gap | Type | Severity | Bridge Path | Timeline |

---

### ✅ Candidate Strengths (Confirmed Matches)
[What the candidate already has that's relevant]

---

### 🗺️ Prioritized Action Plan

**Week 1–2 (Immediate):**
- [ ] [Action 1]
- [ ] [Action 2]

**Week 3–4 (Short-term):**
- [ ] [Action 1]

**Month 2 (Medium-term):**
- [ ] [Action 1]

**Month 3+ (Longer-term):**
- [ ] [Certification / project / experience to build]

---

### 🎓 Recommended Resources
[Specific courses, certifications, projects per critical/significant gap]

---

### 💡 Bridge Strategy
[How to position existing strengths while gaps are being closed.
Candidate should apply NOW for roles where gaps are minor/moderate,
while building toward critical gap roles in parallel.]
```

---

## Gap Closure Resource Mapping

### Common Tech Gap → Closure Path

| Gap | Fastest Closure Path | Certification |
|-----|---------------------|---------------|
| AWS (no experience) | AWS Cloud Practitioner → SAA | AWS SAA-C03 |
| GCP (Azure background) | GCP ACE — ~4 weeks study | GCP ACE |
| dbt | dbt Learn platform (free, 2 weeks) | dbt Certified |
| Spark (SQL background) | Databricks free courses | Databricks Associate |
| Kubernetes | KodeKloud CKA prep (~6 weeks) | CKA |
| Terraform | HashiCorp Learn (2–3 weeks) | Terraform Associate |
| Python (SQL-heavy background) | Python for Data Engineering (Udemy) | None needed |
| Kafka | Confluent developer courses (3 weeks) | Confluent Associate |
| Snowflake | Snowflake University (free, 1 week) | SnowPro Core |

---

## Multi-Surface Behavior

**Claude.ai:** Full markdown gap report.

**Claude Code / API:** JSON available:
```json
{
  "candidate": "",
  "target_role": "",
  "total_gaps": 0,
  "critical_gaps": [],
  "significant_gaps": [],
  "moderate_gaps": [],
  "minor_gaps": [],
  "strengths": [],
  "readiness_timeline_weeks": 0,
  "action_plan": {},
  "resources": []
}
```

---

## Downstream Handoffs

- **→ forge-career-roadmap**: Convert action plan into a structured learning roadmap
- **→ forge-resume-intelligence**: Reposition resume to emphasize bridge strengths
- **→ forge-candidate-matching**: Re-score after gaps are partially closed
- **→ forge-simulation**: Practice weak areas through scenario simulation
