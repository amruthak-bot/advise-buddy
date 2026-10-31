"""Hard-coded decision templates (MVP Spec v1, section 4 step 1).

These are QUESTIONS, not factual claims, so they carry no truth value
about any real scheme. The user edits the list; AI may only suggest
additions, which arrive as pending proposals.
"""
from .models import Blueprint, BlueprintItem


def _items(pairs):
    return [BlueprintItem(id=f"i{n + 1}", label=label, priority=p,
                          anchor=a)
            for n, (label, p, a) in enumerate(pairs)]


TEMPLATES = {
    "passport": Blueprint(
        id="passport",
        title="Passport / Visa application",
        items=_items([
            ("Who is eligible to apply?", "critical", "eligible"),
            ("What documents are required?", "critical", "documents"),
            ("What is the application fee?", "critical", "fee"),
            ("What is the official application link or portal?", "critical", "portal"),
            ("How do I book an appointment?", "important", "appointment"),
            ("How long does processing take?", "important", "processing"),
            ("Is police verification required, and what does it involve?", "important", "police verification"),
            ("What are the renewal conditions?", "important", "renewal"),
            ("What is the contact or help channel?", "optional", "contact"),
        ]),
    ),
    "scholarship": Blueprint(
        id="scholarship",
        title="Scholarship application",
        items=_items([
            ("Who is eligible?", "critical", None),
            ("What is the application deadline?", "critical", None),
            ("What documents are required?", "critical", None),
            ("What are the renewal conditions?", "critical", None),
            ("What is the scholarship amount?", "important", None),
            ("What is the official application link?", "critical", None),
            ("What is the contact or help channel?", "optional", None),
        ]),
    ),
    "college_admission": Blueprint(
        id="college_admission",
        title="College admission",
        items=_items([
            ("Who is eligible?", "critical", None),
            ("What is the application deadline?", "critical", None),
            ("What documents are required?", "critical", None),
            ("What is the fee?", "important", None),
            ("Is there an entrance exam?", "important", None),
            ("What is the official application link?", "critical", None),
            ("What is the contact or help channel?", "optional", None),
        ]),
    ),
    "job_offer": Blueprint(
        id="job_offer",
        title="Job offer",
        items=_items([
            ("What is the role and team?", "critical", None),
            ("What is the salary and benefits?", "critical", None),
            ("What is the joining date?", "critical", None),
            ("What documents are required?", "important", None),
            ("Is there a probation period?", "important", None),
            ("What is the work location and mode?", "important", None),
            ("Who is the contact person?", "optional", None),
        ]),
    ),
}
