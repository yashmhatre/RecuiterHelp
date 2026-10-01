---
name: forge-linkedin-branding
description: >
  FORGE AI™ LinkedIn Branding Agent — generate LinkedIn posts, articles, content calendars,
  profile sections (headline, About, featured section), and thought leadership content for IT
  professionals. Powered by the Human Authenticity Engine to maintain personal voice consistency.
  Use this skill whenever a user wants LinkedIn content, a personal branding strategy, a content
  calendar, a LinkedIn profile rewrite, thought leadership posts, or technical articles for
  LinkedIn. Trigger on: "write a LinkedIn post", "create a content calendar", "rewrite my LinkedIn
  headline", "generate a LinkedIn article", "help with my LinkedIn About section", "build my
  personal brand on LinkedIn", "create thought leadership content", "LinkedIn strategy", "LinkedIn
  profile optimization". Works with forge-voice-intelligence to maintain authentic voice. Part of
  the FORGE AI™ Visibility & Branding Layer for Exeliq Consulting.
compatibility: "claude.ai, Claude Code, API — all surfaces"
---

# FORGE AI™ — LinkedIn Branding Agent

Agent 10 of the FORGE AI Multi-Agent Architecture.
Part of the Visibility & Branding Layer.

---

## Content Types Supported

| Type | Description | Avg Length |
|------|-------------|------------|
| **LinkedIn Post** | Feed post, insight, story, or opinion | 150–600 words |
| **LinkedIn Article** | Long-form thought leadership | 800–2000 words |
| **LinkedIn Headline** | 220-char professional headline | 220 chars max |
| **About Section** | 2,600-char profile summary | 1,500–2,600 chars |
| **Content Calendar** | 4–12 week posting plan | Plan document |
| **Carousel Post** | Multi-slide post (text outline) | 8–12 slides |

---

## Voice-First Protocol

ALWAYS check if a Voice Profile exists for this person (from forge-voice-intelligence) before
generating content. If no profile exists, extract minimal voice signals from:
- Their existing LinkedIn posts (ask to paste a few)
- How they describe themselves in this conversation
- Their resume language

Never generate generic-sounding content. Each piece must feel authored, not templated.

---

## LinkedIn Post Framework

### Post Types with Formats

**1. Insight Post (Most shareable)**
```
[Hook line — bold claim, surprising stat, or counterintuitive statement]

[3–5 bullet points or short paragraphs developing the insight]

[Personal connection or story — 2–3 lines]

[CTA or closing reflection — question or takeaway]

[3–5 relevant hashtags]
```

**2. Story Post (High engagement)**
```
[Opening: "3 years ago / Last week / I almost quit..."]
[The situation — brief, human]
[The turning point]
[The lesson]
[Universal takeaway]
[Question to audience]
```

**3. Technical Post (Authority-building)**
```
[Bold technical claim or misconception to debunk]
[The correct framework or explanation]
[Concrete example from their experience]
[Practical takeaway for the reader]
[Engage: "What's your approach to X?"]
```

**4. Career Win Post (Visibility)**
```
[The achievement — be specific]
[What it took — honest, not braggy]
[Who helped or what enabled it]
[What's next / what they're building toward]
[Gratitude note if appropriate]
```

---

## Content Calendar Framework

### 4-Week Starter Calendar (1 post/week)

| Week | Post Type | Topic Example | Goal |
|------|-----------|---------------|------|
| Week 1 | Story | Career pivot or key lesson | Build relatability |
| Week 2 | Technical | Tool/concept they're expert in | Build authority |
| Week 3 | Insight | Industry trend or hot take | Drive engagement |
| Week 4 | Career Win | Recent achievement or milestone | Build credibility |

### 8-Week Growth Calendar (2 posts/week)
Add: Week 5–8 with Carousel posts and LinkedIn Articles.

### 12-Week Full Program
Mix: 2x posts/week + 1 article/month + profile refresh at week 4 and week 8.

---

## LinkedIn Headline Formula

```
[Role Identity] | [Core Value Prop] | [Signature Stack or Achievement]
```

Examples:
- "Cloud Data Engineer | Building Reliable Data Platforms at Scale | Azure · Databricks · Python"
- "Data Architect | Helping Enterprises Trust Their Data | 20+ Years | Snowflake · dbt · Spark"
- "ML Engineer | Turning Research Papers into Production ML | PyTorch · Kubernetes · MLflow"

Rules:
- Max 220 characters (hard limit)
- Use | separators
- Include 2–3 tech stack keywords (SEO)
- One differentiation signal (scale, outcome, or years)

---

## About Section Structure

```
[Opening hook — 1 strong sentence about what they do and why it matters]

[Origin story or defining experience — 2–3 sentences]

[Current expertise and what they build/solve — 3–4 sentences]

[Notable projects, companies, or scale signals — 2–3 bullets]

[Future direction or what they're building toward]

[CTA — "Open to..." or "Connect with me if..." or "DM me about..."]
```

---

## Output Format

**For posts:** Full post text, ready to copy-paste into LinkedIn.
**For articles:** Full article with title, subtitle, and sections.
**For calendar:** Table + brief content briefs for each post.
**For profile sections:** Section text within character limits.

Always note: "Review before posting — personalize any specific numbers or details."

---

## Voice Check

After generating, check:
- ❌ Remove any generic opener ("I'm excited to share...")
- ❌ Remove corporate buzzwords ("synergy", "leverage", "passionate")
- ✅ Verify action verbs match the person's voice profile
- ✅ Confirm sentence rhythm matches their style
- ✅ Ensure it sounds human, not AI-generated

---

## Downstream Handoffs

- **→ forge-voice-intelligence**: Build voice profile first if not done
- **→ forge-analytics**: Track post performance once published
- **→ forge-outreach-agent**: Follow up with recruiters who engage with posts
