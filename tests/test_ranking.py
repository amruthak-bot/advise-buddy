"""Checklist ranking tests (spec section 8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.rules import rank_checklist

ENTRIES = [
    {"itemId": "a", "kind": "undated", "priority": "critical"},
    {"itemId": "b", "kind": "silent", "priority": "critical"},
    {"itemId": "c", "kind": "conflicting", "priority": "important"},
    {"itemId": "d", "kind": "official_silence", "priority": "important"},
    {"itemId": "e", "kind": "possibly_outdated", "priority": "critical"},
]


def test_ranking_order_conflict_first():
    ranked = rank_checklist([dict(e) for e in ENTRIES])
    kinds = [e["kind"] for e in ranked]
    # conflict (5) > official_silence (4) > silent (3) > outdated (2) >
    # undated (1), each multiplied by priority weight.
    assert kinds == ["conflicting", "official_silence", "silent",
                     "possibly_outdated", "undated"], kinds


def test_priority_breaks_ties_within_kind():
    entries = [
        {"itemId": "x", "kind": "silent", "priority": "optional"},
        {"itemId": "y", "kind": "silent", "priority": "critical"},
    ]
    ranked = rank_checklist(entries)
    assert ranked[0]["itemId"] == "y"
