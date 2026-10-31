"""Date / cycle regex tests (spec section 8): 10 sample strings."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.rules import detect_dates, source_freshness

SAMPLES = [
    ("Last updated: 12 March 2026", True),
    ("Last updated 2026-03-12", True),
    ("2026-03-12", True),
    ("12 March 2026", True),
    ("March 12, 2026", True),
    ("Cycle 2024-25 admissions", True),
    ("AY 2025-26 prospectus", True),
    ("Batch of 2023 students", True),
    ("No date information on this page at all", False),
    ("Apply any time, no deadline mentioned", False),
]


def test_date_regex_on_samples():
    for text, should_find in SAMPLES:
        found = detect_dates(text)
        assert bool(found) == should_find, (text, found)


def test_freshness_rules():
    assert source_freshness([], "2026") == "undated"
    assert source_freshness(["2024-25"], "2026") == "possibly_outdated"
    assert source_freshness(["12 March 2026"], "2026") == "current"
    assert source_freshness(["Batch of 2023"], "2026") == "possibly_outdated"
