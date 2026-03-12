from research.simulator import SimulationConfig, SimulationRunner, build_comparison, build_sweep, default_personas
from research.simulator.runner import _adaptive_policy_profile
from research.simulator.scenarios import build_scenario_window


def test_simulator_produces_report() -> None:
    runner = SimulationRunner(SimulationConfig(days=14, seed=17))
    report = runner.run(default_personas()[:2], variant="adaptive")

    aggregate = report.aggregate()

    assert aggregate["participants"] == 2
    assert aggregate["total_alerts"] >= 0
    assert aggregate["total_soft_alerts"] + aggregate["total_medium_alerts"] + aggregate["total_hard_alerts"] == aggregate["total_alerts"]
    assert 0.0 <= aggregate["retention_rate"] <= 1.0


def test_static_and_adaptive_variants_are_supported() -> None:
    runner = SimulationRunner(SimulationConfig(days=5, seed=9))
    personas = default_personas()[:1]

    adaptive = runner.run(personas, variant="adaptive").aggregate()
    static = runner.run(personas, variant="static_baseline").aggregate()

    assert adaptive["participants"] == 1
    assert static["participants"] == 1


def test_build_comparison_returns_expected_sections() -> None:
    result = build_comparison(days=5, seed=3, include_adverse_events=True)

    assert "adaptive" in result
    assert "static_baseline" in result
    assert "delta_adaptive_minus_static" in result
    assert "per_persona" in result
    assert result["config"]["persona_count"] >= 1
    assert "total_soft_alerts" in result["adaptive"]
    assert "medium_alert_rate" in result["static_baseline"]
    assert len(result["per_persona"]) >= 1
    first = result["per_persona"][0]
    assert "participant_id" in first
    assert "adaptive" in first
    assert "static_baseline" in first
    assert "delta_adaptive_minus_static" in first
    assert "trust_score_final" in first["adaptive"]
    assert "alert_count" in first["static_baseline"]
    assert "preventive_inconvenient_rate" in first["adaptive"]
    assert "beneficial_rate" in result["adaptive"]


def test_adaptive_policy_profile_varies_by_persona_risk() -> None:
    personas = {persona.persona_id: persona for persona in default_personas()}

    cautious = _adaptive_policy_profile(personas["women_household_cautious"], "default")
    fraud_prone = _adaptive_policy_profile(personas["driver_fraud_prone"], "default")

    assert cautious["limit_factor"] > fraud_prone["limit_factor"]
    assert cautious["warning_ratio"] > fraud_prone["warning_ratio"]
    assert cautious["warmup_seed_multiplier"] > fraud_prone["warmup_seed_multiplier"]


def test_adaptive_policy_profile_is_calmer_for_cautious_emergency_context() -> None:
    persona = {item.persona_id: item for item in default_personas()}["women_household_cautious"]

    default_profile = _adaptive_policy_profile(persona, "default")
    emergency_profile = _adaptive_policy_profile(persona, "medical_emergency")

    assert emergency_profile["limit_factor"] > default_profile["limit_factor"]
    assert emergency_profile["warning_ratio"] >= default_profile["warning_ratio"]


def test_build_comparison_supports_scenario_presets() -> None:
    result = build_comparison(days=7, seed=5, include_adverse_events=True, scenario="fraud_week")

    assert result["config"]["scenario"] == "fraud_week"
    assert "per_persona" in result


def test_medical_emergency_scenario_includes_emergency_spike() -> None:
    persona = default_personas()[0]
    timeline = build_scenario_window(
        persona,
        start_date=SimulationConfig().start_date,
        days=14,
        seed=7,
        include_adverse_events=True,
        scenario="medical_emergency",
    )

    assert any(event.description == "medical emergency expense" for event in timeline)


def test_shared_phone_noise_heavy_scenario_increases_noise_events() -> None:
    persona = {item.persona_id: item for item in default_personas()}["shared_phone_household"]
    base_timeline = build_scenario_window(
        persona,
        start_date=SimulationConfig().start_date,
        days=14,
        seed=9,
        include_adverse_events=True,
        scenario="default",
    )
    noisy_timeline = build_scenario_window(
        persona,
        start_date=SimulationConfig().start_date,
        days=14,
        seed=9,
        include_adverse_events=True,
        scenario="shared_phone_noise_heavy",
    )

    base_noise = sum(1 for event in base_timeline if event.event_type == "shared_phone_noise")
    noisy_noise = sum(1 for event in noisy_timeline if event.event_type == "shared_phone_noise")

    assert noisy_noise >= base_noise


def test_build_sweep_returns_all_presets() -> None:
    result = build_sweep(days=5, seed=3, include_adverse_events=True)

    assert result["config"]["scenario_count"] >= 5
    assert "default" in result["scenarios"]
    assert "shared_phone_noise_heavy" in result["scenarios"]
    assert len(result["summary_rows"]) == result["config"]["scenario_count"]


def test_shared_phone_festival_policy_is_calmer_than_default() -> None:
    persona = {item.persona_id: item for item in default_personas()}["shared_phone_household"]

    default_profile = _adaptive_policy_profile(persona, "default")
    festival_profile = _adaptive_policy_profile(persona, "festival_spend")

    assert festival_profile["limit_factor"] > default_profile["limit_factor"]
    assert festival_profile["warning_ratio"] >= default_profile["warning_ratio"]
