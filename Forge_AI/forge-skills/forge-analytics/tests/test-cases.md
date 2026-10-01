# FORGE Analytics — Test Cases

## Test 1: Application pipeline report
**Prompt:**
```
Generate a FORGE progress dashboard for Om Ingale. Last 30 days: 
- Applied to 35 jobs (C2C Data Engineer roles)
- Received 4 responses
- 2 phone screens
- 1 technical interview
- 0 offers so far
LinkedIn: 380 profile views this month, 2 recruiter InMails received.
FORGE Match score average: 76.
```
**Expected:** Full dashboard with pipeline table, conversion rates, benchmark comparison, diagnosis (low response rate = resume/targeting issue), 3 specific recommendations, wins acknowledged.

---

## Test 2: Exeliq staffing pipeline report
**Prompt:**
```
Generate an Exeliq staffing report. This week:
- 5 active candidates (Om, Nishad, Sunil, Vaibhav, Amol)
- 8 client submissions sent
- 3 client responses (all interest)
- 2 interviews scheduled
- 1 placement closed (Sunil Shinde, AWS role, $75/hr C2C)
Last week was: 6 submissions, 1 response, 0 placements.
```
**Expected:** Exeliq format report with week-over-week table, candidate pipeline table, Sunil flagged as win, improved response rate noted.

---

## Test 3: Funnel diagnosis (stuck pipeline)
**Prompt:**
```
My job search data: 60 applications sent in 2 months. 12 responses (20% rate — good). 8 phone screens (67% — good). 1 technical interview. 0 offers. What's wrong?
```
**Expected:** Clear diagnosis — phone screen → technical interview drop-off is the bottleneck. Recommendation: forge-simulation for technical interview practice. Not a resume problem.

---

## Test 4: FORGE score trend tracking
**Prompt:**
```
Track my FORGE scores over 3 months:
Month 1: Match score 65, Sim score 55, Readiness 60
Month 2: Match score 72, Sim score 68, Readiness 70
Month 3: Match score 80, Sim score 75, Readiness 78
```
**Expected:** Trend table with direction arrows. Positive trajectory acknowledged. Sim score still lagging — recommend more simulation sessions. Estimated timeline to interview-ready.

---

## Test 5: LinkedIn metrics + career analytics combo
**Prompt:**
```
Monthly review. Applications: 20, responses: 6 (30% — great). LinkedIn: 500 profile views, 5 inbound recruiter messages, my posts averaged 80 likes each. Learning: completed Databricks cert this month.
```
**Expected:** Dashboard showing strong LinkedIn and response performance. Databricks cert win highlighted. Overall trajectory = positive. Recommendations focus on maintaining momentum and increasing application volume.

---

## Assertions
- [ ] Pipeline table always shows stage-by-stage conversion rates
- [ ] Industry benchmark always provided for comparison
- [ ] Funnel diagnosis always identifies the specific bottleneck stage
- [ ] Recommendations are always specific and actionable (not "apply to more jobs")
- [ ] Exeliq format distinct from individual candidate format
- [ ] FORGE scores tracked with trend direction (↑/↓)
- [ ] Wins are always acknowledged (not just problem-focused)
- [ ] JSON output available when requested
