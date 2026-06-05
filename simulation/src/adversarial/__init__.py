"""
adversarial — Phase 3 adversarial behavior for The Liability State.

Exports
-------
StrategyController
    Main controller that evaluates strategies and decides switching.

AdversarialStrategy
    Abstract base class for all strategies.

StrategyEvaluation, AgentContext
    Data containers for strategy evaluation results and agent state.

Concrete strategies
    HonestBaseline, PremiumEvasion, InsuranceFraud, HarbergerGaming,
    CourtFlooding, GuildRentSeeking, Collusion, ContractBreach, LvtEvasion
"""

from .controller import (
    # Core
    StrategyController,
    # Abstract base
    AdversarialStrategy,
    # Data containers
    StrategyEvaluation,
    AgentContext,
    # Concrete strategies (8 required + honest baseline)
    HonestBaseline,
    PremiumEvasion,
    InsuranceFraud,
    HarbergerGaming,
    CourtFlooding,
    GuildRentSeeking,
    Collusion,
    ContractBreach,
    LvtEvasion,
    # Registry
    BUILTIN_STRATEGIES,
)

__all__ = [
    "StrategyController",
    "AdversarialStrategy",
    "StrategyEvaluation",
    "AgentContext",
    "HonestBaseline",
    "PremiumEvasion",
    "InsuranceFraud",
    "HarbergerGaming",
    "CourtFlooding",
    "GuildRentSeeking",
    "Collusion",
    "ContractBreach",
    "LvtEvasion",
    "BUILTIN_STRATEGIES",
]
