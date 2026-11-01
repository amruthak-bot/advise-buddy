# Advise Buddy — Blueprint-First Information Gap Investigator

Locked concept (2026-10-31): a blueprint-first, evidence-driven
information gap investigator. "You cannot identify what's missing
until you define what complete looks like."

## Stack (decided 2026-10-31)

- **Backend:** Python + FastAPI (NOT Next.js — see below).
- **Frontend:** vanilla JS + Tailwind, served by the same FastAPI
  service, so one repo = one deploy (Render, single web service).
- **LLM:** Google Gemini 2.5 Flash, free tier via AI Studio, behind a
  thin wrapper (`backend/app/llm.py`). Key from `GEMINI_API_KEY`
  env var only, server-side. Never commit a key, never put one in
  frontend code or chat.
- **No key, no problem:** without `GEMINI_API_KEY`, the rule-based
  fallback extractor runs, so the app and the demo work end-to-end
  with zero live LLM calls.

Why FastAPI over the spec's Next.js default: the builder's proven
stack is FastAPI + vanilla JS (VALIDRIFT); Render is already familiar;
Vercel (Next.js's natural host) is blocked on OAuth for this user;
and learning React/TypeScript/Next.js on deadline day is unnecessary
risk. FastAPI serving static files matches the "one repo, one deploy"
goal.

## Hard rules (locked)

- Official silence means "Not confirmed in the official sources
  reviewed" — never "false". Silence is not disproof.
- Quotes are displayed verbatim only (exact substring after
  whitespace/quote normalisation). Fuzzy matching only LOCATES a
  candidate passage; if verification fails, the passage's original
  text is shown as "uncertain", never a rewritten quote.
- Undated sources are labelled "undated", never given a guessed date.
- The LLM never invents dates and never produces a displayed quote
  without passing the substring check.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
GEMINI_API_KEY=... .venv/bin/uvicorn backend.app.main:app --reload --port 8000
# open http://localhost:8000
```

Tests: `.venv/bin/pytest tests/ -q`

## Deploy on Render (one web service, no separate frontend)

1. Push this repo to GitHub. On Render: New → Web Service → connect
   the repo. (Render dashboard steps need the repo owner's login.)
2. Build command: `pip install -r backend/requirements.txt`
   Start command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   (FastAPI serves the frontend itself, so no static-site service.)
3. Environment (optional): `GEMINI_API_KEY` — without it the app runs
   fully on the rule-based fallback, which is what the demo uses.
   `TAVILY_API_KEY` — without it, "Find sources on the web" reports
   that web search is not configured; paste still works. With a free
   Tavily key, typing a question and clicking "Find sources on the
   web" searches the web, fetches the result pages, fills the source
   editor, and runs the analysis. Fetched text goes through the same
   quote verification as pasted text; pages that cannot be fetched
   show as "Not fetched", never invented. Official labels on
   discovered sources are domain-heuristic suggestions the user can
   change in the editor.
4. After deploy, open the public URL and click "Load demo session",
   then "Run analysis": expect the fee conflict, processing conflict,
   Official Silence flags, renewal + contact gaps, and the Tatkaal
   proposal (see Demo session below). If any of those are missing on
   the public URL, the deploy is not the same build — do not submit
   that URL.

## Demo session

`demo_session.json` now holds GENUINE passport excerpts, retrieved
2026-10-31 (short verbatim passages per source, each with its URL;
full pages at those URLs). One explicitly-titled "Sample source
(illustrative)" — an older-cycle 2024 guide, authored for the demo —
is included only to show the possibly-outdated state.

Sources: Passport Seva official portal homepage (official, undated
excerpt); Bharat Seva Guide (Feb 2026, pre-July fees); TripFactory
guide (undated, pre-July fees); Daily Jagran (19 Sep 2026, post-July
fees); InfoBits (July 2026 fee hike). Verified demo outcome:
Completeness 86% of the blueprint covered by evidence in the sources
reviewed (coverage of the blueprint, not factual certainty);
confirmed by an official source: 2 of 9; fee
conflict (pre-July Rs 1,500 vs post-July Rs 2,500 — the real 1 July
2026 revision) and processing conflict, both labelled as possibly
changed over time because their sources carry different dates;
Official Silence flags on eligibility, fee, portal, processing and
police verification (none confirmed in the official homepage excerpt
reviewed); renewal and contact gaps (Evidence Debt 2); Tatkaal
Challenge proposal; and all three freshness states (current /
undated / possibly_outdated). "Load demo session" runs the analysis
by itself, and re-runs print a one-line "Changed in this re-run"
summary. Known limit, stated honestly: a verified quote proves the
words appear in the source and the source is current — it does NOT
prove the claim applies to the user's applicant category,
jurisdiction, or time period. The drawer shows the exact quote so
the user can judge applicability before acting on it.

Honesty notes: excerpts are curated passages, not full pages —
renewal and contact sections were not included in the pasted
excerpts, so those gaps are relative to the sources reviewed, which
is exactly what the product reports. No contradiction was forced:
the fee and processing conflicts come from the genuine sources.

Fee-conflict verification (checked 2026-10-31): the Rs 1,500 vs
Rs 2,500 figures are the SAME category, not a category mix-up —
ordinary fresh passport or reissue, 36 pages, Normal scheme,
10-year validity. The Gazette of India (Extraordinary, Part II,
Section 3(i), No. 465, 25 June 2026; MEA Notification G.S.R. 516(E)
dated 20 June 2026, in force 1 July 2026, substituting Schedule IV
of the Passports Rules, 1980) sets the new Normal fee at Rs 2,500
(Tatkaal Rs 5,000 inclusive). The Rs 1,500 figure is the pre-revision
fee for the identical category, still carried by pre-July guides.
Demo narration should say exactly that: the guides disagree
because the fee changed on 1 July 2026, and the older guides were
never updated — that is the conflict Advise Buddy surfaces.

## What is built (scaffold)

- `backend/app/models.py` — data model (spec section 3)
- `backend/app/templates.py` — passport / scholarship / college /
  job-offer templates (questions only, no factual claims)
- `backend/app/llm.py` — Gemini wrapper, extraction prompt + JSON
  schema, comparison, rule-based fallback extractor
- `backend/app/verify.py` — quote verification + fuzzy locate
- `backend/app/rules.py` — date/cycle regex, freshness, Official
  Silence, Evidence Debt, checklist ranking
- `backend/app/engine.py` — the pipeline (spec section 4)
- `backend/app/main.py` — FastAPI app + endpoints
- `frontend/index.html` — setup, sources, heatmap + evidence drawer,
  checklist, proposals tray, verification loop
- `tests/` — quote verification, date regex, silence rule, ranking
