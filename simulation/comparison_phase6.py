#!/usr/bin/env python3
"""Phase 6 economic simulator — Phase 5 + land heterogeneity, net worth,
wellbeing composite, LVT evasion wiring, family structures.

New (Phase 6):
  - Land value heterogeneity (log-normal land distribution, σ=1.0, μ=11.5)
  - Net worth tracking (cash + land_value + capital)
  - Wellbeing composite score (ARCHITECTURE.md formula)
  - LvtEvasion wiring (adversarial controller strategy)
  - Family structures and children (20 children per seed, household Gini)
All features are config-driven, toggleable, and backward-compatible.
"""
import sys, os, copy, json, time, logging
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase5 import (
    run_phase5, PHASE5_CONFIGS, PHASE5_OVERRIDES,
)
from comparison_phase4 import (
    SEEDS, STEPS, REPORT_INTERVAL, HOURS_PER_STEP,
    LVT_ANNUAL_RATE, LVT_MONTHLY_RATE, INVESTMENT_RATE, BUSINESS_WAGE_BILL,
    WAGE_VARIABILITY, ACCIDENT_PROBABILITY, TFP_TAX_ELASTICITY, LABOR_SUPPLY_ELASTICITY,
    ADMIN_OVERHEAD_BY_TAX, SYSTEM_CONFIGS as P4_SYSTEM_CONFIGS, _mk,
    compute_gini,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")


# ═══════════════════════════════════════════════════════════
#  Population — Land Value Heterogeneity (Phase 6 §1)
# ═══════════════════════════════════════════════════════════
def gen_population(seed):
    """Generate workers, retirees, businesses with log-normal land distribution.

    Workers get land ∼ logNormal(μ=11.5, σ=1.0), resulting in values
    ranging from ~$5K to ~$5M (Phase 4/5 used uniform $20K-$200K).
    Same seed → deterministic and reproducible.
    """
    rng = np.random.RandomState(seed)
    w = [{"id": f"w{i:03d}", "hourly": rng.uniform(10, 40),
          "monthly": rng.uniform(10, 40) * HOURS_PER_STEP,
          "land": float(rng.lognormal(11.5, 1.0)),
          "risk": rng.uniform(0.01, 0.25),
          "cash": rng.uniform(10000, 80000),
          "honesty": rng.uniform(0.3, 0.95),
          "inertia": rng.uniform(0.05, 0.25),
          "concealment": rng.uniform(0, 0.2)}
         for i in range(50)]
    r = [{"id": f"r{i:03d}", "cash": rng.uniform(80000, 200000),
          "land": rng.uniform(50000, 300000)} for i in range(15)]
    b = [{"id": f"b{i:03d}", "cash": rng.uniform(100000, 500000),
          "capital": rng.uniform(100000, 400000),
          "tfp": rng.uniform(1.0, 2.0),
          "markup": rng.uniform(1.1, 1.3),
          "honesty": rng.uniform(0.3, 0.9)} for i in range(10)]
    return w, r, b


# ═══════════════════════════════════════════════════════════
#  Wellbeing Composite (Phase 6 §3)
# ═══════════════════════════════════════════════════════════
def compute_wellbeing(workers, seed, config, gini, mean_cash, has_insurance):
    """Compute the aggregate wellbeing composite score.

    Formula (ARCHITECTURE.md):
        wellbeing = 0.3 × wealth_score
                  + 0.2 × security_score
                  + 0.15 × freedom_score
                  + 0.15 × community_score
                  + 0.10 × purpose_score
                  + 0.10 × stability_score

    Each sub-score is normalised to [0, 1].
    """
    C = config.get

    # wealth_score: normalised mean cash
    wealth_score = min(1.0, mean_cash / 100000.0)

    # security_score: 1.0 if any agent has insurance, else 0.5
    security_score = 1.0 if has_insurance else 0.5

    # freedom_score: 1 - tax_rate (capped at 1)
    tax_type = C('tax_type', 'lvt')
    if tax_type == 'lvt':
        tax_rate = C('lvt_rate', LVT_ANNUAL_RATE)
    elif tax_type == 'income':
        tax_rate = C('income_tax_rate', 0.0)
    else:
        tax_rate = C('vat_rate', 0.0)
    freedom_score = 1.0 - min(1.0, tax_rate)

    # community_score: 0.7 (no guild module wired in Phase 6)
    community_score = 0.7

    # purpose_score: 0.6 (no career progression in Phase 6)
    purpose_score = 0.6

    # stability_score: 1 - min(1, gini)
    stability_score = 1.0 - min(1.0, gini)

    wellbeing = (0.3 * wealth_score + 0.2 * security_score
                 + 0.15 * freedom_score + 0.15 * community_score
                 + 0.10 * purpose_score + 0.10 * stability_score)
    return round(wellbeing, 4)


# ═══════════════════════════════════════════════════════════
#  Family Gini (Phase 6 §5)
# ═══════════════════════════════════════════════════════════
def compute_family_gini(children, workers, bal):
    """Compute Gini coefficient over households.

    Each household = a worker (parent) + their assigned children.
    Workers without children are single-person households.
    Household cash = sum(parent cash, all child cash).
    """
    parent_map = {}  # parent_id -> list of child ids
    for c in children:
        pid = c['parent_id']
        if pid not in parent_map:
            parent_map[pid] = []
        parent_map[pid].append(c['id'])

    household_cash = []
    for w in workers:
        wid = w['id']
        hh = bal.get(wid, 0)
        if wid in parent_map:
            for cid in parent_map[wid]:
                hh += bal.get(cid, 0)
        household_cash.append(hh)

    # Workers with no children are already included as single-person
    return compute_gini(household_cash)


# ═══════════════════════════════════════════════════════════
#  Phase 6 Simulation
# ═══════════════════════════════════════════════════════════
def run_phase6(workers, retirees, businesses, seed, config):
    """Phase 6: same signature as Phase 5. Adds land heterogeneity, net worth
    tracking, wellbeing composite, LVT evasion wiring, and family structures.

    Return dict includes all Phase 5 keys plus:
        - net_worth, net_worth_gini, net_worth_mean
        - wellbeing
        - child_count, family_gini  (if use_families=True)
    """
    # ─── Copy inputs to avoid mutation ──────────────────────────
    workers = [dict(w) for w in workers]
    retirees = [dict(r) for r in retirees]
    businesses = [dict(b) for b in businesses]
    rst = copy.deepcopy(config)

    C = rst.get

    # ─── Phase 6 config flags ──────────────────────────────────
    wire_lvt_evasion = C('wire_lvt_evasion', False)
    use_families = C('use_families', False)

    # ─── Generate children (Phase 6 §5) ────────────────────────
    children = []
    if use_families:
        rng_children = np.random.RandomState(seed)
        worker_ids = [w['id'] for w in workers]
        for i in range(20):
            parent_id = worker_ids[rng_children.randint(0, len(worker_ids))]
            children.append({
                'id': f'c{seed}_{i:03d}',
                'parent_id': parent_id,
                'cash': 0.0,
                'land': 0.0,
            })
    child_ids = [c['id'] for c in children]

    # ─── Set up LVT evasion (Phase 6 §4) ──────────────────────
    lvt_evasion_controller = None
    if wire_lvt_evasion:
        from src.adversarial.controller import (
            StrategyController, LvtEvasion,
        )
        lvt_evasion_controller = StrategyController(
            strategies=[LvtEvasion()]
        )

    # ─── Delegate to Phase 5 for the core simulation ──────────
    # We need to replicate the phase 5 logic with modifications.
    # Rather than calling run_phase5 directly (which doesn't know about
    # our new features), we run the same loop inline with Phase 6 extensions.
    rst['system_name'] = C('system_name', 'Phase6')

    name = C('system_name', 'Phase6')
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
    migration_enabled = C('migration_enabled', False)
    compact_voting = C('compact_voting', False)
    const_amend_rate = float(C('constitutional_amendment_rate', 0.0))

    _log = logging.getLogger(f'p6_{name[:12]}')
    rng = np.random.RandomState(seed)
    lvt_m = (lvt_r / 12) if tx == 'lvt' else 0.0

    # ─── Setup balances ──────────────────────────────────────
    bank_reserve = max(0, float(C('bank_initial_reserve', 0)))
    bal = {e['id']: e['cash'] for e in workers + retirees + businesses}
    # Add children to balance sheet
    for c in children:
        bal[c['id']] = c['cash']
    bal.update({'sys': 500_000_000, 'trust': 0, 'bank': bank_reserve,
                'harberger_escrow': 0} if use_harberger else {'sys': 500_000_000, 'trust': 0, 'bank': bank_reserve})

    wid = [w['id'] for w in workers]
    rid = [r['id'] for r in retirees]
    # all_c includes children when families are active
    all_c = wid + rid + (child_ids if use_families else [])

    wland = {w['id']: w['land'] for w in workers}
    rland = {r['id']: r['land'] for r in retirees}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}
    cum_tr = {a: 0.0 for a in all_c}
    hist = {'gini': [], 'wealth': [], 'wmin': [], 'wmean': [], 'div': []}
    pc = 0.0

    # ─── Governance state ──────────────────────────────────────
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
        from src.core.ledger import LedgerEngine, EntityType
        ledg = LedgerEngine(step_log=False)
        for eid, cash in bal.items():
            ledg.register_entity(eid, EntityType.SYSTEM, initial_cash=cash)
        harv = HarbergerMarket(ledg, lvt_rate=LVT_ANNUAL_RATE / 12)
        for w in workers:
            harv.register_parcel(f"wland_{w['id']}", w['id'], wland[w['id']])
        for r in retirees:
            harv.register_parcel(f"rland_{r['id']}", r['id'], rland[r['id']])
        for b in businesses:
            harv.register_parcel(f"bland_{b['id']}", b['id'], bland[b['id']])
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
            has_insurance_any = False
            for w in workers:
                if rng.random() < tuf:
                    prem = w['monthly'] * 0.05 * epm
                    if bal.get(w['id'], 0) >= prem:
                        xf(w['id'], 'sys', 'prem', prem)
                        has_insurance_any = True
                        if rng.random() < ACCIDENT_PROBABILITY:
                            cl = rng.uniform(1000, 20000)
                            po = min(cl, bal['sys'])
                            if po > 0:
                                xf('sys', w['id'], 'claim', po)

            # ── 4. Adversarial (placeholder) ──────────────
            if ua:
                pass

            # ── 5. Tax ──────────────────────────────────────
            tt = 0.0
            clk = 1 - corr * 0.4

            # ═══ Phase 6 §4: LVT Evasion Wiring ══════════════
            def _lvt_evasion_factor(agent_dict):
                """Compute fraction by which LVT collection is reduced.

                Uses LvtEvasion strategy's core formula (savings_fraction =
                0.15 + concealment * 0.20) modulated by honesty.
                The formula comes from LvtEvasion.reward() — we use it directly
                since the strategy's prereq check (property_count > 1) targets
                a different use case (land fragmentation).
                """
                if not wire_lvt_evasion or lvt_evasion_controller is None:
                    return 1.0
                # evasion_frac = 0.15 + concealment * 0.20  (from LvtEvasion.reward)
                ev = 0.15 + agent_dict.get('concealment', 0) * 0.20
                # honesty discounts: more honest → less effective evasion
                h = agent_dict.get('honesty', 0.5)
                effective_evasion = ev * (1.0 - h)
                # Return the fraction of LVT that is actually collected
                return max(0.0, 1.0 - effective_evasion)

            # ═══ Phase 6 §4: Apply evasion in both Harberger and manual paths
            if use_harberger:
                _sync_to_ledger()

                # Self-assessment convergence toward true value
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

                # Random buyer posts bid
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

                harv.advance_day()

                # ═══ Phase 6 §4: Apply evasion to LVT assessment ═══
                lvt_result = harv.assess_lvt(collector='trust')
                _sync_from_ledger()

                tt = lvt_result['total_lvt']

                # Apply LVT evasion: rebate a portion back to evading agents
                if wire_lvt_evasion and tt > 0:
                    evaded_total = 0.0
                    for parcel_info in lvt_result['parcels']:
                        pid = parcel_info['parcel_id']
                        owner = parcel_info['owner']
                        # Find worker dict for owner
                        owner_dict = None
                        for w in workers:
                            if w['id'] == owner:
                                owner_dict = w
                                break
                        if owner_dict is None:
                            for r in retirees:
                                if r['id'] == owner:
                                    owner_dict = r
                                    break
                        if owner_dict is None:
                            for b in businesses:
                                if b['id'] == owner:
                                    owner_dict = b
                                    break
                        if owner_dict is not None:
                            ef = _lvt_evasion_factor(owner_dict)
                            if ef < 1.0:
                                # Rebate the evaded portion
                                evaded = parcel_info['lvt_paid'] * (1.0 - ef)
                                if evaded > 0 and bal.get('trust', 0) >= evaded:
                                    xf('trust', owner, 'lvt_evasion', evaded)
                                    evaded_total += evaded
                    tt -= evaded_total

                # Agricultural LVT rebate
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
                # Original Phase 4 manual LVT + Phase 6 §4 evasion
                for el, lm in [(workers, wland), (retirees, rland), (businesses, bland)]:
                    for e in el:
                        d = lm[e['id']] * lvt_m * clk
                        # ═══ Phase 6 §4: Apply evasion ═══
                        ef = _lvt_evasion_factor(e)
                        d = d * ef
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

            # ── 9. Welfare (includes children if use_families)
            if tx == 'income' and inc_tx > 0:
                wp = tt * wel_r * (1 - blt)
                if wp > 0:
                    pw = wp / len(all_c)
                    for c in all_c:
                        xf('sys', c, 'welf', pw)
                        cum_tr[c] += pw

            # ── 10. CPF (includes children if use_families)
            if cpf_r > 0:
                cpf_t = sum(sw.get(w['id'], 0) * cpf_r for w in workers)
                if cpf_t > 0:
                    pcpf = cpf_t / len(all_c)
                    for a in all_c:
                        xf('sys', a, 'cpf', pcpf)

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
    #  Gini by decade
    # ══════════════════════════════════════════════════════
    if hist['gini']:
        step_interval = max(1, len(hist['gini']) // 12)
        gini_by_decade = [hist['gini'][i] for i in range(0, len(hist['gini']), step_interval)]
        if len(gini_by_decade) > 12:
            gini_by_decade = gini_by_decade[:12]
    else:
        gini_by_decade = []

    # ══════════════════════════════════════════════════════
    #  Phase 6 §2: Net Worth Tracking
    # ══════════════════════════════════════════════════════
    # net_worth = cash + land_value + capital
    net_worths = {}
    for w in workers:
        net_worths[w['id']] = bal.get(w['id'], 0) + wland.get(w['id'], 0)
    for r in retirees:
        net_worths[r['id']] = bal.get(r['id'], 0) + rland.get(r['id'], 0)
    for b in businesses:
        net_worths[b['id']] = bal.get(b['id'], 0) + bland.get(b['id'], 0) + b['capital']
    for c in children:
        net_worths[c['id']] = bal.get(c['id'], 0) + c['land']

    nw_values = list(net_worths.values())
    net_worth = sum(nw_values)
    net_worth_gini = compute_gini(nw_values)
    net_worth_mean = np.mean(nw_values) if nw_values else 0.0

    # ══════════════════════════════════════════════════════
    #  Phase 6 §3: Wellbeing Composite
    # ══════════════════════════════════════════════════════
    mean_cash = np.mean(ww) if ww else 0.0
    wellbeing = compute_wellbeing(
        workers, seed, rst,
        gini=compute_gini(ww) if ww else 0.0,
        mean_cash=mean_cash,
        has_insurance=(up or ua or any(
            bal.get(w['id'], 0) > 0 for w in workers
        )),
    )

    # ══════════════════════════════════════════════════════
    #  Phase 6 §5: Family Metrics
    # ══════════════════════════════════════════════════════
    child_count = len(children)
    if use_families and children:
        family_gini = compute_family_gini(children, workers, bal)
    else:
        family_gini = 0.0

    # ══════════════════════════════════════════════════════
    #  Build return dict (Phase 5 backward-compatible + new keys)
    # ══════════════════════════════════════════════════════
    result = {
        'name': name,
        'wealth': sum(bal.values()),
        'gini': round(compute_gini(ww), 4) if ww else 0,
        'w_mean': round(np.mean(ww), 2) if ww else 0,
        'w_min': round(min(ww), 2) if ww else 0,
        'w_max': round(max(ww), 2) if ww else 0,
        'div': round(pc, 2),
        'txns': 0,
        'steps': STEPS,
        'gini_by_decade': gini_by_decade,
        'migration_count': migration_count,
        'policy_path': policy_path,
        # Phase 6 additions
        'net_worth': round(net_worth, 2),
        'net_worth_gini': round(net_worth_gini, 4),
        'net_worth_mean': round(net_worth_mean, 2),
        'wellbeing': wellbeing,
        'child_count': child_count,
        'family_gini': round(family_gini, 4),
    }
    return result


# ═══════════════════════════════════════════════════════════
#  System Configurations — Phase 6 (Phase 5 + Phase 6 flags)
# ═══════════════════════════════════════════════════════════
PHASE6_DEFAULTS = {
    'wire_lvt_evasion': False,
    'use_families': False,
}

PHASE6_CONFIGS = {}
for sys_name, cfg in PHASE5_CONFIGS.items():
    c = copy.deepcopy(cfg)
    c.update(PHASE6_DEFAULTS)
    PHASE6_CONFIGS[sys_name] = c


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
            r = run_phase6(*pop, seed, cfg)
            results[name].append(r)
            extras = []
            if r.get('net_worth_gini', 0) > 0:
                extras.append(f"NW_G={r['net_worth_gini']:.4f}")
            if r.get('wellbeing', 0) > 0:
                extras.append(f"WB={r['wellbeing']:.4f}")
            print(f"  s{seed}: G={r['gini']:.4f} M=${r['w_mean']:>8,.0f} D=${r['div']:>5.2f}"
                  + (f" {' '.join(extras)}" if extras else "")
                  + (f" mig={r.get('migration_count',0)}" if r.get('migration_count', 0) > 0 else ""))
    print(f"\nTime: {time.time()-t0:.0f}s")
    return results


def summarize(results):
    print(f"\n{'='*100}\n  PHASE 6 — SYSTEMS\n{'='*100}")
    print(f"{'System':<22} {'Mean$':>10} {'Gini':>8} {'Div':>8}  {'NW_G':>8} {'WB':>6} {'N':>4}")
    print("-" * 100)
    for sn in results:
        rs = results[sn]
        wm, gs, ds, nwg, wb = (
            [r['w_mean'] for r in rs],
            [r['gini'] for r in rs],
            [r['div'] for r in rs],
            [r['net_worth_gini'] for r in rs],
            [r['wellbeing'] for r in rs],
        )
        print(f"{sn:<22} ${np.mean(wm):>7,.0f} {np.mean(gs):>.4f}±{np.std(gs):.4f} ${np.mean(ds):>5.2f}"
              f"  {np.mean(nwg):>.4f}  {np.mean(wb):.4f}  {len(rs)}")
    for label, key, rev in [
        ("Mean Wealth", 'w_mean', True),
        ("Low Gini", 'gini', False),
        ("Low Net Worth Gini", 'net_worth_gini', False),
        ("High Wellbeing", 'wellbeing', True),
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
    cfg = list(PHASE6_CONFIGS.values())
    print(f"Phase6: {len(seeds)} seeds × {len(cfg)} systems = {len(seeds)*len(cfg)} sims")
    r = run_batch(seeds, cfg)
    summarize(r)
    os.makedirs("output", exist_ok=True)
    json.dump(r, open("output/phase6_results.json", "w"), indent=2)
    print("Saved: output/phase6_results.json")


if __name__ == '__main__':
    main()
