"""Advise Buddy data model (mirrors MVP Spec v1, section 3).

Stack decision: FastAPI + Pydantic (NOT Next.js). Reason: the builder's
proven stack is FastAPI + vanilla JS (VALIDRIFT), Render is already
familiar, and learning React/TypeScript/Next.js on deadline day is
unnecessary risk. FastAPI serving the static frontend gives the same
"one repo, one deploy" the spec wants from Next.js.
"""
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field

Priority = Literal["critical", "important", "optional"]
Origin = Literal["template", "ai_suggested_accepted", "challenge_accepted"]
SourceType = Literal["official", "third_party"]
TypeSetBy = Literal["user", "heuristic"]
# "error" = source could not be fetched/reviewed (URL given, no text).
# An error cell is NEVER silent: unreviewed evidence must not be
# reported as a gap, and must not count for or against Official Silence.
# "uncertain" = a claim was made but its exact quote could not be
# verified. It is NEVER rendered as silent: silence means the source
# does not cover the item, while an unverified claim is different
# evidence — present, but unconfirmed.
FindingStatus = Literal["stated", "silent", "conflicting",
                         "possibly_outdated", "error", "uncertain"]
FindingLabel = Literal["sourced", "uncertain", "ai_suggested"]
ProposalState = Literal["pending", "accepted", "rejected"]
GapState = Literal["open", "resolved"]


class BlueprintItem(BaseModel):
    id: str
    label: str
    priority: Priority = "important"
    origin: Origin = "template"
    # Optional distinctive anchor phrase: a sentence containing it
    # counts as evidence on its own. Without an anchor, the rule
    # extractor needs >= 2 distinct label keywords in one sentence,
    # so a shared word like "required" alone cannot fake a match.
    anchor: Optional[str] = None


class Blueprint(BaseModel):
    id: str
    title: str
    items: List[BlueprintItem]


class Source(BaseModel):
    id: str
    title: str
    url: Optional[str] = None
    text: str
    type: SourceType = "third_party"
    typeSetBy: TypeSetBy = "user"
    retrievedAt: Optional[str] = None
    detectedDates: List[str] = Field(default_factory=list)


class Passage(BaseModel):
    id: str
    sourceId: str
    text: str
    start: int
    end: int


class Finding(BaseModel):
    itemId: str
    sourceId: str
    status: FindingStatus
    claimSummary: Optional[str] = None
    passageId: Optional[str] = None
    quote: Optional[str] = None
    quoteVerified: bool = False
    label: FindingLabel = "uncertain"


class Proposal(BaseModel):
    id: str
    label: str
    reason: str
    quote: str
    sourceId: str
    state: ProposalState = "pending"


class GapQuestion(BaseModel):
    itemId: str
    text: str
    state: GapState = "open"


class ChecklistEntry(BaseModel):
    itemId: str
    itemLabel: str
    action: str
    score: float
    kind: str  # conflict | official_silence | uncertain | silent | possibly_outdated | undated
    sourceIds: List[str] = Field(default_factory=list)


class Comparison(BaseModel):
    itemId: str
    sourceA: str
    sourceB: str
    verdict: Literal["same", "different", "unclear"]
    reasonCode: str
    reason: str


class AnalysisRequest(BaseModel):
    question: str
    blueprint: Blueprint
    sources: List[Source]
    currentCycle: str = "2026"


class DiscoverRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    max_results: int = Field(default=5, ge=1, le=5)


class DiscoverResponse(BaseModel):
    sources: List[Source]
    fetched: int = 0
    failed: int = 0


class AnalysisResult(BaseModel):
    question: str
    blueprint: Blueprint
    sources: List[Source]
    findings: List[Finding]
    proposals: List[Proposal]
    checklist: List[ChecklistEntry]
    gapQuestions: List[GapQuestion]
    evidenceDebtCount: int
    evidenceDebtItems: List[str] = Field(default_factory=list)
    officialSilenceFlags: List[str] = Field(default_factory=list)  # itemIds
    noOfficialSourceBanner: bool = False
    summary: List[str] = Field(default_factory=list)
    sourceFreshness: Dict[str, str] = Field(default_factory=dict)
    # Share of blueprint weight covered by verified evidence (0-100).
    # Coverage of the user's blueprint, not a truth score.
    completenessScore: int = 0
    # Items with a verified, currently-stated finding from an
    # Official source. The companion number to the score.
    officialConfirmedCount: int = 0
    comparisons: List[Comparison] = Field(default_factory=list)
