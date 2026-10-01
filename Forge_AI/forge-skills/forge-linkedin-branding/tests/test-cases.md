# FORGE LinkedIn Branding — Test Cases

## Test 1: LinkedIn post — technical insight
**Prompt:**
```
Write a LinkedIn post for Shrenik Randive on this topic: "Most data teams build pipelines before fixing data contracts." 
His voice: direct, confident, short punchy sentences, no corporate speak.
```
**Expected:** Hook challenges the norm, personal insight, practical takeaway, ends with question. Under 400 words. Sounds like Shrenik's voice.

---

## Test 2: LinkedIn headline rewrite
**Prompt:**
```
Rewrite Om Ingale's LinkedIn headline. Current: "Data Engineer at Infosys"
Background: 7 years, Azure + Databricks + PySpark, H1B, targeting US senior DE roles.
```
**Expected:** New headline within 220 chars, includes core stack, seniority signal, differentiation.

---

## Test 3: About section generation
**Prompt:**
```
Write the LinkedIn About section for Deepak Satam.
- 20+ years Data & AI Architect
- Led multi-cloud migrations (Azure + GCP + AWS)
- Worked with HDFC, Infosys, TCS clients
- Passionate about building data-first organizations
- Open to VP/Director roles or consulting
```
**Expected:** Full About section 1,500–2,000 chars, hook opening, story element, expertise, CTA to connect.

---

## Test 4: 4-week content calendar
**Prompt:**
```
Build a 4-week LinkedIn content calendar for Shrenik Randive. He's a Senior Data Engineer building his personal brand in the data engineering space. 1 post per week. Focus: technical authority + career journey.
```
**Expected:** Week-by-week table with post type, topic, hook line, and goal for each week.

---

## Test 5: Career win post
**Prompt:**
```
Write a LinkedIn post announcing Om Ingale's new role as Senior Data Engineer (C2C through Exeliq). 
He came from Infosys in India, this is his first US project. Keep it genuine, not braggy.
Voice: humble but proud, grateful, forward-looking.
```
**Expected:** Story arc: where he was → what he worked on → what he's excited about. Ends with gratitude or lesson, not a "humbled and excited" opener.

---

## Assertions
- [ ] Post hooks never start with "I'm excited to share" or "I'm thrilled to announce"
- [ ] Headline always within 220 characters
- [ ] About section always has a CTA
- [ ] Calendar always includes post type, topic, and goal
- [ ] Voice profile referenced before generating (or minimal signals extracted)
- [ ] All posts end with CTA or engagement question
- [ ] Content sounds human and specific, not generic AI
