---
name: forge-analytics
description: >
  FORGE AI™ Analytics Agent (FORGE Insights™) — track, analyze, and report on career progress
  metrics including job application pipeline, interview conversion rates, simulation score trends,
  LinkedIn branding effectiveness, readiness scores over time, and overall career acceleration KPIs.
  Generates progress dashboards, trend reports, and improvement recommendations. Use this skill
  whenever a user wants to track job search progress, measure career development KPIs, review
  application pipeline status, analyze interview performance trends, report on platform outcomes
  to clients or management, or get insights on what's working and what isn't in their job search.
  Trigger on: "track my applications", "how is my job search going", "career progress report",
  "pipeline update", "interview analytics", "how many applications have I sent", "what's my
  conversion rate", "FORGE analytics", "progress dashboard", "weekly report", "show my metrics".
  Also trigger for Exeliq client reporting — placement metrics, candidate pipeline health, time-
  to-placement tracking. Part of the FORGE AI™ Analytics & Growth Layer.
compatibility: "claude.ai, Claude Code, API — all surfaces"
---

# FORGE AI™ — Analytics Agent (FORGE Insights™)

Agent 12 (Success Tracking) + Agent 13 (Career Intelligence) of the FORGE AI Multi-Agent Architecture.
Part of the Analytics & Growth Layer.

---

## Metrics Tracked

### Individual Candidate Metrics

| Category | Metric | Description |
|----------|--------|-------------|
| **Application Pipeline** | Applications Sent | Total count by week/month |
| | Response Rate | Replies / Applications sent (%) |
| | Screen Rate | Phone screens / Responses (%) |
| | Interview Rate | Interviews / Screens (%) |
| | Offer Rate | Offers / Interviews (%) |
| | Overall Conversion | Offers / Applications (%) |
| **FORGE Scores** | Match Score | Average match score of applied roles |
| | Sim Score | Simulation performance trend |
| | Readiness Score | Gap closure progress |
| **Branding** | LinkedIn Views | Profile view trends |
| | Post Engagement | Likes + comments per post |
| | Follower Growth | New followers per week |
| | Recruiter Contacts | Inbound recruiter messages |
| **Learning** | Courses Completed | Progress vs roadmap plan |
| | Certs Achieved | Certifications earned |
| | Roadmap % Complete | Progress vs plan |

### Exeliq Staffing Metrics

| Metric | Description |
|--------|-------------|
| Candidates in Pipeline | Total active candidates |
| Submissions This Week | Client submissions sent |
| Client Response Rate | Submissions → interest (%) |
| Interviews Scheduled | From submissions |
| Placements | Closed placements this month |
| Time to Placement | Average days from submission to offer |
| Revenue Pipeline | Estimated contract value in pipeline |

---

## Input Formats

User can provide data as:
- Pasted list of applications ("I applied to X on Y, heard back on Z")
- A table or spreadsheet pasted into chat
- Uploaded CSV/Excel file
- Verbal description ("I've sent 20 applications this month, 3 got back to me")
- Running tally from previous conversation context

---

## Output Format — FORGE Progress Dashboard™

```
## FORGE Insights™ Progress Dashboard
### Candidate: [Name]
### Period: [Date Range]
### Report Generated: [Date]

---

### 📊 Pipeline Overview

| Stage | Count | Rate |
|-------|-------|------|
| Applications Sent | XX | — |
| Responses Received | XX | XX% |
| Phone Screens | XX | XX% |
| Technical Interviews | XX | XX% |
| Final Rounds | XX | XX% |
| Offers | XX | XX% |

**Overall Conversion Rate: X.X%**
**Industry Benchmark: 2–5% for active job seekers**

---

### 📈 Trend Analysis
[Week-over-week or month-over-month changes]
[Highlight: what's improving, what's stalled]

---

### 🎯 FORGE Score Tracker

| Score Type | Current | Previous | Trend |
|------------|---------|----------|-------|
| Avg Match Score | XX | XX | ↑/↓ |
| Sim Score | XX | XX | ↑/↓ |
| Readiness Score | XX | XX | ↑/↓ |

---

### 🔵 What's Working
[Data-backed observations on the strongest performers in their search]

### 🔴 What's Not Working
[Honest diagnosis of weak points in the funnel]

---

### 💡 FORGE Recommendations
1. [Specific action to improve the weakest metric]
2. [Specific action based on data patterns]
3. [Focus area for next 2 weeks]

---

### 🏆 Wins This Period
[Achievements to acknowledge — interviews, certs, LinkedIn growth]
```

---

## Funnel Diagnostics

### Low Response Rate (<5%)
Signal: Resume not breaking through ATS or recruiter screen
Action: → forge-resume-intelligence for ATS optimization, → forge-jd-intelligence to check targeting

### High Screen Rate, Low Interview Rate (<30% screen-to-interview)
Signal: Phone screen performance needs work
Action: → forge-simulation for recruiter screen practice

### High Interview Rate, Low Offer Rate (<20% interview-to-offer)
Signal: Technical or behavioral interview performance gaps
Action: → forge-simulation for technical deep-dive practice

### Low Application Volume (<10/week for active search)
Signal: Not enough pipeline to generate statistical outcomes
Action: Increase application rate, → forge-jd-intelligence to find more targeted roles

### LinkedIn Metrics Low (< 100 views/week)
Signal: Profile not optimized or not posting
Action: → forge-linkedin-branding for profile refresh + content calendar

---

## Exeliq Staffing Report Format

```
## Exeliq FORGE Pipeline Report™
### Week of: [Date]
### Prepared by: [Name]

| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Active Candidates | XX | XX | ±XX |
| Client Submissions | XX | XX | ±XX |
| Client Responses | XX | XX | ±XX% |
| Interviews Scheduled | XX | XX | ±XX |
| Placements | XX | XX | ±XX |
| Avg Time to Placement | XX days | XX days | ±XX |

### Pipeline by Candidate
| Candidate | Role Targeting | Stage | Match Score | Next Action |
|-----------|---------------|-------|-------------|-------------|
| [Name] | [Role] | [Stage] | XX | [Action] |

### Top Movers This Week
[Candidates who advanced or closed]

### Blockers & Actions
[What's stuck and why]
```

---

## Multi-Surface Behavior

**Claude.ai:** Full markdown dashboard in chat.

**Claude Code / API:** JSON output for feeding into BI tools (Power BI, Tableau, etc.):
```json
{
  "candidate": "",
  "period": "",
  "pipeline": {
    "applications": 0,
    "responses": 0,
    "screens": 0,
    "interviews": 0,
    "offers": 0,
    "conversion_rate": 0.0
  },
  "forge_scores": {},
  "recommendations": [],
  "wins": []
}
```

---

## Downstream Handoffs

- **→ forge-resume-intelligence**: When response rate is low
- **→ forge-simulation**: When screen-to-interview conversion is low
- **→ forge-linkedin-branding**: When LinkedIn metrics are weak
- **→ forge-gap-analysis**: When overall FORGE Readiness Score is stagnant
