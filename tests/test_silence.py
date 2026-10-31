"""Official Silence rule tests (spec section 8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.models import Finding, Source
from app.rules import official_silence

OFFICIAL = Source(id="off", title="Official", text="x", type="official")
THIRD = Source(id="tp", title="Blog", text="y", type="third_party")


def test_flag_when_third_party_states_and_official_silent():
    findings = [Finding(itemId="i1", sourceId="tp", status="stated",
                         label="sourced"),
                Finding(itemId="i1", sourceId="off", status="silent",
                         label="uncertain")]
    assert official_silence("i1", findings, [OFFICIAL, THIRD]) == "flag"


def test_no_official_source_means_cannot_check():
    findings = [Finding(itemId="i1", sourceId="tp", status="stated",
                         label="sourced")]
    assert official_silence("i1", findings, [THIRD]) == "no_official"


def test_no_flag_when_official_states_it():
    findings = [Finding(itemId="i1", sourceId="tp", status="stated",
                         label="sourced"),
                Finding(itemId="i1", sourceId="off", status="stated",
                         label="sourced")]
    assert official_silence("i1", findings, [OFFICIAL, THIRD]) == "ok"


def test_no_flag_when_nothing_states_it():
    findings = [Finding(itemId="i1", sourceId="tp", status="silent",
                         label="uncertain"),
                Finding(itemId="i1", sourceId="off", status="silent",
                         label="uncertain")]
    assert official_silence("i1", findings, [OFFICIAL, THIRD]) == "ok"
