---
name: forge-career-roadmap
description: >
  FORGE AI™ Career Roadmap Agent — build personalized, time-bound career development plans,
  learning roadmaps, certification paths, and career progression strategies for IT professionals.
  Creates daily, weekly, and multi-month plans based on current skills, target role, and timeline.
  Use this skill whenever a user wants a learning plan, wants to know what to study, needs a
  certification path, wants to map their career progression, or wants a structured development
  roadmap. Trigger on: "build a learning plan", "create a roadmap", "what should I learn next",
  "how do I get to [role]", "career roadmap", "study plan", "certification path", "what's my
  next career step", "how do I become a [role]", "6-month plan", "90-day plan", "development
  plan". Also trigger after forge-gap-analysis to convert identified gaps into a structured plan.
  Part of the FORGE AI™ Career Readiness Layer for Exeliq Consulting.
compatibility: "claude.ai, Claude Code, API — all surfaces"
---

# FORGE AI™ — Career Roadmap Agent

Agent 6 of the FORGE AI Multi-Agent Architecture.
Part of the Career Readiness Layer.

---

## Roadmap Types

| Type | Duration | Use Case |
|------|----------|----------|
| **Sprint Roadmap** | 2–4 weeks | Urgent role targeting or cert prep |
| **90-Day Roadmap** | 3 months | Focused skill development |
| **6-Month Roadmap** | 6 months | Career transition or level-up |
| **12-Month Roadmap** | 1 year | Major career pivot or seniority jump |
| **Certification Path** | Variable | Specific cert achievement |
| **Role Progression Map** | Multi-year | IC → Manager → Director pathway |

---

## Input Requirements

Collect before building:

1. **Current role and skills** (where they are now)
2. **Target role** (where they want to be)
3. **Timeline** (how fast do they need to get there?)
4. **Available learning hours per week** (5h? 20h?)
5. **Preferred learning style** (courses, books, projects, YouTube, hands-on labs)
6. **Budget** (free only vs paid courses acceptable)
7. **Any gap analysis already done** (from forge-gap-analysis — feed directly in)

---

## Roadmap Architecture

### Phase Structure

Every roadmap has 4 phases regardless of duration (scaled proportionally):

```
Phase 1 — Foundation (25% of timeline)
  [Core concepts, environment setup, basics of missing skills]

Phase 2 — Build (35% of timeline)
  [Hands-on projects, practical application, intermediate skills]

Phase 3 — Specialize (25% of timeline)
  [Advanced topics, certification prep, portfolio projects]

Phase 4 — Validate (15% of timeline)
  [Mock interviews, job applications, networking, final review]
```

---

## Output Format — FORGE Career Roadmap™

```
## FORGE Career Roadmap™
### Candidate: [Name]
### Goal: [Target Role]
### Duration: [X weeks/months]
### Study Hours/Week: [X hours]
### Created: [Date]

---

### 🎯 Goal Definition
**Current State:** [Role + top skills]
**Target State:** [Role + skills needed]
**Key Gaps to Close:** [Top 3-5 from gap analysis]

---

### 📅 Phase Breakdown

#### Phase 1: Foundation ([Weeks 1–X])
**Focus:** [theme]
**Weekly Hours:** [X]

| Week | Topic | Resource | Deliverable |
|------|-------|----------|-------------|
| Week 1 | [topic] | [specific course/resource] | [what they'll have done] |
| Week 2 | [topic] | [resource] | [deliverable] |

#### Phase 2: Build ([Weeks X–Y])
[same table format]

#### Phase 3: Specialize ([Weeks Y–Z])
[same table format + cert milestones]

#### Phase 4: Validate ([Final weeks])
[Mock interviews, application strategy, networking]

---

### 🏆 Milestones & Checkpoints

| Milestone | Target Date | Success Criteria |
|-----------|-------------|-----------------|
| Complete [Cert/Course] | [Date] | Pass exam / complete project |
| Build [Portfolio Project] | [Date] | GitHub live, can demo it |
| Apply to [X] roles | [Date] | [X] applications submitted |
| Interview ready | [Date] | FORGE Sim Score >80 |

---

### 📚 Resource Stack

**Primary Learning:**
- [Course 1 + URL + cost + hours]
- [Course 2...]

**Certification:**
- [Cert + exam guide + cost + timeline]

**Hands-on Labs:**
- [Free platform + specific project]

**Communities:**
- [Slack/Discord/Reddit to join]

---

### ⏰ Weekly Schedule Template
[Sample week showing how to fit learning into real life]
```

---

## Certification Fast-Track Paths

### Cloud Certifications

**Azure Data Engineer Associate (DP-203)**
- Prerequisites: Basic Azure knowledge, SQL
- Study time: 6–8 weeks (10h/week)
- Resources: Microsoft Learn (free), Udemy Zeal Vora course

**GCP Professional Data Engineer**
- Prerequisites: GCP basics (ACE level)
- Study time: 8–10 weeks (10h/week)
- Resources: Google Qwiklabs, A Cloud Guru

**AWS Data Engineer Associate (DEA-C01)**
- Prerequisites: AWS basics, SQL, Python
- Study time: 6–8 weeks (10h/week)
- Resources: Stephane Maarek Udemy course, AWS Skill Builder

**Databricks Certified Data Engineer Associate**
- Prerequisites: Python, Spark basics
- Study time: 4 weeks (8h/week)
- Resources: Databricks Academy (free)

**dbt Certified Developer**
- Prerequisites: SQL proficiency
- Study time: 2–3 weeks (6h/week)
- Resources: dbt Learn platform (free)

---

## Learning Hour Budgets

| Hours/Week | Roadmap Approach |
|------------|-----------------|
| 3–5h | Evenings only — 12-month plan minimum for career transition |
| 6–10h | Weekend + evenings — 6-month plan realistic |
| 10–15h | Dedicated part-time — 3-month plan achievable |
| 20h+ | Full sprint — 90-day intensive realistic |

---

## Multi-Surface Behavior

**Claude.ai:** Full roadmap in markdown with tables. Offer to break into weekly task lists.

**Claude Code / API:** JSON output:
```json
{
  "candidate": "",
  "goal": "",
  "duration_weeks": 0,
  "hours_per_week": 0,
  "phases": [],
  "milestones": [],
  "resources": [],
  "weekly_template": {}
}
```

---

## Downstream Handoffs

- **→ forge-gap-analysis**: If gaps haven't been analyzed yet, do that first
- **→ forge-simulation**: Use simulations to validate readiness at Phase 4
- **→ forge-analytics**: Track roadmap completion and milestone progress
- **→ forge-candidate-matching**: Re-run match score after roadmap completion
