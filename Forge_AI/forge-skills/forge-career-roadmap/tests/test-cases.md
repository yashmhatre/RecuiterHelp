# FORGE Career Roadmap — Test Cases

## Test 1: Azure to GCP transition — 6-month plan
**Prompt:**
```
Build a 6-month FORGE Career Roadmap for Nishad Patkar. Current: Azure Data Engineer (ADF, Synapse, Python, SQL). Goal: GCP Senior Data Engineer. Available: 10 hours/week. Budget: up to $200 for courses.
```
**Expected:** 4-phase roadmap covering GCP ACE → GCP PDE cert path, BigQuery/Dataflow hands-on, Terraform basics. Week-by-week schedule for 10h/week. Resources with costs. Milestones with dates.

---

## Test 2: Junior to Senior — 12-month plan
**Prompt:**
```
I'm a junior data analyst, 2 years SQL + Tableau. I want to become a Senior Data Engineer in 12 months. Available: 15 hours/week. Budget: $50/month.
```
**Expected:** Ambitious but structured 12-month plan. Phase 1: Python + cloud basics. Phase 2: Spark + orchestration. Phase 3: cert + portfolio project. Phase 4: job search + interview prep. Honest about challenge level.

---

## Test 3: Certification fast-track
**Prompt:**
```
Om Ingale needs Databricks Certified Data Engineer Associate in 4 weeks. He already knows PySpark and has used Databricks at work. Build a sprint study plan.
```
**Expected:** Tight 4-week sprint. Daily/weekly study targets. Databricks Academy resources. Practice exam schedule. Week 4 = revision + mock exams. No fluff.

---

## Test 4: Role progression map
**Prompt:**
```
Map the career path from Senior Data Engineer → Staff DE → Principal DE → Engineering Manager for me. What does each level require? How long does each step take typically?
```
**Expected:** Multi-year progression map. Each level: skills required, typical timeline, promotion signals, key experiences needed. Honest about IC vs manager fork.

---

## Test 5: Roadmap from gap analysis input
**Prompt:**
```
Here are my gaps from a FORGE Gap Analysis: Critical — Terraform (0 experience). Significant — Kubernetes (basic exposure only). Moderate — Go language. I have 8 hours/week and want to be ready in 3 months.
```
**Expected:** 90-day plan focused on the 3 gaps in priority order (Terraform first since critical). Specific resources. Skips re-doing gap analysis. Works directly from provided gaps.

---

## Assertions
- [ ] All roadmaps have 4 phases regardless of duration
- [ ] Each week has a specific topic, resource, AND deliverable (not just "study X")
- [ ] Resources include cost, time estimate, and URL/platform
- [ ] Learning hour budget is respected in the plan structure
- [ ] Milestones include success criteria, not just dates
- [ ] Junior vs senior learners receive appropriate pacing
- [ ] Roadmap from gap analysis input skips re-analysis and builds directly
- [ ] JSON output available when requested
