from backend.nlp.pipeline import (
    ai_policy_contract,
    build_guarded_ai_explanation,
    filter_ai_explanation_output,
    minimize_ai_explanation_context,
)


def test_ai_context_is_redacted_and_minimized_before_provider_use():
    context = {
        "participant_id": "p-sensitive",
        "raw_message": "OTP 123456 for loan offer at https://bad.example. Aadhaar 1234-5678-9012. Avl Bal Rs. 1,234.56.",
        "risk_level": "red",
        "category": "unknown_link_money_pressure",
        "source_type": "sms",
        "reason_code": "link_with_money_pressure",
        "bank_account": "123456789012",
        "exact_salary": "Rs 52000",
        "safe_detail": "user asked why warning appeared",
    }

    minimized = minimize_ai_explanation_context(context, user_consented=True)
    provider_input = minimized["provider_input"]

    assert minimized["ok_for_ai"] is True
    assert provider_input["risk_level"] == "red"
    assert provider_input["category"] == "unknown_link_money_pressure"
    assert provider_input["source_type"] == "sms"
    assert provider_input["reason_code"] == "link_with_money_pressure"
    assert provider_input["safe_detail"] == "user_asked_why_warning_appeared"
    assert "participant_id" not in provider_input
    assert "bank_account" not in provider_input
    assert "exact_salary" not in provider_input

    serialized = str(provider_input)
    assert "123456" not in serialized
    assert "1234-5678-9012" not in serialized
    assert "1,234.56" not in serialized
    assert "https://bad.example" not in serialized
    assert "[redacted_aadhaar]" in serialized
    assert "[redacted_balance]" in serialized


def test_allowed_ai_context_free_text_is_constrained_to_safe_labels():
    minimized = minimize_ai_explanation_context(
        {
            "risk_level": "yellow",
            "safe_detail": "daily income Rs 900, employer is local contractor Rahul near Pune",
        },
        user_consented=True,
    )

    provider_input = minimized["provider_input"]

    assert provider_input["risk_level"] == "yellow"
    assert provider_input["safe_detail"] == "additional_context_removed"
    serialized = str(provider_input).lower()
    assert "900" not in serialized
    assert "rahul" not in serialized
    assert "pune" not in serialized
    assert "contractor" not in serialized


def test_ai_context_requires_user_consent_before_provider_use():
    minimized = minimize_ai_explanation_context(
        {"raw_message": "Pay Rs 499 now", "risk_level": "red"},
        user_consented=False,
    )

    assert minimized["ok_for_ai"] is False
    assert minimized["provider_input"] == {}
    assert minimized["block_reason"] == "ai_consent_required"


def test_uncertain_ai_explanation_is_forced_to_verify_official_source():
    result = build_guarded_ai_explanation(
        user_query="Is this refund link safe?",
        context={
            "raw_message": "Claim refund now at bit.ly/help",
            "risk_level": "red",
            "category": "unknown_link_money_pressure",
        },
        provider_output="This looks unclear. Pause before acting.",
        user_consented=True,
    )

    assert result["display_allowed"] is True
    assert result["policy_result"]["allowed"] is True
    assert "official source" in result["display_text"].lower()
    assert "not financial advice" in result["display_text"].lower()


def test_ai_output_refuses_loan_investment_and_product_recommendations():
    for candidate in [
        "You should take this loan because it looks good.",
        "Invest in this mutual fund for high returns.",
        "Use KreditBee for this EMI.",
        "You can start SIP in ABC Growth Fund from next month.",
        "I recommend a good credit card for this expense.",
    ]:
        filtered = filter_ai_explanation_output(candidate)

        assert filtered["allowed"] is False
        assert filtered["reason_code"] == "regulated_product_recommendation"
        assert "cannot recommend loans" in filtered["safe_text"].lower()
        assert "official source" in filtered["safe_text"].lower()


def test_guarded_ai_explanation_blocks_unsafe_provider_output_before_display():
    result = build_guarded_ai_explanation(
        user_query="Which loan app should I use?",
        context={
            "raw_message": "Need emergency loan",
            "risk_level": "yellow",
            "category": "generic_promotion",
        },
        provider_output="Take this loan app and repay later.",
        user_consented=True,
    )

    assert result["display_allowed"] is False
    assert result["policy_result"]["reason_code"] == "regulated_product_recommendation"
    assert result["display_text"] == result["policy_result"]["safe_text"]


def test_guarded_ai_explanation_refuses_recommendation_request_even_if_provider_is_soft():
    result = build_guarded_ai_explanation(
        user_query="Which mutual fund should I invest in?",
        context={
            "raw_message": "Need to grow money",
            "risk_level": "yellow",
            "category": "generic_promotion",
        },
        provider_output="You should compare options carefully.",
        user_consented=True,
    )

    assert result["display_allowed"] is False
    assert result["policy_result"]["reason_code"] == "regulated_product_recommendation"
    assert "cannot recommend loans" in result["display_text"].lower()


def test_guarded_ai_explanation_refuses_hinglish_recommendation_requests():
    for query in [
        "Kaunsa loan lena chahiye?",
        "Best SIP recommend karo",
        "Which credit card should I take?",
    ]:
        result = build_guarded_ai_explanation(
            user_query=query,
            context={
                "raw_message": "Need money help",
                "risk_level": "yellow",
                "category": "generic_promotion",
            },
            provider_output="Compare options carefully.",
            user_consented=True,
        )

        assert result["display_allowed"] is False
        assert result["policy_result"]["reason_code"] == "regulated_product_recommendation"


def test_ai_policy_contract_declares_future_stage_boundaries():
    contract = ai_policy_contract()

    assert contract["stage"] == "future_guarded_ai_layer"
    assert contract["requires_user_consent"] is True
    assert contract["input_policy"] == "redacted_minimized_context_only"
    assert "loan_recommendation" in contract["prohibited_outputs"]
    assert "investment_recommendation" in contract["prohibited_outputs"]
    assert "product_recommendation" in contract["prohibited_outputs"]
