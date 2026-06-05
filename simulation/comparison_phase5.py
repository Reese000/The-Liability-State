#!/usr/bin/env python3
"""Phase 5 economic simulator — Phase 4 + Harberger self-assessment market.

Dynamics preserved: corruption, bloat, monopoly, banking, enforcement,
info asymmetry, income effect, inheritance.

New (Phase 5):
  - use_harberger: wires HarbergerMarket (src.mechanics.harberger) into loop
  - agricultural_lvt_rate: reduced rate on 20% of worker parcels
  - minimum_wage: wage floor applied in wage calculation
  - foreign_ownership_allowed: restricts cross-group bidding
  - migration_enabled: workers can move between compacts (Dual_Compact)
  - compact_voting: random walk policy parameters
  - constitutional_amendment_rate: sortition panel changes
"""
import sys, os, copy, json, time, logging
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.core.ledger import LedgerEngine, EntityType

from comparison_phase4 import (
    gen_population, compute_gini, SEEDS, STEPS, REPORT_INTERVAL, HOURS_PER_STEP,
    LVT_ANNUAL_RATE, LVT_MONTHLY_RATE, INVESTMENT_RATE, BUSINESS_WAGE_BILL,
    WAGE_VARIABILITY, ACCIDENT_PROBABILITY, TFP_TAX_ELASTICITY, LABOR_SUPPLY_ELASTICITY,
    ADMIN_OVERHEAD_BY_TAX, SYSTEM_CONFIGS as P4_SYSTEM_CONFIGS, _mk,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")

# ═══════════════════════════════════════════════════════════
#  Phase 5 Simulation
# ═══════════════════════════════════════════════════════════
def run_phase5(workers, retirees, businesses, seed, config):
    """Phase 5: same signature as Phase 4. Adds Harberger + governance features."""
    C = config.get
    name = C('system_name', 'Phase5')
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
    # Phase 4 dynamics
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
    # Phase 5 config
    use_harberger = C('use_harberger', False)
    harv_bf = float(C('harberger_buyer_frequency', 0.05))
    harv_lr = float(C('harberger_learning_rate', 0.1))
    agri_lvt_r = float(C('agricultural_lvt_rate', lvt_r))
    min_wage = float(C('minimum_wage', 0.0))
    foreign_own = C('foreign_ownership_allowed', True)
    # ─── Governance features (Tasks 5, 6, 10) ────────────────
    migration_enabled = C('migration_enabled', False)
    compact_voting = C('compact_voting', False)
    const_amend_rate = float(C('constitutional_amendment_rate', 0.0))

    _log = logging.getLogger(f'p5_{name[:12]}')
    rng = np.random.RandomState(seed)
    lvt_m = (lvt_r / 12) if tx == 'lvt' else 0.0

    # ─── Setup balances ──────────────────────────────────────
    bank_reserve = max(0, float(C('bank_initial_reserve', 0)))
    bal = {e['id']: e['cash'] for e in workers + retirees + businesses}
    bal.update({'sys': 500_000_000, 'trust': 0, 'bank': bank_reserve,
                'harberger_escrow': 0} if use_harberger else {'sys': 500_000_000, 'trust': 0, 'bank': bank_reserve})
    wid = [w['id'] for w in workers]
    rid = [r['id'] for r in retirees]
    all_c = wid + rid
    wland = {w['id']: w['land'] for w in workers}
    rland = {r['id']: r['land'] for r in retirees}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}
    cum_tr = {a: 0.0 for a in all_c}
    hist = {'gini': [], 'wealth': [], 'wmin': [], 'wmean': [], 'div': []}
    pc = 0.0

    # ─── Governance state (Dual Compact migration, voting) ──
    is_dual_compact = C('use_dual_compact', False) or C('use_compacts', False)
    compact_assignment = {}
    compact_params = {
        'A': {'lvt_rate': lvt_r, 'dividend_rate': 0.9, 'court_budget': 1.0},
        'B': {'lvt_rate': lvt_r, 'dividend_rate': 0.9, 'court_budget': 1.0},
    }
    migration_count = 0
    policy_path = {
        'A': {'lvt_rate': [], 'dividend_rate': [], 'court_budget': []},
        'B': {'lvt_rate': [], 'dividend_rate': [], 'court_budget': []},
    }

    if (migration_enabled or compact_voting) and is_dual_compact:
        for i, w in enumerate(workers):
            compact_assignment[w['id']] = 'A' if i % 2 == 0 else 'B'
        for i, r in enumerate(retirees):
            compact_assignment[r['id']] = 'A' if i % 2 == 0 else 'B'

    def xf(fr, to, mech, amt):
        if amt <= 0 or fr not in bal or to not in bal:
            return
        amt = min(amt, bal[fr])
        if amt <= 0:
            return
        bal[fr] -= amt
        bal[to] += amt

    # ─── Harberger setup ────────────────────────────────────
    harv = None
    ledg = None
    agri_wids = set()
    if use_harberger:
        from src.mechanics.harberger import HarbergerMarket
        ledg = LedgerEngine(step_log=False)
        for eid, cash in bal.items():
            ledg.register_entity(eid, EntityType.SYSTEM, initial_cash=cash)
        harv = HarbergerMarket(ledg, lvt_rate=LVT_ANNUAL_RATE / 12)  # monthly rate
        for w in workers:
            harv.register_parcel(f"wland_{w['id']}", w['id'], wland[w['id']])
        for r in retirees:
            harv.register_parcel(f"rland_{r['id']}", r['id'], rland[r['id']])
        for b in businesses:
            harv.register_parcel(f"bland_{b['id']}", b['id'], bland[b['id']])
        # 20% of workers designated agricultural
        n_agri = max(1, len(workers) // 5)
        agri_wids = set(rng.choice([w['id'] for w in workers], n_agri, replace=False))

    def _sync_to_ledger():
        for eid, amount in bal.items():
            if ledg.entity_exists(eid):
                ledg.get_balance(eid).cash = amount

    def _sync_from_ledger():
        for eid, bs in ledg.balances.items():
            bal[eid] = bs.cash

    # ─── Main loop ──────────────────────────────────────────
    for step in range(1, STEPS + 1):
        try:
            dmult = 0.85 if (ue and step == STEPS // 4) else 1.0

            # ── 1. Wages + income effect + minimum wage ────
            sw = {}
            for w in workers:
                after = w['hourly'] * (1 - inc_tx) if tx == 'income' else w['hourly']
                lr = (after / w['hourly']) ** LABOR_SUPPLY_ELASTICITY if w['hourly'] > 0 else 1.0
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

            # ── 2. Business + monopolization ───────────────
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
                                    wid_, wg = w['id'], sw.get(w['id'], 0)
                                    act = min(cp * (wg / tw), max(0, mt - wg))
                                    if act > 0.01:
                                        xf(b['id'], wid_, 'coop', act)
                    else:
                        ret = at - inv
                        if ret > 0:
                            xf('sys', b['id'], 'ret', ret)

            # ── 3. Insurance + info asymmetry ──────────────
            epm, tuf = 1 + inf * 0.5, 1 - inf * 0.3
            for w in workers:
                if rng.random() < tuf:
                    prem = w['monthly'] * 0.05 * epm
                    if bal.get(w['id'], 0) >= prem:
                        xf(w['id'], 'sys', 'prem', prem)
                        if rng.random() < ACCIDENT_PROBABILITY:
                            cl = rng.uniform(1000, 20000)
                            po = min(cl, bal['sys'])
                            if po > 0:
                                xf('sys', w['id'], 'claim', po)

            # ── 4. Adversarial (placeholder for compat) ──
            if ua:
                pass

            # ── 5. Tax ──────────────────────────────────────
            tt = 0.0
            clk = 1 - corr * 0.4

            if use_harberger:
                _sync_to_ledger()

                # 5a. Self-assessment convergence toward true value
                for w in workers:
                    pid = f"wland_{w['id']}"
                    if pid in harv.parcels:
                        p = harv.get_parcel(pid)
                        nv = p.declared_value + (wland[w['id']] - p.declared_value) * harv_lr
                        harv.self_assess(pid, max(0, nv))
                for r in retirees:
                    pid = f"rland_{r['id']}"
                    if pid in harv.parcels:
                        p = harv.get_parcel(pid)
                        nv = p.declared_value + (rland[r['id']] - p.declared_value) * harv_lr
                        harv.self_assess(pid, max(0, nv))
                for b in businesses:
                    pid = f"bland_{b['id']}"
                    if pid in harv.parcels:
                        p = harv.get_parcel(pid)
                        nv = p.declared_value + (bland[b['id']] - p.declared_value) * harv_lr
                        harv.self_assess(pid, max(0, nv))

                # 5b. Random buyer posts bid
                if rng.random() < harv_bf and harv.parcels:
                    pid = rng.choice(list(harv.parcels.keys()))
                    parcel = harv.get_parcel(pid)
                    if not foreign_own:
                        if pid.startswith('wland_'):
                            pool = wid
                        elif pid.startswith('rland_'):
                            pool = rid
                        else:
                            pool = [b['id'] for b in businesses]
                    else:
                        pool = all_c + [b['id'] for b in businesses]
                    candidates = [a for a in pool if a != parcel.owner and bal.get(a, 0) > 0]
                    if candidates:
                        try:
                            harv.post_bid(pid, rng.choice(candidates))
                        except ValueError:
                            pass

                # 5c. Advance day (process bid lifecycles)
                harv.advance_day()

                # 5d. Assess LVT
                lvt_result = harv.assess_lvt(collector='trust')

                # Sync ledger back to bal dict
                _sync_from_ledger()

                tt = lvt_result['total_lvt']

                # 5e. Agricultural LVT rebate (refund excess over agri rate)
                if agri_lvt_r != lvt_r and agri_wids:
                    for wid_ in list(agri_wids):
                        pid = f"wland_{wid_}"
                        if pid in harv.parcels:
                            p = harv.get_parcel(pid)
                            std = lvt_r * p.assessed_for_lvt
                            agri = agri_lvt_r * p.assessed_for_lvt
                            refund = std - agri
                            if refund > 0:
                                r_amt = min(refund, bal.get('trust', 0))
                                if r_amt > 0:
                                    xf('trust', wid_, 'agri_rebate', r_amt)
                                    tt -= r_amt

            elif tx == 'lvt':
                # Original Phase 4 manual LVT
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
                    if t > 0:
                        xf(w['id'], 'sys', 'itax', t)
                        tt += t
            elif uv:
                for w in workers:
                    v = sw.get(w['id'], 0) * vat_r * clk
                    if v > 0:
                        xf(w['id'], 'sys', 'vat', v)
                        tt += v

            # ── 6. Bloat ──────────────────────────────────────
            ac = tt * blt
            if ac > 0:
                xf('sys', 'trust', 'bloat', ac)

            # ── 7. Dividend ───────────────────────────────────
            pc = 0.0
            if tx == 'lvt' and tt > 0:
                nd = tt * (1 - blt)
                pc = nd * 0.9 / len(all_c) if nd > 0 else 0
                if pc > 0:
                    for c in all_c:
                        xf('trust', c, 'div', pc)
                        cum_tr[c] += pc

            # ── 8. Courts + enforcement ───────────────────────
            elt = ACCIDENT_PROBABILITY * enq
            for b in businesses:
                if rng.random() < elt:
                    pl = rng.choice(wid)
                    amt = rng.uniform(1000, 20000)
                    if rng.random() < enq:
                        pay = min(amt, bal.get(b['id'], 0))
                        if pay > 0:
                            xf(b['id'], pl, 'judge', pay)

            # ── 9. Welfare ────────────────────────────────────
            if tx == 'income' and inc_tx > 0:
                wp = tt * wel_r * (1 - blt)
                if wp > 0:
                    pw = wp / len(all_c)
                    for c in all_c:
                        xf('sys', c, 'welf', pw)
                        cum_tr[c] += pw

            # ── 10. CPF ───────────────────────────────────────
            if cpf_r > 0:
                cpf_t = sum(sw.get(w['id'], 0) * cpf_r for w in workers)
                if cpf_t > 0:
                    pcpf = cpf_t / len(wid)
                    for w_id in wid:
                        xf('sys', w_id, 'cpf', pcpf)

            # ── 11. Banking ───────────────────────────────────
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

            # ── 12. Enforcement ───────────────────────────────
            for w in workers:
                if corr > 0 and rng.random() < dpr * enq:
                    pen = w['monthly'] * corr * 0.2 * (1 - enq)
                    if pen > 0 and bal.get(w['id'], 0) >= pen:
                        xf(w['id'], 'sys', 'pen', pen)

            # ══════════════════════════════════════════════════
            #  Task 5: Inter-compact migration
            # ══════════════════════════════════════════════════
            if migration_enabled and is_dual_compact and compact_assignment:
                for w in workers:
                    wid_ = w['id']
                    cur_comp = compact_assignment.get(wid_, 'A')
                    alt_comp = 'B' if cur_comp == 'A' else 'A'

                    inc_w = sw.get(wid_, w['monthly'])
                    # After-tax wage depends on tax type
                    cur_tax = compact_params[cur_comp]['lvt_rate']
                    alt_tax = compact_params[alt_comp]['lvt_rate']
                    if tx == 'income':
                        cur_after = inc_w * (1 - inc_tx)
                        alt_after = inc_w * (1 - inc_tx)
                    elif tx == 'lvt':
                        cur_after = inc_w * (1 - cur_tax)
                        alt_after = inc_w * (1 - alt_tax)
                    else:
                        cur_after = inc_w
                        alt_after = inc_w

                    # Expected dividend from each compact
                    cur_div = pc * compact_params[cur_comp]['dividend_rate'] if tx == 'lvt' else 0
                    alt_div = pc * compact_params[alt_comp]['dividend_rate'] if tx == 'lvt' else 0

                    cur_wf = cur_after + cur_div
                    alt_wf = alt_after + alt_div
                    diff = alt_wf - cur_wf

                    if diff > 0 and cur_wf > 0:
                        p_migrate = min(0.1, (diff / cur_wf) * 0.05)
                        if rng.random() < p_migrate:
                            compact_assignment[wid_] = alt_comp
                            migration_count += 1

            # ══════════════════════════════════════════════════
            #  Task 6: Compact governance (voting random walk)
            # ══════════════════════════════════════════════════
            if compact_voting and is_dual_compact:
                for comp in ['A', 'B']:
                    if rng.random() < 0.05:
                        param = rng.choice(['lvt_rate', 'dividend_rate', 'court_budget'])
                        delta = rng.uniform(-0.002, 0.002)
                        if param == 'lvt_rate':
                            compact_params[comp]['lvt_rate'] = max(
                                0.0, min(0.1, compact_params[comp]['lvt_rate'] + delta))
                        elif param == 'dividend_rate':
                            compact_params[comp]['dividend_rate'] = max(
                                0.5, min(1.0, compact_params[comp]['dividend_rate'] + delta))
                        elif param == 'court_budget':
                            compact_params[comp]['court_budget'] = max(
                                0.0, min(2.0, compact_params[comp]['court_budget'] + delta))
                    # Record policy state
                    policy_path[comp]['lvt_rate'].append(compact_params[comp]['lvt_rate'])
                    policy_path[comp]['dividend_rate'].append(compact_params[comp]['dividend_rate'])
                    policy_path[comp]['court_budget'].append(compact_params[comp]['court_budget'])

            # ══════════════════════════════════════════════════
            #  Task 10: Constitutional amendment (sortition)
            # ══════════════════════════════════════════════════
            if const_amend_rate > 0 and step % 12 == 0:
                if rng.random() < const_amend_rate:
                    param = rng.choice([
                        'lvt_rate', 'income_tax_rate', 'minimum_wage',
                        'enforcement_quality', 'corruption_level',
                    ])
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

            # ── Report ────────────────────────────────────────
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

    # ─── Post-sim: Inheritance ─────────────────────────────
    if ihr > 0:
        for w in workers:
            bq = bal.get(w['id'], 0) * ihr
            pw = bq / len(wid) if wid else 0
            if pw > 0:
                for w_id in wid:
                    xf(w['id'], w_id, 'inherit', pw)

    ww = [bal[i] for i in wid if i in bal]

    # ══════════════════════════════════════════════════════
    #  Task 9: Gini by decade (40-step intervals ≈ decade)
    # ══════════════════════════════════════════════════════
    # hist['gini'] is recorded every REPORT_INTERVAL (12) steps.
    # With STEPS=480, we have 40 entries. Sample ~ every 3-4 entries
    # for roughly decade-scale intervals.
    if hist['gini']:
        step_interval = max(1, len(hist['gini']) // 12)
        gini_by_decade = [hist['gini'][i] for i in range(0, len(hist['gini']), step_interval)]
        if len(gini_by_decade) > 12:
            gini_by_decade = gini_by_decade[:12]
    else:
        gini_by_decade = []

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
        # Task 9: intergenerational tracking
        'gini_by_decade': gini_by_decade,
        # Task 5: migration count
        'migration_count': migration_count,
        # Task 6: policy path
        'policy_path': policy_path,
    }


# ═══════════════════════════════════════════════════════════
#  System Configurations — Phase 5 (all 10 systems extended)
# ═══════════════════════════════════════════════════════════
# Phase 5-specific overrides per system.
PHASE5_OVERRIDES = {
    'LS_Full': {
        'use_harberger': True,
        'agricultural_lvt_rate': 0.01,
        'harberger_buyer_frequency': 0.10,
        'harberger_learning_rate': 0.15,
        'foreign_ownership_allowed': False,
    },
    'US_Style': {
        'use_harberger': False,
        'minimum_wage': 1160.0,  # ~$7.25/hr × 160h monthly
    },
    'Nordic': {
        'use_harberger': False,
    },
    'Singapore': {
        'use_harberger': False,
        'minimum_wage': 0.0,
    },
    'Pure_Georgist': {
        'use_harberger': True,
        'agricultural_lvt_rate': 0.01,
        'harberger_buyer_frequency': 0.10,
        'harberger_learning_rate': 0.15,
    },
    'Mutualist_LS': {
        'use_harberger': True,
        'agricultural_lvt_rate': 0.01,
        'harberger_buyer_frequency': 0.10,
        'harberger_learning_rate': 0.15,
        'foreign_ownership_allowed': False,
    },
    'Laissez_Faire': {
        'use_harberger': False,
    },
    'Worker_Coop': {
        'use_harberger': True,
        'agricultural_lvt_rate': 0.01,
        'harberger_buyer_frequency': 0.10,
        'harberger_learning_rate': 0.15,
    },
    'UBI_VAT': {
        'use_harberger': False,
    },
    'Dual_Compact_LS': {
        'use_harberger': True,
        'agricultural_lvt_rate': 0.01,
        'harberger_buyer_frequency': 0.10,
        'harberger_learning_rate': 0.15,
        'foreign_ownership_allowed': False,
        'migration_enabled': True,
    },
}

PHASE5_CONFIGS = {}
for sys_name, cfg in P4_SYSTEM_CONFIGS.items():
    c = copy.deepcopy(cfg)
    # Apply Phase 5 defaults (non-Harberger, conservative values)
    c.update({
        'use_harberger': False,
        'harberger_buyer_frequency': 0.05,
        'harberger_learning_rate': 0.1,
        'agricultural_lvt_rate': c.get('lvt_rate', LVT_ANNUAL_RATE),
        'minimum_wage': 0.0,
        'foreign_ownership_allowed': True,
        'migration_enabled': False,
        'compact_voting': False,
        'constitutional_amendment_rate': 0.0,
    })
    # Apply system-specific Phase 5 overrides
    if sys_name in PHASE5_OVERRIDES:
        c.update(PHASE5_OVERRIDES[sys_name])
    PHASE5_CONFIGS[sys_name] = c

# Add a dedicated Harberger-Enabled Georgist config
HARBERGER_GEORGIST = copy.deepcopy(PHASE5_CONFIGS['Pure_Georgist'])
HARBERGER_GEORGIST.update({
    'system_name': 'Harberger_Georgist',
    'use_harberger': True,
    'agricultural_lvt_rate': 0.01,
    'harberger_buyer_frequency': 0.10,
    'harberger_learning_rate': 0.15,
})
PHASE5_CONFIGS['Harberger_Georgist'] = HARBERGER_GEORGIST


# ═══════════════════════════════════════════════════════════
#  YAML Config Loading (Task 7)
# ═══════════════════════════════════════════════════════════
def load_phase5_configs_yaml(path=None):
    """Load Phase 5 system configs from a YAML file.

    Falls back to ``PHASE5_CONFIGS`` if the file is missing or
    ``yaml`` is not installed.  Configs in the YAML file completely
    replace the corresponding entries.
    """
    if path is None:
        path = os.path.join(os.path.dirname(__file__), 'configs.yaml')
    if not os.path.exists(path):
        return dict(PHASE5_CONFIGS)
    try:
        import yaml
    except ImportError:
        return dict(PHASE5_CONFIGS)
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
        configs = {}
        for name, vals in raw.items():
            cfg = copy.deepcopy(vals)
            cfg['system_name'] = name
            configs[name] = cfg
        return configs
    except Exception:
        return dict(PHASE5_CONFIGS)


# ═══════════════════════════════════════════════════════════
#  Batch Runner & Main
# ═══════════════════════════════════════════════════════════
def run_batch(seeds, configs):
    results = {c['system_name']: [] for c in configs}
    t0 = time.time()
    for cfg in configs:
        name = cfg['system_name']
        print(f"\n{'='*40}\n  {name}\n{'='*40}")
        for seed in seeds:
            pop = gen_population(seed)
            r = run_phase5(*pop, seed, cfg)
            results[name].append(r)
            print(f"  s{seed}: G={r['gini']:.4f} M=${r['w_mean']:>8,.0f} D=${r['div']:>5.2f}"
                  f"{' mig='+str(r.get('migration_count',0)) if r.get('migration_count',0)>0 else ''}")
    print(f"\nTime: {time.time()-t0:.0f}s")
    return results


def summarize(results):
    print(f"\n{'='*100}\n  PHASE 5 — SYSTEMS\n{'='*100}")
    print(f"{'System':<22} {'Mean$':>10} {'Gini':>8} {'Div':>8}  {'N':>4}")
    print("-" * 100)
    for sn in results:
        rs = results[sn]
        wm, gs, ds = (
            [r['w_mean'] for r in rs],
            [r['gini'] for r in rs],
            [r['div'] for r in rs],
        )
        print(f"{sn:<22} ${np.mean(wm):>7,.0f} {np.mean(gs):>.4f}±{np.std(gs):.4f} ${np.mean(ds):>5.2f}  {len(rs)}")
    for label, key, rev in [
        ("Mean Wealth", 'w_mean', True),
        ("Low Gini", 'gini', False),
    ]:
        ranked = sorted(
            [(np.mean([r[key] for r in results[sn]]), sn) for sn in results],
            reverse=rev,
        )
        print(f"\n{label:^70}")
        for i, (v, n) in enumerate(ranked, 1):
            print(f"  {i}. {n:<25} {v:>9,.4f}")


def main():
    seeds = list(range(1, 3)) if '--quick' in sys.argv else SEEDS
    cfg = list(PHASE5_CONFIGS.values())
    print(f"Phase5: {len(seeds)} seeds × {len(cfg)} systems = {len(seeds)*len(cfg)} sims")
    r = run_batch(seeds, cfg)
    summarize(r)
    os.makedirs("output", exist_ok=True)
    json.dump(r, open("output/phase5_results.json", "w"), indent=2)
    print("Saved: output/phase5_results.json")


if __name__ == '__main__':
    main()
