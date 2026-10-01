# FORGE Voice Intelligence — Test Cases

## Test 1: Voice extraction from LinkedIn posts
**Prompt:**
```
Build a FORGE Voice Profile for Shrenik Randive from these LinkedIn posts:

Post 1: "3 years ago I couldn't explain what a data lakehouse was. Today I'm architecting one for 50M records a day. The gap between knowing and doing is just consistent reps."

Post 2: "Hot take: most data pipelines fail not because of bad code. They fail because nobody owns the data contract. Fix the ownership problem first."

Post 3: "Just got GCP Professional Data Engineer. Is it hard? Yes. Is it worth it? Only if you're going to use it. Certs without context are just wallpaper."
```
**Expected:** Voice profile showing: Conversational 8/10, Confident 8/10, Punchy sentences, direct opens, strong opinion-holder, anti-verbose, preferred verbs (architect, fix, own), anti-patterns (never "passionate about").

---

## Test 2: Voice consistency check (content audit)
**Prompt:**
```
This content was generated for Shrenik but he says it doesn't sound like him. Check it against his voice and rewrite:

"As a passionate and results-driven data engineering professional, I have had the privilege of working with cutting-edge cloud technologies to deliver transformative business outcomes across diverse industry verticals."
```
**Expected:** Clear diagnosis of voice mismatch (passive, corporate, verbose vs his punchy direct style). Rewrite in his voice.

---

## Test 3: Minimal input fallback
**Prompt:**
```
Create a voice profile for Om Ingale. He's a Cloud Data Engineer, quiet professional type, prefers to let his work speak. He doesn't write much online.
```
**Expected:** Graceful fallback, requests resume or any sample writing. If none available, builds a provisional profile from description with note that it's low-confidence until more samples provided.

---

## Test 4: Voice-injected content generation
**Prompt:**
```
Using Shrenik's voice profile, rewrite this generic resume summary:
"Experienced data engineer with expertise in cloud platforms and data pipeline development."
```
**Expected:** Rewrite in his confident, direct, punchy voice. No corporate fluff. Concrete and specific.

---

## Test 5: Multi-source voice extraction
**Prompt:**
```
Build a voice profile using this: resume summary says "I architect data systems at scale", his article opens with "Most data teams are solving the wrong problem", and in an interview he said "I don't build pipelines. I build trust in data."
```
**Expected:** Strong voice profile recognizing consistent themes (architecture thinking, systemic thinker, challenge-the-assumption opener), philosophy-driven, precise language user.

---

## Assertions
- [ ] All 5 tone dimensions always scored (1–10)
- [ ] Vocabulary fingerprint always includes preferred verbs AND phrases to avoid
- [ ] Sample rewrite ("generic vs in their voice") always included
- [ ] Minimal input handled gracefully with explicit confidence note
- [ ] Voice profile JSON available on request
- [ ] Downstream handoffs clearly offered after profile is built
