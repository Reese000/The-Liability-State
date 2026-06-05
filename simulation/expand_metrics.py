#!/usr/bin/env python3
"""Expanded metrics computation — 12 additional economic metrics from Phase 8.

Usage:
    python expand_metrics.py 2>&1 | head -40

Computes FLOW, STOCK, WELFARE, and SYSTEM metrics across all 11 systems
and 3 seeds, then outputs formatted results and saves to JSON.
"""

import sys, os, copy, json, time, logging
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS
from comparison_phase4 import (
    SEEDS, STEPS, REPORT_INTERVAL, HOURS_PER_STEP, LVT_ANNUAL_RATE,
    INVESTMENT_RATE, BUSINESS_WAGE_BILL, WAGE_VARIABILITY, ACCIDENT_PROBABILITY,
    TFP_TAX_ELASTICITY, LABOR_SUPPLY_ELASTICITY, ADMIN_OVERHEAD_BY_TAX, compute_gini,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")


# ─── Per-step metrics tracking wrapper —──────────────────────────────────────

def run_phase8_collect(workers, retirees, businesses, seed, config):
    """Run Phase 8 simulation with per-step tracking for expanded metrics.

    Replicates the logic of run_phase8() while collecting per-step data
    needed to compute all 12 expanded economic metrics.
    """
    workers = [dict(w) for w in workers]
    retirees = [dict(r) for r in retirees]
    businesses = [dict(b) for b in businesses]
    rst = copy.deepcopy(config)

    name = rst.get('system_name', 'Phase8')
    C = rst.get

    wire_lvt_evasion = C('wire_lvt_evasion', False)
    use_families = C('use_families', False)

    # Children
    children = []
    if use_families:
        rng_c = np.random.RandomState(seed)
        wids_ = [w['id'] for w in workers]
        for i in range(20):
            children.append({'id': f'c{seed}_{i:03d}',
                             'parent_id': wids_[rng_c.randint(0, len(wids_))],
                             'cash': 0.0, 'land': 0.0})
    child_ids = [c['id'] for c in children]

    # LVT evasion controller
    lvt_evasion_controller = None
    if wire_lvt_evasion:
        try:
            from src.adversarial.controller import StrategyController, LvtEvasion
            lvt_evasion_controller = StrategyController(strategies=[LvtEvasion()])
        except ImportError:
            pass

    rst['system_name'] = name
    tx = C('tax_type', 'lvt')
    lvt_r = C('lvt_rate', LVT_ANNUAL_RATE)
    inc_tx = C('income_tax_rate', 0.0)
    corp_tx = C('corp_tax_rate', 0.0)
    ua = C('use_adversarial', False)
    up = C('use_pooled_insurance', False)
    ue = C('use_events', False)
    uwc = C('use_worker_coop', False)
    wrc = C('wage_ratio_cap', 5)
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
    bnk = max(0, float(C('banking_multiplier', 0)))
    irt = max(0, float(C('interest_rate', 0.005)))
    ihr = min(1, max(0, float(C('inheritance_rate', 0))))
    enq = min(1, max(0, float(C('enforcement_quality', 1))))
    dpr = min(1, max(0, float(C('detection_probability_base', 0.5))))
    inf = min(1, max(0, float(C('information_asymmetry', 0))))
    min_wage = float(C('minimum_wage', 0.0))
    const_amend_rate = float(C('constitutional_amendment_rate', 0.0))

    # Phase 8a params
    labor_elast = float(C('labor_supply_elasticity', LABOR_SUPPLY_ELASTICITY))
    money_create = float(C('money_creation_rate', 0.0))
    tfp_elast = float(C('TFP_TAX_ELASTICITY', TFP_TAX_ELASTICITY))
    # Phase 8b sectoral params
    health_share = float(C('healthcare_gdp_share', 0.0))
    educ_share = float(C('education_gdp_share', 0.0))
    carbon_tx = float(C('carbon_tax_rate', 0.0))
    elite_cap = float(C('elite_capture_intensity', 0.0))

    rng = np.random.RandomState(seed)
    lvt_m = (lvt_r / 12) if tx == 'lvt' else 0.0

    # Balances
    bank_reserve = max(0, float(C('bank_initial_reserve', 0)))
    bal = {e['id']: e['cash'] for e in workers + retirees + businesses}
    for c in children:
        bal[c['id']] = c['cash']
    bal.update({'sys': 500_000_000, 'trust': 0, 'bank': bank_reserve})
    wid = [w['id'] for w in workers]
    rid = [r['id'] for r in retirees]
    all_c = wid + rid + (child_ids if use_families else [])
    wland = {w['id']: w['land'] for w in workers}
    rland = {r['id']: r['land'] for r in retirees}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}
    cum_tr = {a: 0.0 for a in all_c}
    hist = {'gini': [], 'wealth': [], 'wmin': [], 'wmean': [], 'div': []}
    pc = 0.0
    consumption_stream = []
    educ_growth = educ_share * 0.08

    # ─── Per-step tracking accumulators ─────────────────────────────────
    step_wages_list = []
    step_profits_list = []
    step_taxes_list = []
    step_dividends_list = []
    step_welfare_list = []
    step_courts_list = []
    step_lr_list = []       # mean labor ratio per step
    step_capital_list = []
    step_consumption_list = []

    def xf(fr, to, mech, amt):
        if amt <= 0 or fr not in bal or to not in bal:
            return
        amt = min(amt, bal[fr])
        if amt <= 0:
            return
        bal[fr] -= amt
        bal[to] += amt

    # ─── Simulation loop (same logic as run_phase8, with tracking) ──────
    for step in range(1, STEPS + 1):
        try:
            dmult = 0.85 if (ue and step == STEPS // 4) else 1.0

            twb = sum(w['monthly'] for w in workers)
            hc_step = twb * health_share / STEPS
            educ_inv_step = twb * educ_share / STEPS

            # ── 1. Wages ──────────────────────────────────────────────
            sw = {}
            lr_vals = []
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
                inc = w['monthly'] * lr * rng.uniform(*WAGE_VARIABILITY) * un_p
                if min_wage > 0:
                    inc = max(inc, min_wage)
                if inc > 0 and bal['sys'] >= inc:
                    xf('sys', w['id'], 'wage', inc)
                    sw[w['id']] = inc
                if health_share > 0 and hc_step > 0:
                    prem_share = hc_step / max(twb, 1)
                    prem = inc * prem_share
                    if prem > 0 and bal.get(w['id'], 0) >= prem:
                        xf(w['id'], 'sys', 'health_prem', prem)

                lr_vals.append(lr)

            step_wages = sum(sw.values()) if sw else 0

            # ── 2. Business ─────────────────────────────────────────
            tc = sum(b['capital'] for b in businesses) or 1
            step_gross_profit = 0.0
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
                step_gross_profit += prof  # after carbon tax, before corp tax

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
                    if uwc and sw:
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

            # ── 3. Insurance ─────────────────────────────────────────
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

            # ── 5. Tax ──────────────────────────────────────────────
            tt = 0.0
            clk = 1 - corr * 0.4

            def _evasion_factor(ad):
                if not wire_lvt_evasion or lvt_evasion_controller is None:
                    return 1.0
                ev = 0.15 + ad.get('concealment', 0) * 0.20
                return max(0.0, 1.0 - ev * (1.0 - ad.get('honesty', 0.5)))

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
                for el, lm in [(workers, wland), (retirees, rland), (businesses, bland)]:
                    for e in el:
                        d = lm[e['id']] * lvt_m * clk * _evasion_factor(e)
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
            elif uv:
                for w in workers:
                    v = sw.get(w['id'], 0) * vat_r * clk
                    if v > 0:
                        xf(w['id'], 'sys', 'vat', v)
                        tt += v

            # ── 6. Bloat ────────────────────────────────────────────
            ac = tt * blt
            if ac > 0:
                xf('sys', 'trust', 'bloat', ac)

            # ── 7. Dividend ─────────────────────────────────────────
            pc = 0.0
            step_dividends = 0.0
            if tx == 'lvt' and tt > 0:
                nd = tt * (1 - blt)
                pc = nd * 0.9 / len(all_c) if nd > 0 else 0
                if pc > 0:
                    for c in all_c:
                        xf('trust', c, 'div', pc)
                        cum_tr[c] += pc
                    step_dividends = pc * len(all_c)

            # ── 8. Courts ───────────────────────────────────────────
            elt = ACCIDENT_PROBABILITY * enq
            step_courts = 0.0
            for b in businesses:
                if rng.random() < elt:
                    pl = rng.choice(wid)
                    amt = rng.uniform(1000, 20000)
                    if rng.random() < enq:
                        pay = min(amt, bal.get(b['id'], 0))
                        if pay > 0:
                            xf(b['id'], pl, 'judge', pay)
                            step_courts += pay

            # ── 9. Welfare ──────────────────────────────────────────
            step_welfare = 0.0
            if tx == 'income' and inc_tx > 0:
                wp = tt * wel_r * (1 - blt)
                if wp > 0:
                    pw = wp / len(all_c)
                    for c in all_c:
                        xf('sys', c, 'welf', pw)
                        cum_tr[c] += pw
                    step_welfare = wp

            # ── 10. CPF ────────────────────────────────────────────
            if cpf_r > 0:
                cpf_t = sum(sw.get(w['id'], 0) * cpf_r for w in workers)
                if cpf_t > 0:
                    pcpf = cpf_t / len(all_c)
                    for a in all_c:
                        xf('sys', a, 'cpf', pcpf)

            # ── 11. Banking ─────────────────────────────────────────
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
                bal['sys'] += total_deposits * money_create / STEPS

            # ── 12. Enforcement ─────────────────────────────────────
            for w in workers:
                if corr > 0 and rng.random() < dpr * enq:
                    pen = w['monthly'] * corr * 0.2 * (1 - enq)
                    if pen > 0 and bal.get(w['id'], 0) >= pen:
                        xf(w['id'], 'sys', 'pen', pen)

            # ── 13. Constitutional amendment ────────────────────────
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

            # Track consumption for CRRA
            step_cons = sum(max(0, sw.get(w['id'], 0) * 0.8) for w in workers)
            consumption_stream.append(step_cons)

            # ─── Record per-step tracking data ────────────────────
            step_wages_list.append(step_wages)
            step_profits_list.append(step_gross_profit)
            step_taxes_list.append(tt)
            step_dividends_list.append(step_dividends)
            step_welfare_list.append(step_welfare)
            step_courts_list.append(step_courts)
            step_lr_list.append(np.mean(lr_vals) if lr_vals else 1.0)
            step_capital_list.append(tc)
            step_consumption_list.append(step_cons)

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
            logging.getLogger(f'p8c_{name[:12]}').error("Step %d: %s", step, e)
            break

    # ─── Post-sim inheritance ───────────────────────────────────────────
    if ihr > 0:
        for w in workers:
            bq = bal.get(w['id'], 0) * ihr
            pw = bq / len(wid) if wid else 0
            if pw > 0:
                for w_id in wid:
                    xf(w['id'], w_id, 'inherit', pw)

    # ─── Worker wealth at end (for stock metrics) ──────────────────────
    ww = [bal[i] for i in wid if i in bal]
    w_sorted = sorted(ww) if ww else [0]

    # ─── Compute all 12 expanded metrics ──────────────────────────────

    # Flow metrics (average per-step, then annualised by ×12)
    avg_step_wages = np.mean(step_wages_list) if step_wages_list else 0.0
    avg_step_profits = np.mean(step_profits_list) if step_profits_list else 0.0
    avg_step_taxes = np.mean(step_taxes_list) if step_taxes_list else 0.0
    avg_step_dividends = np.mean(step_dividends_list) if step_dividends_list else 0.0
    avg_step_welfare = np.mean(step_welfare_list) if step_welfare_list else 0.0
    avg_step_courts = np.mean(step_courts_list) if step_courts_list else 0.0
    avg_step_govt = avg_step_dividends + avg_step_welfare + avg_step_courts
    avg_step_consumption = np.mean(step_consumption_list) if step_consumption_list else 0.0
    avg_step_lr = np.mean(step_lr_list) if step_lr_list else 1.0

    # Annualization factor: 12 steps = 1 reporting year (REPORT_INTERVAL)
    ANNUAL_FACTOR = 12

    # 1. GDP = total wages + total business profits + government spending
    gdp_per_step = avg_step_wages + avg_step_profits + avg_step_govt
    gdp_annual = gdp_per_step * ANNUAL_FACTOR

    # 2. Tax-to-GDP ratio
    tax_annual = avg_step_taxes * ANNUAL_FACTOR
    tax_to_gdp = tax_annual / gdp_annual if gdp_annual > 0 else 0.0

    # 3. Consumption = total wages * 0.8
    consumption_annual = avg_step_consumption * ANNUAL_FACTOR

    # 4. Saving rate = (total_income - total_consumption) / total_income
    avg_step_income = (avg_step_wages + avg_step_dividends
                       + avg_step_welfare + avg_step_courts)
    saving_rate = ((avg_step_income - avg_step_consumption) / avg_step_income
                   if avg_step_income > 0 else 0.0)

    # 5. Labor share = total wages / (total wages + total business profits)
    # Capped at 100% — wages cannot exceed total output
    ws = avg_step_wages + avg_step_profits
    labor_share = min(1.0, avg_step_wages / ws) if ws > 0 else 0.0

    # Stock metrics (end-of-simulation)

    # 6. Poverty rate = % workers with wealth < 50% of median wealth
    median_wealth = np.median(w_sorted) if w_sorted else 0.0
    poverty_rate = (np.mean([float(w < 0.5 * median_wealth) for w in w_sorted])
                    if median_wealth > 0 else 0.0)

    # 7. P90/P10 ratio
    if len(w_sorted) > 1:
        n = len(w_sorted)
        p90 = np.percentile(w_sorted, 90)
        p10 = np.percentile(w_sorted, 10)
        p90_p10 = p90 / p10 if p10 > 0 else float('inf')
    else:
        p90_p10 = 0.0

    # 8. Capital-to-income ratio (Piketty's β) = total capital / total annual wages
    total_capital = sum(b['capital'] for b in businesses)
    annual_wages = avg_step_wages * ANNUAL_FACTOR
    beta = total_capital / annual_wages if annual_wages > 0 else 0.0

    # Welfare metrics

    # 9. Leisure index = 1 - (avg hours / full time)
    leisure_index = 1.0 - avg_step_lr

    # 10. Consumption per capita = total consumption / population
    total_pop = len(workers) + len(retirees)
    consumption_per_capita = consumption_annual / total_pop if total_pop > 0 else 0.0

    # System metrics

    # 11. Government share of economy = govt spending / GDP
    govt_share = (avg_step_govt / gdp_per_step if gdp_per_step > 0 else 0.0)

    # 12. Wealth-to-income ratio = total wealth / total annual income
    total_wealth = sum(bal.values())
    annual_income = avg_step_income * ANNUAL_FACTOR
    wealth_to_income = total_wealth / annual_income if annual_income > 0 else 0.0

    # Standard metrics for cross-check
    w_mean = np.mean(ww) if ww else 0.0
    w_gini = compute_gini(ww) if ww else 0.0

    return {
        'name': name,
        # Standard fields
        'w_mean': round(w_mean, 2),
        'gini': round(w_gini, 4),
        'steps': STEPS,
        # ── Expanded metrics ──
        # Flow
        'gdp': round(gdp_annual, 2),
        'tax_to_gdp': round(tax_to_gdp, 4),
        'consumption': round(consumption_annual, 2),
        'saving_rate': round(saving_rate, 4),
        'labor_share': round(labor_share, 4),
        # Stock
        'poverty_rate': round(poverty_rate, 4),
        'p90_p10_ratio': round(p90_p10, 4),
        'capital_to_income_beta': round(beta, 4),
        # Welfare
        'leisure_index': round(leisure_index, 4),
        'consumption_per_capita': round(consumption_per_capita, 2),
        # System
        'govt_share': round(govt_share, 4),
        'wealth_to_income': round(wealth_to_income, 4),
        # Raw per-step averages (for verification)
        '_avg_step_wages': round(avg_step_wages, 2),
        '_avg_step_profits': round(avg_step_profits, 2),
        '_avg_step_taxes': round(avg_step_taxes, 2),
        '_avg_step_govt': round(avg_step_govt, 2),
        '_avg_step_lr': round(avg_step_lr, 4),
        '_total_capital': round(total_capital, 2),
        '_total_wealth': round(total_wealth, 2),
        '_median_wealth': round(median_wealth, 2),
    }


# ─── Formatting helpers ────────────────────────────────────────────────────

def fmt_money(val):
    """Format value as $X,XXX,XXX (or $X,XXX if smaller)."""
    if val >= 1_000_000:
        return f"${val:,.0f}"
    elif val >= 1_000:
        return f"${val:,.0f}"
    else:
        return f"${val:.2f}"


def fmt_pct(val):
    """Format decimal as XX.X%."""
    return f"{val * 100:.1f}%"


def fmt_ratio(val):
    """Format ratio as X.XX."""
    return f"{val:.2f}"


def format_system_metrics(name, results_list):
    """Average results across seeds and produce formatted output."""
    keys = [
        'gdp', 'tax_to_gdp', 'consumption', 'saving_rate', 'labor_share',
        'poverty_rate', 'p90_p10_ratio', 'capital_to_income_beta',
        'leisure_index', 'consumption_per_capita',
        'govt_share', 'wealth_to_income',
    ]
    avg = {}
    for k in keys:
        vals = [r[k] for r in results_list]
        avg[k] = np.mean(vals)

    lines = []
    lines.append(f"  FLOW METRICS:")
    lines.append(f"    GDP: {fmt_money(avg['gdp'])}")
    lines.append(f"    Tax-to-GDP: {fmt_pct(avg['tax_to_gdp'])}")
    lines.append(f"    Consumption: {fmt_money(avg['consumption'])}")
    lines.append(f"    Saving Rate: {fmt_pct(avg['saving_rate'])}")
    lines.append(f"    Labor Share: {fmt_pct(avg['labor_share'])}")
    lines.append(f"  STOCK METRICS:")
    lines.append(f"    Poverty Rate: {fmt_pct(avg['poverty_rate'])}")
    lines.append(f"    P90/P10 Ratio: {fmt_ratio(avg['p90_p10_ratio'])}")
    lines.append(f"    Capital-to-Income (β): {fmt_ratio(avg['capital_to_income_beta'])}")
    lines.append(f"  WELFARE:")
    lines.append(f"    Leisure Index: {fmt_ratio(avg['leisure_index'])}")
    lines.append(f"    Consumption per Capita: {fmt_money(avg['consumption_per_capita'])}")
    lines.append(f"  SYSTEM:")
    lines.append(f"    Government Share: {fmt_pct(avg['govt_share'])}")
    lines.append(f"    Wealth-to-Income: {fmt_ratio(avg['wealth_to_income'])}")

    return '\n'.join(lines), avg


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    seeds = [1, 2, 3]  # 3 seeds as specified
    configs = list(PHASE8_CONFIGS.values())
    t0 = time.time()

    print(f"Phase8 Expanded Metrics: {len(seeds)} seeds × {len(configs)} systems"
          f" = {len(seeds) * len(configs)} sims")

    all_results = {}
    summary_data = {}

    for cfg in configs:
        name = cfg['system_name']
        sys_results = []
        print(f"\n  Running {name}...", end=' ', flush=True)
        for seed in seeds:
            pop = gen_population(seed)
            r = run_phase8_collect(*pop, seed, cfg)
            sys_results.append(r)
        all_results[name] = sys_results
        print(f"Gini={np.mean([r['gini'] for r in sys_results]):.4f}"
              f" GDP={fmt_money(np.mean([r['gdp'] for r in sys_results]))}")

    # ─── Output ───────────────────────────────────────────────────────
    print(f"\n{'='*120}")
    print("EXPANDED METRICS")
    print(f"{'='*120}")

    for name in all_results:
        fmt_str, avg = format_system_metrics(name, all_results[name])
        summary_data[name] = avg
        print(f"\n=== {name} ===")
        print(fmt_str)

    print(f"\n{'='*120}")
    print(f"Total time: {time.time() - t0:.0f}s")

    # ─── Save ────────────────────────────────────────────────────────
    out_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'expanded_metrics.json')
    # Save per-seed raw results + averaged summary
    json_out = {
        'systems': all_results,
        'summary': summary_data,
    }
    json.dump(json_out, open(out_path, 'w'), indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == '__main__':
    main()
