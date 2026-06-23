#!/usr/bin/env python3
"""
missing_mechanisms.py — 10 config-driven mechanisms to bring the simulation closer to reality.

All mechanisms follow the existing pattern from comparison_phase8.py: config-driven,
default OFF, modifiable through PHASE8_DEFAULTS.

Mechanism functions take (config, rng, workers, retirees, businesses, bal, land_values, step, current_metrics)
and modify state in-place. Each returns a dict with any step-level metrics to log.

Config keys added here, default OFF:
  - use_public_goods, public_goods_efficiency
  - inflation_rate
  - bankruptcy_threshold
  - gov_service_productivity, gov_service_elasticity
  - cpf_liquidity_trap, cpf_demand_suppression, cpf_housing_feedback
  - endogenous_tfp, rnd_investment_rate, tfp_growth_rate
  - mobility_cost
  - wage_competition, wage_competition_intensity
  - capital_ownership_share, capital_ownership_concentration
  - use_olg, olg_retirement_age, olg_entry_wealth
  - use_housing_market
  - use_international_trade
  - use_proper_olg
  - use_super_wealthy
  - use_real_trade
  - cpf_opportunity_cost
  - use_power_law_wealth (replaces super_wealthy)
  - use_immigrant_labor
  - inheritance_flow_fraction (replaces inherit_bequest)
  - use_structural_gap
"""
import logging
import numpy as np

_log = logging.getLogger('missing_mechs')

# ─── Config defaults (appended to PHASE8_DEFAULTS) ───────────────────

MISSING_MECH_DEFAULTS = {
    # 1. Public goods funding requirement
    'use_public_goods': False,
    'public_goods_target': 0.05,        # Minimum govt spend as fraction of total output
    'public_goods_penalty': 0.3,        # Productivity penalty when below target (max 30%)
    # 2. Inflation
    'inflation_rate': 0.0,              # Annual inflation rate (0.02 = 2%)
    # 3. Bankruptcy
    'bankruptcy_threshold': 0.0,        # Max negative balance before bankruptcy (0 = disabled)
    # 4. Government services as productivity input
    'gov_service_productivity': 0.0,    # Fraction of tax revenue that boosts worker productivity
    'gov_service_elasticity': 0.15,     # Elasticity of productivity to gov services per capita
    # 5. Forced savings externalities (CPF-side effects)
    'cpf_liquidity_trap': 0.0,         # Max hourly wage reduction from forced savings lock (0-0.15)
    'cpf_demand_suppression': 0.0,     # Max business TFP reduction from demand suppression (0-0.15)
    'cpf_housing_feedback': 0.0,       # Housing cost inflation from forced savings (0-0.10)
    # 6. Endogenous TFP / R&D growth
    'endogenous_tfp': False,
    'rnd_investment_rate': 0.20,        # Fraction of after-tax profit invested in R&D
    'tfp_growth_elasticity': 0.05,     # Annual TFP growth per unit of R&D intensity
    # 7. Occupational choice / labor mobility
    'mobility_cost': 0.0,               # Fraction of wealth lost when switching jobs (0 = disabled)
    # 8. Wage competition / labor market bidding
    'wage_competition': False,
    'wage_competition_intensity': 0.1,  # How much wage competition compresses dispersion (0-1)
    # 9. Capital ownership / equity distribution
    'capital_ownership_share': 0.0,     # Fraction of after-tax profit distributed as capital income
    'capital_ownership_concentration': 0.5, # How concentrated capital income is (0=equal, 1=by wealth)
    # 10. Overlapping generations (simplified)
    'use_olg': False,
    'olg_retirement_periods': 120,       # Steps after which a worker retires (10 years)
    'olg_entry_cash': 20000,            # Cash new entrants receive
    # ── 11. Housing/land market (mortgages, rents, development) ──
    'use_housing_market': False,
    'housing_rent_ratio': 0.005,         # Monthly rent as fraction of land value (0.5%)
    'housing_mortgage_rate': 0.06,       # Annual mortgage interest rate
    'housing_mortgage_lv_ratio': 0.8,    # Max loan-to-value ratio for mortgages
    'housing_development_boost': 0.02,   # Annual land value appreciation from development
    # ── 12. International trade ──
    'use_international_trade': False,
    'trade_openness': 0.2,               # Fraction of output exported/imported
    'trade_land_advantage': 0.1,         # Land-intensive export premium
    'trade_capital_flow': 0.01,          # Capital flow as fraction of trade balance
    # ── 13. Proper OLG with bequests ──
    'use_proper_olg': False,
    'proper_olg_cohorts': 3,             # Number of age cohorts (young, middle, old)
    'proper_olg_productivity': [0.7, 1.3, 0.8],  # Relative productivity by cohort
    'proper_olg_bequest_rate': 0.3,      # Fraction of wealth bequeathed at death
    'proper_olg_generation_length': 40,  # Steps per generation (~40mo = ~3yr)
    # ── 14. Super-wealthy agents (power-law wealth distribution) ──
    'use_super_wealthy': False,
    'super_wealthy_fraction': 0.02,      # Top fraction of workers who are super-wealthy
    'super_wealthy_multiplier': 5.0,     # How much wealthier they are (power-law tail)
    # ── 15. Improved trade mechanism ──
    'use_real_trade': False,
    'real_trade_openness': 0.3,          # Trade as fraction of output
    'real_trade_skill_premium': 0.15,    # Export sector wage premium
    'real_trade_import_penalty': 0.05,   # Import competition wage suppression
    # ── 16. CPF opportunity cost ──
    'cpf_opportunity_cost': 0.0,         # Fraction of CPF wealth lost to below-market returns (0-0.8)
    # ── 17. Power-law wealth concentration (replaces super_wealthy) ──
    'use_power_law_wealth': False,
    'power_law_exponent': 0.3,           # Return premium per log-wealth (0-0.5)
    'wealth_tail_fraction': 0.01,        # Top fraction that get the premium (default 1%)
    # ── 18. Immigrant labor wedge ──
    'use_immigrant_labor': False,
    'immigrant_share': 0.0,              # Bottom fraction of workers who are immigrants (0-1)
    'immigrant_wage_penalty': 0.0,       # Wage suppression fraction (0-1)
    # ── 19. Concentrated inheritance (replaces inherit_bequest) ──
    'inheritance_flow_fraction': 0.0,    # Fraction of total wealth redistributed per year as inheritance (0-1)
    'inheritance_concentration': 0.5,    # 0=equal distribution, 1=wealth-weighted
    # ── 20. Structural wealth gap (racial/group-level initial disparity) ──
    'use_structural_gap': False,
    'structural_gap_groups': [],         # List of group population fractions (e.g., [0.8, 0.2])
    'structural_gap_multipliers': [],    # List of wealth multipliers per group (e.g., [1.0, 0.1])
    'structural_gap_recurrence': 0.1,    # Fraction of gap that reapplies each generation (0-1)
    # ── 21. Forced reinvestment of idle capital (LS-aligned) ──
    'forced_reinvestment': False,
    'reinvestment_rate': 0.3,            # Fraction of excess idle cash reinvested per step (0-1)
    'idle_cash_threshold': 0.3,          # Max idle cash as fraction of productive capital (0-1)
    'reinvestment_boost': 0.05,          # Productivity boost on reinvested capital (new capital is ~5% more productive)
}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 1: Public goods funding requirement
# ═══════════════════════════════════════════════════════════════════════

def apply_public_goods(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """If government spending is below target, productivity suffers.
    
    Uses tax revenue from step_metrics to measure govt capacity.
    For no-tax systems (Laissez-Faire), applies penalty directly.
    """
    use = config.get('use_public_goods', False)
    if not use:
        return {}
    
    target = float(config.get('public_goods_target', 0.05))
    penalty = float(config.get('public_goods_penalty', 0.3))
    
    # Get total tax revenue from step_metrics (set by the step loop)
    tax_revenue = step_metrics.get('total_tax', 0)
    
    # Check if this is a no-tax system
    tax_type = config.get('tax_type', 'lvt')
    
    if tax_type == 'none' or tax_revenue <= 0:
        # Zero government → public goods penalty applies directly
        for w in workers:
            wage_reduction = w.get('hourly', 0) * penalty * 0.5
            w['hourly'] = max(w.get('hourly', 0) - wage_reduction, 5.0)
            w['monthly'] = w['hourly'] * 160
        return {'public_goods_penalty': penalty * 0.5, 'tax_type': 'none'}
    
    # Measure ratio of tax revenue to economy size
    economy_size = sum(bal.get(w['id'], 0) for w in workers) if workers else 1
    economy_size = max(economy_size, 1)
    
    actual_ratio = tax_revenue / economy_size
    if actual_ratio < target and actual_ratio > 0:
        shortfall = (target - actual_ratio) / target
        penalty_mult = min(penalty, shortfall * penalty)
        
        for w in workers:
            wage_reduction = w.get('hourly', 0) * penalty_mult
            w['hourly'] = max(w.get('hourly', 0) - wage_reduction, 5.0)
            w['monthly'] = w['hourly'] * 160
        
        _log.info("Step %d: public goods shortfall %.1f%% -> wage penalty %.1f%%",
                  step, shortfall * 100, penalty_mult * 100)
        return {'public_goods_penalty': penalty_mult}
    
    return {'public_goods_ratio': actual_ratio}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 2: Inflation
# ═══════════════════════════════════════════════════════════════════════

def apply_inflation(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Annual inflation erodes real cash holdings.
    
    Applied monthly: cash *= (1 - inflation_rate/12)^(1/step)
    But we annualize: once per 12 steps, erode cash by annual rate.
    This prevents catastrophic compounding on every step.
    """
    rate = float(config.get('inflation_rate', 0.0))
    if rate <= 0:
        return {}
    
    # Apply erosion once per simulated year (every 12 steps)
    if step % 12 != 0:
        return {}
    
    total_eroded = 0.0
    
    for eid in list(bal.keys()):
        if eid in ('sys', 'trust', 'bank', 'harberger_escrow', 'h_escrow'):
            continue
        cash = bal.get(eid, 0)
        if cash > 0:
            erosion = cash * rate
            bal[eid] = cash - erosion
            bal['sys'] = bal.get('sys', 0) + erosion
            total_eroded += erosion
    
    if total_eroded > 0:
        _log.debug("Year %d: inflation eroded $%.0f (rate=%.1f%%)",
                   step // 12, total_eroded, rate * 100)
    
    return {'inflation_eroded': total_eroded}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 3: Bankruptcy
# ═══════════════════════════════════════════════════════════════════════

def apply_bankruptcy(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Agents with negative cash below threshold declare bankruptcy.
    
    On bankruptcy: balance resets to 0, a fraction of land/capital is 
    liquidated to pay debts (transferred to 'sys').
    """
    threshold = float(config.get('bankruptcy_threshold', 0.0))
    if threshold >= 0:
        return {}  # Only active when threshold < 0 (e.g., -1000)
    
    bankruptcies = 0
    total_recovered = 0.0
    
    all_agents = workers + retirees + businesses
    for agent in all_agents:
        aid = agent['id']
        cash = bal.get(aid, 0)
        if cash < threshold:
            # Bankruptcy: liquidate land/capital
            land_val = agent.get('land', 0)
            capital_val = agent.get('capital', 0) if isinstance(agent, dict) else 0
            recovery = (land_val + capital_val) * 0.5  # 50% recovery
            total_recovered += recovery
            
            # Reset balance to 0
            bal[aid] = 0
            agent['land'] = 0
            if 'capital' in agent:
                agent['capital'] = max(agent.get('capital', 0) * 0.3, 1000)  # Keep 30% capital
            
            bal['sys'] = bal.get('sys', 0) + recovery
            bankruptcies += 1
    
    if bankruptcies > 0:
        _log.info("Step %d: %d bankruptcies, $%.0f recovered", step, bankruptcies, total_recovered)
    
    return {'bankruptcies': bankruptcies, 'recovered': total_recovered}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 4: Government services as productivity input
# ═══════════════════════════════════════════════════════════════════════

def apply_gov_service_productivity(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Government spending on services (welfare, courts, healthcare, education)
    boosts worker productivity. Proportional to per-capita govt services spending.
    
    Formula: productivity_mult = 1 + elasticity * ln(1 + g_per_capita / base_g)
    Applied ONCE per year to baseline hourly wages (not compounding every step).
    Stores baseline in _base_hourly if not set.
    """
    enabled = float(config.get('gov_service_productivity', 0.0))
    elasticity = float(config.get('gov_service_elasticity', 0.15))
    
    if enabled <= 0 or not workers:
        return {}
    
    # Initialize baseline hourly wages on first call
    for w in workers:
        if '_base_hourly' not in w:
            w['_base_hourly'] = w.get('hourly', 20)
    
    # Apply annually
    if step % 12 != 1:
        return {}
    
    # Use tax revenue from step_metrics, annualized
    # Single-step tax * 12 = annual estimate
    total_tax = float(step_metrics.get('total_tax', 0)) * 12
    if total_tax <= 0:
        return {}
    
    population = len(workers) + len(retirees)
    population = max(population, 1)
    
    g_per_capita = total_tax / population
    base_g = 5000  # Calibrated for flow-based (annualized) tax revenue
    
    if g_per_capita > 0:
        prod_mult = 1.0 + elasticity * np.log(1.0 + g_per_capita / base_g)
        prod_mult = max(1.0, min(1.5, prod_mult))
        
        for w in workers:
            base = w.get('_base_hourly', 20)
            w['hourly'] = base * prod_mult
            w['monthly'] = w['hourly'] * 160
        
        return {'gov_prod_mult': prod_mult, 'g_per_capita': g_per_capita}
    
    return {}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 5: Forced savings externalities
def apply_forced_savings_externalities(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Negative externalities from forced savings (CPF-style).
    
    1. Liquidity trap: high savings rate → workers can't invest in human capital
       → hourly wage reduced by up to cpf_liquidity_trap
    2. Demand suppression: high savings → reduced consumption → lower business TFP
    3. Housing feedback: savings channeled into housing → price inflation
    
    Initializes _base_hourly on first call so wage modifications don't compound.
    """
    liq_trap = float(config.get('cpf_liquidity_trap', 0.0))
    demand_supp = float(config.get('cpf_demand_suppression', 0.0))
    housing_fb = float(config.get('cpf_housing_feedback', 0.0))
    
    if liq_trap <= 0 and demand_supp <= 0 and housing_fb <= 0:
        return {}
    
    # Initialize baseline wages for all workers (one-time)
    for w in workers:
        if '_base_hourly' not in w:
            w['_base_hourly'] = w.get('hourly', 20)
    for b in businesses:
        if '_base_tfp' not in b and 'tfp' in b:
            b['_base_tfp'] = b['tfp']
    
    cpf_rate = float(config.get('cpf_rate', 0.0))
    savings_rate = cpf_rate
    if savings_rate <= 0.05:
        return {}
    
    results = {}
    
    # 1. Liquidity trap: one-time reduction applied annually
    if liq_trap > 0 and step % 12 == 1:
        liq_factor = 1.0 - liq_trap * min(1.0, savings_rate / 0.37)
        liq_factor = max(0.85, liq_factor)
        
        for w in workers:
            base = w.get('_base_hourly', 20)
            w['hourly'] = base * liq_factor
            w['monthly'] = w['hourly'] * 160
        
        results['liq_factor'] = liq_factor
    
    # 2. Demand suppression: one-time TFP reduction applied annually
    if demand_supp > 0 and step % 12 == 1:
        demand_factor = 1.0 - demand_supp * min(1.0, savings_rate / 0.37)
        demand_factor = max(0.85, demand_factor)
        
        for b in businesses:
            if 'tfp' in b:
                base_tfp = b.get('_base_tfp', b['tfp'])
                b['tfp'] = base_tfp * demand_factor
        
        results['demand_factor'] = demand_factor
    
    # 3. Housing feedback: one-time wage reduction applied annually
    if housing_fb > 0 and step % 12 == 1:
        housing_factor = 1.0 / (1.0 + housing_fb * min(1.0, savings_rate / 0.37))
        housing_factor = max(0.90, housing_factor)
        
        for w in workers:
            base = w.get('_base_hourly', 20)
            w['hourly'] = base * housing_factor
            w['monthly'] = w['hourly'] * 160
        
        results['housing_factor'] = housing_factor
    
    # 4. CPF opportunity cost: below-market returns reduce effective savings
    opp_cost = float(config.get('cpf_opportunity_cost', 0.0))
    if opp_cost > 0 and savings_rate > 0.05 and step % 12 == 1:  # Annual
        # Reduce effective CPF wealth accumulation
        # The opportunity cost reduces the CPF payout by opp_cost fraction
        # This models: $1 in CPF @ 2.5% vs $1 in market @ 7% over 40 years
        # Transfers the lost returns from workers to 'sys'
        total_lost = 0.0
        for w in workers:
            wage = w.get('monthly', 3200)
            cpf_contribution = wage * savings_rate * opp_cost
            if cpf_contribution > 0 and bal.get(w['id'], 0) >= cpf_contribution * 0.1:
                # Take a fraction from worker balance (simplified — real CPF is locked)
                bal[w['id']] = bal.get(w['id'], 0) - cpf_contribution * 0.05
                bal['sys'] = bal.get('sys', 0) + cpf_contribution * 0.05
                total_lost += cpf_contribution * 0.05
        
        results['opportunity_cost'] = total_lost
    
    return results


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 6: Endogenous TFP / R&D growth
# ═══════════════════════════════════════════════════════════════════════

def apply_endogenous_tfp(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Businesses invest after-tax profit in R&D → TFP grows over time.
    
    Lower tax rates → more retained profit → more R&D → faster TFP growth.
    This is the primary channel by which tax efficiency compounds into wealth.
    """
    if not config.get('endogenous_tfp', False):
        return {}
    
    rnd_rate = float(config.get('rnd_investment_rate', 0.05))
    tfp_elast = float(config.get('tfp_growth_elasticity', 0.02))
    
    total_rd = 0.0
    total_tfp_change = 0.0
    
    for b in businesses:
        # After-tax profit available for R&D (proxy: capital * rate)
        capital = b.get('capital', 100000)
        # Estimate profit as return on capital
        profit = capital * 0.08 / 12  # ~8% annual return, monthly
        rd_investment = profit * rnd_rate
        
        # TFP grows proportionally to R&D intensity (R&D / capital)
        rd_intensity = rd_investment / max(capital, 1)
        tfp_growth = rd_intensity * tfp_elast
        
        # Apply TFP growth (compounds)
        current_tfp = b.get('tfp', 1.0)
        new_tfp = current_tfp * (1.0 + tfp_growth)
        b['tfp'] = min(5.0, max(0.5, new_tfp))  # Cap TFP at 5x
        
        total_rd += rd_investment
        total_tfp_change += tfp_growth
    
    if total_rd > 0 and step % 60 == 0:
        _log.info("Step %d: R&D=$%.0f, avg TFP growth=%.4f",
                  step, total_rd, total_tfp_change / max(len(businesses), 1))
    
    return {'rd_investment': total_rd, 'avg_tfp_growth': total_tfp_change / max(len(businesses), 1)}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 7: Occupational choice / labor mobility
# ═══════════════════════════════════════════════════════════════════════

def apply_occupational_mobility(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Workers can switch to higher-paying jobs with a mobility cost.
    
    Each step, workers evaluate: is there a higher-paying 'job' available?
    Currently proxied by: workers can adjust their hours toward the median.
    A real implementation would have multiple job types.
    """
    mobility_cost = float(config.get('mobility_cost', 0.0))
    if mobility_cost <= 0:
        return {}
    
    switches = 0
    if workers:
        hourly_vals = [w.get('hourly', 0) for w in workers]
        median_hr = float(np.median(hourly_vals)) if hourly_vals else 20.0
        
        for w in workers:
            current = w.get('hourly', 20)
            # Opportunity: move toward median if far from it
            gap = median_hr - current
            if abs(gap) / max(current, 1) > 0.2:  # More than 20% gap
                # Cost to switch (fraction of wealth)
                cost = bal.get(w['id'], 0) * mobility_cost
                if cost < bal.get(w['id'], 0):
                    bal[w['id']] = bal.get(w['id'], 0) - cost
                    bal['sys'] = bal.get('sys', 0) + cost
                    
                    # New wage moves halfway toward median
                    new_hr = current + gap * 0.3
                    w['hourly'] = new_hr
                    w['monthly'] = new_hr * 160
                    switches += 1
    
    if switches > 0:
        _log.debug("Step %d: %d workers switched jobs", step, switches)
    
    return {'job_switches': switches}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 8: Wage competition / labor market bidding
# ═══════════════════════════════════════════════════════════════════════

def apply_wage_competition(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Firms compete for workers, compressing wage dispersion.
    
    In a competitive labor market, firms bid up wages for scarce skills.
    This reduces the dispersion created by education_variance and wage_dispersion_mult.
    Higher competition intensity → more compression.
    
    Effects:
    - Raises bottom wages (firms compete for cheap labor)
    - Compresses top wages slightly (less monopsony power)
    """
    if not config.get('wage_competition', False):
        return {}
    
    intensity = float(config.get('wage_competition_intensity', 0.1))
    if intensity <= 0 or not workers:
        return {}
    
    hourly_vals = np.array([w.get('hourly', 20) for w in workers])
    median_hr = float(np.median(hourly_vals)) if len(hourly_vals) > 0 else 20.0
    
    # Compression: bottom half gets a boost, top half gets slight reduction
    for w in workers:
        hr = w.get('hourly', 20)
        if hr < median_hr:
            # Below median → wage increases from competition for cheap labor
            boost = (median_hr - hr) / median_hr * intensity
            w['hourly'] = hr * (1.0 + boost * 0.5)
        elif hr > median_hr * 1.5:
            # Top earners see slight compression from reduced monopsony
            compression = (hr - median_hr * 1.5) / hr * intensity
            w['hourly'] = hr * (1.0 - compression * 0.3)
        w['monthly'] = w['hourly'] * 160
    
    return {'wage_compression': intensity}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 9: Capital ownership / equity distribution
# ═══════════════════════════════════════════════════════════════════════

def apply_capital_ownership(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Business after-tax profit is distributed to workers as capital income.
    
    This replaces the current system where retained earnings go to 'sys'.
    Config keys control how much profit is distributed and how concentrated.
    
    concentration=0: equal distribution to all workers
    concentration=1: proportional to existing wealth (Matthew effect)
    """
    share = float(config.get('capital_ownership_share', 0.0))
    concentration = float(config.get('capital_ownership_concentration', 0.5))
    
    if share <= 0 or not businesses:
        return {}
    
    total_profit = 0.0
    total_distributed = 0.0
    
    for b in businesses:
        capital = b.get('capital', 100000)
        # Monthly profit estimate
        profit = capital * 0.08 / 12
        tax_rate = float(config.get('corp_tax_rate', 0.0))
        after_tax = profit * (1.0 - min(tax_rate, 0.5))
        
        # Distribution pool
        dist_pool = after_tax * share
        total_profit += after_tax
        
        if dist_pool <= 0 or not workers:
            continue
        
        if concentration <= 0.01:
            # Equal distribution
            per_worker = dist_pool / len(workers)
            for w in workers:
                bal[w['id']] = bal.get(w['id'], 0) + per_worker
                total_distributed += per_worker
        else:
            # Concentrated distribution (proportional to existing wealth)
            wealth_vals = [(w['id'], bal.get(w['id'], 0)) for w in workers]
            total_wealth = sum(wv[1] for wv in wealth_vals)
            if total_wealth > 0:
                for wid, wealth in wealth_vals:
                    # Blend between equal and wealth-proportional
                    equal_share = dist_pool / len(workers)
                    prop_share = dist_pool * (wealth / total_wealth) if total_wealth > 0 else equal_share
                    amount = equal_share * (1.0 - concentration) + prop_share * concentration
                    bal[wid] = bal.get(wid, 0) + amount
                    total_distributed += amount
    
    if total_distributed > 0 and step % 60 == 0:
        _log.info("Step %d: capital income distributed: $%.0f (%.0f%% of after-tax profit)",
                  step, total_distributed, total_distributed / max(total_profit, 1) * 100)
    
    return {'capital_income_distributed': total_distributed}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 10: Overlapping generations (simplified OLG)
# ═══════════════════════════════════════════════════════════════════════

def apply_olg(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Simplified overlapping generations: workers retire, new workers enter.
    
    Every olg_retirement_periods steps, the oldest workers (by index) retire
    and new young workers enter with entry wealth. This creates genuine
    intergenerational dynamics.
    
    Note: This is a simplified version that doesn't track exact ages.
    It uses step count to trigger cohort turnover.
    """
    if not config.get('use_olg', False):
        return {}
    
    period = int(config.get('olg_retirement_periods', 120))
    entry_cash = float(config.get('olg_entry_cash', 20000))
    
    if step % period != 0 or not workers:
        return {}
    
    # Retire the lowest-wealth 10% of workers
    turnover = max(1, len(workers) // 10)
    sorted_by_wealth = sorted(workers, key=lambda w: bal.get(w['id'], 0))
    retiring = sorted_by_wealth[:turnover]
    
    # Remove retiring workers' land and cash
    for w in retiring:
        wid = w['id']
        # Transfer remaining wealth to 'sys'
        bal['sys'] = bal.get('sys', 0) + bal.get(wid, 0)
        bal[wid] = 0
        # They're now retired (remove from active list)
        w['_retired'] = True
    
    # Add new young workers
    new_workers = []
    for i in range(turnover):
        nid = f"ny{step}_{i:03d}"
        new_hr = rng.uniform(12, 30)  # Young workers start with lower wages
        new_worker = {
            'id': nid,
            'hourly': new_hr,
            'monthly': new_hr * 160,
            'land': rng.uniform(10000, 50000),
            'risk': rng.uniform(0.01, 0.15),
            'cash': entry_cash,
        }
        bal[nid] = entry_cash
        new_workers.append(new_worker)
    
    # Replace retired workers with new ones (in-place modification)
    retired_count = 0
    for i, w in enumerate(workers):
        if w.get('_retired') and retired_count < len(new_workers):
            idx = workers.index(w)
            workers[idx] = new_workers[retired_count]
            retired_count += 1
    
    # Clean up _retired flags
    workers[:] = [w for w in workers if not w.get('_retired')]
    workers.extend(new_workers[retired_count:])  # Add any remaining new workers
    
    _log.info("Step %d: OLG turnover — %d retired, %d entered",
              step, len(retiring), len(new_workers))
    
    return {'olg_retired': len(retiring), 'olg_entered': len(new_workers)}



# ─── 11. Housing/land market ────────────────────────────────────────

def apply_housing_market(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Housing market with rents, mortgages, and development.
    
    Landowners receive rent from workers proportional to land value.
    Workers can take mortgages against land to finance consumption/investment.
    Land values appreciate from development.
    """
    if not config.get('use_housing_market', False):
        return {}
    
    rent_ratio = float(config.get('housing_rent_ratio', 0.005))
    mortgage_rate = float(config.get('housing_mortgage_rate', 0.06)) / 12
    lv_ratio = float(config.get('housing_mortgage_lv_ratio', 0.8))
    dev_boost = float(config.get('housing_development_boost', 0.02)) / 12
    
    total_rent_paid = 0.0
    total_mortgage_interest = 0.0
    total_dev = 0.0
    
    # Rents: workers pay rent to landowners (landlords = retirees + businesses)
    landlords = retirees + businesses
    if landlords and workers:
        total_land_value = sum(w.get('land', 0) for w in landlords)
        if total_land_value > 0:
            for w in workers:
                rent = w.get('land', 50000) * rent_ratio
                if bal.get(w['id'], 0) >= rent:
                    bal[w['id']] = bal[w['id']] - rent
                    # Distribute rent to landowners proportionally
                    for ll in landlords:
                        ll_share = rent * (ll.get('land', 0) / max(total_land_value, 1))
                        if ll_share > 0.01:
                            bal[ll['id']] = bal.get(ll['id'], 0) + ll_share
                    total_rent_paid += rent
    
    # Mortgages: workers can borrow against land
    if mortgage_rate > 0 and step % 12 == 1:  # Annual
        for w in workers:
            land_val = w.get('land', 50000)
            max_loan = land_val * lv_ratio
            if max_loan > 10000:
                loan = max_loan * 0.1  # Borrow 10% of capacity
                if bal.get('bank', 0) >= loan:
                    bal[w['id']] = bal.get(w['id'], 0) + loan
                    bal['bank'] = bal['bank'] - loan
                    w['_mortgage'] = w.get('_mortgage', 0) + loan
                    w['_mortgage_rate'] = mortgage_rate
    
    # Mortgage interest
    for w in workers:
        principal = w.get('_mortgage', 0)
        if principal > 0:
            interest = principal * mortgage_rate
            if bal.get(w['id'], 0) >= interest:
                bal[w['id']] = bal[w['id']] - interest
                bal['bank'] = bal.get('bank', 0) + interest
                total_mortgage_interest += interest
    
    # Development: land values appreciate
    if dev_boost > 0:
        for w in workers:
            w['land'] = w.get('land', 50000) * (1.0 + dev_boost)
        for r in retirees:
            r['land'] = r.get('land', 100000) * (1.0 + dev_boost)
        total_dev = dev_boost * sum(w.get('land', 0) for w in workers + retirees)
    
    return {'rent_paid': total_rent_paid, 'mortgage_interest': total_mortgage_interest}


# ─── 12. International trade ────────────────────────────────────────

def apply_international_trade(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Simple international trade sector.
    
    System exports based on land/labor ratio comparative advantage.
    Trade balance affects system wealth (surplus = inflow, deficit = outflow).
    """
    if not config.get('use_international_trade', False):
        return {}
    
    openness = float(config.get('trade_openness', 0.2))
    land_advantage = float(config.get('trade_land_advantage', 0.1))
    capital_flow = float(config.get('trade_capital_flow', 0.01))
    
    # Measure domestic output (total wages + profits)
    total_wages = sum(bal.get(w['id'], 0) for w in workers) if workers else 1
    total_output = total_wages * 1.5  # Approximate GDP
    
    # Export capacity based on land intensity
    avg_land = np.mean([w.get('land', 50000) for w in workers]) if workers else 50000
    land_intensity = avg_land / max(total_wages / max(len(workers), 1), 1)
    
    # Terms of trade: land-abundant systems export at premium
    export_revenue = total_output * openness * (1.0 + land_advantage * land_intensity / 100)
    import_cost = total_output * openness
    
    trade_balance = export_revenue - import_cost
    
    # Apply trade balance to system wealth
    if trade_balance > 0:
        bal['sys'] = bal.get('sys', 0) + trade_balance * 0.01  # 1% of surplus
    elif trade_balance < 0:
        bal['sys'] = bal.get('sys', 0) + trade_balance * 0.005  # 0.5% of deficit
    
    # Capital flows follow trade balance
    if capital_flow > 0:
        flow = trade_balance * capital_flow
        if flow > 0:
            bal['sys'] = bal.get('sys', 0) + flow
    
    return {'trade_balance': trade_balance, 'export_revenue': export_revenue}


# ─── 13. Proper OLG with bequests ───────────────────────────────────

def apply_proper_olg(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Overlapping generations with age cohorts and bequests.
    
    Simplified version: redistributes wealth within existing worker pool
    rather than creating new workers. Old cohort "dies" (wealth bequeathed),
    young cohort receives bequests. No new workers added.
    """
    if not config.get('use_proper_olg', False):
        return {}
    
    n_cohorts = int(config.get('proper_olg_cohorts', 3))
    prod = config.get('proper_olg_productivity', [0.7, 1.3, 0.8])
    bequest_rate = float(config.get('proper_olg_bequest_rate', 0.3))
    gen_length = int(config.get('proper_olg_generation_length', 40))
    
    if not workers or step % gen_length != 0:
        return {}
    
    # Assign cohort ages if not already set
    for i, w in enumerate(workers):
        if '_cohort' not in w:
            w['_cohort'] = i % n_cohorts
    
    # Apply productivity by cohort (modifies hourly wages)
    for cohort in range(n_cohorts):
        prod_mult = prod[cohort] if cohort < len(prod) else 1.0
        for w in workers:
            if w.get('_cohort', 0) == cohort:
                w['_prod_mult'] = prod_mult
                base_hr = w.get('_base_hourly', w.get('hourly', 20))
                w['hourly'] = base_hr * prod_mult
                w['monthly'] = w['hourly'] * 160
    
    # At generation boundary: old cohort dies, bequeaths to young
    highest_cohort = n_cohorts - 1
    dying = [w for w in workers if w.get('_cohort', 0) == highest_cohort]
    young = [w for w in workers if w.get('_cohort', 0) == 0]
    
    total_bequest = 0.0
    for w in dying:
        wid = w['id']
        wealth = bal.get(wid, 0)
        bequest = wealth * bequest_rate
        total_bequest += bequest
        bal[wid] = wealth - bequest
        # Redistribute to young cohort (not sys)
        if young:
            per_young = bequest / len(young)
            for yw in young:
                bal[yw['id']] = bal.get(yw['id'], 0) + per_young
    
    # Shift cohorts
    for w in workers:
        current = w.get('_cohort', 0)
        if current < highest_cohort:
            w['_cohort'] = current + 1
        elif current == highest_cohort:
            w['_cohort'] = 0  # Reset to young (simplified)
    
    # Reset productivity for the new cycle
    hourly_vals = [w.get('_base_hourly', w.get('hourly', 20)) for w in workers]
    avg_base = np.mean(hourly_vals) if hourly_vals else 20
    for cohort in range(n_cohorts):
        prod_mult = prod[cohort] if cohort < len(prod) else 1.0
        for w in workers:
            if w.get('_cohort', 0) == cohort:
                w['hourly'] = w.get('_base_hourly', avg_base) * prod_mult
                w['monthly'] = w['hourly'] * 160
    
    return {'bequests': total_bequest, 'n_dying': len(dying)}


# ─── 14. Super-wealthy agents ───────────────────────────────────────

def apply_super_wealthy(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Add persistent wealth concentration at the top of the distribution.

    Three channels for persistent inequality:
    1. Initial boost: top 2% get 5x initial wealth (step 1)
    2. Persistent wage premium: 30% wage boost every step
    3. Capital income: top workers receive business profits every 12 steps

    This creates a self-reinforcing wealth concentration that persists
    even without trade/housing mechanisms.
    """
    if not config.get('use_super_wealthy', False):
        return {}

    frac = float(config.get('super_wealthy_fraction', 0.02))
    mult = float(config.get('super_wealthy_multiplier', 5.0))

    if not workers:
        return {}

    n_super = max(1, int(len(workers) * frac))

    # Step 1: Initial boost
    if step == 1:
        sorted_by_wealth = sorted(workers, key=lambda w: w.get('cash', bal.get(w['id'], 0)))
        top_workers = sorted_by_wealth[-n_super:]
        total_boost = 0.0
        for w in top_workers:
            wid = w['id']
            initial_cash = w.get('cash', 50000)
            boost = initial_cash * mult
            bal[wid] = bal.get(wid, 0) + boost
            total_boost += boost
            w['_super_wealthy'] = True
        _log.info("Super-wealthy initial boost: ${:>,.0f} to {} workers".format(total_boost, n_super))
        return {'super_wealthy_boost': total_boost}

    # Every step: persistent wage premium for super-wealthy workers (30% boost)
    wage_premium_total = 0.0
    for w in workers:
        if w.get('_super_wealthy'):
            base_hr = w.get('_base_hourly', w.get('hourly', 20))
            w['hourly'] = base_hr * 1.3
            w['monthly'] = w['hourly'] * 160
            wage_premium_total += w['monthly'] * 0.3

    # Monthly capital income: super-wealthy receive business profits directly
    # Subject to income tax (same rate as labor income)
    capital_income = 0.0
    if businesses:
        total_profit = sum(b.get('capital', 100000) * 0.08 for b in businesses) / 12
        profit_share = total_profit * 0.50
        # Apply income tax to capital income at FULL rate (no discount)
        tax_type = config.get('tax_type', 'lvt')
        inc_tx_rate = float(config.get('income_tax_rate', 0.0))
        if tax_type == 'income' and inc_tx_rate > 0:
            profit_share *= (1.0 - inc_tx_rate)
        if profit_share > 0 and bal.get('sys', 0) >= profit_share:
            per_super = profit_share / n_super
            for w in workers:
                if w.get('_super_wealthy'):
                    bal[w['id']] = bal.get(w['id'], 0) + per_super
                    bal['sys'] = bal['sys'] - per_super
                    capital_income += per_super

    return {
        'wage_premium': wage_premium_total,
        'capital_income': capital_income,
    }


# ─── 15. Real trade mechanism ───────────────────────────────────────

def apply_real_trade(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Trade mechanism with sectoral wage effects + dynamic switching.

    Workers are randomly assigned to export-oriented, neutral, or import-competing
    sectors. Export workers get wage premium, import workers face wage penalty.
    Workers can switch sectors at a cost (mobility).
    Trade balance directly affects system wealth.
    """
    if not config.get('use_real_trade', False):
        return {}

    openness = float(config.get('real_trade_openness', 0.3))
    skill_prem = float(config.get('real_trade_skill_premium', 0.15))
    import_pen = float(config.get('real_trade_import_penalty', 0.05))

    if not workers or step % 12 != 1:  # Annual
        return {}

    n_w = len(workers)
    if n_w < 4:
        return {}

    # Assign sectors on step 1 (random thirds)
    if step == 1:
        for i, w in enumerate(workers):
            sector_idx = (i * 7 + hash(w['id']) % 100) % 3  # Deterministic
            w['_trade_sector'] = ['export', 'neutral', 'import'][sector_idx]

    # Sectoral wage effects
    total_export_prem = 0.0
    total_import_pen = 0.0
    switches = 0

    for w in workers:
        sector = w.get('_trade_sector', 'neutral')
        hr = w.get('hourly', 20)

        if sector == 'export':
            premium = hr * openness * skill_prem
            w['hourly'] = hr + premium
            total_export_prem += premium
        elif sector == 'import':
            penalty = hr * openness * import_pen
            w['hourly'] = max(hr - penalty, 8.0)
            total_import_pen += penalty
        # Neutral sector: no direct trade effect

        w['monthly'] = w['hourly'] * 160

    # Dynamic switching: some workers move sectors
    # Workers in import sectors try to move to export/neutral (cost = 1% of wealth)
    for w in workers:
        if w.get('_trade_sector') == 'import' and rng.random() < 0.1:
            # Switch to neutral or export
            new_sector = rng.choice(['neutral', 'export'])
            w['_trade_sector'] = new_sector
            switches += 1

    # Trade balance effect on system wealth
    annual_export = total_export_prem * 12
    trade_surplus = annual_export * 0.01
    if trade_surplus > 0:
        bal['sys'] = bal.get('sys', 0) + trade_surplus

    return {
        'export_premium': total_export_prem,
        'import_penalty': total_import_pen,
        'sector_switches': switches,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 17: Power-law wealth concentration (replaces super_wealthy)
# ═══════════════════════════════════════════════════════════════════════

def apply_power_law_wealth(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Self-reinforcing wealth concentration via return differentials.

    Real-world top 1% earn ~10% annual returns vs ~5% for median (Fagereng et al. 2020)
    due to portfolio diversification, tax avoidance, access to private equity.

    This mechanism models that directly: top `wealth_tail_fraction` of workers get
    a return premium that scales with their log-wealth, creating a power-law tail.

    Formula: return_premium = power_law_exponent * ln(1 + wealth / median_wealth)
    Applied annually as extra wealth growth on top of normal wage income.

    Config keys:
        use_power_law_wealth (bool, default False)
        power_law_exponent (float, 0-0.5, default 0.3) — return premium intensity
        wealth_tail_fraction (float, 0-1, default 0.01) — top fraction affected
    """
    if not config.get('use_power_law_wealth', False):
        return {}

    exponent = float(config.get('power_law_exponent', 0.3))
    tail_frac = float(config.get('wealth_tail_fraction', 0.01))

    if exponent <= 0 or tail_frac <= 0 or not workers:
        return {}

    # Mark tail workers on step 1
    if step == 1:
        sorted_by_wealth = sorted(workers, key=lambda w: bal.get(w['id'], 0))
        n_tail = max(1, int(len(workers) * tail_frac))
        top_workers = sorted_by_wealth[-n_tail:]
        for w in top_workers:
            w['_power_law_tail'] = True
        _log.info("Power-law tail: %d workers (top %.1f%%)", n_tail, tail_frac * 100)

    # Apply return premium annually
    if step % 12 != 1:
        return {}

    # Compute median wealth among ALL workers (not just tail)
    wealth_vals = [bal.get(w['id'], 0) for w in workers]
    median_w = float(np.median(wealth_vals)) if wealth_vals else 50000
    median_w = max(1000, median_w)

    total_premium = 0.0
    n_tail = 0

    for w in workers:
        if not w.get('_power_law_tail'):
            continue
        wid = w['id']
        wealth = bal.get(wid, 0)
        if wealth <= 0:
            continue

        # Return premium scales with log-wealth above median
        log_excess = np.log(max(1.0, wealth / median_w))
        premium_rate = min(0.05, exponent * log_excess)  # Cap at 5pp return gap (Fagereng 2020)
        premium = wealth * premium_rate  # Annual return premium (triggered yearly)

        if premium > 0:
            bal[wid] = bal.get(wid, 0) + premium
            total_premium += premium
            n_tail += 1

    if step % 60 == 0 and n_tail > 0:
        top_share = sum(bal.get(w['id'], 0) for w in workers if w.get('_power_law_tail'))
        total_w = sum(bal.get(w['id'], 0) for w in workers) or 1
        pct = top_share / total_w * 100
        _log.info("Power-law: top %.1f%% wealth share = %.1f%%, annual premium flow=%.0f",
                  tail_frac * 100, pct, total_premium * 12)

    return {
        'power_law_premium': total_premium,
        'power_law_workers': n_tail,
        'power_law_top_share': round(
            sum(bal.get(w['id'], 0) for w in workers if w.get('_power_law_tail', False)) /
            max(sum(bal.get(w['id'], 0) for w in workers), 1) * 100, 2
        ),
    }


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 18: Immigrant labor wedge
# ═══════════════════════════════════════════════════════════════════════

def apply_immigrant_wedge(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Low-wage immigrant workers suppress wages for bottom segment.

    Independent of informal_share. Immigrants work in formal sectors at depressed
    wages due to visa restrictions, limited bargaining power, and employer monopsony
    (Borjas 2003, Card 2005).

    Bottom `immigrant_share` workers get wage = wage * (1 - immigrant_wage_penalty).
    Immigrant workers do NOT pay income tax (modeling undocumented / guest worker gap).

    Config keys:
        use_immigrant_labor (bool, default False)
        immigrant_share (float, 0-1, default 0.0) — fraction of bottom workers affected
        immigrant_wage_penalty (float, 0-1, default 0.0) — wage suppression fraction
    """
    if not config.get('use_immigrant_labor', False):
        return {}

    share = float(config.get('immigrant_share', 0.0))
    penalty = float(config.get('immigrant_wage_penalty', 0.0))

    if share <= 0 or penalty <= 0 or not workers:
        return {}

    # Mark immigrant workers on step 1 (bottom share by hourly wage)
    if step == 1:
        sorted_by_wage = sorted(workers, key=lambda w: w.get('hourly', 20))
        n_imm = max(1, int(len(workers) * min(share, 0.95)))
        immigrant_workers = sorted_by_wage[:n_imm]
        for w in immigrant_workers:
            w['_immigrant'] = True
        _log.info("Immigrant wedge: %d workers (bottom %.1f%%), penalty=%.0f%%",
                  n_imm, share * 100, penalty * 100)

    if step != 1:
        # Reassign immigrants if wage order changes (simplified: keep same set)
        pass

    # Apply wage suppression every step
    # Also apply income tax exemption for immigrants
    # Reassign immigrants every 12 steps to track changing wage order
    if step % 12 == 1:
        sorted_by_wage = sorted(workers, key=lambda w: w.get('hourly', 20))
        n_imm_reassign = max(1, int(len(workers) * min(share, 0.95)))
        # Clear existing tags
        for w in workers:
            w.pop('_immigrant', None)
        for w in sorted_by_wage[:n_imm_reassign]:
            w['_immigrant'] = True
        if step % 60 == 0:
            _log.info("Immigrant wedge reassign: %d workers (%.1f%%)",
                      n_imm_reassign, share * 100)

    # Apply wage suppression every step (uses current tag set)
    total_suppression = 0.0
    n_imm = 0
    for w in workers:
        if not w.get('_immigrant'):
            continue
        n_imm += 1
        hr = w.get('hourly', 20)
        suppressed = hr * penalty
        w['hourly'] = max(hr - suppressed, 7.25)
        w['monthly'] = w['hourly'] * 160
        total_suppression += suppressed

    if step % 60 == 0 and n_imm > 0:
        _log.info("Immigrant wedge: %d workers, avg suppression=$%.0f/mo",
                  n_imm, total_suppression / max(n_imm, 1))

    return {
        'immigrant_workers': n_imm,
        'total_wage_suppression': total_suppression,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 19: Concentrated inheritance
# ═══════════════════════════════════════════════════════════════════════

def apply_inheritance_conc(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Intergenerational wealth transfer concentrating to the already-wealthy.

    Real-world bequests flow disproportionately to wealthy heirs (Wolff & Gractz).
    Top 10% receive ~60% of all inheritance; bottom 50% receive ~10%.

    Applied annually. Takes `inheritance_flow_fraction` of total worker wealth
    and redistributes it with concentration parameter.

    Config keys:
        inheritance_flow_fraction (float, 0-1) — fraction of total wealth redistributed per year
        inheritance_concentration (float, 0-1) — 0=equal, 0.5=proportional, 1=highly concentrated

    Formula: receipt weight = wealth^(1 + 2*conc)
    When conc=0: weight ∝ wealth (neutral — everyone gets back what they contribute)
    When conc=0.5: weight ∝ wealth^2 (concentrated — top gets more)
    When conc=1.0: weight ∝ wealth^3 (highly concentrated — replicating empirical 60% to top 10%)
    """
    flow = float(config.get('inheritance_flow_fraction', 0.0))
    conc = float(config.get('inheritance_concentration', 0.5))

    if flow <= 0 or not workers:
        return {}

    # Apply annually
    if step % 12 != 1:
        return {}

    # Collect all worker wealth
    wealth_map = {w['id']: bal.get(w['id'], 0) for w in workers}
    total_wealth = sum(wealth_map.values())

    if total_wealth <= 0:
        return {}

    # Total inheritance pool = flow_fraction of total wealth
    inheritance_pool = total_wealth * flow

    if inheritance_pool <= 0:
        return {}

    # Compute distribution shares
    if conc <= 0.001:
        # Proportional: contribution = receipt for each person (neutral)
        # This is the identity case — no net transfer
        pass  # No net effect
    else:
        # Concentrated: contribution proportional to wealth, receipt proportional to wealth^exponent
        # exponent = 1.0 + 2.0 * conc
        # conc=0.5 → exponent=2.0 (quadratic weighting)
        # conc=1.0 → exponent=3.0 (cubic weighting)
        exponent = 1.0 + 2.0 * conc
        weights = {}
        for w in workers:
            wid = w['id']
            wgt = (max(wealth_map[wid], 0) ** exponent) if wealth_map[wid] > 0 else 0
            weights[wid] = wgt

        total_weight = sum(weights.values()) or 1

        contributions = {}
        receipts = {}

        for w in workers:
            wid = w['id']
            # Contribution proportional to wealth
            contrib = inheritance_pool * (wealth_map[wid] / max(total_wealth, 1))
            contributions[wid] = contrib
            # Receipt proportional to wealth^conc
            receipt = inheritance_pool * (weights[wid] / total_weight)
            receipts[wid] = receipt

        # Apply net transfers
        net_transfers = 0.0
        for w in workers:
            wid = w['id']
            net = receipts[wid] - contributions[wid]
            if abs(net) > 0.01:
                if net > 0:
                    bal[wid] = bal.get(wid, 0) + net
                    net_transfers += net
                else:
                    take = min(abs(net), bal.get(wid, 0))
                    bal[wid] = bal.get(wid, 0) - take
                    net_transfers += take

        if step % 60 == 0:
            # Compute what fraction of inheritance goes to top 10%
            w_sorted = sorted(workers, key=lambda w: bal.get(w['id'], 0))
            n_top10 = max(1, len(workers) // 10)
            top10_receipt = sum(receipts.get(w['id'], 0) for w in w_sorted[-n_top10:])
            top10_pct = top10_receipt / max(inheritance_pool, 1) * 100
            _log.info("Inheritance: pool=%.0f, flow=%.4f, top10%% receives %.0f%%",
                      inheritance_pool, flow, top10_pct)

    return {
        'inheritance_pool': inheritance_pool,
        'inheritance_flow': flow,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 20: Structural wealth gap (racial/group-level disparity)
# ═══════════════════════════════════════════════════════════════════════

def apply_structural_gap(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Persistent group-level wealth disparity from initial endowments.

    Models structural inequality (racial wealth gap, caste, colonial legacy)
    as persistent group-level wealth multipliers that reapply each generation.

    At step 1, workers are assigned to groups with population fractions and
    wealth multipliers. Groups with lower multipliers have:
    - Lower initial cash
    - Higher mortality risk / lower intergenerational mobility
    - Penalized wage growth (discrimination channel)

    Config keys:
        use_structural_gap (bool)
        structural_gap_groups (list of floats, e.g. [0.8, 0.2]) — population fractions
        structural_gap_multipliers (list of floats, e.g. [1.0, 0.1]) — wealth multipliers
        structural_gap_recurrence (float, 0-1) — fraction of gap that reapplies each generation

    Example: [0.8, 0.2] with [1.0, 0.1] = majority group at par, minority at 10% wealth
    """
    if not config.get('use_structural_gap', False):
        return {}

    groups = config.get('structural_gap_groups', [])
    multipliers = config.get('structural_gap_multipliers', [])
    recurrence = float(config.get('structural_gap_recurrence', 0.1))

    if not groups or not multipliers or len(groups) != len(multipliers):
        return {}

    # Verify groups sum to ~1.0
    if abs(sum(groups) - 1.0) > 0.01:
        _log.warning("structural_gap_groups sum=%.2f, expected 1.0", sum(groups))
        return {}

    n_groups = len(groups)

    # Assign groups on step 1
    if step == 1:
        rng.shuffle(workers)
        assigned = 0
        for gi in range(n_groups):
            n_in_group = int(len(workers) * groups[gi])
            if gi == n_groups - 1:
                n_in_group = len(workers) - assigned
            for w in workers[assigned:assigned + n_in_group]:
                w['_gap_group'] = gi
                w['_gap_mult'] = multipliers[gi]
                # Apply initial wealth penalty
                wid = w['id']
                current_cash = bal.get(wid, w.get('cash', 50000))
                bal[wid] = current_cash * multipliers[gi]
            assigned += n_in_group

        _log.info("Structural gap: %d groups, multipliers=%s", n_groups, multipliers)
        return {'gap_initialized': True, 'n_groups': n_groups}

    # Recurrence: annually, apply a fraction of the gap to reinforce persistence
    # This models housing discrimination, hiring bias, network effects
    if recurrence > 0 and step % 12 == 1:
        total_gap_effect = 0.0
        for w in workers:
            gi = w.get('_gap_group', 0)
            mult = w.get('_gap_mult', 1.0)
            if mult >= 1.0:
                continue  # No penalty for majority group
            # Persistent gap: reduce wealth growth for disadvantaged groups
            wid = w['id']
            wealth = bal.get(wid, 0)
            gap_penalty = wealth * recurrence * (1.0 - mult)
            if gap_penalty > 0 and bal.get(wid, 0) >= gap_penalty:
                bal[wid] = bal.get(wid, 0) - gap_penalty
                bal['sys'] = bal.get('sys', 0) + gap_penalty
                total_gap_effect += gap_penalty

            # Also suppress wage growth for disadvantaged groups
            if mult < 1.0:
                hr = w.get('hourly', 20)
                wage_penalty = hr * recurrence * (1.0 - mult) * 0.5
                w['hourly'] = max(hr - wage_penalty, 7.25)
                w['monthly'] = w['hourly'] * 160

        if step % 60 == 0:
            _log.info("Structural gap recurrence: %.0f wealth transferred to sys", total_gap_effect)

        return {'gap_recurrence_effect': total_gap_effect}

    return {}


# ═══════════════════════════════════════════════════════════════════════
#  Mechanism 21: Forced reinvestment of idle capital
# ═══════════════════════════════════════════════════════════════════════

def apply_forced_reinvestment(config, rng, workers, retirees, businesses, bal, step, step_metrics):
    """Forced reinvestment of idle business cash into productive capital.

    LS-aligned: capital must be deployed or it faces pressure, mirroring the LVT
    principle that land must be developed or sold. Businesses that hoard cash
    beyond a threshold have the excess converted to productive capital investment.

    This replaces the assumption that government spending boosts productivity.
    Instead, the mechanism forces capital circulation: idle cash → productive
    investment → higher TFP → higher output. No government required.

    Config keys:
        forced_reinvestment (bool, default False)
        reinvestment_rate (float, 0-1) — fraction of excess idle cash reinvested each step
        idle_cash_threshold (float, 0-1) — max idle cash as fraction of productive capital
        reinvestment_boost (float, 0-1) — productivity boost on reinvested capital

    Example: threshold=0.3, rate=0.3 → a business with $1M capital and $500k cash
    has excess = $500k - $300k = $200k. Each step, $60k (30%) is converted to capital.
    The new capital gets a 5% productivity boost.
    """
    if not config.get('forced_reinvestment', False):
        return {}

    rate = max(0.0, min(1.0, float(config.get('reinvestment_rate', 0.3))))
    threshold = max(0.0, min(1.0, float(config.get('idle_cash_threshold', 0.3))))
    boost = max(0.0, min(0.2, float(config.get('reinvestment_boost', 0.05))))

    if rate <= 0 or not businesses:
        return {}

    total_reinvested = 0.0
    total_new_capital = 0.0
    businesses_affected = 0

    for b in businesses:
        bid = b['id']
        capital = b.get('capital', 100000)
        cash = bal.get(bid, 0)

        if cash <= 0 or capital <= 0:
            continue

        # Maximum allowed idle cash = threshold * productive capital
        max_idle = capital * threshold
        excess = cash - max_idle

        if excess <= 0:
            continue

        # Reinvest a fraction of the excess
        reinvestment = excess * rate
        if reinvestment <= 0 or reinvestment > cash:
            continue

        # Convert idle cash to productive capital
        # New capital gets a productivity boost (models better allocation)
        effective_investment = reinvestment * (1.0 + boost)
        b['capital'] = capital + effective_investment
        bal[bid] = cash - reinvestment

        total_reinvested += reinvestment
        total_new_capital += effective_investment
        businesses_affected += 1

    if total_reinvested > 0 and step % 60 == 0:
        _log.info("Forced reinvestment: $%.0f reinvested across %d businesses, "
                  "effective capital added=$%.0f (boost=%.0f%%)",
                  total_reinvested, businesses_affected,
                  total_new_capital, boost * 100)

    return {
        'reinvested': total_reinvested,
        'new_capital': total_new_capital,
        'businesses_affected': businesses_affected,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Registry: ordered list of all mechanisms
#  NOTE: Must be AFTER all function definitions (Python resolves top-to-bottom)
# ═══════════════════════════════════════════════════════════════════════

MECHANISM_ORDER = [
    ('public_goods', apply_public_goods),
    ('inflation', apply_inflation),
    ('bankruptcy', apply_bankruptcy),
    ('forced_savings_ext', apply_forced_savings_externalities),
    ('endogenous_tfp', apply_endogenous_tfp),
    ('gov_service_productivity', apply_gov_service_productivity),
    ('occupational_mobility', apply_occupational_mobility),
    ('wage_competition', apply_wage_competition),
    ('capital_ownership', apply_capital_ownership),
    ('olg', apply_olg),
    ('housing_market', apply_housing_market),
    ('international_trade', apply_international_trade),
    ('proper_olg', apply_proper_olg),
    ('super_wealthy', apply_super_wealthy),
    ('real_trade', apply_real_trade),
    ('power_law_wealth', apply_power_law_wealth),
    ('immigrant_wedge', apply_immigrant_wedge),
    ('inheritance_conc', apply_inheritance_conc),
    ('structural_gap', apply_structural_gap),
    ('forced_reinvestment', apply_forced_reinvestment),
]


def apply_missing_mechanisms(config, rng, workers, retirees, businesses,
                              bal, land_values, step, step_metrics):
    """Apply all enabled missing mechanisms in order. Returns combined metrics dict.
    
    Input validation: checks config is dict, rng has RandomState interface,
    workers/retirees/businesses are lists, bal is dict. Missing keys default to 0.
    Logs at WARNING level for invalid inputs, INFO for mechanism activation.
    """
    # Input validation
    if not isinstance(config, dict):
        _log.warning("apply_missing_mechanisms: config is not a dict (got %s), skipping", type(config).__name__)
        return {}
    if not hasattr(rng, 'random'):
        _log.warning("apply_missing_mechanisms: rng has no .random(), skipping")
        return {}
    if workers is None:
        workers = []
    if retirees is None:
        retirees = []
    if businesses is None:
        businesses = []
    if bal is None:
        bal = {}
    if not isinstance(step_metrics, dict):
        step_metrics = {}
    
    # Initialize default step_metrics values
    step_metrics.setdefault('total_tax', 0)
    
    combined = {}
    for name, func in MECHANISM_ORDER:
        # Check if this mechanism has any config keys set
        mech_prefix = name.split('_')[0]
        has_config = any(k.startswith(mech_prefix) for k in config if isinstance(k, str))
        # Or check if the mechanism's primary boolean toggle is True
        primary_key = {
            'public_goods': 'use_public_goods',
            'inflation': 'inflation_rate',
            'bankruptcy': 'bankruptcy_threshold',
            'forced_savings_ext': 'cpf_liquidity_trap',
            'endogenous_tfp': 'endogenous_tfp',
            'gov_service_productivity': 'gov_service_productivity',
            'occupational_mobility': 'mobility_cost',
            'wage_competition': 'wage_competition',
            'capital_ownership': 'capital_ownership_share',
            'olg': 'use_olg',
            'housing_market': 'use_housing_market',
            'international_trade': 'use_international_trade',
            'proper_olg': 'use_proper_olg',
            'super_wealthy': 'use_super_wealthy',
            'real_trade': 'use_real_trade',
            'power_law_wealth': 'use_power_law_wealth',
            'immigrant_wedge': 'use_immigrant_labor',
            'inheritance_conc': 'inheritance_flow_fraction',
            'structural_gap': 'use_structural_gap',
            'forced_reinvestment': 'forced_reinvestment',
        }.get(name, '')
        
        if primary_key:
            val = config.get(primary_key, 0)
            if isinstance(val, bool):
                if not val:
                    continue
            elif isinstance(val, (int, float)):
                if val == 0:
                    continue
        
        try:
            result = func(config, rng, workers, retirees, businesses,
                         bal, step, step_metrics)
            if result:
                combined[name] = result
                if step % 60 == 0:  # Log every 5 years
                    _log.info("Mech '%s' at step %d: %s", name, step, 
                             {k: round(v, 4) if isinstance(v, float) else v for k, v in result.items()})
        except Exception as e:
            _log.error("Mechanism '%s' failed at step %d: %s", name, step, e, exc_info=True)
    return combined


if __name__ == '__main__':
    # Quick self-test
    logging.basicConfig(level=logging.INFO)
    print("Missing Mechanisms module loaded — 10 mechanisms registered.")
    print(f"Config keys: {len(MISSING_MECH_DEFAULTS)}")
    print(f"Mechanisms: {[m[0] for m in MECHANISM_ORDER]}")
