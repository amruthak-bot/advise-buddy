import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.templates import TEMPLATES, research_plan


def test_college_verification_checks_recognition_not_only_admissions():
    plan = research_plan("Is North Example College recognized and accredited?")
    assert plan.id == "college_verification"
    assert any("accreditation" in item.label for item in plan.items)
    assert not any("police" in item.label for item in plan.items)


def test_college_admission_and_scholarship_use_their_own_checks():
    assert research_plan("How do I apply to a college?").id == "college_admission"
    assert research_plan("College scholarship renewal requirements").id == "scholarship"


def test_other_topic_keeps_the_actual_question_without_mutating_templates():
    question = "What evidence supports the claims about a local history exhibition?"
    plan = research_plan(question)
    assert plan.id == "general"
    assert plan.items[0].label == question
    assert len(plan.items) == len(TEMPLATES["general"].items) + 1
    assert all(item.id != "research_question" for item in TEMPLATES["general"].items)
