---
name: forge-voice-intelligence
description: >
  FORGE AI™ Voice Intelligence Agent (FORGE VoiceAI™) — learn, extract, and preserve a
  professional's authentic communication style, writing patterns, and personal brand voice from
  any existing content (LinkedIn posts, articles, resumes, emails, interview transcripts). Builds
  a Voice Profile that powers the Human Authenticity Engine (HAE) across all FORGE AI content
  generation. Use this skill whenever a user wants AI-generated content to sound like them,
  wants their voice captured before generating resumes or LinkedIn content, asks "make it sound
  like me", wants to audit whether content matches their authentic voice, or is setting up FORGE
  AI for the first time for a new client. Trigger on: "learn my voice", "analyze my writing style",
  "make this sound like me", "capture my voice", "create a voice profile", "this doesn't sound
  like me", "keep my authentic voice", "voice analysis". Part of the FORGE AI™ platform for
  Exeliq Consulting — powers forge-resume-intelligence, forge-linkedin-branding, forge-outreach-agent.
compatibility: "claude.ai, Claude Code, API — all surfaces"
---

# FORGE AI™ — Voice Intelligence Agent (FORGE VoiceAI™)

Agent 9 of the FORGE AI Multi-Agent Architecture.
Powers the Human Authenticity Engine (HAE) for all FORGE AI content agents.

---

## Purpose

Most AI-generated career content sounds the same. FORGE VoiceAI™ solves this by learning how
each professional naturally communicates and injecting that into every piece of content generated
— resumes, LinkedIn posts, outreach messages, articles.

---

## Input Sources (from richest to minimal)

Collect as much as available:

| Source | Value | Priority |
|--------|-------|----------|
| LinkedIn posts (10+ samples) | High — reveals authentic professional voice | 🥇 Best |
| Articles / blog posts | High — long-form writing patterns | 🥇 Best |
| Existing resume (their own version) | Medium — verb choices, framing style | 🥈 Good |
| Interview responses / transcripts | High — spoken-to-written voice | 🥈 Good |
| Professional emails they've written | Medium — communication tone | 🥈 Good |
| Brief self-description (fallback) | Low — minimal signals | 🥉 Fallback |

Request as many sources as the user can provide before building the profile.

---

## Voice Extraction Analysis

### Dimension 1 — Sentence Architecture
- Average sentence length (short/punchy vs long/structured)
- Paragraph structure preference
- Use of fragments for emphasis
- Numbered lists vs prose preference

### Dimension 2 — Vocabulary Fingerprint
- Technical jargon comfort level (heavy, moderate, light)
- Action verb preferences (what verbs do they naturally use?)
- Adjective density (sparse and precise vs descriptive and warm)
- Filler phrase patterns (what to avoid in their name)

### Dimension 3 — Tone Signature
- Formal ↔ Conversational scale (1–10)
- Humble ↔ Confident scale (1–10)
- Technical ↔ Strategic scale (1–10)
- Data-driven ↔ Story-driven scale (1–10)

### Dimension 4 — Structural Preferences
- How they open (with context, with a hook, with a statement)
- How they close (with a question, a CTA, a reflection)
- Use of capitalization for emphasis
- Em-dash, parentheses, or colon usage patterns

### Dimension 5 — Content Themes
- Recurring topics they return to
- Opinions they frequently express
- Industries or domains they reference
- Values they signal (impact, craft, leadership, learning, etc.)

---

## Output Format — FORGE Voice Profile™

```
## FORGE Voice Profile™
### Professional: [Name]
### Profile Date: [Date]
### Sources Analyzed: [list]

---

### 🎙️ Voice Signature Summary
[3–4 sentence summary of this person's authentic professional voice.
This becomes the "voice brief" injected into all other FORGE agents.]

---

### 📏 Tone Scales
| Dimension | Score | Description |
|-----------|-------|-------------|
| Formal ↔ Conversational | X/10 | [description] |
| Humble ↔ Confident | X/10 | [description] |
| Technical ↔ Strategic | X/10 | [description] |
| Data-driven ↔ Story-driven | X/10 | [description] |

---

### 🔤 Vocabulary Fingerprint
**Preferred Action Verbs:** [list]
**Signature Phrases:** [phrases they use that are distinctively theirs]
**Avoid in Their Voice:** [generic phrases that don't fit them]

---

### 📐 Structural Preferences
- Sentence length: [Short/Medium/Long/Mixed]
- Paragraph style: [Dense/Airy/Bulleted/Mixed]
- Opening style: [Direct statement / Context first / Hook / Question]
- Closing style: [CTA / Reflection / Open question / Declarative]

---

### 💡 Recurring Themes & Values
[What this person cares about professionally — shows up repeatedly]

---

### 🚫 Voice Anti-Patterns (Things That Don't Sound Like Them)
[Generic AI phrases and styles to avoid when writing in their voice]

---

### ✍️ Voice in Practice — Sample Rewrites
**Generic AI version:**
"Results-driven data engineer with expertise in cloud platforms."

**In [Name]'s voice:**
"[Rewritten in their actual voice using their vocabulary and patterns]"
```

---

## Voice Profile Application

### Injecting into other FORGE agents

When any other FORGE agent generates content for this person, prepend:

```
VOICE BRIEF FOR [NAME]:
[Voice Signature Summary from profile]
Key: [Top 3 vocabulary/style notes]
Avoid: [Top 3 anti-patterns]
```

This ensures resume bullets, LinkedIn posts, and outreach messages all carry the same voice.

---

### Voice Consistency Check

When a user says "this doesn't sound like me" or wants to audit generated content:

1. Compare generated content against Voice Profile dimensions
2. Identify which dimensions are mismatched
3. Produce a specific rewrite correcting voice drift
4. Update anti-patterns in the profile if new drift patterns emerge

---

## Multi-Surface Behavior

**Claude.ai:** Output Voice Profile in markdown. Store in conversation for future reference.

**Claude Code / API:** JSON output:
```json
{
  "professional": "",
  "voice_signature": "",
  "tone_scales": {},
  "preferred_action_verbs": [],
  "signature_phrases": [],
  "avoid_phrases": [],
  "sentence_length": "",
  "opening_style": "",
  "closing_style": "",
  "themes": [],
  "anti_patterns": []
}
```

---

## Downstream Handoffs

After building voice profile:
- **→ forge-resume-intelligence**: Generate resume in this person's voice
- **→ forge-linkedin-branding**: Generate posts and articles in this voice
- **→ forge-outreach-agent**: Write recruiter messages in this voice
