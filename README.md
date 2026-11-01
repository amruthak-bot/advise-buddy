# Advise Buddy — know what to verify next

**Search gives you information. Advise Buddy shows the questions that information still doesn't answer.**

[Open the live app](https://advise-buddy-demo.onrender.com/) · [Demo script](DEMO_SCRIPT.md) · [Submission description](SUBMISSION_DESCRIPTION.md) · [Hackathon readiness](HACKATHON_READINESS.md)

Built for **Digital Dark Spot**, the Shinchan Online Hackathon 2026 information-gap challenge. The tool supports general research and starting checklists for scholarships, college admissions, job offers and passport applications. The cached passport investigation is one worked example. An editable checklist defines what the sources should cover.

## Try it in a minute

1. Enter a topic, name or question and select **Research**. The app chooses relevant checks and collects sources automatically; **Adjust the search** is optional. Or select **Try the passport example** for a cached walkthrough.
2. Read **What we found** and the first three checks, then inspect the clickable coverage heatmap. Each concern includes a next step and supporting sources.
3. Add evidence, record a resolution note, or select **Save checklist** to download the results and references.

The free Render service can take around a minute to wake up. Pages that cannot be fetched are shown as unread and contribute no evidence.

## Why it goes beyond a summary

- Starts from expected questions and reveals what the reviewed sources do not answer.
- Records the specific pair of original verified quotes behind each numeric comparison; considers all pairs, not just the first source.
- Treats different currencies, time units, explicit categories, multiple prices and overlapping ranges as needing context rather than automatic contradictions.
- Rejects common weak matches: headings, navigation and topic mentions without the requested detail.
- Shows original quotes separately from potential issues and proposed checklist additions.
- Lets users add evidence and retain a checklist with quotes, URLs, comparison reasons, fetch status and resolution notes.

## Evidence and limits

**A verified quote means it occurs in reviewed text. It does not mean the statement is true, current or applicable.**

Missing information is scoped to the pages actually reviewed. Absence from official excerpts does not make a third-party claim false. Domain-based official labels are editable suggestions. Date detection finds dates in text, not necessarily publication dates. The deterministic fallback may miss indirect answers and unsupported formats; it does not resolve jurisdiction, eligibility or arbitrary contradictions in document requirements. Confirm important details on the official website.

The original cached demo excerpts are preserved, including a source clearly labelled **illustrative**. The example is reproducible, not a claim about current passport fees or rules.

## Architecture

Question + editable checklist → web search or pasted text → passages → extraction → quote/quality checks → source-pair comparisons → prioritized checks → evidence update and export.

Python/FastAPI serves a buildless HTML/CSS/JavaScript interface. Tavily discovers pages; fetching uses a bounded worker pool. Optional Gemini extraction is followed by deterministic checks. Without a Gemini key, deterministic extraction runs. Numeric comparisons use original verified quotes, not generated summaries.

No account or database is required. Investigations stay in the open page; export before leaving. The app does not save investigations server-side.

## Local setup — Windows

Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt pytest
.\.venv\Scripts\python -m pytest tests -q
.\.venv\Scripts\python -m uvicorn backend.app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`. For macOS/Linux use `.venv/bin/python` instead of `.venv\Scripts\python`.

The example and pasted-source flow work without keys. Set `TAVILY_API_KEY` in the server environment for live discovery; `GEMINI_API_KEY` is optional. Never commit keys, put them in frontend code or paste them into source excerpts.

## Render deployment

- Python web service, repository root, branch `main`.
- Build: `pip install -r backend/requirements.txt`
- Start: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Enter `TAVILY_API_KEY` privately in Render. Gemini is optional.

## Validation and next steps

Run `python -m pytest tests -q` in the environment. Tests cover extraction, quotes, missing/unread sources, dates, official-source flags, discovery and context-aware comparison. Browser verification covers the example, a fresh question, source evidence, additional evidence, report download and phone-width layout.

Next priorities: real-user usability testing, stronger jurisdiction matching, document formats and multilingual research. No user-study results, universal accuracy or win probability are claimed.
