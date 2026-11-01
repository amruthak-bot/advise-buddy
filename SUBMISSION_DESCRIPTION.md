Advise Buddy — Know what to verify next

PROBLEM
Research often gives people plenty of information without showing what is missing. For research into education, careers, public services and other decisions, sources may omit requirements, describe different applicant categories or present figures that need further checking. A confident summary can hide these gaps.

SOLUTION
Advise Buddy turns multiple sources into an evidence-backed checklist of what to verify next. It addresses the Digital Dark Spot challenge by comparing available information against the questions a complete answer should cover. The app supports general research with editable starting checklists for scholarships, college admissions, job offers and passport applications. The cached passport investigation is one worked example, not the scope of the product.

FEATURES
• Ask a question and discover web sources through Tavily, load a reproducible example, or paste source text manually.
• Choose a general, scholarship, college-admission, job-offer or passport checklist and edit its questions before analysis.
• See three prioritized checks first, with a plain-language explanation, suggested action and supporting quotes.
• Explore a source-by-question heatmap to inspect coverage, missing answers and potential disagreements.
• Inspect original source excerpts and links instead of relying only on generated summaries.
• Add evidence, rerun analysis, record resolution notes and see how the findings change.
• Download a Markdown checklist containing actions, source URLs, original quotes and comparison reasons.
• Use the interface on desktop or phone-width screens without creating an account.

UNIQUENESS
Advise Buddy focuses on unanswered questions and next steps. Its expected-question checklist makes information gaps visible even when the retrieved sources never mention them. Every numeric comparison is tied to a specific pair of verified original quotes and an explanation.

The comparison logic is conservative: different currencies, time units, applicant categories, multiple prices and overlapping ranges require review rather than automatically being labelled contradictions. Bare headings, navigation text and topic mentions without an answer do not count as complete evidence. A simple first screen keeps the main actions accessible, while the detailed heatmap and evidence remain available for inspection.

TECH STACK
• Backend: Python and FastAPI.
• Frontend: HTML, CSS and JavaScript, served without a frontend build step.
• Web discovery: Tavily API, with bounded parallel page fetching.
• Extraction: optional Google Gemini, followed by deterministic quote verification and answer-quality checks. Deterministic extraction is available without a Gemini key.
• Comparison: rule-based checks against original verified quotes.
• Validation: pytest regression tests covering extraction, provenance, discovery, unread sources, official-source flags and numeric comparison edge cases; browser checks for desktop, phone-width flows and checklist export.
• Hosting and source control: Render and a public GitHub repository.

CURRENT SCOPE AND RELIABILITY
The app is an information-gap research prototype. Its breadth depends on the checklist and the source evidence; it is not a universal fact checker. A verified quote confirms that text occurs in a reviewed source; it does not prove the statement is correct or applicable. Missing information means no usable answer was found in the reviewed sources. Official-source labels are editable domain-based suggestions. Users still need to check jurisdiction, applicant category and current official guidance.

The example uses cached excerpts, including one clearly marked illustrative older source, to demonstrate the workflow. It does not establish current passport fees or rules. Investigations remain in the open page and can be exported; there is no server-side investigation database.

FUTURE SCOPE
• Conduct usability studies with real applicants and improve the workflow from their feedback.
• Improve jurisdiction, applicant-category and document-date matching.
• Expand and evaluate domain-specific checklists for more public services, research and business decisions.
• Add multilingual research and support for more document formats.
• Evaluate gap detection and evidence quality on broader, clearly labelled datasets.

Advise Buddy helps users finish research with a clearer next step and evidence they can inspect.