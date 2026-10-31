"""The user needs answers, not keyword matches in page furniture."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.discover import extract_text
from app.engine import analyze
from app.llm import is_answer_text, rule_compare, rule_extract
from app.models import AnalysisRequest, Blueprint, BlueprintItem, Source
from app.verify import split_passages


@pytest.mark.parametrize("text", [
    "Documents Required for Passport",
    "What documents are required for a passport?",
    "Normal/Tatkaal Appointment Opening Time",
    "Sitemap Contact Feedback Renewal Application Help",
])
def test_headings_and_navigation_are_not_answers(text):
    item = BlueprintItem(id="a", label="What documents are required?", anchor="documents")
    out = rule_extract(text, split_passages(text, "s"), [item])
    assert out["items"][0]["status"] == "silent"


def test_heading_does_not_hide_the_actual_answer():
    text = "Documents required\n\nApplicants must submit proof of address and date of birth."
    item = BlueprintItem(id="a", label="What documents are required?", anchor="documents")
    # Repeated topic in the answer is necessary for this conservative fallback.
    text += "\nThe documents required are proof of address and date of birth."
    out = rule_extract(text, split_passages(text, "s"), [item])
    quote = out["items"][0]["exactQuote"]
    assert quote == "The documents required are proof of address and date of birth."
    assert quote in text


def test_llm_heading_also_fails_quality_floor(monkeypatch):
    from app import llm
    monkeypatch.setattr(llm, "llm_extract", lambda text, passages, items: {
        "items": [{"itemId": "a", "status": "stated", "passageId": passages[0].id,
                   "exactQuote": text, "claimSummary": text}], "additionalRequirements": []})
    result = analyze(AnalysisRequest(question="Passport?", blueprint=Blueprint(
        id="p", title="Passport", items=[BlueprintItem(id="a", label="Documents?")]),
        sources=[Source(id="s", title="Official", type="official", text="Documents required")]))
    assert result.officialConfirmedCount == 0
    assert result.evidenceDebtCount == 1


def test_page_structure_keeps_navigation_and_heading_out_of_answer():
    text = extract_text("<nav>Renewal Contact Documents</nav><h2>Documents required</h2>"
                        "<p>The documents required are proof of address.</p>")
    assert "Renewal Contact" not in text
    assert "Documents required\nThe documents" in text


def test_different_dates_do_not_create_a_fee_conflict():
    assert rule_compare("Updated 2024. The fee is Rs 1500.",
                        "Updated 2026. The fee is Rs 1500.", "What is the fee?") == "same"


def test_different_applicant_categories_are_not_a_proven_fee_conflict():
    assert rule_compare("Adult fee is Rs 1500.", "Minor fee is Rs 1000.",
                        "What is the fee?") == "unclear"


def test_numbers_in_document_lists_do_not_create_a_conflict():
    assert rule_compare("Submit 2 copies of address proof.",
                        "Submit 3 copies of address proof.",
                        "What documents are required?") == "unclear"


def test_different_same_category_fees_still_need_checking():
    assert rule_compare("Normal fee is Rs 1500.", "Normal fee is Rs 2500.",
                        "What is the fee?") == "different"


@pytest.mark.parametrize("text,label", [
    ("Pay the application fee online.", "What is the application fee?"),
    ("They take care of processing applications.", "How long does processing take?"),
    ("This is the only valid portal to apply online.", "What is the official application portal?"),
    ("Our executive will contact you soon.", "What is the contact or help channel?"),
])
def test_topic_mentions_do_not_answer_specific_questions(text, label):
    assert not is_answer_text(text, label)


def test_explicit_contact_channel_can_pass():
    assert is_answer_text("Please contact the help desk at support@example.gov.in.",
                          "What is the contact or help channel?")
