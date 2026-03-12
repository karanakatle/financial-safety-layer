from .metrics import ParticipantSimulationSummary, SimulationReport
from .personas import PersonaProfile, default_personas
from .runner import SimulationConfig, SimulationRunner
from .scenarios import SimulationEvent, build_daily_scenario, build_scenario_window


def build_comparison(*args, **kwargs):
    from .compare import build_comparison as _build_comparison

    return _build_comparison(*args, **kwargs)

__all__ = [
    "build_comparison",
    "ParticipantSimulationSummary",
    "PersonaProfile",
    "SimulationConfig",
    "SimulationEvent",
    "SimulationReport",
    "SimulationRunner",
    "build_daily_scenario",
    "build_scenario_window",
    "default_personas",
]
