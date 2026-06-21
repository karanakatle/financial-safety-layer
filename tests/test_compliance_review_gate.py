from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8").lower()


def test_compliance_gate_documents_product_boundaries():
    gate = read_text("docs/compliance-review-gate.md")

    required_terms = [
        "not legal advice",
        "scaled pilot",
        "fintech lawyer",
        "privacy lawyer",
        "investment advice",
        "loan recommendation",
        "lender ranking",
        "product sales",
        "regulated financial advice",
        "specific financial product",
        "hallucination",
        "human review",
        "bank",
        "ngo",
        "bc",
        "business correspondent",
        "copy review checklist",
        "before external pilot",
        "conditional go must not be used to bypass a no-go item",
        "owner, due date, and written closure note",
    ]

    missing = [term for term in required_terms if term not in gate]
    assert missing == []


def test_release_and_pilot_docs_reference_compliance_gate():
    play_checklist = read_text("ArthamantriAndroid/PLAY_CONSOLE_CHECKLIST.md")
    pilot_checklist = read_text("research/pilot_rollout_checklist.md")

    for doc in (play_checklist, pilot_checklist):
        assert "docs/compliance-review-gate.md" in doc
        assert "compliance/legal review" in doc
        assert "external pilot" in doc
        assert "investment advice" in doc
        assert "loan recommendation" in doc
        assert "product sales" in doc


def test_ai_adoption_plan_routes_user_facing_ai_through_gate():
    ai_plan = read_text("research/ai_adoption_plan_v1.md")

    assert "docs/compliance-review-gate.md" in ai_plan
    assert "hallucination/advice review" in ai_plan
    assert "investment advice" in ai_plan
    assert "loan recommendation" in ai_plan
    assert "lender ranking" in ai_plan
    assert "product sales" in ai_plan
