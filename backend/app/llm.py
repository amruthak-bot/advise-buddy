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
        return rule_compare(claim_a, claim_b, question)


def _norm_value(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def rule_compare(claim_a: str, claim_b: str, question: str = "") -> str:
    """Compare explicit amounts or durations for the question, not dates
    or arbitrary numbers. Differently labelled applicant categories stay
    unclear. A numeric difference is a reason to check, not proof that
    either source is wrong or that the claims apply to the same case.
    """
    a, b = _norm_value(claim_a), _norm_value(claim_b)
    if not a or not b:
        return "unclear"
    if a == b:
        return "same"
    if re.search(r"\b(?:fee|fees|cost)\b", question, re.I):
        pattern = r"(?:₹|\bRs\.?|\bINR|\$)\s*(\d[\d,]*(?:\.\d+)?)"
    elif re.search(r"\b(?:processing|long|duration)\b", question, re.I):
        pattern = r"(\d+(?:\s*[-–—]\s*\d+)?\s*(?:working\s+|business\s+)?(?:days?|weeks?|months?))\b"
    else:
        # Numbers in a documents or police-verification paragraph do not
        # establish a disagreement about requirements.
        return "unclear"
    values_a = {_norm_value(v) for v in re.findall(pattern, claim_a, re.I)}
    values_b = {_norm_value(v) for v in re.findall(pattern, claim_b, re.I)}
    if not values_a or not values_b:
        return "unclear"
    categories = r"\b(?:normal|tatkaal|tatkal|minor|adult|36\s*pages?|60\s*pages?)\b"
    context_a = set(re.findall(categories, claim_a.lower()))
    context_b = set(re.findall(categories, claim_b.lower()))
    if context_a and context_b and context_a != context_b:
        return "unclear"
    return "same" if values_a == values_b else "different"


# --- Rule-based fallback extractor (no key needed) -------------------------

_STOP = set("what is the are and or of to a an for how do does you your "
            "in on with by be is it its this that".split())


def _keywords(label: str) -> List[str]:
    words = re.findall(r"[a-z]+", label.lower())
    return [w for w in words if w not in _STOP and len(w) > 2]


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"\n+|(?<=[.!?])\s+", text) if s.strip()]


def is_answer_text(text: str, label: str = "") -> bool:
    """Reject questions, headings and navigation lists, even if verbatim.

    This is a conservative quality floor, not proof of relevance or truth.
    A short statement or a labelled amount/duration can pass; a bare topic
    cannot. Keep the original text untouched for quote verification.
    """
    text = (text or "").strip()
    if len(text) < 12 or len(text) > 450 or text.endswith("?"):
        return False
    if re.match(r"^(?:#+\s*|(?:q[:.]\s*)?(?:what|who|how|when|where|why)\b)",
                text, re.I):
        return False
    if re.search(r"\b(?:skip to|sitemap|privacy policy|all rights reserved|"
                 r"cookie settings|table of contents)\b", text, re.I):
        return False
    # Mentioning a fee, portal or contact topic is not an answer to
    # a question asking for the amount, address or contact channel.
    if re.search(r"\b(?:fee|fees|cost)\b", label, re.I):
        if not re.search(r"(?:₹|\bRs\.?|\bINR|\$)\s*\d|\d[\d,]*\s*rupees", text, re.I):
            return False
    if re.search(r"\b(?:processing|how long)\b", label, re.I):
        if not re.search(r"\d+(?:\s*[-–—]\s*\d+)?\s*(?:working\s+|business\s+)?(?:days?|weeks?|months?)\b", text, re.I):
            return False
    if re.search(r"\b(?:portal|application link)\b", label, re.I):
        if not re.search(r"https?://|\b[a-z0-9-]+\.(?:gov|in|com|org|edu)\b", text, re.I):
            return False
    if re.search(r"\b(?:contact|help channel)\b", label, re.I):
        if not re.search(r"https?://|[\w.+-]+@[\w.-]+\.[a-z]+|\b\d[\d ()-]{6,}\d\b", text, re.I):
            return False
    statement = re.search(
        r"\b(?:is|are|must|shall|requires?|involves?|takes?|costs?|"
        r"submit|provide|carry|visit|apply|book|schedule|pay|contact|call|email|"
        r"has|have|can|will|may|should)\b", text, re.I)
    labelled_value = re.search(
        r"(?:\b(?:fee|fees|cost|processing time|duration)\b[^.!?]{0,40}"
        r"(?:₹|\bRs\.?|\bINR|\d+\s*(?:working\s+)?(?:days?|weeks?|months?)))",
        text, re.I)
    return bool(statement or labelled_value)


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
                if not is_answer_text(sent, label):
                    continue
                low = sent.lower()
                hits = sum(1 for k in set(kws) if re.search(r"\b" + re.escape(k) + r"\b", low))
                if (anchor and re.search(r"\b" + re.escape(anchor) + r"s?\b", low)) or hits >= 2:
                    found = (p.id, sent)
                    break
            if found:
                break
        if found:
            items_out.append({"itemId": it.id, "status": "stated",
                              "passageId": found[0],
                              "exactQuote": found[1],
                              "claimSummary": found[1]})
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
