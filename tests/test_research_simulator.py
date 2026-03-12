from research.simulator import SimulationConfig, SimulationRunner, build_comparison, default_personas


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
    assert result["config"]["persona_count"] >= 1
    assert "total_soft_alerts" in result["adaptive"]
    assert "medium_alert_rate" in result["static_baseline"]
