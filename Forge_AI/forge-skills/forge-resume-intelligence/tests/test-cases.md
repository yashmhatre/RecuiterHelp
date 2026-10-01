# FORGE Resume Intelligence — Test Cases

## Test 1: ATS Resume from scratch (Data Engineer)
**Prompt:**
```
Build an ATS resume for Om Ingale. He is a Cloud Data Engineer with 7 years experience.
Skills: Azure Data Factory, Databricks, PySpark, SQL, Python, Delta Lake, Azure Synapse.
Last role: Data Engineer at Infosys (2021–present) — built ETL pipelines for retail client.
Before that: Junior DE at Wipro (2018–2021). B.Tech Computer Science, Pune University 2018.
Target JD: Senior Data Engineer at a US company, Chicago or Remote.
```
**Expected:** Full ATS resume with strong bullets, quantification prompts, skill grid, C2C-ready formatting.

---

## Test 2: Rewrite weak bullets
**Prompt:**
```
Rewrite these resume bullets using FORGE Resume Intelligence:
- Worked on AWS infrastructure
- Did data pipeline stuff using Spark
- Helped the team with Kubernetes deployments
- Responsible for reporting dashboards
```
**Expected:** 4 rewritten bullets with strong action verbs and result framing. Flags missing quantification.

---

## Test 3: JD-targeted tailoring
**Prompt:**
```
Tailor my resume summary and skills section for this JD.
My background: 10 years as Data Architect, Snowflake + dbt + Airflow + GCP + BigQuery.
JD says: "Senior Analytics Engineer — must have dbt, BigQuery, strong SQL, data modeling experience. Looker a plus."
```
**Expected:** Summary rewritten with JD keyword mirroring. Skills section reorganized with dbt/BigQuery/SQL at top.

---

## Test 4: Executive resume
**Prompt:**
```
I need an executive resume. I'm a Director of Data Engineering with 15 years experience.
Led teams of 20+ engineers, delivered $5M cost reduction through data platform modernization,
managed $3M budget, speaking at conferences. Target: VP of Data Engineering roles.
```
**Expected:** Executive format — Leadership Profile first, Areas of Expertise, de-emphasized tech tools, business outcomes prominent.

---

## Test 5: Voice authenticity preservation
**Prompt:**
```
Here is my existing resume summary: "I architect distributed data systems that don't break at scale.
I care deeply about data quality and I've spent 8 years obsessing over it."
Rewrite this for an ATS resume but keep my voice.
```
**Expected:** Retains the distinctive, direct voice while adding keywords. Does NOT convert to generic "Results-driven data professional."

---

## Assertions
- [ ] All bullets start with action verbs (never "Responsible for" or "Helped with")
- [ ] Professional summary is always role-targeted
- [ ] JD keywords embedded when JD is provided
- [ ] Executive format used for Director+ roles
- [ ] Candidate voice preserved — no generic filler phrases
- [ ] Quantification flagged when missing rather than fabricated
- [ ] Quality checklist items verified before delivery
