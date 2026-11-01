"""Hard-coded decision templates (MVP Spec v1, section 4 step 1).

These are QUESTIONS, not factual claims, so they carry no truth value
about any real scheme. The user edits the list; AI may only suggest
additions, which arrive as pending proposals.
"""
import re

from .models import Blueprint, BlueprintItem


def _items(pairs):
    return [BlueprintItem(id=f"i{n + 1}", label=label, priority=p,
                          anchor=a)
            for n, (label, p, a) in enumerate(pairs)]


TEMPLATES = {
    "general": Blueprint(
        id="general",
        title="General research — edit for your topic",
        items=_items([
            ("What requirements or conditions apply?", "critical", None),
            ("What are the costs, fees or charges?", "important", None),
            ("What deadlines or dates apply?", "critical", None),
            ("What steps or process are required?", "important", None),
            ("What restrictions or exceptions apply?", "important", None),
            ("What is the official source or contact?", "important", None),
        ]),
    ),
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

TEMPLATES["college_verification"] = Blueprint(
    id="college_verification", title="College verification",
    items=_items([
        ("Is the college recognized by the relevant authority?", "critical", "recognized"),
        ("What accreditation or approval does the institution have?", "critical", "accreditation"),
        ("Which university is the college affiliated with?", "critical", "affiliated"),
        ("What courses and qualifications are offered?", "important", None),
        ("What are the tuition fees and refund conditions?", "important", None),
        ("What evidence supports placement claims?", "important", "placement"),
        ("What is the official institution contact?", "important", None),
    ]),
)
TEMPLATES["course"] = Blueprint(
    id="course", title="Course / certification",
    items=_items([
        ("Who provides the course and certificate?", "critical", None),
        ("What accreditation or recognition is claimed?", "critical", "accreditation"),
        ("What topics and skills does the syllabus cover?", "important", "syllabus"),
        ("What are the total fees and refund conditions?", "important", None),
        ("What is the course duration and study mode?", "important", None),
        ("What are the eligibility and assessment requirements?", "important", None),
    ]),
)
TEMPLATES["public_service"] = Blueprint(
    id="public_service", title="Government scheme / public service",
    items=_items([
        ("Who is eligible for the scheme or service?", "critical", "eligible"),
        ("What benefits or services are provided?", "critical", None),
        ("What documents are required?", "important", "documents"),
        ("What fees or charges apply?", "important", None),
        ("What are the application steps and deadline?", "critical", None),
        ("What is the official portal or contact?", "important", None),
    ]),
)
TEMPLATES["product"] = Blueprint(
    id="product", title="Product / service comparison",
    items=_items([
        ("What features and specifications are included?", "critical", None),
        ("What is the total price including extra charges?", "critical", None),
        ("What restrictions or exclusions apply?", "important", None),
        ("What are the warranty and support terms?", "important", "warranty"),
        ("What are the cancellation or refund conditions?", "important", None),
        ("What evidence supports the advertised claims?", "important", None),
    ]),
)


def research_plan(question: str) -> Blueprint:
    """Choose a starting checklist; unmatched topics retain the user's question."""
    topic = question.lower()
    categories = [
        ("scholarship", r"scholarship|fellowship|bursary"),
        ("passport", r"passport|visa"),
        ("college_verification", r"college|university|institution"),
        ("college_admission", r"admission|entrance exam"),
        ("job_offer", r"job|employer|salary|employment|internship"),
        ("course", r"course|certification|bootcamp|training"),
        ("public_service", r"government|scheme|public service|subsidy"),
        ("product", r"product|subscription|warranty|laptop|phone|software"),
    ]
    # Admission questions need application requirements, not institution checks.
    if re.search(r"\b(admission|admissions|apply|applying)\b", topic) and re.search(r"\b(college|university)\b", topic):
        key = "college_admission"
    else:
        key = next((key for key, pattern in categories
                    if re.search(r"\b(?:" + pattern + r")\b", topic)), "general")
    plan = TEMPLATES[key].model_copy(deep=True)
    focused = []
    if key == "general" and re.search(r"opening|opening hours|visiting hours|timings", topic):
        focused.append(BlueprintItem(id="opening_hours", label="What are the opening hours?",
                                     priority="critical", anchor="opening hours"))
    if key == "general" and re.search(r"ticket|entry price|admission price", topic):
        focused.append(BlueprintItem(id="ticket_fees", label="What are the entry ticket fees?",
                                     priority="critical", anchor="ticket"))
    if not focused and re.search(r"^(?:what|who|which|where|when|why|how|is|are|can|does|do|should|check|verify)\b|\?$", question, re.I):
        focused = [BlueprintItem(id="research_question", label=question,
                                 priority="critical")]
    plan.items[0:0] = focused
    return plan
