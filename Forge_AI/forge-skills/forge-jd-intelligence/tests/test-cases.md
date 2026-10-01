# FORGE JD Intelligence — Test Cases

## Test 1: Senior Data Engineer (Cloud-heavy)
**Prompt:**
```
Analyze this JD using FORGE JD Intelligence:

Senior Data Engineer — FinTech Startup (Remote)
We are looking for a Senior Data Engineer with 5+ years of experience building scalable data pipelines on AWS. You will work with our data science team to build ETL pipelines using Apache Spark, AWS Glue, and Redshift. Experience with dbt is required. Python expertise is mandatory. Knowledge of Kafka or Kinesis preferred. You should be comfortable in an agile, fast-paced environment. AWS certifications a plus. Salary: $140,000–$170,000.
```
**Expected output:** Full JD Intelligence Report with AWS/Spark/dbt as must-haves, hidden req detection of "fast-paced startup", salary signal captured.

---

## Test 2: Minimal JD (stress test)
**Prompt:**
```
Parse this job posting: "Cloud Architect needed. GCP experience. 10 years IT. Good communication."
```
**Expected output:** Graceful handling of sparse JD, best-effort extraction, note that JD is poorly written, still produces ATS keywords and complexity score.

---

## Test 3: API JSON output request
**Prompt:**
```
Analyze this JD and return structured JSON for our API:

Staff ML Engineer — Big Tech (Hybrid, Seattle)
Requirements: 8+ years ML engineering, Python, PyTorch or TensorFlow, distributed training, MLflow, Kubernetes, strong communication skills, PhD preferred, 3+ years leading ML teams.
```
**Expected output:** Both markdown report AND JSON block with all fields populated.

---

## Test 4: Downstream handoff
**Prompt:**
```
I just shared a JD with you. After analyzing it, I want to match it against Om Ingale's profile (Cloud Data Engineer, 7 years experience, Azure/Databricks/Python).
```
**Expected output:** JD analysis first, then natural offer/transition to forge-candidate-matching.

---

## Assertions
- [ ] ATS keyword list always present (minimum 10 keywords)
- [ ] Must-have vs preferred skills are always separated
- [ ] Seniority level always classified
- [ ] Hidden requirements section always included (even if empty)
- [ ] Downstream handoff options offered at end
- [ ] Handles sparse JDs gracefully without hallucinating requirements
