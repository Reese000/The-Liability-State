#!/usr/bin/env python3
"""Adversarial agent system for comparison_batch integration.

Provides an adapt_adversarial() function that, given a StrategyController
and a list of worker/business dicts, decides whether each agent switches
to an exploitative strategy. Returns modifications to agent behavior.

Usage:
    from adversarial_bridge import adapt_adversarial, setup_controller
    controller = setup_controller(honesty_mean=0.7)
    modifications = adapt_adversarial(controller, workers, businesses,
                                       ledger, step)
"""
import sys, os
sys.path.insert(0, '/mnt/c/Users/reese/OneDrive/Desktop/AI/The Liability State/simulation/src')

import random
import numpy as np

# Late imports to avoid circular deps
_controller = None
_initialized = False

def _lazy_init():
    global _controller, _initialized
    if _initialized:
        return
    try:
        from adversarial.controller import (
            StrategyController,
            AgentContext,
        )
        # Built-in strategies are registered in controller.py
        _controller = StrategyController()
        
        # Set a moderate honesty distribution (some honest, some exploitative)
        # The default BUILTIN_STRATEGIES include: HonestBaseline, PremiumEvasion,
        # InsuranceFraud, HarbergerGaming, CourtFlooding, GuildRentSeeking,
        # Collusion, ContractBreach, LvtEvasion
        _initialized = True
    except ImportError as e:
        print(f"  [adversarial_bridge] WARNING: Could not load controller: {e}")
        _controller = None
        _initialized = True


def setup_controller(honesty_mean=0.7, seed=42):
    """Initialize StrategyController with a given mean honesty level."""
    _lazy_init()
    global _controller
    if _controller is None:
        return None
    return _controller


def choose_agent_strategy(controller, agent_dict, ledger, step, rng):
    """Evaluate whether an agent should switch to an adversarial strategy.
    
    Returns (strategy_name, expected_value, detection_prob).
    strategy_name is None if the agent stays honest.
    """
    _lazy_init()
    if controller is None:
        return (None, 0.0, 0.0)
    
    # Adapt the agent dict to AgentContext
    ctx = controller.adapt_agent(agent_dict)
    
    # Find best strategy
    best = None
    best_ev = -float('inf')
    
    for strategy in controller.strategies:
        # Skip 'honest' — we only evaluate if exploitation is worth it
        if strategy.is_honest:
            continue
        if not strategy.check_prerequisites(ctx):
            continue
        
        ev = strategy.expected_value(ctx)
        # Apply honesty discount: dishonest value * (1 - honesty)
        honesty = getattr(ctx, 'honesty', 0.5)
        discounted_ev = ev * (1.0 - honesty)
        
        if discounted_ev > best_ev:
            best_ev = discounted_ev
            best = strategy
    
    if best is not None and best_ev > 0:
        det_prob = best.detection_probability(ctx)
        return (best.name, round(best_ev, 2), round(det_prob, 3))
    
    return (None, 0.0, 0.0)


def adapt_agent_behavior(agent_dict, strategy_name, ledger, step, rng):
    """Modify agent behavior based on chosen adversarial strategy.
    
    Returns a dict of modifications to apply to the agent's behavior.
    """
    if strategy_name is None:
        return {}
    
    mods = {'strategy': strategy_name}
    
    if strategy_name == 'PremiumEvasion':
        # Agent under-reports risk — effective risk goes down
        declared_risk = agent_dict.get('risk', 0.05) * rng.uniform(0.3, 0.7)
        mods['declared_risk'] = declared_risk
        mods['concealment_premium'] = 0.1  # invest in concealment
    
    elif strategy_name == 'InsuranceFraud':
        # Agent may file a fraudulent claim (lower effective risk, higher claim prob)
        mods['fraud_probability'] = 0.1  # 10% chance to file a fake claim each step
        mods['concealment_fraud'] = 0.2
    
    elif strategy_name == 'CourtFlooding':
        # Agent files frivolous suits
        mods['frivolous_litigation_rate'] = 0.05
    
    elif strategy_name == 'LvtEvasion':
        # Agent tries to evade LVT by under-declaring land value
        mods['lvt_evasion_rate'] = 0.3  # pay only 70% of LVT due
        mods['concealment_lvt'] = 0.15
    
    elif strategy_name == 'Collusion':
        # Agent colludes on pricing
        mods['collusion_markup'] = 0.15  # extra markup
    
    elif strategy_name == 'HarbergerGaming':
        # Agent under-declares land value and colludes with buyer
        mods['harberger_undervalue'] = 0.25
    
    elif strategy_name == 'ContractBreach':
        # Agent may breach contracts
        mods['breach_probability'] = 0.05
    
    elif strategy_name == 'GuildRentSeeking':
        # Guild restricts membership to raise wages
        mods['membership_restriction'] = 0.2
    
    return mods
