# FORGE Simulation — Test Cases

## Test 1: Production failure simulation (Data Engineer)
**Prompt:**
```
Run a FORGE Sim production failure scenario for Om Ingale. He's preparing for Senior DE interviews. Stack: Databricks + Azure Data Factory + Azure Blob Storage.
```
**Expected:** Claude adopts interviewer persona. Delivers 2:47 AM scenario tailored to Azure/Databricks. Probes through 5 stages. Delivers FORGE Sim Score at end.

---

## Test 2: System design (Senior level)
**Prompt:**
```
Run a system design FORGE Sim for me. I'm targeting Staff Data Engineer roles at FAANG. My stack is GCP — BigQuery, Dataflow, Pub/Sub.
```
**Expected:** FAANG-caliber system design question (real-time streaming scale). Claude as senior FAANG interviewer. Deep probing on clarifying questions, architecture trade-offs, failure modes, cost.

---

## Test 3: Leadership dilemma (Manager track)
**Prompt:**
```
I'm preparing for a Director of Data Engineering role. Run a leadership simulation. My background: 3 years managing teams of 5–8 engineers.
```
**Expected:** Leadership dilemma scenario (launch delay vs technical debt). Probes on stakeholder management, team decision-making, upward communication. Score includes leadership-specific dimensions.

---

## Test 4: Quick behavioral (STAR format)
**Prompt:**
```
Give me 3 STAR behavioral questions for a Senior Data Engineer at a fintech company.
```
**Expected:** 3 tailored behavioral questions with STAR format guidance. Offer to run as full interactive simulation.

---

## Test 5: Simulation score report
**Prompt:**
```
Here's my system design answer: [user pastes a long system design response about building a data pipeline]. Score my answer.
```
**Expected:** Applies FORGE Sim Score rubric to the provided answer. 5-dimension scoring table. Specific feedback on strengths and gaps. Recommended next simulation.

---

## Test 6: Gentle warm-up (junior candidate)
**Prompt:**
```
I'm nervous about interviews. Can we do a quick easy practice session? I'm a junior data analyst, 2 years experience.
```
**Expected:** Lighter, supportive simulation at appropriate junior level. No production failure scenarios. SQL/data analysis questions. Encouraging evaluation tone.

---

## Assertions
- [ ] Claude always adopts interviewer persona during simulation (not assistant mode)
- [ ] Probes are asked one at a time, not all at once
- [ ] FORGE Sim Score delivered after every completed simulation
- [ ] Score dimensions always match simulation type (leadership vs technical vs behavioral)
- [ ] Simulation difficulty calibrated to stated target seniority level
- [ ] Junior candidates receive gentler framing and appropriate difficulty
- [ ] Downstream handoffs offered after score delivery
