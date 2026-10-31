"""Comparison labels must have a specific, verified source pair behind them."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.engine import analyze
from app.llm import compare_evidence
from app.models import AnalysisRequest, Blueprint, BlueprintItem, DiscoverRequest, Source


@pytest.mark.parametrize("a,b,question,code", [
    ("The fee is INR 1500.", "The fee is USD 1500.", "Fee?", "different_units"),
    ("The fee is Rs 1500-3500.", "The fee is Rs 2500.", "Fee?", "overlapping_range"),
    ("The adult fee is Rs 1500.", "The minor fee is Rs 1000.", "Fee?", "different_scope"),
    ("The normal fee is Rs 1500.", "The fee is Rs 2500.", "Fee?", "different_scope"),
    ("The fee is Rs 1500 or Rs 2000.", "The fee is Rs 2500.", "Fee?", "multiple_values"),
    ("Processing takes 7 days.", "Processing takes 7 working days.", "Processing time?", "different_units"),
    ("Processing takes 7-14 days.", "Processing takes 10 days.", "Processing time?", "overlapping_range"),
])
def test_incomparable_figures_are_not_conflicts(a, b, question, code):
    verdict, reason_code, reason = compare_evidence(a, b, question)
    assert verdict == "unclear" and reason_code == code and reason


def test_currency_alias_and_commas_do_not_create_false_difference():
    assert compare_evidence("The fee is Rs 1,500.", "The fee is INR 1500.", "Fee?")[0] == "same"


def test_service_aliases_are_the_same_category():
    assert compare_evidence("Tatkaal fee is INR 3500.", "Tatkal fee is Rs 3500.", "Fee?")[0] == "same"


def test_a_mixed_currency_range_is_not_compared_as_one_currency():
    assert compare_evidence("The fee is INR 1500 to USD 3500.",
                            "The fee is INR 5000.", "Fee?")[0] == "unclear"


def test_pair_detection_is_independent_of_first_source(monkeypatch):
    from app import llm
    monkeypatch.setattr(llm, "llm_extract", lambda *args: (_ for _ in ()).throw(llm.NoKeyError()))
    result = analyze(AnalysisRequest(question="Fee?", blueprint=Blueprint(id="t", title="T", items=[
        BlueprintItem(id="fee", label="What is the fee?", anchor="fee")]), sources=[
            Source(id="range", title="Range", text="The fee is Rs 1000-5000."),
            Source(id="a", title="Guide A", text="The fee is Rs 1500."),
            Source(id="b", title="Guide B", text="The fee is Rs 2500."),
        ]))
    differences = [c for c in result.comparisons if c.verdict == "different"]
    assert len(differences) == 1
    assert {differences[0].sourceA, differences[0].sourceB} == {"a", "b"}
    assert next(f for f in result.findings if f.sourceId == "range").status != "conflicting"


def test_comparison_uses_original_quote_not_generated_summary(monkeypatch):
    from app import llm
    def extraction(text, passages, items):
        return {"items": [{"itemId":"fee", "status":"stated", "passageId":passages[0].id,
                           "exactQuote":text, "claimSummary":"The fee is Rs 9999."}],
                "additionalRequirements":[]}
    monkeypatch.setattr(llm, "llm_extract", extraction)
    result = analyze(AnalysisRequest(question="Fee?", blueprint=Blueprint(id="t", title="T", items=[
        BlueprintItem(id="fee", label="Fee?", anchor="fee")]), sources=[
            Source(id="a", title="A", text="The fee is Rs 1500."),
            Source(id="b", title="B", text="The fee is Rs 2500.")]))
    assert result.comparisons[0].verdict == "different"


@pytest.mark.parametrize("count", [0, 6, 500])
def test_discovery_has_a_bounded_fetch_count(count):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        DiscoverRequest(question="Passport fee?", max_results=count)
