# Plan: Recruiter Email Agent v1 (Free Stack)

Build an agent that watches one mailbox (Gmail or Outlook), identifies genuine recruiter emails, matches the recruiter's requirement against our candidate profiles, and saves a reply as a draft in the same thread with the right resumes attached. A person reviews and sends every draft. v1 runs entirely on free, self-hosted tools, with a clear path to paid models if accuracy falls short.

## Scope

**In scope**
- One tracked mailbox, Gmail or Outlook, behind a common provider interface
- Recruiter detection with sender authenticity checks
- Candidate database where one candidate can have multiple role profiles, each with its own resume
- Matching profiles to the recruiter's job requirement
- Reply saved as a draft with resumes attached, never sent automatically
- Resume requests answered from the database
- Logging, tracing and an evaluation test set

**Out of scope for v1**
- Automatic sending
- Multiple mailboxes or multiple users
- Web portal (review happens in Gmail or Outlook)
- Calendar scheduling, cover letters, LinkedIn or WhatsApp

## Requirements and acceptance criteria

| # | Requirement | Accepted when |
|---|---|---|
| 1 | Classify recruiter email correctly | 95% or higher accuracy on the labelled test set |
| 2 | Candidates can have multiple profiles | Schema supports candidate, then profiles, then resumes; profiles load from existing resumes |
| 3 | Reply with matching profiles and resumes | Top matches are drafted with a short highlight each and the matching resume attached |
| 4 | Choose the best-suited tools | Stack below is chosen and tested on real emails |
| 5 | Output is a draft only | Agent code has no send path; Outlook app has no `Mail.Send` permission |
| 6 | Email must be genuinely from a recruiter, and resume requests are handled | Failed authentication or bulk mail never gets a draft; resume requests attach resumes from the database |
| 7 | Outlook and Gmail both supported | Same pipeline passes the test set on both providers |
| 8 | One mailbox tracked | Single mailbox configured, with sync state stored and resumed after restarts |

## How one email flows

1. **Fetch.** Poll every 2 minutes using Gmail's history ID or Outlook's delta link. Only new messages are fetched.
2. **Verify sender (code).** Require SPF, DKIM and DMARC to pass in `Authentication-Results`. Flag a `Reply-To` domain that differs from `From`, a free-mail sender claiming a company, or a domain that doesn't match the company named.
3. **Pre-filter (code).** Skip `List-Unsubscribe`, `Precedence: bulk`, job alerts, newsletters, auto-replies and our own sent mail.
4. **Classify and extract (model, JSON schema).**
   - Recruiter or not, with a confidence score.
   - Intent: new requirement, resume request, follow-up, interview, other.
   - Fields: role, skills, experience, location, candidate names mentioned, and whether a resume was requested.
5. **Match profiles.**
   - Hard filters: location, notice period, experience.
   - Hybrid search: vector similarity plus keyword match on skills.
   - Model re-rank of the top 10, with a one-line reason each.
   - Keep the top 1 to 3 above the threshold, and at most one profile per candidate.
6. **Draft.**
   - The reply uses only facts from the matched profiles, with one short highlight per profile and each resume attached.
   - If a candidate was named, that candidate's best-matching profile is used.
7. **Validate (code).** Before saving, check:
   - Recipient is the authenticated sender.
   - Every resume the draft mentions is attached, and each belongs to the right candidate.
   - No salary figures.
   - Facts used exist in the profile.
   - The draft is within the word limit.
8. **Save draft** in the original thread and label or categorise it "AI Draft". Low confidence or failed checks get a "Needs review" label instead, with no draft.
9. **Log** the classification, match scores, reasons and draft ID to the database and MLflow.

## Free tech stack

| Part | Choice |
|---|---|
| Language | Python 3.11+ |
| Email | Gmail API, Microsoft Graph |
| Classification and extraction | Ollama, Qwen3 8B, JSON output, thinking off |
| Re-rank and drafting | Ollama, Qwen3 14B (or 8B on smaller machines) |
| Embeddings | nomic-embed-text or bge-m3 via Ollama |
| Database | PostgreSQL with pgvector (self-hosted) |
| Resume files | Local folder, paths stored in PostgreSQL |
| PDF and DOCX parsing | pypdf, python-docx |
| Scheduler | Python loop or cron, every 2 minutes |
| Tracing and evaluation | MLflow (self-hosted) |
| Secrets | `.env` file, never committed |
| Hosting | Always-on PC, office machine, or Oracle Cloud Always Free VM |

Hardware: 16 GB RAM for 8B models, 32 GB or a GPU for 14B.

Mailbox access: use Microsoft 365, or a Google Workspace account with an "Internal" OAuth app. A personal gmail.com account in Testing mode needs re-authorising every 7 days.

## Project structure

```
email-agent/
  config/            settings, thresholds, prompts
  providers/         base.py, gmail.py, outlook.py
  pipeline/          verify.py, prefilter.py, classify.py, match.py, draft.py, validate.py
  db/                schema.sql, models.py, migrations/
  profiles/          import_resumes.py, embed_profiles.py
  eval/              dataset/, run_eval.py, metrics.py
  resumes/           resume files (gitignored)
  main.py            polling loop
  tests/
```

## Data model

| Table | Key fields |
|---|---|
| `candidates` | id, name, email, phone, location, notice_period, availability, active |
| `profiles` | id, candidate_id, title, skills, years_experience, summary, embedding, active |
| `resumes` | id, profile_id, file_path, version, uploaded_at, is_current |
| `mailbox_state` | provider, address, sync_cursor, last_run_at |
| `emails` | id, provider_message_id, thread_id, sender, received_at, auth_result, status |
| `classifications` | email_id, is_recruiter, intent, fields (JSON), confidence, model |
| `matches` | email_id, profile_id, score, reason, selected |
| `drafts` | id, email_id, provider_draft_id, profiles_used, attachments, validation (JSON), created_at |

## Action items

### Phase 0: Setup (week 1)
- [ ] Confirm the mailbox provider and account type (Microsoft 365, Workspace or personal Gmail)
- [ ] Register the OAuth app: Graph with `Mail.ReadWrite` only, or Gmail with the read and compose scopes
- [ ] Set up the machine: Python, Ollama with the models pulled, PostgreSQL with pgvector, MLflow
- [ ] Create the repo with the project structure above and the `.env` template

### Phase 1: Data (week 2)
- [ ] Create the database schema and migrations
- [ ] Build `import_resumes.py`: parse each resume, extract profile fields with the model, save for review
- [ ] Review and correct every imported profile by hand, then generate embeddings
- [ ] Label 200 to 300 real emails from the mailbox: recruiter or not, intent, fields and correct profiles

### Phase 2: Pipeline (weeks 3 to 4)
- [ ] Build the provider interface and the implementation for the chosen provider, with sync state
- [ ] Build sender verification and the pre-filter
- [ ] Build classification and extraction with fixed JSON schemas
- [ ] Build matching: filters, hybrid search, model re-rank, thresholds
- [ ] Build drafting with attachments and threading
- [ ] Build validation checks, the "AI Draft" and "Needs review" labels, and logging to MLflow

### Phase 3: Test and tune (week 5)
- [ ] Run `eval/run_eval.py` on the labelled set and record all metrics
- [ ] Run the adversarial emails: salary pressure, prompt injection, scam offers, vague requests, unknown candidate names, spoofed sender
- [ ] Tune prompts, thresholds and rules until the targets below are met
- [ ] Add the second provider and rerun the test set on it

### Phase 4: Pilot (weeks 6 to 7)
- [ ] Run live on the mailbox, reviewing every draft before sending
- [ ] Record per draft: sent as is, edited, or discarded, plus any wrong match
- [ ] Review results weekly and decide whether the free models are good enough

## Targets

| Metric | Target |
|---|---|
| Recruiter vs not-recruiter accuracy | 95% or higher |
| Intent accuracy | 90% or higher |
| Correct profile in the top matches | 90% or higher |
| Wrong candidate's resume attached | 0 |
| Adversarial checks passed | 100% |
| Drafts sent with no or minor edits (pilot) | 60% or higher |
| Time from email arrival to draft | Under 5 minutes on CPU |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Local models misclassify or match poorly | Rules and validation in code, labelled test set, option to switch only the model step to a paid API |
| Wrong resume or wrong candidate in a draft | One profile per candidate, attachment check, human review before sending |
| Scam or spoofed sender | Authentication checks, no draft on failure, "Needs review" label |
| Machine off or restarted | Sync cursor stored, missed mail picked up on the next run |
| Candidate data exposure | Data stays local, `.env` and resumes excluded from Git, database backups encrypted |
| Gmail tokens expiring every 7 days | Use Workspace "Internal" app or Outlook |

## Upgrade path when needed

1. Swap the model step to a paid API (GPT-5 mini class for classification, GPT-5 class for drafting), about $15 a month at current volume.
2. Move hosting to Azure Container Apps and managed PostgreSQL, about $40 to $50 a month in total.
3. Add a web review portal, more mailboxes and optional auto-send for proven email types.

## Open questions
- Which mailbox provider and account type will the pilot use?
- How many candidates and profiles need to be loaded at the start?
- Should a draft include all matches above the threshold, or at most one to three?
