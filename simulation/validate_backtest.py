#!/usr/bin/env python3
"""Historical backtesting of US_Style model 1960-2020.

Runs 4 chained calibration periods (1960→1980→2000→2020), each 120 steps,
comparing wealth/Gini trajectories to stylized US historical facts.

Usage:
    python validate_backtest.py

Output:
    stdout: text report
    output/backtest_results.json: full results
"""

import sys, os, copy, json, time, math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from comparison_phase4 import (
    STEPS as _STEPS, REPORT_INTERVAL, HOURS_PER_STEP,
    LVT_ANNUAL_RATE, LVT_MONTHLY_RATE, INVESTMENT_RATE, BUSINESS_WAGE_BILL,
    WAGE_VARIABILITY, ACCIDENT_PROBABILITY, TFP_TAX_ELASTICITY, LABOR_SUPPLY_ELASTICITY,
    ADMIN_OVERHEAD_BY_TAX, compute_gini,
)
from comparison_phase6 import gen_population, PHASE6_CONFIGS

# ─── Calibration points (stylized US historical data) ──────
CALIBRATIONS = [
    {"label": "1960", "income_tax_rate": 0.20, "corp_tax_rate": 0.52, "welfare_rate": 0.03},
    {"label": "1980", "income_tax_rate": 0.28, "corp_tax_rate": 0.46, "welfare_rate": 0.08},
    {"label": "2000", "income_tax_rate": 0.25, "corp_tax_rate": 0.35, "welfare_rate": 0.10},
    {"label": "2020", "income_tax_rate": 0.22, "corp_tax_rate": 0.21, "welfare_rate": 0.14},
]
STEPS_PER_PERIOD = 120
TOTAL_STEPS = STEPS_PER_PERIOD * len(CALIBRATIONS)
SEED = 42

# Stylized US facts
STYLIZED_GDP_GROWTH = 3.0   # GDP grew ~3x 1960-2020
STYLIZED_GINI_START = 0.35  # Approximate US Gini in 1960
STYLIZED_GINI_END = 0.48    # Approximate US Gini in 2020


def run_backtest():
    """Run chained backtest across all calibration periods.

    Returns dict with full trajectory and per-period results.
    """
    t0 = time.time()

    # ─── Base config: US_Style ──────────────────────────────
    base_cfg = copy.deepcopy(PHASE6_CONFIGS['US_Style'])

    # ─── Generate initial population ─────────────────────────
    workers, retirees, businesses = gen_population(SEED)
    # We'll maintain mutable copies for chaining
    workers = [dict(w) for w in workers]
    retirees = [dict(r) for r in retirees]
    businesses = [dict(b) for b in businesses]

    # Agent lookup by id
    wid = [w['id'] for w in workers]
    rid = [r['id'] for r in retirees]
    bid = [b['id'] for b in businesses]
    all_c = wid + rid

    # ─── Simulation state ────────────────────────────────────
    rng = np.random.RandomState(SEED)

    # Land values (fixed per agent throughout)
    wland = {w['id']: w['land'] for w in workers}
    rland = {r['id']: r['land'] for r in retirees}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}

    # Cumulative transfers (for income effect)
    cum_tr = {a: 0.0 for a in all_c}

    # Trajectory recording
    full_trajectory = {
        'step': [], 'wealth': [], 'gini': [], 'w_mean': [],
        'period': [], 'calibration': [],
    }

    periods = []

    # ─── Helper: transfer funds between accounts ─────────────
    def xf(bal, fr, to, mech, amt):
        if amt <= 0 or fr not in bal or to not in bal:
            return
        amt = min(amt, bal[fr])
        if amt <= 0:
            return
        bal[fr] -= amt
        bal[to] += amt

    # ─── Run each calibration period ─────────────────────────
    period_start_wealth = 0.0
    period_start_gini = 0.0

    for period_idx, cal in enumerate(CALIBRATIONS):
        label = cal['label']
        inc_tx = cal['income_tax_rate']
        corp_tx = cal['corp_tax_rate']
        wel_r = cal['welfare_rate']

        # Build config for this period (US_Style base + calibration overrides)
        cfg = copy.deepcopy(base_cfg)
        cfg['income_tax_rate'] = inc_tx
        cfg['corp_tax_rate'] = corp_tx
        cfg['welfare_rate'] = wel_r

        # Extract config values (same pattern as run_phase6)
        C = cfg.get
        system_name = C('system_name', 'US_Style')
        tx = C('tax_type', 'income')
        lvt_r = C('lvt_rate', LVT_ANNUAL_RATE)
        ua = C('use_adversarial', False)
        up = C('use_pooled_insurance', False)
        ue = C('use_events', False)
        uwc = C('use_worker_coop', False)
        wrc = C('wage_ratio_cap', 5)
        uv = C('use_vat', False)
        vat_r = C('vat_rate', 0.20)
        un_p = C('union_premium', 1.0)
        cpf_r = C('cpf_rate', 0.0)

        # Phase 4 dynamics
        corr = max(0, min(1, float(C('corruption_level', 0.15))))
        ie = max(0, min(.15, float(C('income_effect_labor', 0.08))))
        blt = max(0, float(C('admin_overhead', 0.08)))
        eos = max(0, float(C('economies_of_scale', 0.08)))
        mmm = max(1, float(C('monopoly_markup_max', 1.4)))
        bnk = max(0, float(C('banking_multiplier', 3)))
        irt = max(0, float(C('interest_rate', 0.003)))
        ihr = min(1, max(0, float(C('inheritance_rate', 0.25))))
        enq = min(1, max(0, float(C('enforcement_quality', 0.7))))
        dpr = min(1, max(0, float(C('detection_probability_base', 0.5))))
        inf = min(1, max(0, float(C('information_asymmetry', 0.35))))
        min_wage = float(C('minimum_wage', 1160.0))

        lvt_m = 0.0  # US_Style uses income tax, not LVT

        # ─── Initialize balance sheet ────────────────────────
        bal = {}
        for w in workers:
            bal[w['id']] = w.get('cash', 0)
        for r in retirees:
            bal[r['id']] = r.get('cash', 0)
        for b in businesses:
            bal[b['id']] = b.get('cash', 0)
        bal['sys'] = 500_000_000
        bal['trust'] = 0
        bal['bank'] = max(0, float(C('bank_initial_reserve', 0)))

        # ─── Per-period trajectory ───────────────────────────
        period_traj = {'step': [], 'wealth': [], 'gini': [], 'w_mean': []}

        # ─── Main loop for this period ───────────────────────
        for step in range(1, STEPS_PER_PERIOD + 1):
            global_step = period_idx * STEPS_PER_PERIOD + step

            try:
                dmult = 1.0  # No event shock in backtest

                # ── 1. Wages + income effect + minimum wage ──
                sw = {}
                for w in workers:
                    after = w['hourly'] * (1 - inc_tx) if tx == 'income' else w['hourly']
                    lr = (after / w['hourly']) ** LABOR_SUPPLY_ELASTICITY if w['hourly'] > 0 else 1.0
                    if ie > 0:
                        ti = cum_tr.get(w['id'], 0)
                        bi = w['monthly'] * lr
                        if bi + ti > 0:
                            lr *= max(.5, 1 - ie * ti / (bi + ti))
                    inc = w['monthly'] * lr * rng.uniform(*WAGE_VARIABILITY) * un_p
                    if min_wage > 0:
                        inc = max(inc, min_wage)
                    if inc > 0 and bal['sys'] >= inc:
                        xf(bal, 'sys', w['id'], 'wage', inc)
                        sw[w['id']] = inc

                # ── 2. Business + monopolization ─────────────
                tc = sum(b['capital'] for b in businesses) or 1
                for b in businesses:
                    sb = 0.0
                    if eos > 0 and b['capital'] > 50000:
                        sb = eos * np.log(b['capital'] / 50000)
                    etfp = b['tfp'] * (1 + sb)
                    ms = b['capital'] / tc
                    mm = 1 + (mmm - 1) * ms
                    rev = etfp * (b['capital'] ** 0.3) * (8 ** 0.7) * mm * dmult
                    prof = rev - BUSINESS_WAGE_BILL
                    if prof > 0:
                        tax = prof * corp_tx if tx == 'income' and corp_tx > 0 else 0
                        at = prof - tax
                        if tax > 0:
                            xf(bal, b['id'], 'sys', 'ctax', tax)
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
                                        wid_, wg = w['id'], sw.get(w['id'], 0)
                                        act = min(cp * (wg / tw), max(0, mt - wg))
                                        if act > 0.01:
                                            xf(bal, b['id'], wid_, 'coop', act)
                        else:
                            ret = at - inv
                            if ret > 0:
                                xf(bal, 'sys', b['id'], 'ret', ret)

                # ── 3. Insurance + info asymmetry ────────────
                epm, tuf = 1 + inf * 0.5, 1 - inf * 0.3
                for w in workers:
                    if rng.random() < tuf:
                        prem = w['monthly'] * 0.05 * epm
                        if bal.get(w['id'], 0) >= prem:
                            xf(bal, w['id'], 'sys', 'prem', prem)
                            if rng.random() < ACCIDENT_PROBABILITY:
                                cl = rng.uniform(1000, 20000)
                                po = min(cl, bal['sys'])
                                if po > 0:
                                    xf(bal, 'sys', w['id'], 'claim', po)

                # ── 4. Adversarial (placeholder) ─────────────
                if ua:
                    pass

                # ── 5. Tax (income tax) ──────────────────────
                tt = 0.0
                clk = 1 - corr * 0.4

                if tx == 'income':
                    for w in workers:
                        t = sw.get(w['id'], 0) * inc_tx * clk
                        if t > 0:
                            xf(bal, w['id'], 'sys', 'itax', t)
                            tt += t
                elif tx == 'lvt':
                    for el, lm in [(workers, wland), (retirees, rland), (businesses, bland)]:
                        for e in el:
                            d = lm[e['id']] * lvt_m * clk
                            if d > 0 and bal.get(e['id'], 0) >= d * 0.5:
                                c = min(d, bal[e['id']])
                                xf(bal, e['id'], 'trust', 'lvt', c)
                                tt += c
                elif uv:
                    for w in workers:
                        v = sw.get(w['id'], 0) * vat_r * clk
                        if v > 0:
                            xf(bal, w['id'], 'sys', 'vat', v)
                            tt += v

                # ── 6. Bloat ─────────────────────────────────
                ac = tt * blt
                if ac > 0:
                    xf(bal, 'sys', 'trust', 'bloat', ac)

                # ── 7. Dividend (only for LVT) ───────────────
                pc = 0.0
                if tx == 'lvt' and tt > 0:
                    nd = tt * (1 - blt)
                    pc = nd * 0.9 / len(all_c) if nd > 0 else 0
                    if pc > 0:
                        for c in all_c:
                            xf(bal, 'trust', c, 'div', pc)
                            cum_tr[c] += pc

                # ── 8. Courts + enforcement ──────────────────
                elt = ACCIDENT_PROBABILITY * enq
                for b in businesses:
                    if rng.random() < elt:
                        pl = rng.choice(wid)
                        amt = rng.uniform(1000, 20000)
                        if rng.random() < enq:
                            pay = min(amt, bal.get(b['id'], 0))
                            if pay > 0:
                                xf(bal, b['id'], pl, 'judge', pay)

                # ── 9. Welfare (from income tax) ─────────────
                if tx == 'income' and inc_tx > 0:
                    wp = tt * wel_r * (1 - blt)
                    if wp > 0:
                        pw = wp / len(all_c)
                        for c in all_c:
                            xf(bal, 'sys', c, 'welf', pw)
                            cum_tr[c] += pw

                # ── 10. CPF ──────────────────────────────────
                if cpf_r > 0:
                    cpf_t = sum(sw.get(w['id'], 0) * cpf_r for w in workers)
                    if cpf_t > 0:
                        pcpf = cpf_t / len(all_c)
                        for a in all_c:
                            xf(bal, 'sys', a, 'cpf', pcpf)

                # ── 11. Banking ──────────────────────────────
                if bnk > 0:
                    db = sum(bal.get(a, 0) * 0.1 for a in all_c)
                    for a in all_c:
                        ip = bal.get(a, 0) * 0.1 * irt
                        if ip > 0 and bal['bank'] >= ip:
                            xf(bal, 'bank', a, 'int', ip)
                    lp = db * bnk * 0.01
                    for b in businesses:
                        cs = b['capital'] / tc
                        loan = lp * cs
                        if loan > 0 and bal['bank'] >= loan:
                            xf(bal, 'bank', b['id'], 'loan', loan)
                            b['capital'] += loan * 0.5
                            bal['bank'] += loan * 0.02

                # ── 12. Enforcement ──────────────────────────
                for w in workers:
                    if corr > 0 and rng.random() < dpr * enq:
                        pen = w['monthly'] * corr * 0.2 * (1 - enq)
                        if pen > 0 and bal.get(w['id'], 0) >= pen:
                            xf(bal, w['id'], 'sys', 'pen', pen)

                # ── Record trajectory ────────────────────────
                ww = [bal[i] for i in wid if i in bal]
                if ww:
                    gini_val = compute_gini(ww)
                    wealth_val = sum(bal.values())
                    wmean_val = float(np.mean(ww))

                    full_trajectory['step'].append(global_step)
                    full_trajectory['wealth'].append(wealth_val)
                    full_trajectory['gini'].append(gini_val)
                    full_trajectory['w_mean'].append(wmean_val)
                    full_trajectory['period'].append(period_idx)
                    full_trajectory['calibration'].append(label)

                    period_traj['step'].append(step)
                    period_traj['wealth'].append(wealth_val)
                    period_traj['gini'].append(gini_val)
                    period_traj['w_mean'].append(wmean_val)

            except Exception as e:
                print(f"  ERROR at period {label}, step {step}: {e}")
                break

        # ─── Post-period: Inheritance ────────────────────────
        if ihr > 0:
            for w in workers:
                bq = bal.get(w['id'], 0) * ihr
                pw = bq / len(wid) if wid else 0
                if pw > 0:
                    for w_id in wid:
                        xf(bal, w['id'], w_id, 'inherit', pw)

        # ─── Compute final period stats ──────────────────────
        ww_final = [bal[i] for i in wid if i in bal]
        final_gini = compute_gini(ww_final) if ww_final else 0
        final_wealth = sum(bal.values())
        final_w_mean = float(np.mean(ww_final)) if ww_final else 0

        # ─── Update agent cash for next period (chaining!) ──
        for w in workers:
            w['cash'] = bal.get(w['id'], 0)
        for r in retirees:
            r['cash'] = bal.get(r['id'], 0)
        for b in businesses:
            b['cash'] = bal.get(b['id'], 0)

        periods.append({
            'label': label,
            'config': {'income_tax_rate': inc_tx, 'corp_tax_rate': corp_tx,
                       'welfare_rate': wel_r},
            'final': {'wealth': round(final_wealth, 2),
                      'gini': round(final_gini, 4),
                      'w_mean': round(final_w_mean, 2)},
            'trajectory': {k: [float(x) for x in v]
                           for k, v in period_traj.items()},
        })

        print(f"  {label}: inc_tx={inc_tx:.2f} corp_tx={corp_tx:.2f}"
              f" wel={wel_r:.2f} → G={final_gini:.4f} $W={final_wealth:>12,.0f}"
              f" $M={final_w_mean:>8,.0f}")

    # ─── Overall assessment ──────────────────────────────────
    initial_wealth = full_trajectory['wealth'][0] if full_trajectory['wealth'] else 0
    final_wealth_total = full_trajectory['wealth'][-1] if full_trajectory['wealth'] else 0
    initial_gini = full_trajectory['gini'][0] if full_trajectory['gini'] else 0
    final_gini_total = full_trajectory['gini'][-1] if full_trajectory['gini'] else 0

    wealth_ratio = final_wealth_total / initial_wealth if initial_wealth > 0 else 0
    gini_delta = final_gini_total - initial_gini

    rising_wealth = final_wealth_total > initial_wealth
    rising_gini = final_gini_total > initial_gini

    elapsed = time.time() - t0

    # ─── Print report ────────────────────────────────────────
    print()
    print("=" * 90)
    print("  US HISTORICAL BACKTEST — 1960 TO 2020")
    print("=" * 90)
    print()
    print(f"  {'Period':<8} {'IncTx':>6} {'CorpTx':>6} {'Welfare':>8}  "
          f"{'Final Wealth':>14} {'Final Gini':>10} {'Mean$':>10}")
    print(f"  {'-'*8} {'-'*6} {'-'*6} {'-'*8}  {'-'*14} {'-'*10} {'-'*10}")
    for p in periods:
        print(f"  {p['label']:<8} {p['config']['income_tax_rate']:>6.2f} "
              f"{p['config']['corp_tax_rate']:>6.2f} "
              f"{p['config']['welfare_rate']:>8.2f}  "
              f"${p['final']['wealth']:>12,.0f}  "
              f"{p['final']['gini']:>8.4f}   "
              f"${p['final']['w_mean']:>8,.0f}")
    print()
    print(f"  Full trajectory: {len(full_trajectory['step'])} observations "
          f"over {TOTAL_STEPS} steps")
    print()
    print(f"  ── Comparison to Stylized US Facts ──")
    print(f"  Initial wealth (step 1):  ${initial_wealth:>12,.0f}")
    print(f"  Final wealth (step {TOTAL_STEPS}):   ${final_wealth_total:>12,.0f}")
    print(f"  Wealth ratio:             {wealth_ratio:>8.2f}×  "
          f"(stylized US GDP: ~{STYLIZED_GDP_GROWTH}×)")
    if abs(wealth_ratio - STYLIZED_GDP_GROWTH) < 1.0:
        print(f"  ✓ Wealth ratio within range of stylized fact (~{STYLIZED_GDP_GROWTH}×)")
    else:
        print(f"  Δ Wealth ratio differs from stylized fact ({wealth_ratio:.2f}× vs ~{STYLIZED_GDP_GROWTH}×)")
    print()
    print(f"  Initial Gini:  {initial_gini:.4f}  (stylized US 1960: ~{STYLIZED_GINI_START})")
    print(f"  Final Gini:    {final_gini_total:.4f}  (stylized US 2020: ~{STYLIZED_GINI_END})")
    print(f"  Gini Δ:        {gini_delta:+.4f}  (stylized Δ: +{STYLIZED_GINI_END - STYLIZED_GINI_START:.2f})")
    if abs(gini_delta - (STYLIZED_GINI_END - STYLIZED_GINI_START)) < 0.1:
        print(f"  ✓ Gini rise consistent with stylized facts")
    else:
        print(f"  Δ Gini change differs from stylized fact")
    print()
    print(f"  ── Pass/Fail Assessment ──")
    print(f"  Rising wealth over 60 years: {'✅ PASS' if rising_wealth else '❌ FAIL'}"
          f" ({'grew' if rising_wealth else 'shrank'} from ${initial_wealth:,.0f}"
          f" to ${final_wealth_total:,.0f})")
    print(f"  Rising Gini over 60 years:   {'✅ PASS' if rising_gini else '❌ FAIL'}"
          f" ({'rose' if rising_gini else 'fell'} from {initial_gini:.4f}"
          f" to {final_gini_total:.4f})")
    print(f"  Overall: {'✅ PASS' if rising_wealth and rising_gini else '❌ FAIL'}")
    print()
    print(f"  Time: {elapsed:.1f}s")
    print()

    # ─── Build output ────────────────────────────────────────
    result = {
        'metadata': {
            'seed': SEED,
            'steps_per_period': STEPS_PER_PERIOD,
            'total_steps': TOTAL_STEPS,
            'elapsed_seconds': round(elapsed, 1),
        },
        'calibrations': CALIBRATIONS,
        'periods': periods,
        'full_trajectory': {k: [float(x) for x in v]
                            for k, v in full_trajectory.items()},
        'stylized_facts': {
            'gdp_growth_3x': {
                'initial_wealth': round(initial_wealth, 2),
                'final_wealth': round(final_wealth_total, 2),
                'ratio': round(wealth_ratio, 4),
                'stylized_target': STYLIZED_GDP_GROWTH,
            },
            'gini_rise': {
                'initial_gini': round(initial_gini, 4),
                'final_gini': round(final_gini_total, 4),
                'delta': round(gini_delta, 4),
                'stylized_start': STYLIZED_GINI_START,
                'stylized_end': STYLIZED_GINI_END,
            },
        },
        'pass_fail': {
            'rising_wealth': rising_wealth,
            'rising_gini': rising_gini,
            'overall_pass': rising_wealth and rising_gini,
        },
    }

    return result


def main():
    print("=" * 90)
    print("  US HISTORICAL BACKTEST — VALIDATION SCRIPT")
    print(f"  Seed: {SEED}  |  Periods: {len(CALIBRATIONS)}"
          f"  |  Steps/period: {STEPS_PER_PERIOD}"
          f"  |  Total steps: {TOTAL_STEPS}")
    print(f"  Calibrations: {', '.join(c['label'] for c in CALIBRATIONS)}")
    print("=" * 90)
    print()
    print(f"  {'Period':<8} {'IncTx':>6} {'CorpTx':>6} {'Welfare':>8}  "
          f"{'Final Wealth':>14} {'Final Gini':>10} {'Mean$':>10}")
    print(f"  {'-'*8} {'-'*6} {'-'*6} {'-'*8}  {'-'*14} {'-'*10} {'-'*10}")

    result = run_backtest()

    # Save
    sim_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(sim_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, 'backtest_results.json')
    with open(outpath, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"  Saved: {outpath}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
