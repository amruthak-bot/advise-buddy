# GapScope — know what to verify next

## Problem

When researching a passport application, scholarship or other important decision, people find plenty of information but struggle to see what remains unanswered. Sources can use different categories, list different figures, omit important details or contain old information. A fluent summary can conceal those gaps.

## Solution and core workflow

GapScope turns several sources into an evidence-backed verification checklist. The focused prototype demonstrates Indian passport research. Users enter a question and search the web, try a reproducible example, or paste source text. An editable checklist defines what a complete answer should address.

The main result shows three prioritized checks in plain language. Each explains the concern, the next action and the supporting evidence. Additional checks and a detailed source-by-question heatmap remain available without overwhelming the first screen.

The workflow is question → source collection → extracted information → potential gaps/comparisons → next-step checklist. Users can inspect original quotes, add evidence, see what changed, record a resolution note and download a checklist with references.

## Distinctive features

- **Expected questions first:** detect unanswered requirements instead of summarizing only the text search returned.
- **Traceable comparisons:** every numeric signal records a specific pair of original verified quotes and its reason. All pairs are considered.
- **Context before contradiction:** different currencies, time units, explicit categories, multiple prices and overlapping ranges require review instead of automatically becoming conflicts.
- **Evidence quality:** bare headings, common navigation and topic mentions without an answer do not count as complete evidence.
- **Transparent dashboard:** source quotes, potential issues, freshness labels and suggested checklist additions are distinct. Suggestions require user acceptance.
- **Practical output:** save the next-step checklist with source URLs, original quotes, comparison reasons, unread-page status and resolution notes.

## Technical implementation

Python/FastAPI serves a buildless HTML/CSS/JavaScript interface. Tavily provides web discovery; a bounded worker pool fetches independent pages while preserving search order. Optional Gemini extraction is followed by deterministic quote verification and answer-quality checks. Without a Gemini key, deterministic extraction runs. Numeric comparisons use original verified quotes, never a model's paraphrased figures.

Regression tests cover extraction, provenance, missing/unread sources, dates, official-source flags, discovery and comparisons. Comparison cases include currencies, ranges, categories, source-order independence and misleading generated summaries. Browser checks cover desktop and phone-width flows and checklist export.

## Accuracy, scope and uncertainty

A verified quote proves textual provenance, not truth or applicability. A missing answer means no usable answer in the reviewed sources, not proof of absence. Official labels on web results are editable domain-based suggestions. Absence from official excerpts does not make a third-party statement false.

This is a focused prototype, not a general fact checker or eligibility decision-maker. Deterministic matching can miss indirect answers; dates detected in page text may not be publication dates; jurisdiction and applicant applicability still need human review. Investigations remain in the open page; no account or server-side database is required, and users can export before leaving.

The cached example preserves cached source excerpts and one clearly marked illustrative older source. It demonstrates the workflow and is not asserted to establish current passport fees or rules. The live application and accompanying walkthrough script make the core workflow inspectable; the final video is a separate recording step.

## Future scope

Real-user usability testing, stronger jurisdiction/category matching, broader document formats and multilingual research. No completed user study, fabricated impact metric or guaranteed accuracy is claimed.

**GapScope helps users leave research with a clearer next step, not just another answer.**
