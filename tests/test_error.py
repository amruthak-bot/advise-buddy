"""Error-source tests: an unfetched source is never silent, never
evidence, and never counts for or against Official Silence."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.engine import analyze
from app.models import AnalysisRequest, Blueprint, BlueprintItem, Source

BP = Blueprint(id="t", title="T", items=[
    BlueprintItem(id="i1", label="What documents are required?",
                  anchor="documents"),
])


def _req(sources):
    return AnalysisRequest(question="Q?", blueprint=BP, sources=sources,
                           currentCycle="2026")


def test_url_only_source_yields_error_cells_not_silent():
    req = _req([Source(id="u", title="Unfetched", url="https://x.example",
                       text="", type="official")])
    res = analyze(req)
    assert all(f.status == "error" for f in res.findings)
    assert res.checklist == []
    assert res.evidenceDebtCount == 0
    assert res.noOfficialSourceBanner is True


def test_error_source_does_not_veto_a_genuine_gap():
    req = _req([
        Source(id="u", title="Unfetched", url="https://x.example",
               text="", type="third_party"),
        Source(id="tp", title="Blog", text="Something unrelated.",
               type="third_party"),
    ])
    res = analyze(req)
    kinds = [c.kind for c in res.checklist]
    assert "silent" in kinds  # the gap survives the error source


def test_conflicting_item_still_flags_official_silence():
    """Comparison rewrites stated -> conflicting before the silence
    rule runs; a conflicting item unconfirmed by officials must
    still flag (caught by the genuine-data demo run, 2026-10-31)."""
    from app.models import Finding
    from app.rules import official_silence
    findings = [
        Finding(itemId="i1", sourceId="off", status="silent"),
        Finding(itemId="i1", sourceId="tp1", status="conflicting"),
        Finding(itemId="i1", sourceId="tp2", status="conflicting"),
    ]
    sources = [
        Source(id="off", title="O", text="x", type="official"),
        Source(id="tp1", title="T1", text="y", type="third_party"),
        Source(id="tp2", title="T2", text="z", type="third_party"),
    ]
    assert official_silence("i1", findings, sources) == "flag"


def test_error_official_does_not_block_or_create_silence_flag():
    req = _req([
        Source(id="u", title="Unfetched official",
               url="https://x.example", text="", type="official"),
        Source(id="tp", title="Blog", text="The documents required are X.",
               type="third_party"),
    ])
    res = analyze(req)
    # The official source was never reviewed, so silence cannot be
    # checked — banner, not a flag, and not "ok by default".
    assert res.noOfficialSourceBanner is True
    assert res.officialSilenceFlags == []
