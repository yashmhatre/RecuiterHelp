# FORGE Outreach Agent — Test Cases

## Test 1: LinkedIn connection request
**Prompt:**
```
Write a LinkedIn connection request from Om Ingale to a recruiter at Amazon who posts about Data Engineering roles. Om is a Cloud Data Engineer, 7 years experience, Databricks + Azure.
```
**Expected:** Under 300 chars, specific to recruiter/Amazon, mentions his relevant stack, not generic "I'd love to connect."

---

## Test 2: Exeliq candidate submission email
**Prompt:**
```
Write a candidate submission email for Om Ingale (Cloud DE, H1B, Exeliq sponsor, available immediately, $65/hr C2C) to a Chicago client who posted for a Senior Data Engineer with Databricks + Python requirements. FORGE Match score is 88/100.
```
**Expected:** Uses Exeliq C2C submission template, includes match score, all required details, clear CTA.

---

## Test 3: Cold recruiter email
**Prompt:**
```
Write a cold email from Nishad Patkar to a recruiter at Google Cloud who focuses on data engineering roles. Nishad has 5 years, Azure background, targeting GCP roles as he pivots.
```
**Expected:** Short (150–200 words), one clear ask (15-min call), Azure→GCP bridge narrative as hook, no resume attached in first touch.

---

## Test 4: Interview thank-you note
**Prompt:**
```
Write an interview thank-you email for Shrenik Randive. He interviewed for a Staff Data Engineer role at Stripe. Interviewer was Sarah Chen. They discussed his experience with exactly-once delivery in Kafka during the technical round.
```
**Expected:** Under 150 words, specific to Sarah and the Kafka discussion, reinforces fit, sent within 2 hours recommendation.

---

## Test 5: Referral request
**Prompt:**
```
Write a referral request LinkedIn message from Jayesh Chawan (Senior HR Director) to a former colleague now at Akanksha Foundation. Jayesh is applying for their Head of HR role.
```
**Expected:** Warm, specific, low-friction ask, offers to draft the intro message himself. Under 150 words.

---

## Test 6: Follow-up 3-touch sequence
**Prompt:**
```
Generate a 3-message follow-up sequence for Om Ingale following a recruiter outreach that got no response. First sent Monday. Keep each message different.
```
**Expected:** Day 1 (reminder, brief), Day 4 (new angle/value add), Day 9 (graceful close). Each under 100 words. Never aggressive.

---

## Assertions
- [ ] LinkedIn connection requests always ≤300 characters
- [ ] Cold emails never include resume as attachment in first message
- [ ] Submission emails always include work auth, availability, rate, and match score
- [ ] Thank-you notes always reference something specific from the interview
- [ ] Referral requests always offer to make it easy for the referrer
- [ ] 3-touch sequences are each distinct — no copy-paste repetition
- [ ] Voice profile referenced or minimal voice signals extracted
- [ ] Subject lines included for all email types
