# Hackathon readiness — Digital Dark Spot

Based on the supplied two-page Shinchan Online Hackathon 2026 brief. This is an evidence checklist, not a predicted score or promise of winning.

| Criterion | Weight | Demonstrate | Remaining limit |
|---|---:|---|---|
| Problem understanding and relevance | 15% | A concrete passport question and practical next steps | Test with unfamiliar users; no user-study results yet |
| Innovation and originality | 20% | Expected questions first, inspectable source pairs, an evidence-update loop | Do not pitch this as ordinary search or a general fact checker |
| Working prototype and functionality | 25% | Question → source review → original quotes → issues → checklist → export | Some pages cannot be fetched; show this honestly |
| Technical implementation | 15% | FastAPI, bounded concurrent fetching, optional AI extraction, deterministic checks and regression tests | Rule extraction is conservative and format-dependent |
| Evidence, accuracy and transparency | 15% | Original quotes, pair-specific reasons, unread/undated/illustrative labels | Provenance is not truth; context needs human review |
| Presentation and demo | 10% | The short script, one useful concern, evidence inspection, saved checklist | Check actual narration, video readability and link access |

## Validation

- Run `python -m pytest tests -q` in the project environment.
- Check page-script syntax with `node --check`.
- Preserve `demo_session.json`; comparison changes must not rewrite evidence to obtain a desired result.
- Verify the example, a fresh search, source links, summary, additional evidence, report download and phone layout.
- Consult the final delivery notes for the actual executed test count. Do not infer passing validation for a later changed build from this document alone.

## Submission requirements

The PDF calls the platform Unista. The organizer-linked live listing identifies **Unstop** and states submission through Unstop only, using the registered account. Registration is closed; an existing registration must be confirmed.

Event: https://unstop.com/p/shinchan-online-hackathon-24-hour-hackathon-devengers-1771802

- Required name: **Advise Buddy**.
- Required description: use `SUBMISSION_DESCRIPTION.md`.
- Required public code: https://github.com/amruthak-bot/advise-buddy
- Optional live app: https://gapscope-qdmr.onrender.com/
- Optional video: record `DEMO_SCRIPT.md`, upload it and verify access.
- Slides are optional. Prioritize a working app and clear walkthrough.

The brief lists opening on **31 October 2026 at 10:00 AM** and closing on **1 November 2026 at 5:00 PM**. The existing checklist specifies IST. The live event listing also displays submission closing on 1 November 2026 at 5:00 PM IST. Final submission must be verified in the registered account.

## Final checks

1. Open the public repository and app without depending on a private connection.
2. Inspect the source evidence in the example and run a fresh question.
3. Download and inspect the checklist's references and resolution notes.
4. Watch the final video, including sound, and verify access to its link.
5. Ask someone unfamiliar with the app to explain one flag and their next step without coaching. Record actual feedback; do not invent results.
6. Submit through the registered account and retain its confirmation. A prepared form or attempted click is not proof of submission.
