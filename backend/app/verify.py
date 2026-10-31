"""Quote verification (MVP Spec v1, section 4 step 4) — deterministic, no LLM.

HARD RULES (locked with the user):
- A quote is only ever displayed verbatim: it must be an exact substring
  of the cited passage after whitespace/quote normalisation.
- Fuzzy / semantic matching may only LOCATE a candidate passage. When
  verification fails, we show THAT passage's original text with the badge
  "evidence located, exact quote not confirmed" and label `uncertain`.
  We never rewrite, paraphrase, or invent a quote.
- If nothing is found, the finding is silent, never stated.
"""
import difflib
import re
from typing import List, Optional, Tuple

from .models import Passage

_QUOTE_CHARS = str.maketrans({
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    "\u00a0": " ",
})


def normalize(text: str) -> str:
    """Collapse whitespace and unify quote characters for comparison only.
    The ORIGINAL text is always what gets displayed."""
    return re.sub(r"\s+", " ", text.translate(_QUOTE_CHARS)).strip()


def verify_quote(quote: str, passage_text: str) -> bool:
    """True only if the quote is an exact substring of the passage
    after normalisation."""
    if not quote or not passage_text:
        return False
    return normalize(quote) in normalize(passage_text)


def split_passages(text: str, source_id: str) -> List[Passage]:
    """Split source text into paragraphs, keeping character offsets."""
    passages: List[Passage] = []
    for n, para in enumerate(re.split(r"\n\s*\n", text.strip())):
        para = para.strip()
        if not para:
            continue
        start = text.find(para)
        passages.append(Passage(
            id=f"{source_id}-p{n}",
            sourceId=source_id,
            text=para,
            start=start if start >= 0 else 0,
            end=(start + len(para)) if start >= 0 else len(para),
        ))
    if not passages and text.strip():
        passages.append(Passage(id=f"{source_id}-p0", sourceId=source_id,
                                text=text.strip(), start=0, end=len(text)))
    return passages


def locate_passage(quote: str, passages: List[Passage],
                   threshold: float = 0.6) -> Optional[Tuple[Passage, float]]:
    """Fuzzy-locate the passage most similar to a failed quote.
    Returns the passage and similarity ratio, or None. The caller must
    display the passage's ORIGINAL text, never the model's quote."""
    norm_q = normalize(quote)
    if not norm_q:
        return None
    best: Optional[Tuple[Passage, float]] = None
    for p in passages:
        ratio = difflib.SequenceMatcher(None, norm_q,
                                        normalize(p.text)).ratio()
        if best is None or ratio > best[1]:
            best = (p, ratio)
    if best and best[1] >= threshold:
        return best
    return None
