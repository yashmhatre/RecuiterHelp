# FORGE Gap Analysis — Test Cases

## Test 1: Cloud migration gap (Azure to GCP)
**Prompt:**
```
Run FORGE Gap Analysis. Candidate: Nishad Patkar, 5 years Azure Data Engineer (ADF, Synapse, Azure Blob, Python, SQL). Target: GCP Data Engineer roles requiring BigQuery, Dataflow, GCP Storage, Pub/Sub, Terraform.
```
**Expected:** Azure→GCP gaps identified, Terraform as critical, Dataflow as significant (Synapse/Spark bridge exists), resource mapping to GCP ACE cert + Terraform Associate.

---

## Test 2: IC to Manager gap
**Prompt:**
```
Gap analysis for Deepak Satam, 20 years Data & AI Architect. He wants to move to VP of Data Engineering. Currently: strong technical, no people management, no P&L ownership, no board presentations. Target: VP role at large enterprise.
```
**Expected:** Leadership/scope gaps flagged prominently. Technical gaps = none. Visibility gaps (thought leadership). Action plan focuses on management exposure, executive communication, LinkedIn presence.

---

## Test 3: Certification-focused gap
**Prompt:**
```
What certifications is Om Ingale missing for senior DE roles? He has AWS Cloud Practitioner, Databricks Associate. Target roles want: AWS SAA, dbt Certified, Spark Performance Tuning.
```
**Expected:** AWS SAA as significant gap (already has CCP, upgrade path clear), dbt as significant, Spark perf as moderate. Closure timelines provided.

---

## Test 4: Junior to Senior gap
**Prompt:**
```
I have 3 years experience as a Data Analyst (SQL, Tableau, Excel, some Python). I want to become a Senior Data Engineer in 12 months. What's my gap?
```
**Expected:** Major technical gaps (Spark, cloud platforms, orchestration tools). 12-month timeline assessed as ambitious but achievable. Week-by-week learning plan offered.

---

## Test 5: Minimal information (graceful handling)
**Prompt:**
```
What gaps do I have for cloud roles?
```
**Expected:** Asks clarifying questions: What's your current background? What specific cloud roles? Which cloud provider? Does NOT produce generic/useless report.

---

## Assertions
- [ ] Gap severity always rated (Critical/Significant/Moderate/Minor)
- [ ] Readiness timeline estimate always provided
- [ ] Resources mapped to specific gaps (not generic "take a course")
- [ ] Bridge strategy always included (existing strengths to leverage)
- [ ] Action plan is time-bound (Week 1–2, Month 1, Month 2–3)
- [ ] Clarifying questions asked when input is too vague
- [ ] Downstream handoffs offered
