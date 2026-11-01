# Advise Buddy — Blueprint-First Information Gap Investigator

**Tagline:** Discover what's missing, not just what's available.

> Paste-ready for the Unista submission form. Verified against the
> FastAPI scaffold on 2026-10-31: every feature below is implemented,
> including web discovery (which needs a Tavily API key on the
> server; without one, the paste flow still works).

### Problem Statement

Every day, people rely on information from websites, articles, official portals, and online guides to make important decisions. However, finding information does not necessarily mean finding complete or reliable information.

Existing search and summarization tools help users understand what sources say, but users can still struggle to identify missing details, contradictory claims, outdated information, and statements that lack official confirmation.

### Our Solution

Advise Buddy is an AI-assisted information gap detection platform that helps users investigate the completeness and reliability of information across multiple sources.

Our core idea is simple: **You cannot identify what's missing until you define what complete looks like.**

Instead of immediately summarizing information, Advise Buddy starts with an editable **Expectation Blueprint** — a structured checklist of the information needed to answer a question completely. Users can select predefined templates for scenarios such as passport applications, scholarships, college admissions, and job offers.

The platform then analyzes the provided source material against the blueprint and presents the findings in an interactive **Evidence Coverage Heatmap**.

Each requirement is compared across sources, helping users identify available evidence, potential information gaps, possible contradictions, and freshness concerns. Users can inspect supporting passages rather than relying only on AI-generated conclusions.

### Key Features

**1. Blueprint-First Analysis:** Defines what a complete answer should cover before evaluating the available evidence.

**2. Evidence Coverage Heatmap:** Visually compares requirements across sources, with clickable evidence and separate indicators for conflicts and outdated information.

**3. Verifiable Source Evidence:** Uses deterministic quote verification to ensure displayed quotations originate from the reviewed material. Unverified evidence is not presented as confirmed.

**4. Official Silence Detection:** Identifies claims that appear in third-party material but are not confirmed in the relevant official sources reviewed, without treating silence as proof of falsity.

**5. Evidence Freshness Analysis:** Highlights potentially outdated information and explicitly identifies undated sources.

**6. Evidence Debt and Prioritized Checklist:** Summarizes unresolved information gaps and recommends which questions should be verified first.

**7. Verification and Re-analysis:** Allows users to add further evidence, reassess findings, and track resolved gaps. Manual resolution requires an explanatory note.

**8. Blueprint Challenge Mode:** Suggests additional requirements discovered during source analysis, allowing users to decide whether to expand the blueprint.

**9. Automatic Web Discovery:** From the user's question alone, Advise Buddy searches the web, fetches result pages, and adds them as sources for analysis — no pasted URLs needed. Fetched text goes through the same deterministic quote verification as pasted text, pages that cannot be fetched are shown as unfetched rather than invented, and official-versus-third-party labels on discovered sources are heuristic suggestions the user can change.

### Technical Implementation

Advise Buddy is built using Python and FastAPI for the backend, with JavaScript and Tailwind CSS for the frontend. The analysis engine supports Google Gemini for AI-assisted evidence extraction and comparison, alongside a rule-based fallback for demonstrations without live AI access.

The application separates evidence extraction, quote verification, freshness checks, official-silence detection, and checklist generation into distinct processing stages. This improves transparency, testability, and reliability.

A cached demonstration session allows the workflow to be explored without depending on external AI availability.

### What Makes Advise Buddy Different?

Advise Buddy focuses on **information completeness rather than answer generation alone**.

Its main differentiator is the combination of a user-controlled completeness blueprint, source-by-source evidence inspection, explicit uncertainty labels, and an actionable verification process.

Rather than simply presenting an answer, Advise Buddy helps users understand which parts are supported, which remain uncertain, and what evidence is needed next.

### Future Scope

Future improvements include broader document support, more advanced evidence comparison, and deeper explanations for why sources disagree.

### Conclusion

Advise Buddy transforms online research from passive information collection into a structured process of evidence investigation and verification.

**Advise Buddy doesn't just tell you what you know. It helps you discover what you don't know — and what to verify next.**
