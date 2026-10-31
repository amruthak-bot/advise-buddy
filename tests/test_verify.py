"""Quote verification tests (spec section 8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.verify import locate_passage, split_passages, verify_quote

PASSAGE = "The application fee is Rs 1500. Book an appointment online."


def test_exact_match_passes():
    assert verify_quote("The application fee is Rs 1500.", PASSAGE)


def test_whitespace_and_curly_quote_differences_pass():
    assert verify_quote("  The   application\u2019s fee\nis Rs 1500. ",
                        "The application\u2019s fee is Rs 1500.")


def test_altered_quote_fails():
    assert not verify_quote("The application fee is Rs 2000.", PASSAGE)


def test_quote_from_wrong_passage_fails():
    other = "Processing takes 7 working days."
    assert not verify_quote("The application fee is Rs 1500.", other)


def test_fuzzy_locate_finds_right_passage_but_never_rewrites():
    # Near-miss quote: punctuation drift breaks the exact substring
    # check, but fuzzy locate must still find the passage — and the
    # passage's ORIGINAL text is what may be shown, never the quote.
    passages = split_passages(
        "The documents required are proof of address.\n\n"
        "The application fee is Rs 1500.", "s1")
    assert not verify_quote("The application fee is Rs. 1500.",
                             passages[1].text)
    located = locate_passage("The application fee is Rs. 1500.", passages)
    assert located is not None
    passage, _ratio = located
    assert "Rs 1500" in passage.text
    assert "Rs." not in passage.text
