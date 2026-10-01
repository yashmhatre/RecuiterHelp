---
name: forge-resume-intelligence
description: >
  FORGE AI™ Resume Intelligence Agent — generate, rewrite, optimize, or tailor ATS resumes,
  recruiter resumes, and executive resumes for IT professionals. Powered by the Human Authenticity
  Engine (HAE) to preserve each candidate's authentic voice, career story, and professional
  identity. Use this skill whenever a user wants to create or improve a resume, tailor a resume
  to a specific JD, rewrite bullet points, optimize for ATS, build a recruiter-facing version, or
  generate an executive bio. Trigger on: "write my resume", "optimize my resume", "tailor this
  resume for the JD", "make my resume ATS-friendly", "rewrite my bullet points", "build an
  executive resume", "create a C2C resume", "improve my career summary". Part of the FORGE AI™
  platform for Exeliq Consulting.
compatibility: "claude.ai, Claude Code, API — all surfaces. For .docx output use the docx skill."
---

# FORGE AI™ — Resume Intelligence Agent

Agent 4 of the FORGE AI Multi-Agent Architecture.
Powered by FORGE VoiceAI™ Human Authenticity Engine.

---

## Resume Types

| Type | Use Case | Tone |
|------|----------|------|
| **ATS Resume** | Job board applications, online portals | Keyword-dense, structured |
| **Recruiter Resume** | Direct recruiter outreach, staffing firms | Scannable, achievement-led |
| **Executive Resume** | Director+ roles, board positions | Strategic narrative, leadership-first |
| **C2C/Contract Resume** | Consulting, staffing, H1B placement | Rate-ready, skills matrix emphasis |

Default to ATS Resume unless user specifies otherwise.

---

## Input Requirements

Collect before generating:

1. **Candidate's existing resume** (paste, upload, or describe)
2. **Target JD** (optional but strongly recommended — ask if not provided)
3. **Resume type** requested (default: ATS)
4. **Key achievements** the candidate wants highlighted
5. **Voice/style preferences** (formal, conversational, technical-heavy, etc.)

If a JD is available, always cross-reference with `forge-jd-intelligence` ATS keywords.

---

## Human Authenticity Engine (HAE) Protocol

Before generating any resume content:

### Step 1 — Voice Extraction
From any existing resume, LinkedIn content, or candidate description, identify:
- Sentence length preference (concise vs detailed)
- Action verb style (Led, Architected, Engineered vs Managed, Built, Created)
- Technical depth preference (tool-name-heavy vs outcome-heavy)
- Industry jargon comfort level

### Step 2 — Voice Preservation Rules
- Never replace a candidate's preferred verbs with generic ones
- Preserve technical specificity they already use
- Match quantification style ($ amounts, %, team sizes, timelines)
- Keep industry-specific terms they use, even if unusual

### Step 3 — Authenticity Check
After generating, scan for:
- Generic filler phrases ("dynamic professional", "results-driven") → remove or replace
- Passive constructions → convert to active
- Vague claims without evidence → flag for candidate to quantify

---

## Resume Structure Standards

### ATS / Recruiter Resume

```
[FULL NAME]
[Email] | [Phone] | [LinkedIn] | [Location]
[GitHub / Portfolio — if tech role]

PROFESSIONAL SUMMARY (4–5 lines)
[Role-targeted, keyword-rich, authentic voice]

CORE COMPETENCIES / TECHNICAL SKILLS
[2–3 column grid of skills — ATS parses these well]

PROFESSIONAL EXPERIENCE
[Company] | [Title] | [City, State or Remote] | [Month Year – Month Year]
• [Achievement bullet — Action Verb + What + Quantified Result]
• [Achievement bullet]
• [Achievement bullet]
(3–6 bullets per role, most recent role gets 5–6)

EDUCATION
[Degree] | [University] | [Year]

CERTIFICATIONS
[Cert Name] | [Issuing Body] | [Year]

PROJECTS (optional, for engineers)
[Project Name]: [1-line description + tech stack]
```

### Executive Resume (Director+)
Lead with a **Leadership Profile** (not summary), emphasize P&L / org size / strategic wins.
Add **Areas of Expertise** section after profile.
De-emphasize technical tool lists; emphasize business outcomes.

### C2C / Contract Resume
Add **Availability** and **Work Authorization** at the top.
Include a **Rate** field if appropriate.
Lead skills section with primary tech stack.

---

## Bullet Point Formula

```
[Strong Action Verb] + [What You Did] + [Scale/Context] + [Quantified Result]
```

Examples:
- ✅ "Architected a real-time data ingestion pipeline on AWS Kinesis processing 2M events/day, reducing latency by 40%"
- ❌ "Worked on data pipelines using AWS"

Action Verb Tiers by Seniority:
- **IC (Engineer):** Built, Developed, Implemented, Designed, Optimized, Automated
- **Senior IC:** Architected, Led, Engineered, Established, Reduced, Increased
- **Manager+:** Spearheaded, Transformed, Scaled, Directed, Championed, Delivered

---

## JD Targeting Protocol

When a JD is available (from forge-jd-intelligence or directly):

1. Extract top 15 ATS keywords from JD
2. Ensure each keyword appears at least once in the resume (naturally, not stuffed)
3. Mirror the JD's exact terminology (e.g., if JD says "data lakehouse" not "data lake", use "data lakehouse")
4. Match the seniority language of the JD

---

## Output Format

**Claude.ai:** Output formatted resume in markdown. Offer to create .docx via docx skill.

**Claude Code / API:** Output as:
- Markdown (default)
- JSON with sections as structured fields (on request)
- Plain text for ATS paste (on request)

---

## Quality Checklist (run before delivering)

- [ ] Professional summary is role-targeted, not generic
- [ ] All bullets start with strong action verbs
- [ ] At least 70% of bullets are quantified
- [ ] JD keywords are naturally embedded (if JD provided)
- [ ] No "responsible for" or "helped with" language
- [ ] Candidate's authentic voice preserved
- [ ] No fabricated experience, titles, or companies
- [ ] Dates are consistent (Month Year format)
- [ ] Technical skills section is scannable in 10 seconds

---

## Downstream Handoffs

After resume generation:
- **→ forge-candidate-matching**: Score this resume against the target JD
- **→ forge-gap-analysis**: Identify what's still missing
- **→ forge-linkedin-branding**: Generate LinkedIn profile updates from this resume
