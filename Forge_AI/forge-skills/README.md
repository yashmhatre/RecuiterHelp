# FORGE AI™ Skills Suite
## AI-Powered Career Acceleration Platform — Exeliq Consulting

---

## Overview

This skills suite implements the FORGE AI™ multi-agent architecture as Claude skills. Each skill
corresponds to one or more FORGE AI agents and can be installed individually or as a complete suite.

---

## Skill Index

| # | Skill | FORGE Agent(s) | Layer |
|---|-------|---------------|-------|
| 1 | `forge-jd-intelligence` | Agent 2 — JD Intelligence | Talent Intelligence |
| 2 | `forge-resume-intelligence` | Agent 4 — Resume Intelligence | Career Readiness |
| 3 | `forge-candidate-matching` | Agent 3 — Candidate Matching | Talent Intelligence |
| 4 | `forge-gap-analysis` | Agent 5 — Gap Analysis | Career Readiness |
| 5 | `forge-voice-intelligence` | Agent 9 — Voice Intelligence | Human Authenticity |
| 6 | `forge-linkedin-branding` | Agent 10 — LinkedIn Branding | Visibility & Branding |
| 7 | `forge-outreach-agent` | Agent 11 — Outreach | Visibility & Branding |
| 8 | `forge-simulation` | Agent 7 — FORGE Sim™ | Interview Simulation |
| 9 | `forge-career-roadmap` | Agent 6 — Learning & Development | Career Readiness |
| 10 | `forge-analytics` | Agents 12 + 13 — Success Tracking + Career Intelligence | Analytics & Growth |

---

## Agent Flow Diagram

```
JD → forge-jd-intelligence
         ↓
    forge-candidate-matching  ←→  forge-resume-intelligence
         ↓                              ↑
    forge-gap-analysis    →    forge-career-roadmap
         ↓
    forge-simulation    (validates readiness)
    
Parallel track (always running):
    forge-voice-intelligence  →  forge-linkedin-branding
                              →  forge-outreach-agent
                              →  forge-resume-intelligence

Tracking layer (all agents feed into):
    forge-analytics
```

---

## Recommended Start Sequence (New Client)

1. **forge-voice-intelligence** — capture their authentic voice first
2. **forge-jd-intelligence** — analyze their target roles
3. **forge-candidate-matching** — score them against target JDs
4. **forge-gap-analysis** — identify what's missing
5. **forge-resume-intelligence** — build targeted resume
6. **forge-career-roadmap** — plan how to close gaps
7. **forge-linkedin-branding** — build visibility
8. **forge-outreach-agent** — start reaching out
9. **forge-simulation** — prepare for interviews
10. **forge-analytics** — track everything

---

## Compatibility

All skills work on:
- **Claude.ai** (chat interface) — full markdown output
- **Claude Code** (terminal) — markdown + JSON output modes
- **API** (custom apps) — JSON output for all agents, structured for integration

---

## Proprietary IP Alignment

| FORGE IP | Implemented In |
|----------|---------------|
| FORGE Match™ | forge-candidate-matching |
| FORGE VoiceAI™ / HAE | forge-voice-intelligence + forge-resume-intelligence |
| FORGE Sim™ | forge-simulation |
| FORGE Insights™ | forge-analytics |
| FORGE Growth™ | forge-linkedin-branding + forge-outreach-agent |

---

## Test Cases

Each skill has a `tests/test-cases.md` file with 5–6 test scenarios and assertions.
Use these to validate skill behavior after installation.

---

*FORGE AI™ is a product of Exeliq Consulting. Built with LearningBuddy.*
