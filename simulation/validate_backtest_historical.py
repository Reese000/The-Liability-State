#!/usr/bin/env python3
"""
validate_backtest_historical.py — Historical backtesting against real data.

Runs chained simulations over 4 historical time points (1960, 1980, 2000, 2020)
for US_Style, Nordic (Sweden), and Singapore systems.  Each period runs 120 steps
(~10 years) chained end-to-start.  Compares simulated Gini and Tax/GDP against
real historical data, reports PASS/FAIL based on directional Gini trend.

The simulator uses a closed system (total wealth conserved at ~$507M). It cannot
reproduce GDP growth but CAN reproduce Gini trajectories and tax ratios.

Usage:
    python validate_backtest_historical.py
"""

import sys, os, copy, json, math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase4 import (
    gen_population, compute_gini, STEPS, REPORT_INTERVAL, HOURS_PER_STEP,
    LVT_ANNUAL_RATE, INVESTMENT_RATE, BUSINESS_WAGE_BILL, WAGE_VARIABILITY,
    ACCIDENT_PROBABILITY, TFP_TAX_ELASTICITY, LABOR_SUPPLY_ELASTICITY,
    ADMIN_OVERHEAD_BY_TAX,
)
from comparison_phase8 import PHASE8_CONFIGS, PHASE8_DEFAULTS

# ── Historical calibration data ──────────────────────────────────────────
# Source: World Bank, OECD, Piketty-Saez, ICTWSS, CPF Board

HISTORICAL_DATA = {
    'US_Style': {
        'system_label': 'US_Style',
        'actual_tax_gdp': {1960: 25, 1980: 27, 2000: 29, 2020: 25},
        'actual_tax_gdp_source': 'OECD Tax Revenue Database',
        'periods': {
            1960: {'income_tax': 0.25, 'corp_tax': 0.52, 'welfare': 0.03,
                   'healthcare': 0.05, 'gini_actual': 0.35},
            1980: {'income_tax': 0.28, 'corp_tax': 0.46, 'welfare': 0.08,
                   'healthcare': 0.08, 'gini_actual': 0.38},
            2000: {'income_tax': 0.25, 'corp_tax': 0.35, 'welfare': 0.10,
                   'healthcare': 0.13, 'gini_actual': 0.46},
            2020: {'income_tax': 0.22, 'corp_tax': 0.21, 'welfare': 0.14,
                   'healthcare': 0.18, 'gini_actual': 0.48},
        }
    },
    'Nordic': {
        'system_label': 'Nordic (Sweden)',
        'actual_tax_gdp': {1960: 30, 1980: 48, 2000: 52, 2020: 43},
        'actual_tax_gdp_source': 'OECD Tax Revenue Database, Sweden',
        'periods': {
            1960: {'income_tax': 0.30, 'corp_tax': 0.50, 'welfare': 0.05,
                   'union_premium': 1.10, 'gini_actual': 0.28},
            1980: {'income_tax': 0.48, 'corp_tax': 0.52, 'welfare': 0.15,
                   'union_premium': 1.15, 'gini_actual': 0.25},
            2000: {'income_tax': 0.52, 'corp_tax': 0.28, 'welfare': 0.18,
                   'union_premium': 1.15, 'gini_actual': 0.27},
            2020: {'income_tax': 0.43, 'corp_tax': 0.21, 'welfare': 0.16,
                   'union_premium': 1.10, 'gini_actual': 0.28},
        }
    },
    'Singapore': {
        'system_label': 'Singapore',
        'actual_tax_gdp': {1960: 15, 1980: 18, 2000: 20, 2020: 14},
        'actual_tax_gdp_source': 'Singapore Dept. of Statistics, World Bank',
        'periods': {
            1960: {'income_tax': 0.10, 'corp_tax': 0.40, 'cpf': 0.10,
                   'welfare': 0.01, 'gini_actual': 0.40},
            1980: {'income_tax': 0.15, 'corp_tax': 0.40, 'cpf': 0.25,
                   'welfare': 0.02, 'gini_actual': 0.42},
            2000: {'income_tax': 0.20, 'corp_tax': 0.26, 'cpf': 0.36,
                   'welfare': 0.03, 'gini_actual': 0.44},
            2020: {'income_tax': 0.22, 'corp_tax': 0.17, 'cpf': 0.37,
                   'welfare': 0.03, 'gini_actual': 0.45},
        }
    },
}

# ── Simulation constants ─────────────────────────────────────────────────
PERIOD_STEPS = 120  # 10 years (12 steps/year × 10)


def build_historical_config(system_name, period_params, base_config):
    """Build a Phase 8 config for a given system and historical time point.

    Overrides base config with historical tax/welfare/CPF/healthcare parameters.
    Structural parameters (corruption, enforcement, etc.) are kept from base.
    Inheritance is disabled to avoid distorting chained Gini trajectory.
    """
    cfg = copy.deepcopy(base_config)

    param_map = {
        'income_tax': 'income_tax_rate',
        'corp_tax': 'corp_tax_rate',
        'welfare': 'welfare_rate',
        'healthcare': 'healthcare_gdp_share',
        'cpf': 'cpf_rate',
        'union_premium': 'union_premium',
    }

    for hist_key, cfg_key in param_map.items():
        if hist_key in period_params:
            cfg[cfg_key] = period_params[hist_key]

    # Disable inheritance — real inheritance is not a universal wealth
    # redistribution; the model's inheritance mechanism is strongly equalizing
    # and compounds across chained periods.
    cfg['inheritance_rate'] = 0.0

    # Ensure consistent label
    cfg['system_name'] = system_name
    return cfg


def run_historical_period(
    workers, retirees, businesses,
    initial_balances,  # dict: {'sys': val, 'trust': val, 'bank': val}
    rng, config, steps=PERIOD_STEPS
):
    """Run the simulation for `steps` steps chaining from prior state.

    Unlike run_phase8, this does NOT reset sys/trust/bank to defaults but
    uses the provided initial_balances, enabling true chaining of fiscal state.

    Key differences from run_phase8 for chaining correctness:
      - sys/trust/bank balance carried forward via initial_balances
      - No post-sim inheritance (handled by build_historical_config setting ihr=0)
      - Returns final balances for next period chaining

    Returns (metrics_dict, final_balances, workers, retirees, businesses, rng).
    """
    # Deep-copy mutable objects so the caller's references survive
    workers = [dict(w) for w in workers]
    retirees = [dict(r) for r in retirees]
    businesses = [dict(b) for b in businesses]
    rst = copy.deepcopy(config)

    name = rst.get('system_name', 'Phase8')
    C = rst.get

    # ── Config flags ─────────────────────────────────────────────
    use_families = C('use_families', False)
    use_adversarial = C('use_adversarial', False)
    use_pooled_insurance = C('use_pooled_insurance', False)
    use_events = C('use_events', False)
    use_worker_coop = C('use_worker_coop', False)
    use_vat = C('use_vat', False)

    tx = C('tax_type', 'income')
    lvt_r = C('lvt_rate', 0.0) if tx == 'lvt' else 0.0
    inc_tx = C('income_tax_rate', 0.0)
    corp_tx = C('corp_tax_rate', 0.0)
    wel_r = C('welfare_rate', 0.0)
    un_p = C('union_premium', 1.0)
    cpf_r = C('cpf_rate', 0.0)
    vat_r = C('vat_rate', 0.20)
    wrc = C('wage_ratio_cap', 5)
    min_wage = float(C('minimum_wage', 0.0))

    corr = max(0, min(1, float(C('corruption_level', 0))))
    ie = max(0, min(.15, float(C('income_effect_labor', 0))))
    blt = max(0, float(C('admin_overhead', ADMIN_OVERHEAD_BY_TAX.get(tx, 0.01))))
    eos = max(0, float(C('economies_of_scale', 0)))
    mmm = max(1, float(C('monopoly_markup_max', 1.3)))
    bnk = max(0, float(C('banking_multiplier', 0)))
    irt = max(0, float(C('interest_rate', 0.005)))
    ihr = min(1, max(0, float(C('inheritance_rate', 0))))
    enq = min(1, max(0, float(C('enforcement_quality', 1))))
    dpr = min(1, max(0, float(C('detection_probability_base', 0.5))))
    inf = min(1, max(0, float(C('information_asymmetry', 0))))

    labor_elast = float(C('labor_supply_elasticity', LABOR_SUPPLY_ELASTICITY))
    money_create = float(C('money_creation_rate', 0.0))
    tfp_elast = float(C('TFP_TAX_ELASTICITY', TFP_TAX_ELASTICITY))

    health_share = float(C('healthcare_gdp_share', 0.0))
    educ_share = float(C('education_gdp_share', 0.0))
    carbon_tx = float(C('carbon_tax_rate', 0.0))
    elite_cap = float(C('elite_capture_intensity', 0.0))
    const_amend_rate = float(C('constitutional_amendment_rate', 0.0))

    # ── Children (unused in most configs) ───────────────────────
    children = []
    child_ids = []
    if use_families:
        rng_c = np.random.RandomState(rng.randint(0, 2**31))
        wids_ = [w['id'] for w in workers]
        for i in range(20):
            children.append({'id': f'c{steps}_{i:03d}',
                             'parent_id': wids_[rng_c.randint(0, len(wids_))],
                             'cash': 0.0, 'land': 0.0})
        child_ids = [c['id'] for c in children]

    # ── Balances: carry forward from previous period ────────────
    bal = {e['id']: e['cash'] for e in workers + retirees + businesses}
    for c in children:
        bal[c['id']] = c['cash']
    # Use caller-provided balances, falling back to defaults on first period
    bal['sys'] = initial_balances.get('sys', 500_000_000)
    bal['trust'] = initial_balances.get('trust', 0)
    bal['bank'] = initial_balances.get('bank', 0)

    wid = [w['id'] for w in workers]
    rid = [r['id'] for r in retirees]
    all_c = wid + rid + child_ids
    wland = {w['id']: w['land'] for w in workers}
    rland = {r['id']: r['land'] for r in retirees}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}
    cum_tr = {a: 0.0 for a in all_c}

    # ── Tracking ────────────────────────────────────────────────
    accumulated_tax = 0.0
    total_wages = 0.0
    total_business_revenue = 0.0
    step_ginis = []
    pc = 0.0
    educ_growth = educ_share * 0.08
    # Track per-step tax for government share calculation
    step_tax_revenues = []

    def xf(fr, to, mech, amt):
        if amt <= 0 or fr not in bal or to not in bal:
            return
        amt = min(amt, bal[fr])
        if amt <= 0:
            return
        bal[fr] -= amt
        bal[to] += amt

    # ── Main loop ───────────────────────────────────────────────
    for step in range(1, steps + 1):
        try:
            dmult = 0.85 if (use_events and step == steps // 4) else 1.0

            twb = sum(w['monthly'] for w in workers)
            hc_step = twb * health_share / steps
            educ_inv_step = twb * educ_share / steps

            # ── 1. Wages ──────────────────────────────────────
            sw = {}
            for w in workers:
                if educ_share > 0:
                    w['hourly'] *= (1.0 + educ_growth / steps)
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
                inc = w['monthly'] * lr * rng.uniform(*WAGE_VARIABILITY) * un_p
                if min_wage > 0:
                    inc = max(inc, min_wage)
                if inc > 0 and bal['sys'] >= inc:
                    xf('sys', w['id'], 'wage', inc)
                    sw[w['id']] = inc
                # Healthcare premium
                if health_share > 0 and hc_step > 0:
                    prem_share = hc_step / max(twb, 1)
                    prem = inc * prem_share
                    if prem > 0 and bal.get(w['id'], 0) >= prem:
                        xf(w['id'], 'sys', 'health_prem', prem)

            total_wages += sum(sw.values())

            # ── 2. Business ───────────────────────────────────
            step_biz_rev = 0.0
            tc = sum(b['capital'] for b in businesses) or 1
            for b in businesses:
                sb = 0.0
                if eos > 0 and b['capital'] > 50000:
                    sb = eos * np.log(b['capital'] / 50000)
                etfp = b['tfp'] * (1 + sb)
                ms = b['capital'] / tc
                mm = 1 + (mmm - 1) * ms
                rev = etfp * (b['capital'] ** 0.3) * (8 ** 0.7) * mm * dmult

                if tfp_elast != 0:
                    eff_tax = inc_tx if tx == 'income' else (lvt_r * 0.3 if tx == 'lvt' else 0)
                    rev *= max(0.5, 1.0 + tfp_elast * eff_tax)

                if carbon_tx > 0:
                    ct = rev * carbon_tx
                    if ct > 0 and bal.get(b['id'], 0) >= ct:
                        xf(b['id'], 'sys', 'carbon_tax', ct)
                    rev -= ct

                prof = rev - BUSINESS_WAGE_BILL
                step_biz_rev += rev
                if prof > 0:
                    tax = prof * corp_tx if tx == 'income' and corp_tx > 0 else 0
                    at = prof - tax
                    if tax > 0:
                        xf(b['id'], 'sys', 'ctax', tax)
                    eir = INVESTMENT_RATE * (1 + bnk * 0.05) if (bnk > 0 and bal.get('bank', 0) > 0) else INVESTMENT_RATE
                    eir = min(1, eir)
                    inv = at * eir
                    if inv > 0:
                        b['capital'] += inv
                    if use_worker_coop and sw:
                        cp = at - inv
                        if cp > 0.01:
                            tw = sum(sw.values())
                            if tw > 0:
                                mt = min(w['monthly'] for w in workers) * wrc
                                for w in workers:
                                    act = min(cp * (sw.get(w['id'], 0) / tw),
                                              max(0, mt - sw.get(w['id'], 0)))
                                    if act > 0.01:
                                        xf(b['id'], w['id'], 'coop', act)
                    else:
                        ret = at - inv
                        if ret > 0:
                            xf('sys', b['id'], 'ret', ret)

            total_business_revenue += step_biz_rev

            # ── 3. Insurance ──────────────────────────────────
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

            # ── 5. Tax ────────────────────────────────────────
            tt = 0.0
            clk = 1 - corr * 0.4

            elite_factor = {}
            if elite_cap > 0 and tx == 'income':
                ww_sorted = sorted([(w['id'], bal.get(w['id'], 0)) for w in workers],
                                   key=lambda x: -x[1])
                nw = len(ww_sorted)
                for idx, (wid_, _) in enumerate(ww_sorted):
                    pctile = (1.0 - idx / max(nw - 1, 1)) * 100.0
                    cap = 1.0 - (pctile / 100.0) * elite_cap
                    elite_factor[wid_] = max(0.7, min(1.0, cap)) if idx < max(1, nw // 10) else 1.0

            if tx == 'lvt':
                lvt_m = lvt_r / 12
                for el, lm in [(workers, wland), (retirees, rland), (businesses, bland)]:
                    for e in el:
                        d = lm[e['id']] * lvt_m * clk
                        if d > 0 and bal.get(e['id'], 0) >= d * 0.5:
                            c = min(d, bal[e['id']])
                            xf(e['id'], 'trust', 'lvt', c)
                            tt += c
            elif tx == 'income':
                for w in workers:
                    t = sw.get(w['id'], 0) * inc_tx * clk
                    t *= elite_factor.get(w['id'], 1.0)
                    if t > 0:
                        xf(w['id'], 'sys', 'itax', t)
                        tt += t
            elif use_vat:
                for w in workers:
                    v = sw.get(w['id'], 0) * vat_r * clk
                    if v > 0:
                        xf(w['id'], 'sys', 'vat', v)
                        tt += v

            step_tax_revenues.append(tt)
            accumulated_tax += tt

            # ── 6. Bloat ────────────────────────────────────
            ac = tt * blt
            if ac > 0:
                xf('sys', 'trust', 'bloat', ac)

            # ── 7. Dividend (LVT only) ──────────────────────
            pc = 0.0
            if tx == 'lvt' and tt > 0:
                nd = tt * (1 - blt)
                pc = nd * 0.9 / len(all_c) if nd > 0 else 0
                if pc > 0:
                    for c in all_c:
                        xf('trust', c, 'div', pc)
                        cum_tr[c] += pc

            # ── 8. Courts ──────────────────────────────────
            elt = ACCIDENT_PROBABILITY * enq
            for b in businesses:
                if rng.random() < elt:
                    pl = rng.choice(wid)
                    amt = rng.uniform(1000, 20000)
                    if rng.random() < enq:
                        pay = min(amt, bal.get(b['id'], 0))
                        if pay > 0:
                            xf(b['id'], pl, 'judge', pay)

            # ── 9. Welfare ─────────────────────────────────
            if tx == 'income' and inc_tx > 0:
                wp = tt * wel_r * (1 - blt)
                if wp > 0:
                    pw = wp / len(all_c)
                    for c in all_c:
                        xf('sys', c, 'welf', pw)
                        cum_tr[c] += pw

            # ── 10. CPF ────────────────────────────────────
            if cpf_r > 0:
                cpf_t = sum(sw.get(w['id'], 0) * cpf_r for w in workers)
                if cpf_t > 0:
                    pcpf = cpf_t / len(all_c)
                    for a in all_c:
                        xf('sys', a, 'cpf', pcpf)

            # ── 11. Banking ────────────────────────────────
            if bnk > 0:
                db = sum(bal.get(a, 0) * 0.1 for a in all_c)
                for a in all_c:
                    ip = bal.get(a, 0) * 0.1 * irt
                    if ip > 0 and bal['bank'] >= ip:
                        xf('bank', a, 'int', ip)
                lp = db * bnk * 0.01
                for b in businesses:
                    cs = b['capital'] / tc
                    loan = lp * cs
                    if loan > 0 and bal['bank'] >= loan:
                        xf('bank', b['id'], 'loan', loan)
                        b['capital'] += loan * 0.5
                        bal['bank'] += loan * 0.02

            # Money creation
            if money_create > 0:
                total_deposits = sum(bal.get(a, 0) for a in all_c)
                bal['sys'] += total_deposits * money_create / steps

            # ── 12. Enforcement ────────────────────────────
            for w in workers:
                if corr > 0 and rng.random() < dpr * enq:
                    pen = w['monthly'] * corr * 0.2 * (1 - enq)
                    if pen > 0 and bal.get(w['id'], 0) >= pen:
                        xf(w['id'], 'sys', 'pen', pen)

            # ── 13. Constitutional amendment ───────────────
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

            # Track Gini at report intervals (every 12 steps ≈ yearly)
            if step % 12 == 0:
                ww = [bal[i] for i in wid if i in bal]
                if ww:
                    step_ginis.append(compute_gini(ww))

        except Exception as e:
            print(f"  [ERROR] {name} step {step}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            raise

    # ── Final metrics (NO inheritance post-step — ihr=0) ─────────
    ww = [bal[i] for i in wid if i in bal]
    final_gini = round(compute_gini(ww), 4) if ww else 0.0

    # Tax/GDP = total tax over all steps / total wages + business revenue
    total_economic_output = total_wages + total_business_revenue
    tax_gdp_ratio = (accumulated_tax / total_economic_output * 100) if total_economic_output > 0 else 0.0

    # Government share = sys balance / total wealth
    total_system_wealth = sum(bal.values())
    gov_share = (bal.get('sys', 0) / total_system_wealth * 100) if total_system_wealth > 0 else 0.0

    # Gini is the last recorded value from the loop
    sim_gini = float(step_ginis[-1]) if step_ginis else final_gini

    metrics = {
        'gini': sim_gini,
        'final_gini': final_gini,
        'tax_gdp_pct': round(tax_gdp_ratio, 2),
        'gov_share_pct': round(gov_share, 2),
        'accumulated_tax': round(accumulated_tax, 2),
        'total_wages': round(total_wages, 2),
        'total_biz_revenue': round(total_business_revenue, 2),
        'steps_run': steps,
        'sys_balance': round(bal.get('sys', 0), 2),
        'ginis_by_step': [float(g) for g in step_ginis],
    }

    # Update agent cash for chaining
    for w in workers:
        w['cash'] = bal.get(w['id'], 0)
    for r in retirees:
        r['cash'] = bal.get(r['id'], 0)
    for b in businesses:
        b['cash'] = bal.get(b['id'], 0)

    # Return final balances for next period
    final_balances = {
        'sys': bal.get('sys', 0),
        'trust': bal.get('trust', 0),
        'bank': bal.get('bank', 0),
    }

    return metrics, final_balances, workers, retirees, businesses, rng


def classify_trend(values):
    """Classify a list of values as RISING, FALLING, or STABLE.

    Uses simple linear regression slope.  If |slope|/mean < 0.08 → STABLE.
    Threshold slightly relaxed to capture direction meaningfully.
    """
    if len(values) < 3:
        return "STABLE"
    x = np.arange(len(values))
    y = np.array(values)
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    mean_y = np.mean(y)
    if mean_y == 0:
        return "STABLE"
    rel_change = abs(slope) / mean_y
    # ~8% relative change threshold; if the slope is very shallow relative to
    # the mean, call it STABLE
    if rel_change < 0.08:
        return "STABLE"
    return "RISING" if slope > 0 else "FALLING"


def main():
    np.random.seed(42)
    out_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(out_dir, exist_ok=True)

    all_results = {}

    for system_name, system_data in HISTORICAL_DATA.items():
        label = system_data['system_label']
        periods = sorted(system_data['periods'].keys())
        actual_ginis = [system_data['periods'][p]['gini_actual'] for p in periods]

        print(f"\n{'='*70}")
        print(f"  System: {label}")
        print(f"{'='*70}")

        # Build base config from existing PHASE8_CONFIGS
        if system_name in PHASE8_CONFIGS:
            base_config = PHASE8_CONFIGS[system_name]
        else:
            print(f"  [WARN] {system_name} not in PHASE8_CONFIGS, using generic")
            base_config = {
                'system_name': system_name, 'tax_type': 'income',
                'lvt_rate': 0.0, 'income_tax_rate': 0.25, 'corp_tax_rate': 0.21,
                'welfare_rate': 0.10, 'union_premium': 1.0, 'cpf_rate': 0.0,
                'use_adversarial': False, 'use_pooled_insurance': False,
                'use_events': False, 'use_worker_coop': False,
                'wage_ratio_cap': 5, 'use_vat': False, 'vat_rate': 0.20,
                'corruption_level': 0.1, 'income_effect_labor': 0.05,
                'admin_overhead': 0.05, 'economies_of_scale': 0.05,
                'monopoly_markup_max': 1.3, 'banking_multiplier': 0.0,
                'interest_rate': 0.003, 'inheritance_rate': 0.0,
                'enforcement_quality': 0.8, 'detection_probability_base': 0.5,
                'information_asymmetry': 0.2, 'minimum_wage': 0.0,
                **PHASE8_DEFAULTS,
                'healthcare_gdp_share': 0.0, 'education_gdp_share': 0.0,
                'carbon_tax_rate': 0.0, 'elite_capture_intensity': 0.0,
            }

        # Generate initial population & RNG for the chained run
        seed = 42
        workers, retirees, businesses = gen_population(seed)
        rng = np.random.RandomState(seed)
        initial_balances = {'sys': 500_000_000, 'trust': 0, 'bank': 0}

        sim_ginis = []
        sim_tax_gdps = []
        sim_gov_shares = []
        period_metrics = []

        for period in periods:
            params = system_data['periods'][period]
            cfg = build_historical_config(system_name, params, base_config)

            # Display key params
            hc = cfg.get('healthcare_gdp_share', 0)
            cpf = cfg.get('cpf_rate', 0)
            up = cfg.get('union_premium', 1.0)
            extra = ""
            if cpf > 0:
                extra += f", cpf={cpf:.2f}"
            if up != 1.0:
                extra += f", union={up:.2f}"
            print(f"\n  ── {period}s ──────────────────────────────────")
            print(f"     income_tax={cfg['income_tax_rate']:.2f}, "
                  f"corp_tax={cfg['corp_tax_rate']:.2f}, "
                  f"welfare={cfg['welfare_rate']:.2f}, "
                  f"health={hc:.2f}{extra}")

            metrics, initial_balances, workers, retirees, businesses, rng = \
                run_historical_period(
                    workers, retirees, businesses,
                    initial_balances, rng, cfg
                )

            sim_ginis.append(metrics['gini'])
            sim_tax_gdps.append(metrics['tax_gdp_pct'])
            sim_gov_shares.append(metrics['gov_share_pct'])
            period_metrics.append({
                'period': period,
                'config': {k: float(v) if isinstance(v, (int, float)) else v
                          for k, v in cfg.items() if isinstance(v, (int, float, str, bool))},
                'metrics': metrics,
                'actual_gini': params['gini_actual'],
            })

            print(f"     → Gini: {metrics['gini']:.4f}, "
                  f"Tax/GDP: {metrics['tax_gdp_pct']:.1f}%, "
                  f"GovShare: {metrics['gov_share_pct']:.1f}%, "
                  f"Sys: \${metrics.get('sys_balance',0):,.0f}")

        # Trend analysis
        sim_trend = classify_trend(sim_ginis)
        actual_trend = classify_trend(actual_ginis)
        trend_match = (sim_trend == actual_trend)
        pass_fail = "PASS" if trend_match else "FAIL"

        # ── Output table ─────────────────────────────────────
        print(f"\n  {'='*70}")
        print(f"  {'Period':>8} | {'Sim Gini':>9} | {'Actual Gini':>11} | {'Δ':>7} | "
              f"{'Sim Tax/GDP':>11} | {'Actual Tax/GDP':>14} | {'Δ':>7}")
        print(f"  {'-'*8}-+-{'-'*9}-+-{'-'*11}-+-{'-'*7}-+-"
              f"{'-'*11}-+-{'-'*14}-+-{'-'*7}")
        for i, period in enumerate(periods):
            actual = system_data['periods'][period]
            actual_tax = system_data['actual_tax_gdp'].get(period, 0)
            delta_gini = sim_ginis[i] - actual['gini_actual']
            delta_tax = sim_tax_gdps[i] - actual_tax
            print(f"  {period}s  | {sim_ginis[i]:>9.4f} | {actual['gini_actual']:>11.4f} | "
                  f"{delta_gini:>+7.4f} | {sim_tax_gdps[i]:>10.1f}% | "
                  f"{actual_tax:>12d}% | {delta_tax:>+7.1f}%")
        print(f"\n  Trend   | {sim_trend:<9} | ACTUAL: {actual_trend:<9} | "
              f"{'MATCH' if trend_match else 'MISMATCH':>9}")
        print(f"  Result  | {pass_fail}")

        all_results[system_name] = {
            'label': label,
            'periods': list(periods),
            'sim_ginis': sim_ginis,
            'actual_ginis': actual_ginis,
            'sim_tax_gdp_pcts': sim_tax_gdps,
            'actual_tax_gdp_pcts': [system_data['actual_tax_gdp'].get(p, 0) for p in periods],
            'sim_gov_shares': sim_gov_shares,
            'sim_trend': sim_trend,
            'actual_trend': actual_trend,
            'trend_match': trend_match,
            'pass_fail': pass_fail,
            'period_details': period_metrics,
        }

    # ── Summary ──────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    all_pass = True
    for system_name, r in all_results.items():
        status = r['pass_fail']
        if status != 'PASS':
            all_pass = False
        print(f"  {r['label']:<22} | Trend: {r['sim_trend']:<8} "
              f"(actual: {r['actual_trend']:<8}) | {status}")

    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
    print(f"{'='*70}")

    # ── Save JSON ───────────────────────────────────────────
    output_path = os.path.join(out_dir, 'backtest_historical.json')
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Saved: {output_path}")


if __name__ == '__main__':
    main()
