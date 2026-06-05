#!/usr/bin/env python3
"""
validate_backtest_us_fix.py — US backtest with 5 configurable inequality mechanisms.

Replicates the US backtest from validate_backtest_historical.py with 4 chained
periods (1960, 1980, 2000, 2020), then adds 5 inequality mechanisms:

  A. Skill-biased technical change  (skill_premium_growth)
  B. Union decline                 (union_coverage)
  C. Financialization              (capital_income_share)
  D. Import competition            (import_competition)
  E. Progressive taxation          (use_progressive_tax)

Runs TWICE:
  RUN 1: All 5 OFF (baseline — should match existing stable Gini ~0.185)
  RUN 2: All 5 ON with historically calibrated values

Saves results to output/backtest_us_fix.json.

Usage:
    python validate_backtest_us_fix.py
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

# ── Historical calibration data (US only) ──────────────────────────────
US_DATA = {
    'system_label': 'US_Style',
    'actual_tax_gdp': {1960: 25, 1980: 27, 2000: 29, 2020: 25},
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
}

PERIOD_STEPS = 120  # 10 years (12 steps/year × 10)


def build_historical_config(system_name, period_params, base_config):
    """Build a Phase 8 config for a given historical time point."""
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

    # Disable inheritance for chaining
    cfg['inheritance_rate'] = 0.0
    cfg['system_name'] = system_name
    return cfg


def calculate_progressive_tax_once(annual_income):
    """Calculate US 2020 federal income tax for a given annual income.

    Brackets (married filing jointly, simplified approximation):
        10%  on first   $20,000
        15%  on next    $30,000  ($20k–$50k)
        25%  on next    $50,000  ($50k–$100k)
        35%  on next   $100,000  ($100k–$200k)
        40%  on amount over $200k
    """
    brackets = [
        (0, 20000, 0.10),
        (20000, 50000, 0.15),
        (50000, 100000, 0.25),
        (100000, 200000, 0.35),
        (200000, float('inf'), 0.40),
    ]
    tax = 0.0
    for lower, upper, rate in brackets:
        if annual_income <= lower:
            break
        taxable = min(annual_income, upper) - lower
        tax += taxable * rate
    return tax


def classify_trend(values):
    """Classify a list of values as RISING, FALLING, or STABLE."""
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
    if rel_change < 0.08:
        return "STABLE"
    return "RISING" if slope > 0 else "FALLING"


# ═══════════════════════════════════════════════════════════════════════
#  Modified simulation loop with 5 inequality mechanisms
# ═══════════════════════════════════════════════════════════════════════

def run_historical_period_with_inequality(
    workers, retirees, businesses,
    initial_balances, rng, config,
    steps=PERIOD_STEPS,
    # ── 5 configurable inequality mechanisms ──
    skill_premium_growth=0.0,    # A: SBTC annual premium (top 50%)
    union_coverage=0.0,          # B: union coverage rate (0-1)
    capital_income_share=0.0,    # C: financialization share (0-1)
    import_competition=0.0,      # D: import competition intensity (0-1)
    use_progressive_tax=False,   # E: use progressive brackets
):
    """Run simulation with inequality mechanisms inserted after wage calc.

    Returns (metrics_dict, final_balances, workers, retirees, businesses, rng).
    """
    workers = [dict(w) for w in workers]
    retirees = [dict(r) for r in retirees]
    businesses = [dict(b) for b in businesses]
    rst = copy.deepcopy(config)

    name = rst.get('system_name', 'Phase8')
    C = rst.get

    # ── Config flags ──
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

    # ── Children ──
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

    # ── Balances ──
    bal = {e['id']: e['cash'] for e in workers + retirees + businesses}
    for c in children:
        bal[c['id']] = c['cash']
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

    # ── Tracking ──
    accumulated_tax = 0.0
    total_wages = 0.0
    total_business_revenue = 0.0
    step_ginis = []
    pc = 0.0
    educ_growth = educ_share * 0.08
    step_tax_revenues = []

    def xf(fr, to, mech, amt):
        if amt <= 0 or fr not in bal or to not in bal:
            return
        amt = min(amt, bal[fr])
        if amt <= 0:
            return
        bal[fr] -= amt
        bal[to] += amt

    # ── Main loop ──
    for step in range(1, steps + 1):
        try:
            dmult = 0.85 if (use_events and step == steps // 4) else 1.0

            twb = sum(w['monthly'] for w in workers)
            hc_step = twb * health_share / steps
            educ_inv_step = twb * educ_share / steps

            # ──────── A. Skill-biased technical change (annual) ────────
            if skill_premium_growth > 0 and (step % 12 == 1):
                # Top 50% of workers by hourly wage get compounding premium
                w_sorted = sorted(workers, key=lambda x: x['hourly'])
                nw = len(w_sorted)
                for idx_w, w in enumerate(w_sorted):
                    if idx_w >= nw // 2:  # top 50%
                        w['hourly'] *= (1.0 + skill_premium_growth)
                        w['monthly'] = w['hourly'] * HOURS_PER_STEP

            # ── 1. Wages ──
            sw = {}

            # Pre-compute hourly rankings for inequality adjustments (recalc each step
            # because SBTC may have shifted them)
            hourly_sorted = sorted(workers, key=lambda x: x['hourly'])
            hourly_rank = {w['id']: i for i, w in enumerate(hourly_sorted)}
            nw = len(workers)

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

                # ── B. Union coverage adjustment ──
                if union_coverage > 0:
                    rank = hourly_rank.get(w['id'], 0)
                    if rank < nw // 2:  # bottom 50% get boost
                        inc *= (1.0 + union_coverage * 0.1)
                    else:  # top 50% get reduction
                        inc *= (1.0 - union_coverage * 0.05)

                # ── D. Import competition adjustment ──
                if import_competition > 0:
                    rank = hourly_rank.get(w['id'], 0)
                    if rank < nw // 4:  # bottom 25% get wage reduction
                        inc *= (1.0 - import_competition * 0.02)

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

            # ── 2. Business ──
            step_biz_rev = 0.0
            total_at_profit = 0.0  # for financialization tracking
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
                    total_at_profit += at
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

            # ──────── C. Financialization ─────────────────────────────
            if capital_income_share > 0 and total_at_profit > 0:
                capital_income = total_at_profit * capital_income_share
                if capital_income > 0 and bal['sys'] >= capital_income:
                    # Sort workers by wealth (cash balance)
                    w_sorted = sorted(workers, key=lambda x: bal.get(x['id'], 0))
                    nw2 = len(w_sorted)
                    top10_count = max(1, nw2 // 10)
                    top10_workers = w_sorted[-top10_count:]

                    # Distribute proportionally by wealth
                    total_wealth = sum(bal.get(w['id'], 0) for w in top10_workers)
                    if total_wealth > 0:
                        for w in top10_workers:
                            share = bal.get(w['id'], 0) / total_wealth
                            amount = capital_income * share
                            if amount > 0:
                                xf('sys', w['id'], 'capital_income', amount)

            # ── 3. Insurance ──
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

            # ── 5. Tax ──
            tt = 0.0
            clk = 1 - corr * 0.4

            elite_factor = {}
            if elite_cap > 0 and tx == 'income':
                ww_sorted = sorted([(w['id'], bal.get(w['id'], 0)) for w in workers],
                                   key=lambda x: -x[1])
                nw3 = len(ww_sorted)
                for idx, (wid_, _) in enumerate(ww_sorted):
                    pctile = (1.0 - idx / max(nw3 - 1, 1)) * 100.0
                    cap = 1.0 - (pctile / 100.0) * elite_cap
                    elite_factor[wid_] = max(0.7, min(1.0, cap)) if idx < max(1, nw3 // 10) else 1.0

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
                    wage_amt = sw.get(w['id'], 0)
                    if wage_amt <= 0:
                        continue

                    # ── E. Progressive taxation ──
                    if use_progressive_tax:
                        # Calculate annual tax from monthly wage, then divide back
                        annual_income = wage_amt * 12
                        annual_tax = calculate_progressive_tax_once(annual_income)
                        monthly_tax = annual_tax / 12.0
                        t = monthly_tax * clk
                    else:
                        t = wage_amt * inc_tx * clk

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

            # ── 6. Bloat ──
            ac = tt * blt
            if ac > 0:
                xf('sys', 'trust', 'bloat', ac)

            # ── 7. Dividend (LVT only) ──
            pc = 0.0
            if tx == 'lvt' and tt > 0:
                nd = tt * (1 - blt)
                pc = nd * 0.9 / len(all_c) if nd > 0 else 0
                if pc > 0:
                    for c in all_c:
                        xf('trust', c, 'div', pc)
                        cum_tr[c] += pc

            # ── 8. Courts ──
            elt = ACCIDENT_PROBABILITY * enq
            for b in businesses:
                if rng.random() < elt:
                    pl = rng.choice(wid)
                    amt = rng.uniform(1000, 20000)
                    if rng.random() < enq:
                        pay = min(amt, bal.get(b['id'], 0))
                        if pay > 0:
                            xf(b['id'], pl, 'judge', pay)

            # ── 9. Welfare ──
            if tx == 'income' and inc_tx > 0:
                wp = tt * wel_r * (1 - blt)
                if wp > 0:
                    pw = wp / len(all_c)
                    for c in all_c:
                        xf('sys', c, 'welf', pw)
                        cum_tr[c] += pw

            # ── 10. CPF ──
            if cpf_r > 0:
                cpf_t = sum(sw.get(w['id'], 0) * cpf_r for w in workers)
                if cpf_t > 0:
                    pcpf = cpf_t / len(all_c)
                    for a in all_c:
                        xf('sys', a, 'cpf', pcpf)

            # ── 11. Banking ──
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

            if money_create > 0:
                total_deposits = sum(bal.get(a, 0) for a in all_c)
                bal['sys'] += total_deposits * money_create / steps

            # ── 12. Enforcement ──
            for w in workers:
                if corr > 0 and rng.random() < dpr * enq:
                    pen = w['monthly'] * corr * 0.2 * (1 - enq)
                    if pen > 0 and bal.get(w['id'], 0) >= pen:
                        xf(w['id'], 'sys', 'pen', pen)

            # ── 13. Constitutional amendment ──
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

    # ── Final metrics ──
    ww = [bal[i] for i in wid if i in bal]
    final_gini = round(compute_gini(ww), 4) if ww else 0.0

    total_economic_output = total_wages + total_business_revenue
    tax_gdp_ratio = (accumulated_tax / total_economic_output * 100) if total_economic_output > 0 else 0.0

    total_system_wealth = sum(bal.values())
    gov_share = (bal.get('sys', 0) / total_system_wealth * 100) if total_system_wealth > 0 else 0.0

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

    final_balances = {
        'sys': bal.get('sys', 0),
        'trust': bal.get('trust', 0),
        'bank': bal.get('bank', 0),
    }

    return metrics, final_balances, workers, retirees, businesses, rng


# ═══════════════════════════════════════════════════════════════════════
#  Backtest runner — runs 4 chained US periods with given inequality params
# ═══════════════════════════════════════════════════════════════════════

def run_us_backtest(label, inequality_params_by_period, base_config):
    """Run US backtest with 4 chained periods and per-period inequality params.

    inequality_params_by_period: dict mapping year -> dict of inequality kwargs
        to pass to run_historical_period_with_inequality.
    """
    system_name = 'US_Style'
    periods = sorted(US_DATA['periods'].keys())

    seed = 42
    workers, retirees, businesses = gen_population(seed)
    rng = np.random.RandomState(seed)
    initial_balances = {'sys': 500_000_000, 'trust': 0, 'bank': 0}

    sim_ginis = []
    sim_tax_gdps = []
    sim_gov_shares = []
    period_metrics = []

    for period in periods:
        params = US_DATA['periods'][period]
        cfg = build_historical_config(system_name, params, base_config)

        # Get inequality params for this period (or empty dict for OFF)
        ineq_kwargs = inequality_params_by_period.get(period, {})

        print(f"\n  ── {period}s [{label}] ───────────────────────────")
        print(f"     income_tax={cfg['income_tax_rate']:.2f}, "
              f"corp_tax={cfg['corp_tax_rate']:.2f}, "
              f"welfare={cfg['welfare_rate']:.2f}, "
              f"health={cfg.get('healthcare_gdp_share', 0):.2f}"
              + (f", ineq={ineq_kwargs}" if ineq_kwargs else ""))

        metrics, initial_balances, workers, retirees, businesses, rng = \
            run_historical_period_with_inequality(
                workers, retirees, businesses,
                initial_balances, rng, cfg,
                **ineq_kwargs,
            )

        sim_ginis.append(metrics['gini'])
        sim_tax_gdps.append(metrics['tax_gdp_pct'])
        sim_gov_shares.append(metrics['gov_share_pct'])
        period_metrics.append({
            'period': period,
            'inequality_params': dict(ineq_kwargs),
            'metrics': metrics,
            'actual_gini': params['gini_actual'],
        })

        print(f"     → Gini: {metrics['gini']:.4f}, "
              f"Tax/GDP: {metrics['tax_gdp_pct']:.1f}%, "
              f"GovShare: {metrics['gov_share_pct']:.1f}%, "
              f"Sys: ${metrics.get('sys_balance',0):,.0f}")

    return sim_ginis, sim_tax_gdps, sim_gov_shares, period_metrics


# ═══════════════════════════════════════════════════════════════════════
#  Main: run TWICE and compare
# ═══════════════════════════════════════════════════════════════════════

def main():
    np.random.seed(42)
    out_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(out_dir, exist_ok=True)

    system_name = 'US_Style'

    # ── Build base config ──
    if system_name in PHASE8_CONFIGS:
        base_config = PHASE8_CONFIGS[system_name]
    else:
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

    periods = sorted(US_DATA['periods'].keys())
    actual_ginis = [US_DATA['periods'][p]['gini_actual'] for p in periods]

    print("=" * 70)
    print("  US BACKTEST — 5 INEQUALITY MECHANISMS TEST")
    print("=" * 70)

    # ────────────────────────────────────────────────────────────
    # RUN 1: Baseline (ALL mechanisms OFF)
    # ────────────────────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print(f"  RUN 1: BASELINE — ALL 5 MECHANISMS OFF")
    print(f"{'─'*70}")

    no_inequality = {p: {} for p in periods}  # empty = all defaults (0/False)
    base_ginis, base_tax_gdps, base_gov_shares, base_details = \
        run_us_backtest("BASELINE (no mechs)", no_inequality, base_config)

    base_trend = classify_trend(base_ginis)

    # ────────────────────────────────────────────────────────────
    # RUN 2: Full (ALL 5 mechanisms ON with historical calibration)
    # ────────────────────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print(f"  RUN 2: FULL — ALL 5 MECHANISMS ON (historical)")
    print(f"{'─'*70}")

    # Union coverage declines linearly: 0.35 (1960) → 0.10 (2020)
    def linear_union_coverage(period_year):
        """Linear decline from 0.35 (1960) to 0.10 (2020)."""
        return 0.35 + (0.10 - 0.35) * (period_year - 1960) / (2020 - 1960)

    full_inequality = {}
    for p in periods:
        full_inequality[p] = {
            'skill_premium_growth': 0.015,        # SBTC 1.5%/year
            'union_coverage': round(linear_union_coverage(p), 4),
            'capital_income_share': 0.15,          # 15% profits to top 10%
            'import_competition': 0.20,            # moderate import exposure
            'use_progressive_tax': True,           # US 2020 bracket schedule
        }

    full_ginis, full_tax_gdps, full_gov_shares, full_details = \
        run_us_backtest("FULL (5 mechs ON)", full_inequality, base_config)

    full_trend = classify_trend(full_ginis)

    # ────────────────────────────────────────────────────────────
    # REPORT
    # ────────────────────────────────────────────────────────────
    period_labels = [f"{p}s" for p in periods]

    print(f"\n{'='*70}")
    print(f"  === US BACKTEST — INEQUALITY MECHANISMS TEST ===")
    print(f"{'='*70}")
    header = f"  {'':>20}  " + "  ".join(f"{l:>8}" for l in period_labels) + "    Trend"
    print(header)
    print(f"  {'─'*20}──" + "─" * 44)

    base_row = f"  {'BASELINE (no mechs):':>20}  " + \
               "  ".join(f"{g:>8.4f}" for g in base_ginis) + f"   {base_trend}"
    print(base_row)

    full_row = f"  {'FULL (5 mechs ON):':>20}  " + \
               "  ".join(f"{g:>8.4f}" for g in full_ginis) + f"   {full_trend}"
    print(full_row)

    actual_row = f"  {'ACTUAL US DATA:':>20}  " + \
                 "  ".join(f"{g:>8.4f}" for g in actual_ginis) + "   RISING"
    print(actual_row)

    # Improvement (how much closer to actual data compared to baseline)
    # Positive = closer to actual data (better)
    # Negative = further from actual data (worse)
    print(f"\n  IMPROVEMENT (Δ vs actual):")
    improvements = []
    for i, p in enumerate(periods):
        base_err = abs(base_ginis[i] - actual_ginis[i])
        full_err = abs(full_ginis[i] - actual_ginis[i])
        imp = base_err - full_err  # positive = improvement
        improvements.append(imp)
        print(f"    {period_labels[i]:>8}: baseline off by {base_err:+.4f}, "
              f"full off by {full_err:+.4f} → {'BETTER' if imp > 0 else 'WORSE' if imp < 0 else 'SAME'} ({imp:+.4f})")

    # Check: does full run show a RISING trend?
    trend_match_full = (full_trend == "RISING")
    direction_match = full_trend == "RISING"

    print(f"\n  TREND ANALYSIS:")
    print(f"    Baseline:  {base_trend}")
    print(f"    Full:      {full_trend}")
    print(f"    Actual:    RISING")
    print(f"    Direction matches actual? {'YES' if direction_match else 'NO'}")

    # Gini change from first to last period
    base_change = base_ginis[-1] - base_ginis[0]
    full_change = full_ginis[-1] - full_ginis[0]
    actual_change = actual_ginis[-1] - actual_ginis[0]

    print(f"\n  DELTA (2020−1960):")
    print(f"    Baseline:  {base_change:+.4f}")
    print(f"    Full:      {full_change:+.4f}")
    print(f"    Actual:    {actual_change:+.4f}")

    # ── Summary PASS/FAIL ──
    print(f"\n{'='*70}")
    if direction_match:
        print(f"  ✅ PASS — Full mechanisms produce RISING Gini (matches actual)")
    else:
        print(f"  ❌ FAIL — Full mechanisms still produce {full_trend} (not RISING)")
    print(f"{'='*70}")

    # ── Save JSON ──
    result = {
        'run_label': 'US Backtest — 5 Inequality Mechanisms',
        'periods': list(periods),
        'actual_ginis': actual_ginis,
        'baseline': {
            'ginis': base_ginis,
            'tax_gdp_pcts': base_tax_gdps,
            'gov_shares': base_gov_shares,
            'trend': base_trend,
            'period_details': base_details,
        },
        'full_mechanisms': {
            'ginis': full_ginis,
            'tax_gdp_pcts': full_tax_gdps,
            'gov_shares': full_gov_shares,
            'trend': full_trend,
            'period_details': full_details,
            'inequality_params_by_period': {
                str(p): full_inequality[p] for p in periods
            },
        },
        'analysis': {
            'baseline_trend': base_trend,
            'full_trend': full_trend,
            'actual_trend': 'RISING',
            'direction_matches_actual': direction_match,
            'pass_fail': 'PASS' if direction_match else 'FAIL',
            'delta_1960_2020_baseline': round(base_change, 4),
            'delta_1960_2020_full': round(full_change, 4),
            'delta_1960_2020_actual': round(actual_change, 4),
            'improvements_by_period': {
                str(periods[i]): round(improvements[i], 4)
                for i in range(len(periods))
            },
        },
    }

    output_path = os.path.join(out_dir, 'backtest_us_fix.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n  Saved: {output_path}")


if __name__ == '__main__':
    main()
