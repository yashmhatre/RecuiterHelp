---
name: forge-jd-intelligence
description: >
  FORGE AI™ JD Intelligence Agent — parse and deeply analyze any job description (JD) to extract
  structured intelligence: required skills, certifications, experience levels, ATS keywords, role
  seniority signals, compensation signals, and hidden requirements. Use this skill whenever a user
  pastes, uploads, or references a job description and wants it analyzed, decoded, or compared.
  Trigger on phrases like "analyze this JD", "parse this job posting", "what skills does this role
  need", "extract keywords from this job", "decode this job description", "what does this role
  require", or any time a raw JD text is provided as input. Also trigger when building candidate
  match reports, resume targeting, or gap analysis that starts from a JD. Part of the FORGE AI™
  platform for Exeliq Consulting.
compatibility: "claude.ai, Claude Code, API — all surfaces"
---

# FORGE AI™ — JD Intelligence Agent

Agent 2 of the FORGE AI Multi-Agent Architecture.

## Purpose

Transform raw job description text into structured career intelligence that powers downstream
agents: Candidate Matching, Resume Intelligence, Gap Analysis, and Learning Roadmap.

---

## Input Formats Accepted

- Pasted JD text (most common)
- URL to job posting (fetch if possible)
- Uploaded PDF or DOCX of a job posting
- Screenshot description (extract via vision)

---

## Output Structure

Always produce the full JD Intelligence Report in this format:

```
## FORGE JD Intelligence Report™
### Role: [Title] at [Company]

**Role Tier:** [IC / Manager / Director / VP / C-Suite]
**Seniority Level:** [Entry / Mid / Senior / Staff / Principal / Executive]
**Employment Type:** [FTE / Contract / C2C / W2 / Part-time]
**Location:** [Remote / Hybrid / Onsite — City, State]
**Compensation Signal:** [If visible or inferable]

---

### 🔵 Must-Have Skills (Hard Requirements)
| Skill | Category | Years Required |
|-------|----------|---------------|
| ...   | ...      | ...           |

### 🟡 Preferred Skills (Nice-to-Have)
| Skill | Category | Weight |
|-------|----------|--------|

### 🟢 Certifications
| Certification | Required / Preferred |
|---------------|---------------------|

### 📋 Experience Requirements
- Total years: 
- Domain years:
- Management experience:
- Industry background:

### 🎯 ATS Power Keywords (Top 20)
[comma-separated list — use these verbatim in resumes]

### 🔍 Hidden Requirements (Reading Between the Lines)
[Inferred culture fit signals, unstated tech stack, team dynamics, pace signals]

### 📊 Role Complexity Score: X/10
[Justify the score briefly]

### ⚡ FORGE Match Readiness Signal
[What a strong candidate profile looks like for this role in 3–4 sentences]
```

---

## Processing Instructions

### Step 1 — Classify the Role
Determine: IC vs management track, seniority tier, domain (Data/Cloud/DevOps/AI/Security/PM/etc.)

### Step 2 — Extract Structured Skills
Split skills into:
- **Hard technical skills** (tools, platforms, languages, frameworks)
- **Soft/leadership skills** (separately, lower weight for ATS)
- **Domain knowledge** (industry, business context)

### Step 3 — Keyword Intelligence
Identify which keywords are likely ATS-weighted vs aspirational.
Flag any skills that appear multiple times — they carry higher weight.

### Step 4 — Hidden Requirement Detection
Look for coded language:
- "Fast-paced environment" = startup culture / high workload
- "Self-starter" = low management support
- "Cross-functional collaboration" = heavy stakeholder management
- "5+ years with X (required)" vs "5+ years with X (preferred)" — huge difference

### Step 5 — Certification Mapping
Map mentioned certs to actual certifying bodies:
- AWS SAA → Amazon Web Services Solutions Architect Associate
- GCP ACE → Google Cloud Associate Cloud Engineer
- AZ-900 → Microsoft Azure Fundamentals
- etc.

### Step 6 — Compensation Signal (if available)
If salary range is stated, note it. If not, infer from:
- Seniority signals
- Location
- Company size/type signals in the JD

---

## Multi-Surface Behavior

**Claude.ai:** Output the full report in markdown directly in chat.

**Claude Code / API:** If called programmatically, also offer to output as structured JSON:
```json
{
  "role_title": "",
  "company": "",
  "seniority": "",
  "employment_type": "",
  "location": "",
  "must_have_skills": [],
  "preferred_skills": [],
  "certifications": [],
  "ats_keywords": [],
  "experience_requirements": {},
  "hidden_requirements": [],
  "complexity_score": 0,
  "match_readiness_signal": ""
}
```

---

## Downstream Agent Handoff

After producing the JD Intelligence Report, offer to:
- **→ forge-candidate-matching**: "Want me to match a candidate profile against this JD?"
- **→ forge-resume-intelligence**: "Want me to tailor a resume for this role?"
- **→ forge-gap-analysis**: "Want me to run a gap analysis for a specific candidate?"

---

## Quality Standards

- Never fabricate requirements not in the JD
- Flag ambiguous requirements clearly rather than guessing
- If the JD is poorly written, note that and do best-effort extraction
- Always produce the ATS keyword list — this is critical for resume targeting
