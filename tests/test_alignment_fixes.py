import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import discover
from app.llm import is_answer_text, rule_extract
from app.models import BlueprintItem
from app.templates import research_plan
from app.verify import split_passages


def test_unrelated_university_sentence_is_not_affiliation_evidence():
    text = ("EdifyEdu earns zero referral commissions from University of Mysore, "
            "which is why this verification page presents both strengths and gaps without favouritism.")
    item = BlueprintItem(id="a", label="Which university is the college affiliated with?", anchor="affiliated")
    assert not is_answer_text(text, item.label)
    assert rule_extract(text, split_passages(text, "s"), [item])["items"][0]["status"] == "silent"
    answer = "The college is affiliated with Example University."
    assert rule_extract(answer, split_passages(answer, "s"), [item])["items"][0]["status"] == "stated"


def test_scholarship_answers_do_not_require_question_wording():
    text = "Students studying in class VIII must meet the income requirements. The scholarship is Rs. 12000 per annum."
    items = [BlueprintItem(id="e", label="Who is eligible?"),
             BlueprintItem(id="a", label="What is the scholarship amount?")]
    out = rule_extract(text, split_passages(text, "s"), items)["items"]
    assert all(item["status"] == "stated" for item in out)
    assert "Rs. 12000" in out[1]["exactQuote"]
    assert all(item["exactQuote"] in text for item in out)


def test_bare_topic_is_not_a_missing_answer_question():
    plan = research_plan("National Means-cum-Merit Scholarship")
    assert plan.id == "scholarship"
    assert all(item.id != "research_question" for item in plan.items)


def test_application_steps_are_not_a_deadline():
    item = BlueprintItem(id="deadline", label="What is the application deadline?")
    text = "Eligible applicants can apply by following these steps:-"
    assert not is_answer_text(text, item.label)
    assert rule_extract(text, split_passages(text, "s"), [item])["items"][0]["status"] == "silent"
    answer = "Applicants must apply by 31 October 2026."
    assert rule_extract(answer, split_passages(answer, "s"), [item])["items"][0]["status"] == "stated"


def test_thin_search_retries_once_and_prefers_readable_official_source(monkeypatch):
    queries = []
    def search(query, key, count):
        queries.append(query)
        if len(queries) == 1:
            return [{"title": "Unread", "url": "https://blog.example.com/unread"}]
        return [{"title": "Official", "url": "https://example.gov/details"}]
    monkeypatch.setattr(discover, "tavily_search", search)
    monkeypatch.setattr(discover, "fetch_text", lambda url: "Students must apply by October." if ".gov/" in url else "")
    result = discover.discover("scholarship", api_key="test-key", max_results=1)
    assert queries == ["scholarship", "scholarship official"]
    assert len(result["sources"]) == 1
    assert result["sources"][0].type == "official"
    assert result["fetched"] == 1


def test_retry_failure_keeps_original_results(monkeypatch):
    def search(query, key, count):
        if query.endswith(" official"):
            raise discover.SearchFailed("retry unavailable")
        return [{"title": "Original", "url": "https://blog.example.com/original"}]
    monkeypatch.setattr(discover, "tavily_search", search)
    monkeypatch.setattr(discover, "fetch_text", lambda url: "")
    result = discover.discover("scholarship", api_key="test-key")
    assert result["sources"][0].title == "Original"
    assert result["failed"] == 1


def test_readable_third_party_batch_still_seeks_an_official_source(monkeypatch):
    queries = []
    def search(query, key, count):
        queries.append(query)
        if query.endswith(" official"):
            return [{"title": "Official", "url": "https://example.gov/details"}]
        return [{"title": "Guide", "url": f"https://blog.example.com/{n}"} for n in range(3)]
    monkeypatch.setattr(discover, "tavily_search", search)
    monkeypatch.setattr(discover, "fetch_text", lambda url: "Students must apply by October.")
    result = discover.discover("scholarship", api_key="test-key", max_results=3)
    assert len(queries) == 2
    assert len(result["sources"]) == 3
    assert result["sources"][0].type == "official"


def test_edited_minor_fee_question_rejects_adult_fee_and_finds_child_answer():
    item = BlueprintItem(id="fee", label="What is the fee for minors?", anchor="fee")
    adult = "The standard adult fee is Rs 1500."
    child = "The fee for children under 18 is Rs 1000."
    assert not is_answer_text(adult, item.label)
    out = rule_extract(adult + " " + child, split_passages(adult + " " + child, "s"), [item])
    assert out["items"][0]["exactQuote"] == child
    assert rule_extract(adult, split_passages(adult, "s"), [item])["items"][0]["status"] == "silent"


def test_model_quote_also_respects_edited_question_category(monkeypatch):
    from app import llm
    from app.engine import analyze
    from app.models import AnalysisRequest, Blueprint, Source
    adult = "The standard adult fee is Rs 1500."
    child = "The fee for minors is Rs 1000."
    def extract(text, passages, items):
        return {"items": [{"itemId": "fee", "status": "stated", "passageId": passages[0].id,
                           "exactQuote": text, "claimSummary": text}], "additionalRequirements": []}
    monkeypatch.setattr(llm, "llm_extract", extract)
    result = analyze(AnalysisRequest(question="Passport fees", blueprint=Blueprint(id="p", title="Fees", items=[
        BlueprintItem(id="fee", label="What is the minor fee?", anchor="fee")]), sources=[
            Source(id="adult", title="Adult", text=adult), Source(id="child", title="Child", text=child)]))
    assert next(f for f in result.findings if f.sourceId == "adult").status == "silent"
    assert next(f for f in result.findings if f.sourceId == "child").quote == child
