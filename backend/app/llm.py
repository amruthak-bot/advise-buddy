"""Thin LLM wrapper (MVP Spec v1, section 2).

LLM DECISION: Google Gemini 2.5 Flash, free tier via AI Studio.
Why: zero cost for a student (no card required), structured JSON output
is supported, and quality is sufficient for extraction + comparison
because every LLM output passes deterministic verification afterwards
(see verify.py) — the LLM never gets the final word. Key comes ONLY
from the GEMINI_API_KEY environment variable, server-side. Never put
a key in frontend code, in chat, or in the repo.

If no key is set, the engine uses the rule-based fallback extractor
below, so the app runs end-to-end and the demo never depends on a
live LLM call. Swap providers by replacing _call_gemini only.
"""
import json
import os
import re
import urllib.request
from typing import Dict, List, Optional

GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              "gemini-2.5-flash:generateContent")

EXTRACTION_PROMPT = """You extract evidence from ONE source text against a list of
blueprint questions. Rules you must obey:
- For each blueprint item, answer "stated" ONLY if the source text
  directly addresses it. Otherwise answer "silent".
- "exactQuote" must be copied character-for-character from the source
  text. Never paraphrase inside a quote, never invent dates, never
  invent a quote. If unsure, answer "silent".
- "claimSummary" is your short paraphrase (not a quote) of what the
  source says about the item, or null when silent.
- "additionalRequirements" lists requirements the source mentions that
  are NOT in the blueprint, each with its exact quote. If none, [].
Return JSON only, matching the schema."""

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "itemId": {"type": "string"},
                    "status": {"type": "string",
                               "enum": ["stated", "silent"]},
                    "passageId": {"type": ["string", "null"]},
                    "exactQuote": {"type": ["string", "null"]},
                    "claimSummary": {"type": ["string", "null"]},
                },
                "required": ["itemId", "status"],
            },
        },
        "additionalRequirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "reason": {"type": "string"},
                    "exactQuote": {"type": "string"},
                },
                "required": ["label", "reason", "exactQuote"],
            },
        },
    },
    "required": ["items", "additionalRequirements"],
}

COMPARE_PROMPT = """Compare two claim summaries about the same question.
Return JSON only: {"verdict": "same" | "different" | "unclear"}.
"different" ONLY when the two claims give incompatible values or
requirements. Vague wording differences are "unclear", not "different"."""


class NoKeyError(RuntimeError):
    pass


def _call_gemini(prompt: str, schema: Optional[dict] = None) -> dict:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise NoKeyError("GEMINI_API_KEY is not set")
    body: Dict = {"contents": [{"parts": [{"text": prompt}]}]}
    if schema:
        body["generationConfig"] = {
            "response_mime_type": "application/json",
            "response_schema": schema,
        }
    req = urllib.request.Request(
        GEMINI_URL + "?key=" + key,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    # Retry once after stripping any code fence the model may add.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(),
                         flags=re.M)
        return json.loads(cleaned)


def llm_extract(source_text: str, passages, blueprint_items) -> dict:
    """One LLM call per source (spec step 3). Returns raw model JSON;
    the engine verifies every quote afterwards."""
    item_lines = "\n".join(f"- {it.id}: {it.label}"
                           for it in blueprint_items)
    passage_lines = "\n\n".join(f"[{p.id}] {p.text}" for p in passages)
    prompt = (EXTRACTION_PROMPT + "\n\nBLUEPRINT ITEMS:\n" + item_lines
              + "\n\nSOURCE TEXT (passages in brackets):\n" + passage_lines)
    return _call_gemini(prompt, EXTRACTION_SCHEMA)


def llm_compare(claim_a: str, claim_b: str, question: str) -> str:
    try:
        out = _call_gemini(
            COMPARE_PROMPT + f"\n\nQuestion: {question}\nClaim A: {claim_a}"
            f"\nClaim B: {claim_b}",
            {"type": "object",
             "properties": {"verdict": {"type": "string"}},
             "required": ["verdict"]})
        v = str(out.get("verdict", "unclear")).lower()
        return v if v in ("same", "different", "unclear") else "unclear"
    except Exception:
        return rule_compare(claim_a, claim_b)


def _norm_value(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def rule_compare(claim_a: str, claim_b: str) -> str:
    """Conservative fallback: equal after normalisation -> same;
    both claims carry numbers and the number sets differ -> different
    (e.g. two different fees); else unclear. Never upgrades 'unclear'
    to 'different' on a wording guess."""
    a, b = _norm_value(claim_a), _norm_value(claim_b)
    if not a or not b:
        return "unclear"
    if a == b:
        return "same"
    nums_a = set(re.findall(r"\d[\d,]*", claim_a or ""))
    nums_b = set(re.findall(r"\d[\d,]*", claim_b or ""))
    if nums_a and nums_b and nums_a != nums_b:
        return "different"
    return "unclear"


# --- Rule-based fallback extractor (no key needed) -------------------------

_STOP = set("what is the are and or of to a an for how do does you your "
            "in on with by be is it its this that".split())


def _keywords(label: str) -> List[str]:
    words = re.findall(r"[a-z]+", label.lower())
    return [w for w in words if w not in _STOP and len(w) > 2]


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def rule_extract(source_text: str, passages, blueprint_items) -> dict:
    """Deterministic extraction used when no LLM key is set.
    A sentence becomes evidence only if it contains the item's anchor
    phrase, or at least 2 distinct label keywords. The 2-keyword bar
    exists because a single shared word (e.g. "required" in a
    documents sentence) must never fake a match for another item
    (e.g. police verification). Quotes are EXACT sentences."""
    items_out = []
    for it in blueprint_items:
        label = it.label if not isinstance(it, dict) else it["label"]
        kws = _keywords(label)
        anchor = it.anchor if not isinstance(it, dict) else it.get("anchor")
        anchor = (anchor or "").lower()
        found = None
        for p in passages:
            for sent in _sentences(p.text):
                low = sent.lower()
                hits = sum(1 for k in kws if k in low)
                if (anchor and anchor in low) or hits >= 2:
                    found = (p.id, sent)
                    break
            if found:
                break
        if found:
            items_out.append({"itemId": it.id, "status": "stated",
                              "passageId": found[0],
                              "exactQuote": found[1],
                              "claimSummary": found[1][:200]})
        else:
            items_out.append({"itemId": it.id, "status": "silent",
                              "passageId": None, "exactQuote": None,
                              "claimSummary": None})
    # Challenge Mode candidates (rule-based): "## Heading" lines that
    # share no keyword with any blueprint item. Quote = heading text,
    # which is an exact substring of its passage.
    all_kws = set()
    for it in blueprint_items:
        all_kws.update(_keywords(it.label))
    extra = []
    for p in passages:
        for line in p.text.splitlines():
            line = line.strip()
            if line.startswith("## "):
                heading = line[3:].strip()
                hkws = set(_keywords(heading))
                if heading and not (hkws & all_kws):
                    extra.append({"label": heading,
                                  "reason": ("This source mentions a "
                                             "requirement not in the "
                                             "blueprint."),
                                  "exactQuote": heading})
    return {"items": items_out, "additionalRequirements": extra}
