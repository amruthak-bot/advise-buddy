"""Tests for the two idea additions that passed the simplicity bar:
change-over-time detection and the completeness score."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.engine import analyze
from app.models import AnalysisRequest, Blueprint, BlueprintItem, Source
from app.rules import completeness_score

BP = Blueprint(id="t", title="T", items=[
    BlueprintItem(id="i3", label="What is the application fee?",
                  anchor="fee"),
])


def _req(sources):
    return AnalysisRequest(question="Q?", blueprint=BP, sources=sources,
                           currentCycle="2026")


def test_completeness_score_weighted():
    bp = Blueprint(id="t", title="T", items=[
        BlueprintItem(id="a", label="A?", priority="critical"),
        BlueprintItem(id="b", label="B?", priority="critical"),
        BlueprintItem(id="c", label="C?", priority="optional"),
    ])
    from app.models import Finding
    # 3 of 7 weight covered -> 43%.
    findings = [Finding(itemId="a", sourceId="s", status="stated",
                        label="sourced")]
    assert completeness_score(findings, bp) == 43
    assert completeness_score([], bp) == 0
    assert completeness_score([], Blueprint(id="e", title="E",
                                            items=[])) == 0


def test_change_over_time_flagged_for_different_dates():
    req = _req([
        Source(id="s1", title="Old", text=(
            "The application fee is Rs 1500. Updated: February 2026."),
            type="third_party"),
        Source(id="s2", title="New", text=(
            "The application fee is Rs 2500. "
            "Passport fees increased on 1 July 2026."),
            type="third_party"),
    ])
    res = analyze(req)
    assert res.checklist and res.checklist[0].kind == "conflicting"
    assert "change over time" in res.checklist[0].action


def test_change_over_time_absent_for_same_date_and_undated():
    req = _req([
        Source(id="s1", title="A", text=(
            "The application fee is Rs 1500. Updated: February 2026."),
            type="third_party"),
        Source(id="s2", title="B", text=(
            "The application fee is Rs 2500. Updated: February 2026."),
            type="third_party"),
        Source(id="s3", title="C", text="The application fee is Rs 3000.",
               type="third_party"),
    ])
    res = analyze(req)
    assert res.checklist and res.checklist[0].kind == "conflicting"
    assert "change over time" not in res.checklist[0].action
