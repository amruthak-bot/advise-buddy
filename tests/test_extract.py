"""Rule-extractor guard tests: a shared word must never fake a match,
and the demo's key cells must come out exactly right."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.llm import rule_extract
from app.models import BlueprintItem
from app.verify import split_passages

ITEMS = [
    BlueprintItem(id="fee", label="What is the application fee?",
                  anchor="fee"),
    BlueprintItem(id="link",
                  label="What is the official application link or portal?",
                  anchor="portal"),
    BlueprintItem(id="police",
                  label="Is police verification required, and what does "
                        "it involve?",
                  anchor="police verification"),
    BlueprintItem(id="docs", label="What documents are required?",
                  anchor="documents"),
]

TEXT = ("The documents required are proof of address.\n\n"
        "The application fee is Rs 1500.\n\n"
        "Apply through the official portal at passport.example.gov.")


def _stated(item_id):
    passages = split_passages(TEXT, "s1")
    out = rule_extract(TEXT, passages, ITEMS)
    entry = next(e for e in out["items"] if e["itemId"] == item_id)
    return entry


def test_documents_sentence_does_not_state_police_item():
    # "required" alone must not fake a police-verification match.
    assert _stated("police")["status"] == "silent"


def test_fee_sentence_does_not_state_link_item():
    # "application" alone must not fake a portal match; the portal
    # sentence states it instead.
    entry = _stated("link")
    assert entry["status"] == "stated"
    assert "portal" in (entry["exactQuote"] or "")


def test_single_keyword_fee_sentence_states_via_anchor():
    assert _stated("fee")["status"] == "stated"
