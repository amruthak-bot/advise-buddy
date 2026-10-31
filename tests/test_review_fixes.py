"""Regression tests for the 2026-10-31 re-review fixes:
per-source change-over-time dates, Month YYYY detection,
unverified-quote status, Official Silence wording, and the
official-confirmed companion count."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import llm as llm_mod
from app.engine import analyze
from app.models import (AnalysisRequest, Blueprint, BlueprintItem,
                        Finding, Source)
from app.rules import (changed_over_time, detect_dates,
                       official_confirmed_count)

BP = Blueprint(id="t", title="T", items=[
    BlueprintItem(id="i1", label="Fee?", anchor="fee"),
])


def _conflict_fixture(dates_by_source):
    findings, sources = [], []
    for sid, dates in dates_by_source.items():
        sources.append(Source(id=sid, title=sid, text="x",
                              type="third_party", detectedDates=dates))
        findings.append(Finding(itemId="i1", sourceId=sid,
                                status="conflicting"))
    return findings, sources


def test_month_year_detected_and_overlaps_dropped():
    assert detect_dates("Updated: February 2026") == ["February 2026"]
    assert detect_dates("Fees changed July 2026") == ["July 2026"]
    assert detect_dates("19 Sep 2026") == ["19 Sep 2026"]
    # One mention, one string: no bare-year shadow.
    assert detect_dates("Passport fees increased on 1 July 2026.") == [
        "1 July 2026"]
    assert detect_dates("Batch of 2024.") == ["Batch of 2024"]


def test_change_over_time_is_per_source():
    # One source carrying two dates cannot trigger it alone.
    f, s = _conflict_fixture({"a": ["1 July 2026", "2026"],
                              "b": ["1 July 2026"]})
    assert changed_over_time("i1", f, s) is False
    # Year-only never counts as a different time from a dated source.
    f, s = _conflict_fixture({"a": ["2026"], "b": ["1 July 2026"]})
    assert changed_over_time("i1", f, s) is False
    # A source with two genuinely different months is unplaceable.
    f, s = _conflict_fixture({"a": ["February 2026", "July 2026"],
                              "b": ["July 2026"]})
    assert changed_over_time("i1", f, s) is False
    # Genuine month-known difference still triggers it.
    f, s = _conflict_fixture({"a": ["February 2026"],
                              "b": ["July 2026"]})
    assert changed_over_time("i1", f, s) is True
    # Same month-known date does not.
    f, s = _conflict_fixture({"a": ["February 2026"],
                              "b": ["February 2026"]})
    assert changed_over_time("i1", f, s) is False


def test_unverified_quote_is_uncertain_not_silent(monkeypatch):
    def fake_extract(text, passages, items):
        return {"items": [{"itemId": "i1", "status": "stated",
                           "exactQuote": "A quote that appears nowhere.",
                           "passageId": "p1",
                           "claimSummary": "Something claimed"}],
                "additionalRequirements": []}

    monkeypatch.setattr(llm_mod, "llm_extract", fake_extract)
    req = AnalysisRequest(
        question="Q?",
        blueprint=Blueprint(id="t", title="T", items=[
            BlueprintItem(id="i1", label="Fee?", anchor="fee")]),
        sources=[Source(id="s1", title="S", text="Some passport text.",
                        type="third_party")],
        currentCycle="2026")
    res = analyze(req)
    f = res.findings[0]
    assert f.status == "uncertain" and f.label == "uncertain"
    assert f.quote is None  # unverifiable: no quote shown
    assert res.checklist and res.checklist[0].kind == "uncertain"


def test_official_silence_wording_is_scoped():
    req = AnalysisRequest(
        question="Q?",
        blueprint=Blueprint(id="t", title="T", items=[
            BlueprintItem(id="i1", label="Who is eligible?",
                          anchor="eligible")]),
        sources=[
            Source(id="tp", title="Guide",
                   text="Eligible applicants must be citizens.",
                   type="third_party"),
            Source(id="off", title="Portal", text="Welcome to the portal.",
                   type="official")],
        currentCycle="2026")
    res = analyze(req)
    assert res.officialSilenceFlags == ["i1"]
    assert res.checklist and res.checklist[0].kind == "official_silence"
    assert "was not found in the official excerpts reviewed" in \
        res.checklist[0].action


def test_official_confirmed_count_rules():
    bp = Blueprint(id="t", title="T", items=[
        BlueprintItem(id="a", label="A?"),
        BlueprintItem(id="b", label="B?")])
    sources = [Source(id="off", title="O", text="x", type="official"),
               Source(id="tp", title="T", text="x", type="third_party")]
    findings = [
        Finding(itemId="a", sourceId="off", status="stated",
                label="sourced"),
        Finding(itemId="b", sourceId="off", status="conflicting",
                label="sourced"),
        Finding(itemId="b", sourceId="tp", status="stated",
                label="sourced"),
    ]
    assert official_confirmed_count(findings, bp, sources) == 1


def test_demo_score_and_official_pair():
    demo = json.loads(
        (Path(__file__).resolve().parents[1] / "demo_session.json")
        .read_text(encoding="utf-8"))
    res = analyze(AnalysisRequest(**demo))
    # Headings and a claim that an unnamed portal is valid do not
    # answer eligibility, appointment or application-link questions.
    # The original 86 / 2-of-9 pair counted these weak matches.
    assert res.completenessScore == 57
    assert res.officialConfirmedCount == 1
    assert res.evidenceDebtCount == 4
    assert not any(f.itemId == "i1" and f.label == "sourced"
                   for f in res.findings)
    assert next(f for f in res.findings
                if f.itemId == "i5" and f.sourceId == "sA").status == "silent"
    assert not any(f.itemId == "i4" and f.label == "sourced"
                   for f in res.findings)
