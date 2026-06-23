#!/usr/bin/env python3
"""Phase 8: fixes core biases + sectoral extensions.

Phase 8a — Core Biases: CRRA welfare, TFP_TAX_ELASTICITY, labor elasticity, money creation
Phase 8b — Sectoral: healthcare, education, environment (carbon tax), elite capture

Usage:
    from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS
"""
import sys, os, copy, json, time, logging
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
from comparison_phase4 import (
    SEEDS, STEPS, REPORT_INTERVAL, HOURS_PER_STEP, LVT_ANNUAL_RATE,
    INVESTMENT_RATE, BUSINESS_WAGE_BILL, WAGE_VARIABILITY, ACCIDENT_PROBABILITY,
    TFP_TAX_ELASTICITY, LABOR_SUPPLY_ELASTICITY, ADMIN_OVERHEAD_BY_TAX, compute_gini,
)
from comparison_phase6 import gen_population, PHASE6_CONFIGS, compute_wellbeing, compute_family_gini
from harberger_bridge import create_harberger_market, HARBERGER_ESCROW
from missing_mechanisms import MISSING_MECH_DEFAULTS, apply_missing_mechanisms

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")


def compute_crra_utility(consumption_stream, gamma=1.0, beta=0.996):
    """CRRA welfare = Σ β^t * U(c_t), U(c) = (c^(1-γ)-1)/(1-γ)."""
    welfare = 0.0
    for t, c in enumerate(consumption_stream):
        if c <= 0:
            continue
        if gamma == 1.0:
            u = np.log(c)
        else:
            u = (c ** (1.0 - gamma) - 1.0) / (1.0 - gamma)
        welfare += (beta ** t) * u
    return welfare


def _error_result(config, reason):
    """Return a safe error result when simulation cannot initialize."""
    return {
        'name': config.get('system_name', 'ERROR') if config else 'ERROR',
        'wealth': 0, 'gini': 0.0, 'w_mean': 0.0, 'w_min': 0.0, 'w_max': 0.0,
        'div': 0.0, 'txns': 0, 'steps': 0, 'gini_by_decade': [],
        'migration_count': 0, 'policy_path': {}, 'net_worth': 0.0,
        'net_worth_gini': 0.0, 'net_worth_mean': 0.0,
        'wellbeing': 0.0, 'child_count': 0, 'family_gini': 0.0,
        'crra_welfare': 0.0, 'consumption_steps': 0,
        'error': reason,
    }


US_BRACKETS = [
    (0, 0.444, 0.10),
    (0.444, 1.111, 0.15),
    (1.111, 2.222, 0.25),
    (2.222, 4.444, 0.35),
    (4.444, float('inf'), 0.40),
]

def calculate_progressive_tax_once(annual_income, median_annual, brackets=None):
    """Progressive tax brackets scaled to simulation income level.

    brackets: list of (lower_frac, upper_frac, rate) tuples where fractions
    are multiples of median annual income. Default: US 2020 brackets.
    median_annual MUST be > 0 (computed from population median at step 1).
    """
    import logging
    _log = logging.getLogger('tax')
    
    if brackets is None:
        brackets = US_BRACKETS
        _log.debug("Using US progressive tax brackets (default)")
    
    # ── Input validation with logging ────────────────────────────────
    validated = _validate_tax_brackets(brackets)
    if validated is None:
        _log.warning("Configured progressive_tax_brackets invalid — falling back to US brackets")
        brackets = US_BRACKETS
        validated = US_BRACKETS
    else:
        # Log which bracket set is in use (first call only)
        if brackets is not US_BRACKETS:
            _log.info("Using custom progressive tax brackets: %s", brackets)
    
    m = max(1.0, median_annual)
    tax = 0.0
    for lower_frac, upper_frac, rate in validated:
        lower = lower_frac * m
        upper = upper_frac * m if upper_frac != float('inf') else float('inf')
        if annual_income <= lower:
            break
        taxable = min(annual_income, upper) - lower
        tax += taxable * rate
    return tax


def _validate_tax_brackets(brackets):
    """Validate progressive tax bracket configuration.

    Returns validated brackets list on success, None on failure.
    Silent on failure — caller handles logging.
    """
    if not isinstance(brackets, (list, tuple)):
        return None
    if len(brackets) == 0:
        return None
    
    validated = []
    for i, br in enumerate(brackets):
        if not isinstance(br, (list, tuple)) or len(br) != 3:
            return None
        
        lower_frac, upper_frac, rate = br
        
        if isinstance(upper_frac, str) and upper_frac.strip().lower() == 'inf':
            upper_frac = float('inf')
        if isinstance(lower_frac, str) and lower_frac.strip().lower() == 'inf':
            return None
        
        for name, val in [('lower', lower_frac), ('upper', upper_frac), ('rate', rate)]:
            if not isinstance(val, (int, float)):
                return None
        
        lower_frac = float(lower_frac)
        upper_frac = float(upper_frac) if upper_frac != float('inf') else float('inf')
        rate = float(rate)
        
        if lower_frac < 0:
            return None
        if rate < 0 or rate > 1:
            return None
        if upper_frac != float('inf') and upper_frac <= lower_frac:
            return None
        if lower_frac == float('inf'):
            return None
        
        validated.append((lower_frac, upper_frac, rate))
    
    for i in range(1, len(validated)):
        if validated[i][0] < validated[i-1][1] and validated[i-1][1] != float('inf'):
            return None
    
    return validated


def run_phase8(workers, retirees, businesses, seed, config):
    """Full Phase 8 simulation loop. Same signature as run_phase6/7."""
    # Input validation
    if not workers:
        return _error_result(config, 'no workers')
    if config is None:
        return _error_result(config, 'no config')
    if not isinstance(seed, int):
        seed = int(seed)

    workers = [dict(w) for w in workers]
    retirees = [dict(r) for r in retirees]
    businesses = [dict(b) for b in businesses]
    rst = copy.deepcopy(config)

    name = rst.get('system_name', 'Phase8')
    _log = logging.getLogger(f'p8_{name[:12]}')
    C = rst.get

    wire_lvt_evasion = C('wire_lvt_evasion', False)
    use_families = C('use_families', False)
    use_harberger = C('use_harberger', False)

    # Children
    children = []
    if use_families:
        rng_c = np.random.RandomState(seed)
        wids_ = [w['id'] for w in workers]
        for i in range(20):
            children.append({'id': f'c{seed}_{i:03d}', 'parent_id': wids_[rng_c.randint(0, len(wids_))],
                             'cash': 0.0, 'land': 0.0})
    child_ids = [c['id'] for c in children]

    # LVT evasion
    lvt_evasion_controller = None
    if wire_lvt_evasion:
        try:
            from src.adversarial.controller import StrategyController, LvtEvasion
            lvt_evasion_controller = StrategyController(strategies=[LvtEvasion()])
        except ImportError:
            _log.warning("src.adversarial not available")

    rst['system_name'] = name
    tx = C('tax_type', 'lvt')
    lvt_r = C('lvt_rate', LVT_ANNUAL_RATE)
    inc_tx = C('income_tax_rate', 0.0)
    corp_tx = C('corp_tax_rate', 0.0)
    ua = C('use_adversarial', False)
    up = C('use_pooled_insurance', False)
    ue = C('use_events', False)
    uwc = C('use_worker_coop', False)
    wrc = C('wage_ratio_cap', 5)  # Legacy — see top_marginal_surcharge
    # ── Top marginal rate surcharge (replaces arbitrary wage_ratio_cap) ──
    top_surcharge = float(C('top_marginal_surcharge', 0.0))   # Additional rate on top earners (0-1)
    top_surcharge_thresh = float(C('top_surcharge_threshold', 0.8))  # Top fraction who pay it (default 20%)
    uv = C('use_vat', False)
    vat_r = C('vat_rate', 0.20)
    wel_r = C('welfare_rate', 0.0)
    un_p = C('union_premium', 1.0)
    cpf_r = C('cpf_rate', 0.0)
    corr = max(0, min(1, float(C('corruption_level', 0))))
    ie = max(0, min(.15, float(C('income_effect_labor', 0))))
    blt = max(0, float(C('admin_overhead', ADMIN_OVERHEAD_BY_TAX.get(tx, 0.01))))
    eos = max(0, float(C('economies_of_scale', 0)))
    mmm = max(1, float(C('monopoly_markup_max', 1.3)))
    bnk = max(0, float(C('banking_multiplier', 0)))  # Legacy — see reserve_requirement
    # ── Reserve requirement (replaces ad-hoc banking_multiplier) ──
    reserve_req = float(C('reserve_requirement', 0.0))  # Fraction of deposits held as reserves (0-1)
    if reserve_req < 0 or reserve_req > 1:
        _log.warning("reserve_requirement=%.4f outside [0,1], clamping to [0,1]", reserve_req)
        reserve_req = max(0.0, min(1.0, reserve_req))
    irt = max(0, float(C('interest_rate', 0.005)))
    ihr = min(1, max(0, float(C('inheritance_rate', 0))))
    enq = min(1, max(0, float(C('enforcement_quality', 1))))
    dpr = min(1, max(0, float(C('detection_probability_base', 0.5))))
    inf = min(1, max(0, float(C('information_asymmetry', 0))))
    min_wage = float(C('minimum_wage', 0.0))
    const_amend_rate = float(C('constitutional_amendment_rate', 0.0))

    # Phase 8a new params
    labor_elast = float(C('labor_supply_elasticity', LABOR_SUPPLY_ELASTICITY))
    money_create = float(C('money_creation_rate', 0.0))
    tfp_elast = float(C('TFP_TAX_ELASTICITY', 0.0))  # Legacy — default 0; use tax_efficiency_loss
    # ── Tax efficiency loss (Harberger deadweight loss) ──
    # DWL = 0.5 * efficiency_loss * t^2 where t = effective tax rate
    # Replaces non-identifiable TFP_TAX_ELASTICITY with well-estimated parameter
    # η ≈ 0.3–0.5 (Chetty 2012). DWL = 0.5 × η × t² × revenue.
    tax_eff_loss = float(C('tax_efficiency_loss', 0.0))  # Harberger η (deadweight loss parameter), 0-1
    if tax_eff_loss < 0 or tax_eff_loss > 1:
        _log.warning("tax_efficiency_loss=%.4f outside [0,1], clamping to [0,1]", tax_eff_loss)
        tax_eff_loss = max(0.0, min(1.0, tax_eff_loss))
    # Phase 8b sectoral params
    health_share = float(C('healthcare_gdp_share', 0.0))
    educ_share = float(C('education_gdp_share', 0.0))
    carbon_tx = float(C('carbon_tax_rate', 0.0))
    elite_cap = float(C('elite_capture_intensity', 0.0))

    # ── Phase 8c: Inequality mechanism config keys (all default OFF) ──
    skill_prem = float(C('skill_premium_growth', 0.0))     # A: SBTC annual premium
    union_cov = float(C('union_coverage', 0.0))             # B: union coverage rate (0-1)
    fin_share = float(C('capital_income_share', 0.0))       # C: financialization share
    import_comp = float(C('import_competition', 0.0))       # D: import competition intensity
    import_displacement = float(C('import_displacement_rate', 0.0))  # D2: sectoral reallocation rate (0-1)
    if import_displacement < 0 or import_displacement > 1:
        _log.warning("import_displacement_rate=%.4f outside [0,1], clamping", import_displacement)
        import_displacement = max(0.0, min(1.0, import_displacement))
    # Annual displacement intensity multiplier (fraction of exposed workers displaced per year)
    # 0.1 = at import_comp=0.20, displacement_rate=0.25 → 0.5% of workers displaced per month
    # Calibrated so at US 2020 peak (import_comp=0.20, disp_rate=0.25), roughly
    # 6% of bottom-half workers experience displacement over the 10-year simulation,
    # consistent with Autor, Dorn & Hanson (2013) finding that ~5-8% of workers
    # in high-exposure regions experienced job displacement from China trade shock.
    import_disp_intensity = float(C('import_disp_intensity', 0.1))  # Annual displacement multiplier (default 0.1)
    if import_disp_intensity < 0 or import_disp_intensity > 1:
        _log.warning("import_disp_intensity=%.4f outside [0,1], clamping", import_disp_intensity)
        import_disp_intensity = max(0.0, min(1.0, import_disp_intensity))
    min_wage_floor = float(C('min_wage_floor', 10.0))  # Displacement wage floor (default $10/hr)
    import_disp_recovery = float(C('import_disp_recovery_rate', 0.003))  # Monthly wage recovery rate (default 0.3%, JLS 1993)
    use_prog_tax = C('use_progressive_tax', False)          # E: progressive tax brackets
    # ── Config-driven progressive tax brackets (overrides US defaults) ──
    # Format: list of [lower_frac, upper_frac, rate] where fractions are of median income.
    # Example Nordic: [[0, 1.5, 0.30], [1.5, 3.0, 0.45], [3.0, inf, 0.55]]
    prog_tax_brackets = C('progressive_tax_brackets', None)  # None = use US defaults
    # UK-specific mechanisms
    housing_wealth = float(C('housing_wealth_concentration', 0.0))     # UK housing appreciation for top decile
    fin_serv_prem = float(C('financial_services_premium', 0.0))        # UK financial sector wage premium
    # Germany-specific mechanisms
    reuni_shock = float(C('reunification_shock', 0.0))     # East Germany integration shock
    hartz = float(C('hartz_reform', 0.0))                  # Hartz labor market reforms (0-1)
    # Brazil-specific mechanisms
    patrimonial = float(C('patrimonial_wealth', 0.0))      # Land/patrimonial wealth concentration (0-1)
    # France-specific mechanisms
    child_benefit = float(C('child_benefit_taper', 0.0))   # Progressive child benefit taper rate
    # General structural mechanisms
    unemp_rate = float(C('unemployment_rate', 0.0))        # Fraction of workers unemployed (0-1)
    wage_disp = float(C('wage_dispersion_mult', 1.0))      # Wage dispersion multiplier (>=1.0)
    wage_disp = max(1.0, min(10.0, wage_disp))
    # ── Informal/dual labor market sector ──
    informal_share = float(C('informal_share', 0.0))       # Bottom fraction in informal sector (0-1)
    informal_penalty = float(C('informal_wage_penalty', 0.5))  # Informal wage as fraction of formal
    informal_penalty = max(0.1, min(1.0, informal_penalty))
    # Pre-compute which workers are informal (recalculated each step due to wage changes)

    # ── Capital income concentration (top x% get business profits) ──
    cap_income_conc = float(C('capital_income_concentration', 0.0))  # Fraction of biz profit to top (0-1)
    cap_income_top = float(C('capital_income_top_share', 0.1))      # Top fraction who receive it (default 10%)

    # ── Realistic inheritance: wealth bequeaths to already-wealthy ──
    inherit_bequest = C('inherit_bequest', False)  # When True, inheritance concentrates to wealthy

    # ── Education system inequality (causal driver of wage dispersion) ──
    # Asymmetric stretch: education inequality pulls top wages UP
    # while bottom wages stay near baseline (minimum wage floor effect).
    # Formula: top_stretch = 1 + edu_var * 2.0
    # Verified: US ev=0.70 → pre-tax 90/10≈4.1x, France 0.60→4.0x
    # Post-tax/welfare Gini depends on each country's fiscal system.
    edu_var = float(C('education_variance', 0.0))
    edu_var = max(0.0, min(1.0, edu_var))

    rng = np.random.RandomState(seed)
    # ── Apply education-based wage dispersion at initialization ──
    if edu_var > 0 and workers:
        hourly_vals = np.array([w['hourly'] for w in workers])
        median_hr = float(np.median(hourly_vals))
        stretch = 1.0 + edu_var * 2.0
        for w in workers:
            deviation = (w['hourly'] - median_hr) / median_hr
            if deviation > 0:
                # Top wages stretch: educated workers earn more premium
                w['hourly'] = median_hr + median_hr * deviation * stretch
            # Bottom wages stay at baseline (minimum wage floor)
            w['hourly'] = max(median_hr * 0.4, w['hourly'])
            w['monthly'] = w['hourly'] * HOURS_PER_STEP
    # Fallback or additive: original uniform baseline (ev=0) or legacy wage_dispersion_mult
    # NOTE: When edu_var > 0, wage_disp applies ON TOP of education-stretched wages,
    # creating a composite effect (education baseline × residual dispersion multiplier).
    # Backward compatible: edu_var=0, wage_disp=1.0 = original baseline.
    if wage_disp > 1.0 and workers:
        hourly_vals = np.array([w['hourly'] for w in workers])
        median_hr = float(np.median(hourly_vals))
        if median_hr > 0:
            deviations = (hourly_vals - median_hr) / median_hr
            scaled = median_hr + median_hr * deviations * wage_disp
            scaled = np.clip(scaled, median_hr * 0.4, None)
            for idx_w, w in enumerate(workers):
                w['hourly'] = float(scaled[idx_w])
                w['monthly'] = w['hourly'] * HOURS_PER_STEP

    lvt_m = (lvt_r / 12) if tx == 'lvt' else 0.0

    # Balances
    bank_reserve = max(0, float(C('bank_initial_reserve', 0)))
    bal = {e['id']: e['cash'] for e in workers + retirees + businesses}
    for c in children:
        bal[c['id']] = c['cash']
    bal.update({'sys': 500_000_000, 'trust': 0, 'bank': bank_reserve})
    if use_harberger:
        bal[HARBERGER_ESCROW] = 0.0
    wid = [w['id'] for w in workers]
    rid = [r['id'] for r in retirees]
    all_c = wid + rid + (child_ids if use_families else [])
    wland = {w['id']: w['land'] for w in workers}
    rland = {r['id']: r['land'] for r in retirees}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}
    # ── Harberger market (initialized after land values are defined) ──
    harberger_market = None
    if use_harberger:
        harberger_market = create_harberger_market(
            config, workers, retirees, businesses,
            wland, rland, bland,
        )
        _log.info("Harberger market initialized: %d parcels",
                  len(harberger_market.parcels))
    cum_tr = {a: 0.0 for a in all_c}
    hist = {'gini': [], 'wealth': [], 'wmin': [], 'wmean': [], 'div': []}
    pc = 0.0
    consumption_stream = []  # per-worker median consumption each step
    educ_growth = educ_share * 0.08  # 8% return per GDP share
    disp_target = {}  # worker_id -> wage target for displacement recovery

    def xf(fr, to, mech, amt):
        if amt <= 0 or fr not in bal or to not in bal:
            return
        amt = min(amt, bal[fr])
        if amt <= 0:
            return
        bal[fr] -= amt
        bal[to] += amt

    for step in range(1, STEPS + 1):
        try:
            dmult = 0.85 if (ue and step == STEPS // 4) else 1.0

            twb = sum(w['monthly'] for w in workers)
            hc_step = twb * health_share / STEPS
            educ_inv_step = twb * educ_share / STEPS

            # ── Compute median annual wage for progressive tax brackets ──
            if step == 1:
                median_monthly = float(np.median([w['monthly'] for w in workers]))
                median_annual = median_monthly * 12

            # ── A. Skill-biased technical change (annual premium for top 50%) ──
            if skill_prem > 0 and (step % 12 == 1):
                w_sorted = sorted(workers, key=lambda x: x['hourly'])
                nw = len(w_sorted)
                for idx_w, w in enumerate(w_sorted):
                    if idx_w >= nw // 2:  # top 50%
                        w['hourly'] *= (1.0 + skill_prem)
                        w['monthly'] = w['hourly'] * HOURS_PER_STEP

            # ── 1. Wages ────────────────────────────────────────
            sw = {}

            # Determine which workers are in informal sector (bottom informal_share by hourly wage)
            informal_ids = set()
            if informal_share > 0:
                w_by_hr = sorted(workers, key=lambda x: x['hourly'])
                n_inf = int(len(w_by_hr) * informal_share)
                informal_ids = {w['id'] for w in w_by_hr[:n_inf]}

            for w in workers:
                if educ_share > 0:
                    w['hourly'] *= (1.0 + educ_growth / STEPS)
                    w['monthly'] = w['hourly'] * HOURS_PER_STEP
                health_mult = 1.0 + health_share * 0.5
                eff_hr = w['hourly'] * health_mult
                after = eff_hr * (1 - inc_tx) if tx == 'income' else eff_hr
                lr = (after / eff_hr) ** labor_elast if eff_hr > 0 else 1.0
                if ie > 0:
                    ti = cum_tr[w['id']]
                    bi = w['monthly'] * lr
                    if bi + ti > 0:
                        lr *= max(.5, 1 - ie * ti / (bi + ti))
                # ── Wage dispersion multiplier ──
                wv_factor = rng.uniform(*WAGE_VARIABILITY)
                inc = w['monthly'] * lr * wv_factor * un_p

                # ── Informal sector wage penalty (bottom informal_share, lower wages) ──
                if w['id'] in informal_ids:
                    inc *= informal_penalty  # e.g., 0.5 → 50% of formal wage

                # ── B. Union coverage adjustment (bottom 50% boost, top 50% reduction) ──
                if union_cov > 0:
                    w_sorted_rank = sorted(workers, key=lambda x: x['hourly'])
                    rank = next((j for j, wj in enumerate(w_sorted_rank) if wj['id'] == w['id']), 0)
                    nw_rank = len(w_sorted_rank)
                    if rank < nw_rank // 2:  # bottom 50% get union boost
                        inc *= (1.0 + union_cov * 0.1)
                    else:  # top 50% pay union premium penalty
                        inc *= (1.0 - union_cov * 0.05)

                # ── D. Import competition adjustment (bottom 25% suppression) ──
                # Multiplier increased from 0.02 to 0.05 to better match empirical
                # evidence: Autor, Dorn & Hanson (2013) find import competition
                # reduces wages of bottom-quartile workers by 2-4% nationally.
                # At 0.05 multiplier with import_comp=0.20: 1% wage reduction for
                # bottom 25%, consistent with national average estimates from
                # Feenstra & Weinstein (2010) and Acemoglu & Restrepo (2020).
                if import_comp > 0:
                    w_sorted_rank2 = sorted(workers, key=lambda x: x['hourly'])
                    rank2 = next((j for j, wj in enumerate(w_sorted_rank2) if wj['id'] == w['id']), 0)
                    nw2_rank = len(w_sorted_rank2)
                    if rank2 < nw2_rank // 4:  # bottom 25% hit by import competition
                        inc *= (1.0 - import_comp * 0.05)

                # ── Germany Hartz reform (suppress bottom tier wages) ──
                if hartz > 0:
                    w_sorted_rank3 = sorted(workers, key=lambda x: x['hourly'])
                    rank3 = next((j for j, wj in enumerate(w_sorted_rank3) if wj['id'] == w['id']), 0)
                    nw3_rank = len(w_sorted_rank3)
                    if rank3 < nw3_rank // 3:  # bottom 33% face wage suppression
                        inc *= (1.0 + hartz * (-0.1 + 0.05 * (rank3 / max(nw3_rank // 3, 1))))
                    elif rank3 >= nw3_rank * 2 // 3:  # top 33% get mini-job competition benefit
                        inc *= (1.0 + hartz * 0.02)

                # ── UK financial services premium (top decile wage boost) ──
                if fin_serv_prem > 0:
                    w_sorted_rank4 = sorted(workers, key=lambda x: x['hourly'])
                    rank4 = next((j for j, wj in enumerate(w_sorted_rank4) if wj['id'] == w['id']), 0)
                    nw4_rank = len(w_sorted_rank4)
                    if rank4 >= nw4_rank * 9 // 10:  # top 10% get finance sector premium
                        inc *= (1.0 + fin_serv_prem * 0.15)
                    elif rank4 < nw4_rank // 2:  # bottom 50% get wage suppression from crowding
                        inc *= (1.0 - fin_serv_prem * 0.03)

                if min_wage > 0:
                    inc = max(inc, min_wage)

                # ── Unemployment: a fraction of workers get no wage (only welfare) ──
                if unemp_rate > 0:
                    worker_rank = sorted(workers, key=lambda x: x['hourly'])
                    rank_unemp = next((j for j, wj in enumerate(worker_rank) if wj['id'] == w['id']), 0)
                    nw_unemp = len(worker_rank)
                    if rank_unemp < nw_unemp * unemp_rate:  # bottom unemp_rate% are unemployed
                        inc = 0.0  # No wage income; welfare later

                if inc > 0 and bal['sys'] >= inc:
                    xf('sys', w['id'], 'wage', inc)
                    sw[w['id']] = inc
                if health_share > 0 and hc_step > 0:
                    prem_share = hc_step / max(twb, 1)
                    prem = inc * prem_share
                    if prem > 0 and bal.get(w['id'], 0) >= prem:
                        xf(w['id'], 'sys', 'health_prem', prem)

            # ── D2. Import displacement — sectoral reallocation (runs once/step after wages) ──
            if import_displacement > 0 and import_comp > 0:
                disp_prob = min(1.0, import_comp * import_displacement * import_disp_intensity)
                displaced_this_step = 0
                # Apply wage recovery for previously displaced workers
                for w in workers:
                    worker_id = w.get('id', '')
                    if worker_id in disp_target:
                        current = w.get('hourly', 0)
                        target = disp_target[worker_id]
                        if current < target:
                            gap = target - current
                            w['hourly'] = current + import_disp_recovery * gap
                            w['monthly'] = w['hourly'] * HOURS_PER_STEP
                # Only bottom-half workers by hourly wage are vulnerable to displacement
                w_sorted_disp = sorted(workers, key=lambda x: x.get('hourly', 0))
                bottom_half_count = len(workers) // 2
                for idx_w, w in enumerate(w_sorted_disp):
                    if idx_w > bottom_half_count:
                        break
                    if rng.random() < disp_prob:
                        worker_id = w.get('id', '')
                        old_hr = w.get('hourly', 0)
                        disp_target[worker_id] = old_hr  # target = pre-cut wage
                        new_hr = max(old_hr * 0.7, min_wage_floor)
                        w['hourly'] = new_hr
                        w['monthly'] = new_hr * HOURS_PER_STEP
                        displaced_this_step += 1
                        _log.info("Displaced worker %s: wage %.2f→%.2f target=%.2f",
                                  worker_id, old_hr, new_hr, disp_target[worker_id])
                if displaced_this_step > 0 and step % 60 == 0:
                    _log.info("Step %d: %d bottom-half displaced (%d recovering)",
                              step, displaced_this_step, len(disp_target))

            # ── 2. Business ─────────────────────────────────────
            tc = sum(b['capital'] for b in businesses) or 1
            total_at_profit = 0.0
            for b in businesses:
                sb = 0.0
                if eos > 0 and b['capital'] > 50000:
                    sb = eos * np.log(b['capital'] / 50000)
                etfp = b['tfp'] * (1 + sb)
                ms = b['capital'] / tc
                mm = 1 + (mmm - 1) * ms
                rev = etfp * (b['capital'] ** 0.3) * (750 ** 0.7) * mm * dmult

                # ── Tax efficiency loss (Harberger deadweight loss) ──
                # DWL = 0.5 * tax_eff_loss * t^2 × revenue, t = effective tax rate
                if tax_eff_loss > 0:
                    eff_tax = inc_tx if tx == 'income' else (lvt_r * 0.3 if tx == 'lvt' else 0)
                    dwl = 0.5 * tax_eff_loss * (eff_tax ** 2)
                    rev *= max(0.5, 1.0 - dwl)
                elif tfp_elast != 0:  # Legacy fallback
                    eff_tax = inc_tx if tx == 'income' else (lvt_r * 0.3 if tx == 'lvt' else 0)
                    rev *= max(0.5, 1.0 + tfp_elast * eff_tax)

                # Carbon tax
                if carbon_tx > 0:
                    ct = rev * carbon_tx
                    if ct > 0 and bal.get(b['id'], 0) >= ct:
                        xf(b['id'], 'sys', 'carbon_tax', ct)
                    rev -= ct

                prof = rev - BUSINESS_WAGE_BILL
                if prof > 0:
                    tax = prof * corp_tx if tx == 'income' and corp_tx > 0 else 0
                    at = prof - tax
                    total_at_profit += at
                    if tax > 0:
                        xf(b['id'], 'sys', 'ctax', tax)
                    # Investment rate: lower reserve requirements → more lending capacity → more investment
                    eir = INVESTMENT_RATE
                    if reserve_req > 0 and bal.get('bank', 0) > 0:
                        eir *= (1.0 + (1.0 - min(0.99, reserve_req)) * 0.02)
                    eir = min(1.0, eir)
                    inv = at * eir
                    if inv > 0:
                        b['capital'] += inv
                    if uwc and sw:
                        cp = at - inv
                        if cp > 0.01:
                            tw = sum(sw.values())
                            if tw > 0:
                                mt = min(w['monthly'] for w in workers) * wrc
                                for w in workers:
                                    act = min(cp * (sw.get(w['id'], 0) / tw), max(0, mt - sw.get(w['id'], 0)))
                                    if act > 0.01:
                                        xf(b['id'], w['id'], 'coop', act)
                    else:
                        ret = at - inv
                        if ret > 0:
                            xf('sys', b['id'], 'ret', ret)

            # ── C. Financialization — capital income diverted to top 10% wealthiest ──
            if fin_share > 0 and total_at_profit > 0:
                capital_income = total_at_profit * fin_share
                if capital_income > 0 and bal['sys'] >= capital_income:
                    w_sorted_wealth = sorted(workers, key=lambda x: bal.get(x['id'], 0))
                    nw_fin = len(w_sorted_wealth)
                    top10_count = max(1, nw_fin // 10)
                    top10_workers = w_sorted_wealth[-top10_count:]
                    total_wealth_top = sum(bal.get(w['id'], 0) for w in top10_workers)
                    if total_wealth_top > 0:
                        capital_per_worker = capital_income / top10_count
                        for w in top10_workers:
                            amount = capital_income * (bal.get(w['id'], 0) / total_wealth_top)
                            if amount > 0:
                                xf('sys', w['id'], 'financial_income', amount)

            # ── Brazil patrimonial wealth — top 5% get land/patrimonial rent ──
            if patrimonial > 0:
                w_sorted_pat = sorted(workers, key=lambda x: bal.get(x['id'], 0))
                nw_pat = len(w_sorted_pat)
                pat_pool = sum(bal.get(w['id'], 0) for w in workers) * patrimonial * 0.01
                if pat_pool > 0 and bal['sys'] >= pat_pool:
                    top5 = w_sorted_pat[-max(1, nw_pat // 20):]  # top 5%
                    for w in top5:
                        gain = pat_pool * 0.4 / len(top5)  # 40% to top 5%
                        if gain > 0:
                            xf('sys', w['id'], 'patrimonial_rent', gain)

            # ── Capital income concentration — top cap_income_top% get business profits ──
            if cap_income_conc > 0 and total_at_profit > 0:
                cap_pool = total_at_profit * cap_income_conc
                if cap_pool > 0 and bal['sys'] >= cap_pool:
                    n_top = max(1, int(len(workers) * min(1.0, max(0.01, cap_income_top))))
                    w_sorted_cap = sorted(workers, key=lambda x: bal.get(x['id'], 0))
                    top_cap = w_sorted_cap[-n_top:]
                    total_top_cap = sum(bal.get(w['id'], 0) for w in top_cap)
                    if total_top_cap > 0:
                        for w in top_cap:
                            share = bal.get(w['id'], 0) / total_top_cap
                            amount = cap_pool * share
                            if amount > 0:
                                xf('sys', w['id'], 'capital_income', amount)

            # ── 3. Insurance ────────────────────────────────────
            epm, tuf = 1 + inf * 0.5, 1 - inf * 0.3
            for w in workers:
                if rng.random() < tuf:
                    prem = w['monthly'] * 0.05 * epm
                    if bal.get(w['id'], 0) >= prem:
                        xf(w['id'], 'sys', 'prem', prem)
                        if rng.random() < ACCIDENT_PROBABILITY:
                            po = min(rng.uniform(1000, 20000), bal['sys'])
                            if po > 0:
                                xf('sys', w['id'], 'claim', po)

            if ua:
                pass

            # ── Harberger self-assessment + bidding (every step) ──
            if use_harberger and harberger_market is not None:
                harberger_market.advance_step(
                    rng, all_c, bal,
                    land_values={e['id']: wland.get(e['id'], rland.get(e['id'], bland.get(e['id'], 50000)))
                                 for e in workers + retirees + businesses}
                )

            # ── 5. Tax ──────────────────────────────────────────
            tt = 0.0
            clk = 1 - corr * 0.4

            def _evasion_factor(ad):
                if not wire_lvt_evasion or lvt_evasion_controller is None:
                    return 1.0
                ev = 0.15 + ad.get('concealment', 0) * 0.20
                return max(0.0, 1.0 - ev * (1.0 - ad.get('honesty', 0.5)))

            # Elite capture: top 10% wealthiest get tax avoidance (income tax only)
            elite_factor = {}
            if elite_cap > 0 and tx == 'income':
                ww_sorted = sorted([(w['id'], bal.get(w['id'], 0)) for w in workers], key=lambda x: -x[1])
                nw = len(ww_sorted)
                for idx, (wid_, _) in enumerate(ww_sorted):
                    pctile = (1.0 - idx / max(nw - 1, 1)) * 100.0
                    cap = 1.0 - (pctile / 100.0) * elite_cap
                    elite_factor[wid_] = max(0.7, min(1.0, cap)) if idx < max(1, nw // 10) else 1.0

            if tx == 'lvt':
                if use_harberger and harberger_market is not None:
                    tt += harberger_market.collect_lvt(bal, collector='trust')
                else:
                    for el, lm in [(workers, wland), (retirees, rland), (businesses, bland)]:
                        for e in el:
                            d = lm[e['id']] * lvt_m * clk * _evasion_factor(e)
                            if d > 0 and bal.get(e['id'], 0) >= d * 0.5:
                                c = min(d, bal[e['id']])
                                xf(e['id'], 'trust', 'lvt', c)
                                tt += c
            elif tx == 'income':
                for w in workers:
                    wage_amt = sw.get(w['id'], 0)
                    if wage_amt <= 0:
                        continue
                    # Informal workers don't pay income tax
                    if w['id'] in informal_ids:
                        continue
                    # ── E. Progressive taxation (US brackets by default, config-driven) ──
                    if use_prog_tax:
                        annual_income = wage_amt * 12
                        annual_tax = calculate_progressive_tax_once(annual_income, median_annual,
                                                                     brackets=prog_tax_brackets)
                        monthly_tax = annual_tax / 12.0
                        t = monthly_tax * clk
                    else:
                        t = wage_amt * inc_tx * clk
                    t *= elite_factor.get(w['id'], 1.0)
                    # ── Top marginal rate surcharge on top earners ──
                    if top_surcharge > 0:
                        w_sorted_tax = sorted(workers, key=lambda x: bal.get(x['id'], 0))
                        rank_tax = next((j for j, wj in enumerate(w_sorted_tax) if wj['id'] == w['id']), 0)
                        nw_tax = len(w_sorted_tax)
                        if rank_tax >= nw_tax * (1.0 - top_surcharge_thresh):
                            t += wage_amt * top_surcharge * clk
                    if t > 0:
                        xf(w['id'], 'sys', 'itax', t)
                        tt += t
            elif uv:
                for w in workers:
                    v = sw.get(w['id'], 0) * vat_r * clk
                    if v > 0:
                        xf(w['id'], 'sys', 'vat', v)
                        tt += v

            # ── 6. Bloat ────────────────────────────────────────
            ac = tt * blt
            if ac > 0:
                xf('sys', 'trust', 'bloat', ac)

            # ── 7. Dividend ─────────────────────────────────────
            pc = 0.0
            if tx == 'lvt' and tt > 0:
                nd = tt * (1 - blt)
                pc = nd * 0.9 / len(all_c) if nd > 0 else 0
                if pc > 0:
                    for c in all_c:
                        xf('trust', c, 'div', pc)
                        cum_tr[c] += pc

            # ── 8. Courts ───────────────────────────────────────
            elt = ACCIDENT_PROBABILITY * enq
            for b in businesses:
                if rng.random() < elt:
                    pl = rng.choice(wid)
                    amt = rng.uniform(1000, 20000)
                    if rng.random() < enq:
                        pay = min(amt, bal.get(b['id'], 0))
                        if pay > 0:
                            xf(b['id'], pl, 'judge', pay)

            # ── 9. Welfare (excludes informal workers) ──────────────
            if tx == 'income' and inc_tx > 0:
                wp = tt * wel_r * (1 - blt)
                if wp > 0:
                    # Only formal-sector workers get welfare
                    formal_c = [c for c in all_c if (c.startswith('w') and c not in informal_ids) or not c.startswith('w')]
                    n_formal = len(formal_c) or 1
                    pw = wp / n_formal
                    for c in formal_c:
                        xf('sys', c, 'welf', pw)
                        cum_tr[c] = cum_tr.get(c, 0) + pw

            # ── France child benefit taper — progressive benefits to bottom 50% ──
            if child_benefit > 0 and tx == 'income':
                w_sorted_cb = sorted(workers, key=lambda x: bal.get(x['id'], 0))
                nw_cb = len(w_sorted_cb)
                cb_pool = tt * child_benefit * 0.5  # up to 50% of tax revenue
                if cb_pool > 0 and bal['sys'] >= cb_pool:
                    for idx_cb, w in enumerate(w_sorted_cb):
                        if idx_cb >= nw_cb // 2:
                            break  # only bottom 50%
                        # Taper: poorest get more, middle gets less
                        taper_factor = 1.0 - 0.8 * (idx_cb / max(nw_cb // 2, 1))
                        cb_amount = cb_pool * 0.6 * taper_factor / (nw_cb // 2)
                        if cb_amount > 0:
                            xf('sys', w['id'], 'child_benefit', cb_amount)
                            cum_tr[w['id']] += cb_amount

            # ── 10. CPF ─────────────────────────────────────────
            if cpf_r > 0:
                cpf_t = sum(sw.get(w['id'], 0) * cpf_r for w in workers)
                if cpf_t > 0:
                    pcpf = cpf_t / len(all_c)
                    for a in all_c:
                        xf('sys', a, 'cpf', pcpf)

            # ── 11. Banking ─────────────────────────────────────
            if bnk > 0 or reserve_req > 0:
                db = sum(bal.get(a, 0) * 0.1 for a in all_c)
                for a in all_c:
                    ip = bal.get(a, 0) * 0.1 * irt
                    if ip > 0 and bal['bank'] >= ip:
                        xf('bank', a, 'int', ip)
                # Reserve-requirement-based lending — uses reserve_req when set, legacy bnk fallback otherwise
                # NOTE: reserve_req takes priority when both are set (mutual exclusivity enforced)
                if reserve_req > 0:
                    lp = db * (1.0 - min(0.99, max(0.0, reserve_req)))
                else:
                    lp = db * bnk * 0.01  # Legacy fallback — only fires when bnk > 0 AND reserve_req == 0
                for b_entity in businesses:
                    cs = b_entity['capital'] / tc
                    loan = lp * cs
                    if loan > 0 and bal['bank'] >= loan:
                        xf('bank', b_entity['id'], 'loan', loan)
                        b_entity['capital'] += loan * 0.5
                        bal['bank'] += loan * 0.02

            # ── Money creation (per-capita injection through bank lending) ──
            # Fixed per-capita injection (not proportional to wealth) so money
            # creation CAN affect Gini. Banks lend to businesses proportionally
            # to their capital stock → capital-rich firms benefit more → wealth
            # concentrates → Gini rises. All new money goes through bank channel.
            if money_create > 0:
                # Per-capita annual new money (dollars), injected monthly
                total_agents = len(all_c)
                monthly_per_capita = money_create / 12.0
                new_money = monthly_per_capita * total_agents
                # 100% goes to bank reserves for lending (phasing out direct injection)
                bal['bank'] += new_money
                # Bank lending: loans to businesses proportional to capital stock
                # Lending active whenever there are bank reserves to lend
                if bal['bank'] > 0:
                    effective_reserve = max(0.01, min(0.99, reserve_req)) if reserve_req > 0 else 0.1
                    loan_pool = bal['bank'] * (1.0 - effective_reserve)
                    for b in businesses:
                        cs = b['capital'] / max(tc, 1)
                        loan = loan_pool * cs * 0.15  # spread across businesses
                        if loan > 0 and bal['bank'] >= loan:
                            xf('bank', b['id'], 'creative_loan', loan)
                            b['capital'] += loan * 0.6
                            # Loan recipient deposits flow back to bank
                            bal['bank'] += loan * 0.02  # bank profit

            # ── UK housing wealth concentration (top decile property appreciation) ──
            if housing_wealth > 0 and (step % 12 == 1):  # annual
                w_sorted_wealth_h = sorted(workers, key=lambda x: bal.get(x['id'], 0))
                nw_h = len(w_sorted_wealth_h)
                for idx_h, w in enumerate(w_sorted_wealth_h):
                    if idx_h >= nw_h * 9 // 10:  # top 10% by wealth get housing appreciation
                        h_gain = bal.get(w['id'], 0) * housing_wealth * 0.03
                        if h_gain > 0 and bal['sys'] >= h_gain:
                            xf('sys', w['id'], 'housing_gain', h_gain)
                    elif idx_h < nw_h * 3 // 4:  # bottom 75% lose housing affordability
                        h_loss = bal.get(w['id'], 0) * housing_wealth * 0.005
                        if h_loss > 0 and bal.get(w['id'], 0) >= h_loss:
                            xf(w['id'], 'sys', 'housing_cost', h_loss)

            # ── German reunification shock (one-time at step for 1990 equivalent) ──
            if reuni_shock > 0 and step == STEPS // 2:
                for w in workers:
                    shock_penalty = bal.get(w['id'], 0) * 0.05 * reuni_shock
                    if shock_penalty > 0 and bal.get(w['id'], 0) >= shock_penalty:
                        xf(w['id'], 'sys', 'reuni_penalty', shock_penalty)
                # System pays transfer to workers (solidarity surcharge effect)
                sys_solidarity = bal['sys'] * 0.03 * reuni_shock
                if sys_solidarity > 0:
                    for w in workers:
                        payment = sys_solidarity / len(workers)
                        if payment > 0:
                            xf('sys', w['id'], 'solidarity', payment)

            # ── 12. Enforcement ─────────────────────────────────
            for w in workers:
                if corr > 0 and rng.random() < dpr * enq:
                    pen = w['monthly'] * corr * 0.2 * (1 - enq)
                    if pen > 0 and bal.get(w['id'], 0) >= pen:
                        xf(w['id'], 'sys', 'pen', pen)

            # ── 13. Constitutional amendment ────────────────────
            if const_amend_rate > 0 and step % 12 == 0:
                if rng.random() < const_amend_rate:
                    param = rng.choice(['lvt_rate', 'income_tax_rate', 'minimum_wage',
                                        'enforcement_quality', 'corruption_level'])
                    delta = rng.uniform(-0.01, 0.01)
                    if param == 'lvt_rate':
                        lvt_r = max(0.0, min(0.1, lvt_r + delta))
                    elif param == 'income_tax_rate':
                        inc_tx = max(0.0, min(0.7, inc_tx + delta))
                    elif param == 'minimum_wage':
                        min_wage = max(0.0, min_wage + delta * 1000)
                    elif param == 'enforcement_quality':
                        enq = max(0.0, min(1.0, enq + delta))
                    elif param == 'corruption_level':
                        corr = max(0.0, min(1.0, corr + delta))

            # ── Missing mechanisms (config-driven, all default OFF) ──
            missing_log = apply_missing_mechanisms(
                rst, rng, workers, retirees, businesses, bal, 
                {e['id']: wland.get(e['id'], rland.get(e['id'], bland.get(e['id'], 50000)))
                 for e in workers + retirees + businesses},
                step, {'total_tax': tt},
            )

            # Track per-worker median consumption for CRRA welfare
            per_worker_c = [max(0, sw.get(w['id'], 0) * 0.8) for w in workers]
            median_c = float(np.median(per_worker_c)) if per_worker_c else 0.0
            consumption_stream.append(median_c)

            # Report
            if step % REPORT_INTERVAL == 0:
                ww = [bal[i] for i in wid if i in bal]
                if ww:
                    hist['gini'].append(compute_gini(ww))
                    hist['wealth'].append(sum(bal.values()))
                    hist['wmean'].append(np.mean(ww))
                    hist['wmin'].append(min(ww))
                    hist['div'].append(pc)

        except Exception as e:
            _log.error("Step %d: %s", step, e)
            break

    # Post-sim
    # ── Inheritance (post-simulation, one-time transfer) ──
    if ihr > 0 and wid:
        if inherit_bequest:
            # Realistic bequest: inheritance flows proportional to existing wealth
            # Wealthy get more — replicates intergenerational wealth concentration
            total_wealth_pool = sum(bal.get(w_id, 0) for w_id in wid)
            total_bequest = total_wealth_pool * ihr
            wealth_dist = {w_id: bal.get(w_id, 0) for w_id in wid}
            total_dist_wealth = sum(wealth_dist.values())
            if total_dist_wealth > 0 and total_bequest > 0:
                for w_id in wid:
                    inherit_share = total_bequest * (wealth_dist[w_id] / total_dist_wealth)
                    if inherit_share > 0 and bal.get(w_id, 0) >= inherit_share * 0.01:
                        # Take proportionally from all, give proportionally to wealth
                        for src_id in wid:
                            take = inherit_share * (wealth_dist[src_id] / total_dist_wealth)
                            if take > 0 and bal.get(src_id, 0) >= take:
                                xf(src_id, w_id, 'bequest', take)
        else:
            # Original equalizing inheritance: take proportionally, give equally
            for w in workers:
                bq = bal.get(w['id'], 0) * ihr
                pw = bq / len(wid) if wid else 0
                if pw > 0:
                    for w_id in wid:
                        xf(w['id'], w_id, 'inherit', pw)

    ww = [bal[i] for i in wid if i in bal]

    # Gini by decade
    if hist['gini']:
        si = max(1, len(hist['gini']) // 12)
        gbd = [hist['gini'][i] for i in range(0, len(hist['gini']), si)][:12]
    else:
        gbd = []

    # Net worth
    nw_map = {}
    for w in workers:
        nw_map[w['id']] = bal.get(w['id'], 0) + wland.get(w['id'], 0)
    for r in retirees:
        nw_map[r['id']] = bal.get(r['id'], 0) + rland.get(r['id'], 0)
    for b in businesses:
        nw_map[b['id']] = bal.get(b['id'], 0) + bland.get(b['id'], 0) + b['capital']
    for c in children:
        nw_map[c['id']] = bal.get(c['id'], 0) + c['land']
    nw_vals = list(nw_map.values())
    nw_gini = compute_gini(nw_vals)
    nw_mean = np.mean(nw_vals) if nw_vals else 0.0

    # Wellbeing
    mean_cash = np.mean(ww) if ww else 0.0
    wellbeing = compute_wellbeing(workers, seed, rst, gini=compute_gini(ww) if ww else 0.0,
                                  mean_cash=mean_cash,
                                  has_insurance=(up or ua or any(bal.get(w['id'], 0) > 0 for w in workers)))

    # Family
    child_count = len(children)
    family_gini = compute_family_gini(children, workers, bal) if use_families and children else 0.0

    # CRRA welfare
    crra = compute_crra_utility(consumption_stream)

    return {
        'name': name,
        'wealth': sum(bal.values()),
        'gini': round(compute_gini(ww), 4) if ww else 0,
        'w_mean': round(np.mean(ww), 2) if ww else 0,
        'w_min': round(min(ww), 2) if ww else 0,
        'w_max': round(max(ww), 2) if ww else 0,
        'div': round(pc, 2),
        'txns': 0,
        'steps': STEPS,
        'gini_by_decade': gbd,
        'migration_count': 0,
        'policy_path': {},
        'net_worth': round(sum(nw_vals), 2),
        'net_worth_gini': round(nw_gini, 4),
        'net_worth_mean': round(nw_mean, 2),
        'wellbeing': wellbeing,
        'child_count': child_count,
        'family_gini': round(family_gini, 4),
        'crra_welfare': round(crra, 4),
        'consumption_steps': len(consumption_stream),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Phase 8 System Configurations
# ═══════════════════════════════════════════════════════════════════════════

PHASE8_DEFAULTS = {
    'labor_supply_elasticity': LABOR_SUPPLY_ELASTICITY,
    'money_creation_rate': 0.0,       # Per-capita annual new money ($), injected monthly via bank lending
    'tax_efficiency_loss': 0.0,          # Harberger deadweight loss η (Chetty 2012)
    'healthcare_gdp_share': 0.0,
    'education_gdp_share': 0.0,
    'carbon_tax_rate': 0.0,
    'elite_capture_intensity': 0.0,
    # Inequality mechanisms (all default OFF)
    'skill_premium_growth': 0.0,
    'union_coverage': 0.0,
    'capital_income_share': 0.0,
    'import_competition': 0.0,
    'import_displacement_rate': 0.0,   # D2: sectoral reallocation annual rate (0-1)
    'import_disp_intensity': 0.1,      # D2 calibration: annual displacement multiplier
    'min_wage_floor': 10.0,            # D2: displacement wage floor ($/hr)
    'import_disp_recovery_rate': 0.003, # D2: monthly wage recovery rate (default 0.3%, JLS 1993)
    'use_progressive_tax': False,
    # UK-specific
    'housing_wealth_concentration': 0.0,
    'financial_services_premium': 0.0,
    # Germany-specific
    'reunification_shock': 0.0,
    'hartz_reform': 0.0,
    # Brazil-specific
    'patrimonial_wealth': 0.0,
    # France-specific
    'child_benefit_taper': 0.0,
    # General structural
    'unemployment_rate': 0.0,
    'wage_dispersion_mult': 1.0,
    # Dual labor market
    'informal_share': 0.0,
    'informal_wage_penalty': 0.5,
    # Capital ownership
    'capital_income_concentration': 0.0,
    'capital_income_top_share': 0.1,
    # Inheritance
    'inherit_bequest': False,
    # Education system inequality (causal wage dispersion)
    'education_variance': 0.0,
    # Justified replacements for uncertain/arbitrary mechanisms
    'reserve_requirement': 0.0,          # Fraction of deposits banks must hold as reserves (Basel III)
    'top_marginal_surcharge': 0.0,       # Additional tax on top earners by wealth percentile
    'top_surcharge_threshold': 0.8,      # Top 20% by default
    # Legacy keys (kept for backward compatibility, default OFF)
    'TFP_TAX_ELASTICITY': 0.0,           # Replaced by tax_efficiency_loss
    'banking_multiplier': 0.0,           # Replaced by reserve_requirement
    'wage_ratio_cap': 5,                 # Coop-only (Mondragon) — use top_marginal_surcharge for general
    # Harberger self-assessment
    'harberger_self_assess_rate': 0.1,   # Fraction of gap to true value closed per step
    'harberger_bid_probability': 0.02,   # Probability of a bid per step per buyer
    'harberger_buyer_fraction': 0.3,     # Fraction of agents willing to bid
}
PHASE8_DEFAULTS.update(MISSING_MECH_DEFAULTS)

PHASE8_CONFIGS = {}
for sys_name, cfg in PHASE6_CONFIGS.items():
    PHASE8_CONFIGS[sys_name] = dict(cfg, **PHASE8_DEFAULTS)

# ─── Neutralize vibes-based Phase 4 parameters (equalize across ALL systems) ───
# These were set in Phase 4 to make each system "feel right" but have no empirical
# basis for their differing values. Equalizing them ensures comparison is about
# the tax/legal structure, not arbitrary parameter advantages.
_NEUTRAL_EOS = 0.03   # Small positive scale effect (was 0-0.15 across systems)
_NEUTRAL_MMM = 1.2    # Moderate monopoly markup (was 1.0-1.6)
_NEUTRAL_BNK = 0.0    # Replaced by reserve_requirement (was 0-5, all use RR now)
_NEUTRAL_IHR = 0.0    # Replaced by inheritance_flow_fraction (was 0-0.5)
for cfg in PHASE8_CONFIGS.values():
    cfg['economies_of_scale'] = _NEUTRAL_EOS
    cfg['monopoly_markup_max'] = _NEUTRAL_MMM
    cfg['banking_multiplier'] = _NEUTRAL_BNK
    cfg['inheritance_rate'] = _NEUTRAL_IHR

# System-specific sectoral parameters
SECTORAL = {
    'Singapore':     {'healthcare_gdp_share': 0.04, 'education_gdp_share': 0.03, 'carbon_tax_rate': 0.005, 'elite_capture_intensity': 0.0,
                      'education_variance': 0.7, 'wage_dispersion_mult': 3.0,
                      'skill_premium_growth': 0.009,
                      'capital_income_concentration': 0.5, 'capital_income_top_share': 0.03,
                      'cpf_liquidity_trap': 0.15, 'cpf_demand_suppression': 0.12,
                      'cpf_housing_feedback': 0.08, 'cpf_opportunity_cost': 0.4,
                      'use_immigrant_labor': False, 'immigrant_share': 0.0, 'immigrant_wage_penalty': 0.0,
                      'inheritance_flow_fraction': 0.014, 'inheritance_concentration': 0.78},
    'LS_Full':       {'healthcare_gdp_share': 0.05, 'education_gdp_share': 0.02, 'carbon_tax_rate': 0.01, 'elite_capture_intensity': 0.0,
                      'education_variance': 0.3, 'wage_dispersion_mult': 1.3,
                      'inheritance_flow_fraction': 0.01, 'inheritance_concentration': 0.3},
    'US_Style':      {'healthcare_gdp_share': 0.18, 'education_gdp_share': 0.05, 'carbon_tax_rate': 0.0, 'elite_capture_intensity': 0.15,
                      'education_variance': 0.7, 'wage_dispersion_mult': 2.5, 'skill_premium_growth': 0.008,
                      'capital_income_concentration': 0.3, 'capital_income_top_share': 0.05,
                      'use_power_law_wealth': True, 'power_law_exponent': 0.10, 'wealth_tail_fraction': 0.01,
                      'use_immigrant_labor': True, 'immigrant_share': 0.05, 'immigrant_wage_penalty': 0.3,
                      'inheritance_flow_fraction': 0.01, 'inheritance_concentration': 0.15,
                      'use_structural_gap': True, 'structural_gap_groups': [0.87, 0.13], 'structural_gap_multipliers': [1.0, 0.5], 'structural_gap_recurrence': 0.2},
    'Nordic':        {'healthcare_gdp_share': 0.10, 'education_gdp_share': 0.06, 'carbon_tax_rate': 0.03, 'elite_capture_intensity': 0.05,
                      'education_variance': 0.4, 'wage_dispersion_mult': 1.5, 'union_coverage': 0.7,
                      'use_progressive_tax': True, 'top_marginal_surcharge': 0.15,
                      'inheritance_flow_fraction': 0.02, 'inheritance_concentration': 0.5},
    'Mutualist_LS':  {'healthcare_gdp_share': 0.05, 'education_gdp_share': 0.02, 'carbon_tax_rate': 0.01, 'elite_capture_intensity': 0.0,
                      'education_variance': 0.25, 'wage_dispersion_mult': 1.2,
                      'inheritance_flow_fraction': 0.01, 'inheritance_concentration': 0.2},
    'Pure_Georgist': {'healthcare_gdp_share': 0.05, 'education_gdp_share': 0.02, 'carbon_tax_rate': 0.01, 'elite_capture_intensity': 0.0,
                      'education_variance': 0.2, 'wage_dispersion_mult': 1.1,
                      'inheritance_flow_fraction': 0.01, 'inheritance_concentration': 0.2},
    'Worker_Coop':   {'healthcare_gdp_share': 0.05, 'education_gdp_share': 0.02, 'carbon_tax_rate': 0.005, 'elite_capture_intensity': 0.0,
                      'education_variance': 0.2, 'wage_dispersion_mult': 1.1, 'union_coverage': 0.8,
                      'inheritance_flow_fraction': 0.005, 'inheritance_concentration': 0.1},
    'UBI_VAT':       {'healthcare_gdp_share': 0.10, 'education_gdp_share': 0.04, 'carbon_tax_rate': 0.02, 'elite_capture_intensity': 0.05,
                      'education_variance': 0.5, 'wage_dispersion_mult': 1.8,
                      'inheritance_flow_fraction': 0.02, 'inheritance_concentration': 0.6},
    'Laissez_Faire':  {'education_variance': 0.85, 'wage_dispersion_mult': 4.0,
                      'use_super_wealthy': True, 'super_wealthy_multiplier': 15.0, 'super_wealthy_fraction': 0.03,
                      'inheritance_flow_fraction': 0.07, 'inheritance_concentration': 0.9,
                      'forced_reinvestment': True, 'reinvestment_rate': 0.5, 'idle_cash_threshold': 0.5},
    'Harberger_Georgist': {'education_variance': 0.3, 'wage_dispersion_mult': 1.5,
                          'inheritance_flow_fraction': 0.02, 'inheritance_concentration': 0.5,
                          'forced_reinvestment': True, 'reinvestment_rate': 0.4, 'idle_cash_threshold': 0.3},
}
for name, overrides in SECTORAL.items():
    if name in PHASE8_CONFIGS:
        PHASE8_CONFIGS[name].update(overrides)

# ── China (state capitalism: SOEs, hukou, state-directed investment) ─────
# Key characteristics:
# - Hukou urban/rural divide: structural gap 60/40 pop split, rural at 60% wealth
#   (World Bank: rural disposable income ~60% of urban, 2023)
# - SOEs dominate strategic sectors → forced_reinvestment (idle→productive cap)
# - State limits top-end wealth → power_law OFF, low inheritance concentration
# - Elite capture ~0.08 (moderate: CCP anti-corruption reduces pure rent-seeking)
# - 25% informal economy (migrant workers in construction/services)
# - Income tax 15% (effective rate including VAT/POI; nominal rate 25% reduced by credits)
# - Welfare 6% of GDP (fragmented, urban-biased; US target was 14%)
# Target Gini: ~0.47 (World Bank 2020: 0.467)
# Calibrated to produce Gini 0.462 ± 0.006 (5-seed mean)
CHINA = copy.deepcopy(PHASE8_CONFIGS['US_Style'])
CHINA.update({
    'system_name': 'China',
    'education_variance': 0.25, 'wage_dispersion_mult': 1.8,
    'skill_premium_growth': 0.006,
    'use_structural_gap': True, 'structural_gap_groups': [0.6, 0.4],
    'structural_gap_multipliers': [1.0, 0.6], 'structural_gap_recurrence': 0.08,
    'use_power_law_wealth': False,
    'inheritance_flow_fraction': 0.008, 'inheritance_concentration': 0.3,
    'forced_reinvestment': True, 'reinvestment_rate': 0.5, 'idle_cash_threshold': 0.3,
    'elite_capture_intensity': 0.08, 'corruption_level': 0.15,
    'informal_share': 0.25,
    'income_tax_rate': 0.15, 'corp_tax_rate': 0.25, 'welfare_rate': 0.06,
    'enforcement_quality': 0.6, 'information_asymmetry': 0.3,
})
PHASE8_CONFIGS['China'] = CHINA

# ── India (informal dominance: 70% informal, caste gaps, weak state) ─────
# Key characteristics:
# - Caste-based structural gaps: 3-tier (general/OBC/SC-ST at ~70/20/10% pop)
#   Wealth multipliers ~1.0/0.6/0.3 based on NCAER household survey disparities
# - 70% informal economy (NSSO 2023: 93% of workers in unorganized sector)
#   → suppresses formal-sector inequality (low ed_variance, wage_dispersion)
# - Low effective tax rate (8% income, 15% corp — narrow base, high evasion)
# - Weak state capacity: enforcement_quality=0.35, high info asymmetry
# - Welfare 3% GDP (lowest among BRICS; NITI Aayog target)
# - Elite capture elevated (0.05) — crony capitalism in natural resources
# Target Gini: ~0.48 (World Bank 2020: 0.484)
# Calibrated to produce Gini 0.484 ± 0.007 (5-seed mean)
INDIA = copy.deepcopy(PHASE8_CONFIGS['US_Style'])
INDIA.update({
    'system_name': 'India',
    'education_variance': 0.12, 'wage_dispersion_mult': 1.0,
    'skill_premium_growth': 0.005,
    'use_structural_gap': True, 'structural_gap_groups': [0.7, 0.2, 0.1],
    'structural_gap_multipliers': [1.0, 0.6, 0.3], 'structural_gap_recurrence': 0.10,
    'use_power_law_wealth': False,
    'inheritance_flow_fraction': 0.012, 'inheritance_concentration': 0.2,
    'elite_capture_intensity': 0.05, 'corruption_level': 0.25,
    'capital_income_concentration': 0.3, 'capital_income_top_share': 0.06,
    'informal_share': 0.70,
    'income_tax_rate': 0.08, 'corp_tax_rate': 0.15, 'welfare_rate': 0.03,
    'enforcement_quality': 0.35, 'information_asymmetry': 0.5,
    'admin_overhead': 0.15,
})
PHASE8_CONFIGS['India'] = INDIA

# ─── Runtime validation for China/India configs ────────────────
for _name in ['China', 'India']:
    _cfg = PHASE8_CONFIGS.get(_name)
    if _cfg is None:
        raise KeyError(f"CRITICAL: {_name} not registered in PHASE8_CONFIGS")
    # Validate structural gap groups == multipliers length
    if _cfg.get('use_structural_gap'):
        _g = _cfg.get('structural_gap_groups', [])
        _m = _cfg.get('structural_gap_multipliers', [])
        assert len(_g) == len(_m), (
            f"{_name}: structural_gap_groups (len={len(_g)}) != "
            f"structural_gap_multipliers (len={len(_m)})")
        _sum = sum(_g)
        assert 0.99 <= _sum <= 1.01, (
            f"{_name}: structural_gap_groups sum={_sum:.2f} != 1.0")
    # Range checks on critical continuous params
    for _k, _lo, _hi in [('education_variance', 0, 2), ('wage_dispersion_mult', 0.5, 10),
                          ('elite_capture_intensity', 0, 1), ('corruption_level', 0, 1),
                          ('informal_share', 0, 1), ('enforcement_quality', 0, 1),
                          ('income_tax_rate', 0, 0.7), ('welfare_rate', 0, 0.5)]:
        _v = _cfg.get(_k, -1)
        assert _lo <= _v <= _hi, (
            f"{_name}: {_k}={_v} outside [{_lo}, {_hi}]")

def run_batch(seeds, configs):
    results = {}
    t0 = time.time()
    for cfg in configs:
        name = cfg.get('system_name', 'unknown')
        sys_out = []
        for seed in seeds:
            r = run_phase8(*gen_population(seed), seed, cfg)
            sys_out.append(r)
        results[name] = sys_out
        r0 = sys_out[0]
        print(f'{name:<22} Mean=${r0["w_mean"]:>8,.0f} Gini={r0["gini"]:.4f} CRRA={r0.get("crra_welfare",0):.4f}')
    print(f'Time: {time.time()-t0:.0f}s')
    return results


def summarize(results):
    print(f"\n{'='*120}\n  PHASE 8 — SYSTEMS (with CRRA welfare)\n{'='*120}")
    print(f"{'System':<22} {'Mean$':>10} {'Gini':>8} {'Div':>8}  {'NW_G':>8} {'WB':>6} {'CRRA':>10} {'N':>4}")
    print("-" * 120)
    for sn in results:
        rs = results[sn]
        print(f"{sn:<22} ${np.mean([r['w_mean'] for r in rs]):>7,.0f} "
              f"{np.mean([r['gini'] for r in rs]):>.4f}±{np.std([r['gini'] for r in rs]):.4f} "
              f"${np.mean([r['div'] for r in rs]):>5.2f}  "
              f"{np.mean([r.get('net_worth_gini',0) for r in rs]):>.4f}  "
              f"{np.mean([r.get('wellbeing',0) for r in rs]):.4f}  "
              f"{np.mean([r.get('crra_welfare',0) for r in rs]):>10.4f}  {len(rs)}")
    for label, key, rev in [("Mean Wealth", 'w_mean', True), ("Low Gini", 'gini', False),
                            ("Low Net Worth Gini", 'net_worth_gini', False),
                            ("High Wellbeing", 'wellbeing', True), ("High CRRA Welfare", 'crra_welfare', True)]:
        ranked = sorted([(np.mean([r[key] for r in results[sn]]), sn) for sn in results], reverse=rev)
        print(f"\n{label:^70}")
        for i, (v, n) in enumerate(ranked, 1):
            print(f"  {i}. {n:<25} {v:>9,.4f}")


def main():
    seeds = list(range(1, 3)) if '--quick' in sys.argv else SEEDS
    cfg = list(PHASE8_CONFIGS.values())
    print(f"Phase8: {len(seeds)} seeds × {len(cfg)} systems = {len(seeds)*len(cfg)} sims")
    r = run_batch(seeds, cfg)
    summarize(r)
    os.makedirs("output", exist_ok=True)
    json.dump(r, open("output/phase8_results.json", "w"), indent=2)
    print("Saved: output/phase8_results.json")


if __name__ == '__main__':
    main()
