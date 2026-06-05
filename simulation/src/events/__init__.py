"""Events module — shock event system for The Liability State simulation."""

from .events import (
    ShockEvent,
    NaturalDisaster,
    MassTort,
    Recession,
    InsuranceMarketStress,
    EventManager,
    build_schedule,
    DEFAULT_EVENT_SCHEDULE,
    linear_recovery,
    exponential_recovery,
    step_recovery,
)

__all__ = [
    "ShockEvent",
    "NaturalDisaster",
    "MassTort",
    "Recession",
    "InsuranceMarketStress",
    "EventManager",
    "build_schedule",
    "DEFAULT_EVENT_SCHEDULE",
    "linear_recovery",
    "exponential_recovery",
    "step_recovery",
]
