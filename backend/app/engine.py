"""Analysis pipeline (MVP Spec v1, section 4).

Order: ingest -> extract -> VERIFY (deterministic) -> compare ->
Official Silence -> freshness -> checklist -> proposals -> summary.
The LLM never produces a displayed quote without passing the
substring check, never invents dates, and silence is never falsity.
"""
from typing import Dict, List

from . import llm, rules
from .models import (AnalysisRequest, AnalysisResult, ChecklistEntry,
                     Finding, GapQuestion, Proposal)
from .verify import locate_passage, split_passages, verify_quote


def _extract_for_source(source, blueprint_items):
    passages = split_passages(source.text, source.id)
    try:
        raw = llm.llm_extract(source.text, passages, blueprint_items)
    except Exception:
        raw = llm.rule_extract(source.text, passages, blueprint_items)
    return passages, raw


def analyze(req: AnalysisRequest) -> AnalysisResult:
    findings: List[Finding] = []
    proposals: List[Proposal] = []
    passages_by_source: Dict[str, list] = {}

    # 1-2. Ingest + extract + verify, per source.
    for src in req.sources:
        src.detectedDates = rules.detect_dates(src.text)
        if not src.text.strip():
            # URL given (or empty) but no text retrieved: the source
            # was NOT reviewed. Mark every cell "error", never silent,
            # and never fabricate findings for it (plan guardrail).
            for item in req.blueprint.items:
                findings.append(Finding(itemId=item.id, sourceId=src.id,
                                        status="error", label="uncertain"))
            passages_by_source[src.id] = []
            continue
        passages = split_passages(src.text, src.id)
        passages_by_source[src.id] = passages
        try:
            raw = llm.llm_extract(src.text, passages, req.blueprint.items)
        except Exception:
            raw = llm.rule_extract(src.text, passages, req.blueprint.items)
        by_id = {p.id: p for p in passages}
        for entry in raw.get("items", []):
            item_id = entry.get("itemId")
            if entry.get("status") != "stated":
                findings.append(Finding(itemId=item_id, sourceId=src.id,
                                        status="silent", label="uncertain"))
                continue
            quote = entry.get("exactQuote")
            passage = by_id.get(entry.get("passageId") or "")
            if quote and passage and verify_quote(quote, passage.text):
                findings.append(Finding(
                    itemId=item_id, sourceId=src.id, status="stated",
                    claimSummary=entry.get("claimSummary"),
                    passageId=passage.id, quote=quote,
                    quoteVerified=True, label="sourced"))
            elif quote:
                located = locate_passage(quote, passages)
                if located:
                    p, _ = located
                    # Show the PASSAGE's original text, never the quote.
                    findings.append(Finding(
                        itemId=item_id, sourceId=src.id, status="stated",
                        claimSummary=entry.get("claimSummary"),
                        passageId=p.id, quote=p.text,
                        quoteVerified=False, label="uncertain"))
                else:
                    # Quote claimed but no passage matches it: this is
                    # an UNVERIFIED claim, never silence. Silence
                    # means the source does not cover the item; here
                    # the source said something we could not confirm.
                    findings.append(Finding(
                        itemId=item_id, sourceId=src.id, status="uncertain",
                        claimSummary=entry.get("claimSummary"),
                        label="uncertain"))
            else:
                findings.append(Finding(itemId=item_id, sourceId=src.id,
                                        status="silent", label="uncertain"))
        for n, req_item in enumerate(raw.get("additionalRequirements", [])):
            q = req_item.get("exactQuote") or ""
            ok = any(verify_quote(q, p.text) for p in passages)
            if ok:
                proposals.append(Proposal(
                    id=f"prop-{src.id}-{n}", label=req_item.get("label", ""),
                    reason=req_item.get("reason", ""), quote=q,
                    sourceId=src.id, state="pending"))

    # 3. Compare per item across stating sources -> possible conflicts.
    for item in req.blueprint.items:
        stated = [f for f in findings
                  if f.itemId == item.id and f.status == "stated"
                  and f.claimSummary]
        if len(stated) >= 2:
            base = stated[0]
            for other in stated[1:]:
                try:
                    verdict = llm.llm_compare(base.claimSummary or "",
                                               other.claimSummary or "",
                                               item.label)
                except Exception:
                    verdict = llm.rule_compare(base.claimSummary or "",
                                                other.claimSummary or "")
                if verdict == "different":
                    base.status = "conflicting"
                    other.status = "conflicting"

    # 4. Freshness: stating sources that are outdated -> possibly_outdated.
    freshness = {s.id: rules.source_freshness(s.detectedDates,
                                              req.currentCycle)
                 for s in req.sources}
    for f in findings:
        if f.status == "stated" and freshness.get(f.sourceId) == "possibly_outdated":
            f.status = "possibly_outdated"

    # 5. Official Silence flags — over REVIEWED sources only. An
    # unfetched source is not evidence of anything: it neither states
    # nor stays silent, so it must not create or block a flag.
    reviewed_ids = {f.sourceId for f in findings if f.status != "error"}
    reviewed_sources = [s for s in req.sources if s.id in reviewed_ids]
    silence_flags = []
    no_official = not any(s.type == "official"
                          for s in reviewed_sources)
    for item in req.blueprint.items:
        if rules.official_silence(item.id, findings,
                                  reviewed_sources) == "flag":
            silence_flags.append(item.id)

    # 6. Evidence Debt + checklist (rule-based ranking).
    debt_count, debt_items = rules.evidence_debt(findings, req.blueprint)
    by_item = {}
    for f in findings:
        by_item.setdefault(f.itemId, []).append(f)
    raw_entries = []
    for item in req.blueprint.items:
        fs = by_item.get(item.id, [])
        # Gap logic runs over REVIEWED findings only: an error source
        # must not veto a genuine gap (its silence is not evidence).
        reviewed_fs = [f for f in fs if f.status != "error"]
        statuses = {f.status for f in reviewed_fs}
        src_ids = [f.sourceId for f in fs]
        # A current sourced confirmation silences stale/undated noise:
        # an item confirmed by a current source is not nagged about
        # just because some other source is old or undated.
        has_current = any(f.status == "stated"
                          and freshness.get(f.sourceId) == "current"
                          for f in fs)
        stating = [f for f in fs if f.status in ("stated",
                                                  "possibly_outdated")]
        all_undated = bool(stating) and all(
            freshness.get(f.sourceId) == "undated" for f in stating)
        if "conflicting" in statuses:
            action = (f"Possible conflict on '{item.label}': sources "
                      "disagree. Confirm against the official source.")
            if rules.changed_over_time(item.id, findings, req.sources):
                action += (" Sources from different dates disagree, so "
                           "this may reflect a change over time rather "
                           "than an error — compare the source dates.")
            kind, action = "conflicting", action
        elif item.id in silence_flags:
            kind, action = "official_silence", (
                f"'{item.label}' was not found in the official excerpts "
                "reviewed. Ask the official body.")
        elif reviewed_fs and all(f.status == "silent"
                                 for f in reviewed_fs):
            kind, action = "silent", (
                f"Potential gap: '{item.label}' is not covered by any "
                "source reviewed. Verify it next.")
        elif "possibly_outdated" in statuses and not has_current:
            kind, action = "possibly_outdated", (
                f"'{item.label}' rests on an older cycle or date. "
                "Confirm it still applies.")
        elif all_undated:
            kind, action = "undated", (
                f"'{item.label}' comes only from undated sources. "
                "Confirm the information is current.")
        elif any(f.status == "uncertain" for f in reviewed_fs):
            kind, action = "uncertain", (
                f"'{item.label}' was mentioned but the exact quote "
                "could not be verified. Treat it as unconfirmed.")
        else:
            continue
        raw_entries.append({"itemId": item.id, "itemLabel": item.label,
                            "action": action, "kind": kind,
                            "priority": item.priority, "sourceIds": src_ids})
    ranked = rules.rank_checklist(raw_entries)
    checklist = [ChecklistEntry(itemId=e["itemId"],
                                itemLabel=e["itemLabel"],
                                action=e["action"], score=e["score"],
                                kind=e["kind"],
                                sourceIds=e["sourceIds"])
                 for e in ranked]

    # 7. Gap questions (verification loop drafts) for open gaps.
    gap_questions = [
        GapQuestion(itemId=e.itemId,
                    text=(f"Could you please confirm: {e.itemLabel} "
                          f"— {e.action}"),
                    state="open")
        for e in checklist
    ]

    # 8. Summary panel: stated cells as readable facts.
    summary = []
    for f in findings:
        if f.status in ("stated", "possibly_outdated") and f.claimSummary:
            item_label = next((it.label for it in req.blueprint.items
                               if it.id == f.itemId), f.itemId)
            summary.append(f"{item_label}: {f.claimSummary}")

    return AnalysisResult(
        question=req.question, blueprint=req.blueprint,
        sources=req.sources, findings=findings, proposals=proposals,
        checklist=checklist, gapQuestions=gap_questions,
        evidenceDebtCount=debt_count, evidenceDebtItems=debt_items,
        officialSilenceFlags=silence_flags,
        noOfficialSourceBanner=no_official, summary=summary,
        sourceFreshness=freshness,
        completenessScore=rules.completeness_score(findings,
                                                   req.blueprint),
        officialConfirmedCount=rules.official_confirmed_count(
            findings, req.blueprint, req.sources))
