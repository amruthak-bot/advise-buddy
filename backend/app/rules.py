"""Deterministic rules (MVP Spec v1, sections 4 steps 6-7, 10).

No LLM here: freshness, Official Silence, Evidence Debt, checklist
ranking. Every rule is inspectable, which is the point of GapScope.
"""
import re
from typing import Dict, List, Tuple

# --- Date / cycle detection (regex first, per spec) -----------------------

# Full month names first, then abbreviations (longest first so
# "September" is never stolen by "Sep").
_MONTHS_FULL = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November",
                "December"]
_MONTHS_ABBR = ["Sept", "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug",
                "Sep", "Oct", "Nov", "Dec"]
_MONTH_ALT = "|".join(_MONTHS_FULL + _MONTHS_ABBR)

_DATE_RES = [
    # "Last updated: 12 March 2026" / "Last updated 2026-03-12"
    re.compile(r"last\s+updated[:\s]+([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})", re.I),
    re.compile(r"\b(20[0-9]{2})-(20[0-9]{2})\b"),                    # cycle 2024-2025
    re.compile(r"\b(?:AY|academic year)\s*(20[0-9]{2})[-–](?:20)?([0-9]{2})\b", re.I),
    re.compile(r"\bBatch of (20[0-9]{2})\b", re.I),
    re.compile(r"\b(20[0-9]{2})-[0-9]{2}-[0-9]{2}\b"),                # ISO date
    re.compile(r"\b([0-9]{1,2}\s+(?:" + _MONTH_ALT + r")\s+20[0-9]{2})\b", re.I),
    re.compile(r"\b((?:" + _MONTH_ALT + r")\s+[0-9]{1,2},?\s+20[0-9]{2})\b", re.I),
    re.compile(r"\b((?:" + _MONTH_ALT + r")\s+20[0-9]{2})\b", re.I),  # Month YYYY
    re.compile(r"\b(20[0-9]{2})-[0-9]{2}\b"),                         # 2024-25 shorthand
    # Bare year, last resort: must NOT match money ("Rs 2000") or parts
    # of larger numbers. Currency lookbehinds are the fix for the
    # Rs-2000-parsed-as-year-2000 bug found in demo testing.
    re.compile(r"(?<![\d,])(?<!Rs\s)(?<!Rs\.\s)(?<!₹\s)(?<!INR\s)"
               r"(?<!\$)(?<!€)(?<!£)\b(20[0-9]{2})\b"),
]


def detect_dates(text: str) -> List[str]:
    """Return raw date/cycle strings found in text, de-duplicated.
    Longer, more specific matches win: a match overlapping an already
    accepted span is skipped, so '1 July 2026' does not also yield a
    bare '2026', and 'February 2026' does not also yield '2026'.
    Without this, one source could appear to carry two different
    dates and fake a change-over-time signal."""
    found: List[str] = []
    spans: List[tuple] = []
    for rx in _DATE_RES:
        for m in rx.finditer(text or ""):
            start, end = m.span()
            if any(start < e and s < end for s, e in spans):
                continue
            spans.append((start, end))
            raw = m.group(0).strip()
            if raw not in found:
                found.append(raw)
    return found


def _year_of(raw: str) -> int:
    m = re.search(r"20[0-9]{2}", raw)
    return int(m.group(0)) if m else 0


_MONTHS = {name: i + 1 for i, name in enumerate(_MONTHS_FULL)}
_MONTHS.update({"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Jun": 6,
                "Jul": 7, "Aug": 8, "Sep": 9, "Sept": 9, "Oct": 10,
                "Nov": 11, "Dec": 12})


def _date_key(raw: str) -> tuple:
    """(year, month) for a detected date string; month 0 when the
    string carries no month. Used only to tell whether conflicting
    claims come from different points in time."""
    year = _year_of(raw)
    if not year:
        return (0, 0)
    m = re.search(r"(" + _MONTH_ALT + r")", raw, re.I)
    if not m:
        return (year, 0)
    token = m.group(1)
    month = _MONTHS.get(token.capitalize(),
                        _MONTHS.get(token, 0))
    return (year, month)


def _source_date_key(source) -> tuple:
    """One (year, month) placing a source in time, or None.
    Unplaceable when the source has no month-known date, or more than
    one distinct month-known date (its claims cannot be pinned to one
    point in time). Year-only dates NEVER place a source: the month
    is unknown, so '2026' and '1 July 2026' are not different times."""
    keys = set()
    for raw in (source.detectedDates or []):
        key = _date_key(raw)
        if key[0] and key[1]:
            keys.add(key)
    if len(keys) == 1:
        return keys.pop()
    return None


def _cycle_year(current_cycle: str) -> int:
    m = re.search(r"20[0-9]{2}", current_cycle or "")
    return int(m.group(0)) if m else 0


def source_freshness(detected_dates: List[str], current_cycle: str) -> str:
    """'current' | 'possibly_outdated' | 'undated'. A source with no
    detectable date is undated, NEVER guessed (spec hard rule)."""
    if not detected_dates:
        return "undated"
    current = _cycle_year(current_cycle)
    if not current:
        return "current"
    years = [_year_of(d) for d in detected_dates]
    if years and max(years) < current:
        return "possibly_outdated"
    return "current"


# --- Official Silence (pure rule, spec step 6) -----------------------------

def official_silence(item_id: str, findings, sources) -> str:
    """Returns 'flag' | 'no_official' | 'ok'.
    flag: stated in >=1 third-party source, silent in EVERY official source.
    Silence means 'Not found in the official excerpts reviewed' — never
    'false', and never a claim that the authority failed to address
    the question (the excerpts reviewed may simply not cover it).
    If no official source was added, it cannot be checked.
    NOTE: 'conflicting' counts as stated here. Comparison (step 3)
    rewrites stated -> conflicting before this rule runs (step 5), so
    excluding it would hide the silence dimension of every item whose
    third-party sources also disagree with each other."""
    by_source = {f.sourceId: f.status for f in findings
                 if f.itemId == item_id}
    officials = [s for s in sources if s.type == "official"]
    if not officials:
        return "no_official"
    third_party_states = any(
        by_source.get(s.id) in ("stated", "possibly_outdated", "conflicting")
        for s in sources if s.type == "third_party")
    official_silent = all(
        by_source.get(s.id) in ("silent", None) for s in officials)
    if third_party_states and official_silent:
        return "flag"
    return "ok"


def changed_over_time(item_id: str, findings, sources) -> bool:
    """True when an item's conflicting claims come from sources placed
    at two or more different points in time, ONE date per source.
    A single source carrying two dates can never trigger this on its
    own, and a year-only source never counts as a different time from
    a dated source in the same year. The claim stays narrow: different
    dates + disagreement = MAY have changed, never proof that it did
    — the checklist wording says so."""
    by_id = {s.id: s for s in sources}
    dates = set()
    for f in findings:
        if f.itemId != item_id or f.status != "conflicting":
            continue
        src = by_id.get(f.sourceId)
        if not src:
            continue
        key = _source_date_key(src)
        if key:
            dates.add(key)
    return len(dates) >= 2


# --- Evidence Debt + checklist ranking (spec step 10) ----------------------

_PRIORITY_W = {"critical": 3.0, "important": 2.0, "optional": 1.0}
_STATUS_W = {
    "conflicting": 5.0,
    "official_silence": 4.0,
    "uncertain": 3.5,
    "silent": 3.0,
    "possibly_outdated": 2.0,
    "undated": 1.0,
}


def official_confirmed_count(findings, blueprint, sources) -> int:
    """Items with a verified (sourced-label), currently-stated finding
    from an Official source. Conflicting, stale, or unverified
    official mentions do not count: they are not confirmation. This
    is the companion to the completeness score — coverage says how
    much of the blueprint has any verified evidence, this says how
    much an official source actually confirms."""
    officials = {s.id for s in sources if s.type == "official"}
    confirmed = {f.itemId for f in findings
                 if f.label == "sourced" and f.status == "stated"
                 and f.sourceId in officials}
    return sum(1 for it in blueprint.items if it.id in confirmed)


def evidence_debt(findings, blueprint) -> Tuple[int, List[str]]:
    """Items with zero Sourced cells among REVIEWED sources.
    An item covered only by unfetched (error) sources is not debt —
    its problem is fetch failure, shown by the error column, not
    missing evidence. Returns (count, item labels)."""
    sourced_items = {f.itemId for f in findings if f.label == "sourced"}
    reviewed_items = {f.itemId for f in findings if f.status != "error"}
    debt = [it.label for it in blueprint.items
            if it.id in reviewed_items and it.id not in sourced_items]
    return len(debt), debt


def completeness_score(findings, blueprint) -> int:
    """Share of blueprint weight covered by verified (sourced-label)
    evidence, as a percentage. Weighted by priority: a critical item
    counts more than an optional one. A conflicting item still counts
    as covered — its evidence exists, it just disagrees. The score is
    coverage OF THE USER'S BLUEPRINT, not a truth score, and the UI
    must word it that way. Empty blueprint -> 0."""
    weights = _PRIORITY_W
    total = sum(weights.get(it.priority, 1.0) for it in blueprint.items)
    if not total:
        return 0
    sourced = {f.itemId for f in findings if f.label == "sourced"}
    covered = sum(weights.get(it.priority, 1.0) for it in blueprint.items
                  if it.id in sourced)
    return round(100 * covered / total)


def rank_checklist(entries: List[dict]) -> List[dict]:
    """Score = status weight x 10 + priority weight, so the spec's
    ordering always holds — conflict > official silence > silent
    everywhere > outdated > undated — with priority breaking ties
    inside a status (spec step 10)."""
    for e in entries:
        e["score"] = (_STATUS_W.get(e["kind"], 1.0) * 10.0
                      + _PRIORITY_W.get(e.get("priority", "important"),
                                        2.0))
    return sorted(entries, key=lambda e: -e["score"])
