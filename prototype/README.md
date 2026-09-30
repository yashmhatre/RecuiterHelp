# Prototype

A working end-to-end demo of the agent, in a web page. Built in one sitting; deliberately not the
production design in `Plan.md`.

## Run it

```bash
.venv/Scripts/python.exe -m prototype.app     # then open http://127.0.0.1:8000
```

Two screens:

- **Candidates** — enter a candidate's details and upload their resume. Upload first and the form
  pre-fills from the file; correct it before saving. One person can hold several role profiles:
  submit again with the same email and a different title.
- **Inbox** — paste a recruiter email or pick a sample, then watch every stage run. The
  adversarial samples are the interesting ones: they show the pipeline *refusing* to draft.

## The model

Reads whichever key is in `.env`, in this order, and falls back to keyword heuristics with none:

| Key | Where to get it | Notes |
|---|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Free tier. Currently in use. |
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) | Free tier, faster |
| `OPENAI_API_KEY` | any OpenAI-compatible endpoint via `OPENAI_BASE_URL` | |
| `OLLAMA_HOST` | local Ollama | Nothing leaves the machine |

The badge in the header shows which backend actually answered, so a degraded run is never
mistaken for a good one. Gemini's free tier returns `503` under load, so the client retries with
backoff and then tries alternate models before giving up.

**The model never reads a resume.** It classifies the email and re-ranks short profile summaries.
Resume files are bytes copied into the draft. So even on a hosted API, resumes stay on this
machine.

## What it does and does not do

Reuses the tested production stages: [`pipeline/verify.py`](../pipeline/verify.py) and
[`pipeline/prefilter.py`](../pipeline/prefilter.py). Everything else is a miniature in
[`pipeline.py`](pipeline.py).

Deliberate shortcuts, all reversible:

| Plan | Prototype | Why |
|---|---|---|
| Gmail / Graph API | paste into a web form | OAuth registration is hours of waiting |
| PostgreSQL + pgvector | SQLite, same column names | migration later, not a rewrite |
| embeddings + vector index | skill overlap + model re-rank | better than an index at 20 profiles, and needs no embedding model |
| model writes the reply | templates write it, model only ranks | removes "the model invented a fact about a candidate" entirely |
| Ollama Qwen3 | any free hosted API | no 5 GB download |

Kept, because they are the point of the product:

- **Verification runs before any model call.** A spoofed sender never reaches one.
- **One profile per candidate.** The same person is never offered twice.
- **The recipient is the verified sender**, never `Reply-To`, never an address from the body.
- **The validation gate discards the draft** rather than saving a bad one.
- **No send path.** A draft downloads as `.eml` for a person to open and send.

## Order of the pipeline

```
Pre-filter  ->  Verify  ->  Classify  ->  Match  ->  Draft  ->  Validate
(bulk, auto)   (SPF/DKIM   (model)      (filters,  (template)  (9 checks)
               /DMARC)                   re-rank)
     |             |            |            |                     |
  skipped_bulk  needs_review  not_recruiter  needs_review     needs_review
                                                              (draft discarded)
```

## Tests

`pytest tests/test_prototype.py` — 28 tests, offline, no API key needed.

The one that matters is
`test_a_request_for_an_unknown_person_never_substitutes_a_different_candidate`. The first version
of this prototype answered a request for "Zebediah Featherstonehaugh" by attaching a different
candidate's resume. That is the single failure the plan gives a target of **zero**, and it is now
blocked in two independent places: matching refuses to fall through to general scoring when a
named person does not resolve, and the validation gate rejects the draft even if matching were
wrong.

## Known limits

- The keyword fallback has poor recall — it missed a plainly genuine requirement in testing. It
  exists so the demo runs with no key, not to be good.
- Location matching is generous. A wrongly excluded candidate is invisible; a wrongly included one
  scores low and gets read.
- The pre-filter and verifier have only been measured against the 10 synthetic emails. The real
  numbers need the labelled set from ticket P1-05.
