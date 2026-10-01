# FORGE Candidate Matching — Test Cases

## Test 1: Strong match scenario
**Prompt:**
```
Run a FORGE Match for this candidate vs JD.

Candidate: Om Ingale, 7 years Cloud Data Engineer. Skills: Azure Data Factory, Databricks, PySpark, Python, SQL, Delta Lake, Azure Synapse, Airflow. Work auth: H1B (Exeliq sponsor). Location: Open to Chicago or Remote.

JD: Senior Data Engineer — Chicago company. Requirements: 5+ years data engineering, Databricks (required), PySpark (required), Python (required), Azure experience preferred, Airflow preferred. Salary $130–160k. Remote-friendly.
```
**Expected:** Score 80-90+, strong match signal, H1B work auth noted, bridge positioning if needed.

---

## Test 2: Partial match with bridge positioning
**Prompt:**
```
Match this candidate: Nishad Patkar, 5 years, Snowflake + dbt + Python + AWS S3 + Redshift. No GCP experience.

JD: Data Engineer at Google. Requires: BigQuery, Dataflow, GCP, dbt, Python. 4+ years required.
```
**Expected:** Partial/good match. Bridge narrative: dbt + Python = direct match, Redshift→BigQuery migration story, no Dataflow but Spark patterns transferable.

---

## Test 3: Multi-candidate comparison
**Prompt:**
```
Compare these 3 candidates for the role: ML Engineer, Python + PyTorch + Kubernetes + MLflow required.

- Candidate A: 6 years ML, TensorFlow (no PyTorch), Python, Docker not K8s
- Candidate B: 4 years ML, PyTorch, Python, Kubernetes, MLflow certified
- Candidate C: 8 years data science, R + Python, some ML, no MLOps tools
```
**Expected:** Comparison table first, then individual reports. B ranked highest, A has bridge, C is stretch.

---

## Test 4: JSON output for API
**Prompt:**
```
Run FORGE Match and return JSON. Candidate: Sunil Shinde, GCP Data Engineer, 8 years. JD requires GCP, BigQuery, Dataflow, Python, Terraform. He has all except Terraform.
```
**Expected:** JSON output with score ~85, gap flagged as Terraform (preferred, not blocker), bridge strategy included.

---

## Test 5: Poor match — do not submit
**Prompt:**
```
Can we submit this candidate? Junior developer, 1 year experience, React + JavaScript. Role: Principal Data Architect, 12+ years required, Snowflake + Kafka + Spark.
```
**Expected:** Score <40, clear "Do not submit" recommendation, respectful explanation, offer to route to development plan instead.

---

## Assertions
- [ ] Score is always X/100 with clear signal emoji
- [ ] All 6 dimensions always scored with notes
- [ ] Bridge positioning always attempted before flagging gap as fatal
- [ ] Multi-candidate comparison table generated when 2+ candidates
- [ ] Poor match recommendations are clear and never buried
- [ ] JSON output available when requested
- [ ] Downstream handoffs offered at end
