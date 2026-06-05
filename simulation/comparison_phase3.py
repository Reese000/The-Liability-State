#!/usr/bin/env python3
"""
comparison_phase3.py — Phase 3 multi-system comparison with ALL fixes.

Integrates:
- Adversarial behavior (StrategyController)
- Community-rated insurance pooling (cross-subsidization)
- Event injection (MassTort, Recession shocks)
- Compact competition (2 compacts with different court biases)
- Endogenous TFP (productivity responds to tax burden)
- Longer horizon (480 steps = 40 years)

Usage:
  python comparison_phase3.py [--seeds 5] [--steps 480]
"""
import sys, os, json, time, logging
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s:%(message)s')

from core.ledger import LedgerEngine, EntityType
from mechanics.courts import CourtSystem, Court, create_case
from mechanics.insurance import InsuranceMarket

from adversarial_bridge import setup_controller, choose_agent_strategy, adapt_agent_behavior
from insurance_pooling_bridge import setup_pooled_insurance, process_claims_pooled, get_pooled_premium
from event_injection_bridge import setup_events, apply_event_modifiers
from compact_competition_bridge import create_compacts, assign_compact_ids, get_compact_lvt_modifier, get_compact_litigation_rate

SEEDS = list(range(1, 6))  # 5 seeds for Phase 3
STEPS = 480  # 40 years monthly
REPORT_INTERVAL = 12
LVT_ANNUAL_RATE = 0.03
LVT_MONTHLY_RATE = LVT_ANNUAL_RATE / 12
HOURS_PER_STEP = 160

# ─── Constants ────────────────────────────────────────────────────────
INVESTMENT_RATE = 0.3
BUSINESS_WAGE_BILL = 5000.0
WAGE_VARIABILITY = (0.92, 1.0)
ACCIDENT_PROBABILITY = 0.02

# TFP parameters: TFP responds to tax burden
# Higher tax burden → lower TFP (disincentive effect)
# Tax burden = (total taxes paid) / (total revenue)
TFP_BASELINE = 1.0
TFP_TAX_ELASTICITY = -0.15  # 10% higher tax burden → 1.5% lower TFP

SYSTEMS = []
SYSTEM_NAMES = []

def make_ledger():
    L = LedgerEngine(step_log=False)
    L.register_entity('sys', EntityType.SYSTEM, initial_cash=500_000_000)
    L.register_entity('trust', EntityType.TRUST)
    L.register_entity('ally', EntityType.ALLIANCE)
    return L

def gen_population(seed):
    rng = np.random.RandomState(seed)
    workers = []
    for i in range(50):
        hourly = rng.uniform(10, 40)
        workers.append({
            'id': f'w{i:03d}', 'hourly': hourly,
            'monthly': hourly * HOURS_PER_STEP,
            'land': rng.uniform(20000, 200000),
            'risk': rng.uniform(0.01, 0.25),
            'cash': rng.uniform(10000, 80000),
            'honesty': rng.uniform(0.3, 0.95),
            'inertia': rng.uniform(0.05, 0.25),
            'concealment': rng.uniform(0.0, 0.2),
        })
    businesses = []
    for i in range(10):
        businesses.append({
            'id': f'b{i:03d}', 'cash': rng.uniform(100000, 500000),
            'capital': rng.uniform(100000, 400000),
            'tfp': rng.uniform(1.0, 2.0), 'markup': rng.uniform(1.1, 1.3),
            'honesty': rng.uniform(0.3, 0.9),
        })
    return workers, businesses


# ═══════════════════════════════════════════════════════════════════════
#  Run phase 3 simulation for a given config dictionary
# ═══════════════════════════════════════════════════════════════════════

def run_phase3(workers, businesses, seed, config):
    """
    config dict keys:
      system_name    — label for this run
      use_adversarial — wire adversarial controller?
      use_pooled_insurance — community-rated pooling?
      use_events     — inject shocks at step (default: STEPS//4)?
      use_compacts   — split into 2 compacts?
      use_endogenous_tfp — TFP responds to tax burden?
      tax_type       — 'lvt', 'income', 'none'
      lvt_rate       — annual LVT rate (float)
      income_tax_rate — flat income tax rate
      corp_tax_rate  — corporate tax rate
    """
    name = config.get('system_name', 'Phase3')
    use_adversarial = config.get('use_adversarial', False)
    use_pooled = config.get('use_pooled_insurance', False)
    use_events = config.get('use_events', False)
    use_compacts = config.get('use_compacts', False)
    use_endogenous_tfp = config.get('use_endogenous_tfp', False)
    tax_type = config.get('tax_type', 'lvt')
    lvt_rate = config.get('lvt_rate', LVT_ANNUAL_RATE)
    income_tax_rate = config.get('income_tax_rate', 0.0)
    corp_tax_rate = config.get('corp_tax_rate', 0.0)

    _log = logging.getLogger(f'phase3_{name[:20].replace(" ","_")}')

    # ── Setup ledger ───────────────────────────────────────────────
    ledger = make_ledger()
    rng = np.random.RandomState(seed)
    for w in workers: ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
    for b in businesses: ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])

    # ── Compacts ───────────────────────────────────────────────────
    if use_compacts:
        compacts, wmap, bmap = create_compacts(workers, businesses, n_compacts=2, seed=seed)
        assign_compact_ids(workers, businesses, wmap, bmap)
    else:
        wmap = {w['id']: 'compact_0' for w in workers}
        bmap = {b['id']: 'compact_0' for b in businesses}
        compacts = {'compact_0': {'id': 'compact_0', 'name': 'Default', 'court_bias': 0.7, 'litigation_rate': 0.02, 'lvt_modifier': 1.0}}

    # ── Courts ────────────────────────────────────────────────────
    if use_compacts:
        courts = CourtSystem()
        for cid, cdata in compacts.items():
            court_bias = cdata['court_bias']
            bias_param = (court_bias - 0.5) / 2.0  # 0.5→0.0, 0.9→0.2
            courts.register_court(Court(cid, f'{cdata["name"]} Court', 0.03, 5, bias_param, 0.0))
    else:
        courts = CourtSystem()
        courts.register_court(Court('fast', 'Default Court', 0.03, 5, 0.0, 0.0))

    # ── Insurance ──────────────────────────────────────────────────
    if use_pooled:
        # Community-rated: everyone pays same premium
        insurance_policies = setup_pooled_insurance(workers, ledger, loading=1.2)
        mutual_pool = sum(p['premium'] for p in insurance_policies.values() if p.get('paid'))
    else:
        # Risk-based: existing InsuranceMarket model
        insurance = InsuranceMarket(ledger, base_rate=0.05, loading_factor=1.3)
        insurance.register_insurer('ins_a', 500000)
        insurance.register_insurer('ins_b', 400000)
        mutual_pool = 0  # Not used in risk-based mode

    # ── Adversarial controller ─────────────────────────────────────
    controller = None
    if use_adversarial:
        controller = setup_controller(honesty_mean=0.7)
        # Track which agents are adversarial
        agent_strategies = {}

    # ── Events ─────────────────────────────────────────────────────
    event_manager = None
    shock_step = STEPS // 4  # Shock at quarter point
    if use_events:
        event_manager = setup_events(step_shock=shock_step)

    # ── Land values ────────────────────────────────────────────────
    lvt_monthly_rate = (lvt_rate / 12) if tax_type == 'lvt' else 0.0
    wland = {w['id']: w['land'] for w in workers}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}

    wid = [w['id'] for w in workers]
    bid = [b['id'] for b in businesses]
    hist = {'gini':[], 'wealth':[], 'wmin':[], 'wmean':[], 'div':[]}
    event_log = []

    # ── Main simulation loop ───────────────────────────────────────
    for step in range(1, STEPS + 1):
        try:
            ledger.begin_step()

            # ── 0. Event injection ─────────────────────────────────
            demand_mult = 1.0
            claim_freq_mult = 1.0
            if event_manager:
                logs = event_manager.fire_events({'workers': workers, 'businesses': businesses, 'ledger': ledger, 'courts': courts}, step)
                event_log.extend(logs)
                mods = event_manager.get_active_modifiers(step)
                if 'demand_multiplier' in mods:
                    demand_mult = mods['demand_multiplier']
                if 'claim_freq_multiplier' in mods:
                    claim_freq_mult = mods['claim_freq_multiplier']
                # Apply land value reductions
                if 'land_value_multiplier' in mods:
                    for w in workers:
                        wland[w['id']] *= mods['land_value_multiplier']
                    for b in businesses:
                        bland[b['id']] *= mods['land_value_multiplier']

            # ── 1. Wages ───────────────────────────────────────────
            # Check adversarial modifier for wage (e.g., premium evasion reduces declared income)
            for w in workers:
                inc = w['monthly'] * rng.uniform(*WAGE_VARIABILITY)
                if inc > 0:
                    # TFP effect: higher tax burden → lower productivity → lower wages
                    if use_endogenous_tfp:
                        # Estimate effective tax rate for this worker
                        if tax_type == 'income' and income_tax_rate > 0:
                            effective_tax = income_tax_rate
                        elif tax_type == 'lvt':
                            # LVT burden as % of income
                            annual_lvt = wland[w['id']] * lvt_rate
                            effective_tax = min(0.5, annual_lvt / max(w['monthly'] * 12, 1))
                        else:
                            effective_tax = 0.0
                        tfp_factor = max(0.5, 1.0 + TFP_TAX_ELASTICITY * effective_tax)
                        inc *= tfp_factor
                    ledger.transfer('sys', w['id'], 'wage', inc)

            # ── 2. Business activity ───────────────────────────────
            for b in businesses:
                try:
                    # Base revenue with demand multiplier from events
                    tfp = b['tfp']
                    rev = tfp * (b['capital'] ** 0.3) * (8 ** 0.7) * b['markup'] * demand_mult

                    # Adversarial: collusion adds markup
                    adv_markup = 1.0
                    if controller and b['id'] in agent_strategies:
                        astrat = agent_strategies[b['id']]
                        if astrat == 'Collusion':
                            adv_markup = 1.15

                    rev *= adv_markup
                    profit = rev - BUSINESS_WAGE_BILL

                    if profit > 0:
                        # Tax
                        tax_amount = 0.0
                        if tax_type == 'income' and corp_tax_rate > 0:
                            tax_amount = profit * corp_tax_rate

                        after_tax = profit - tax_amount

                        if tax_amount > 0:
                            ledger.transfer(b['id'], 'sys', 'corp_tax', tax_amount)

                        ledger.transfer('sys', b['id'], 'rev', after_tax)
                        inv = after_tax * INVESTMENT_RATE
                        if inv > 0:
                            ledger.transfer(b['id'], 'sys', 'invest', inv)
                            b['capital'] += inv
                except Exception as e:
                    _log.warning('Step %d biz %s: %s', step, b['id'], e)

            # ── 3. Insurance ───────────────────────────────────────
            if use_pooled:
                # Process claims from pooled fund
                claim_prob = 0.3 * claim_freq_mult  # accident probability = risk * 0.3 * multiplier
                mutual_pool, _ = process_claims_pooled(
                    workers, ledger, mutual_pool, rng, step,
                    claim_prob_mult=claim_prob,
                )
            else:
                # Risk-based InsuranceMarket
                for w in workers:
                    try:
                        p = insurance.price_policy(w['id'], w['risk'], 50000)
                        if p < ledger.balances[w['id']].cash * 0.1:
                            insurance.purchase_policy(w['id'], 'ins_a', w['risk'], 50000)
                    except Exception:
                        pass
                insurance.run_step()

            # ── 4. Adversarial strategy evaluation ─────────────────
            if controller:
                # Evaluate all agents each step
                for w in workers:
                    strat, ev, det = choose_agent_strategy(controller, w, ledger, step, rng)
                    if strat:
                        agent_strategies[w['id']] = strat
                        mods = adapt_agent_behavior(w, strat, ledger, step, rng)
                        # Apply modifications
                        if 'declared_risk' in mods:
                            w['risk'] = mods['declared_risk']
                for b in businesses:
                    strat, ev, det = choose_agent_strategy(controller, b, ledger, step, rng)
                    if strat:
                        agent_strategies[b['id']] = strat

            # ── 5. LVT / Tax collection ────────────────────────────
            if tax_type == 'lvt':
                # Get compact-specific LVT modifier
                for w in workers:
                    try:
                        cid = wmap.get(w['id'], 'compact_0')
                        lvt_mod = get_compact_lvt_modifier(cid, compacts) if use_compacts else 1.0
                        effective_monthly = lvt_monthly_rate * lvt_mod
                        d = wland[w['id']] * effective_monthly
                        if ledger.balances[w['id']].cash >= d:
                            ledger.transfer(w['id'], 'trust', 'lvt', d)
                    except Exception as e:
                        _log.warning('Step %d LVT w %s: %s', step, w['id'], e)
                for b in businesses:
                    try:
                        cid = bmap.get(b['id'], 'compact_0')
                        lvt_mod = get_compact_lvt_modifier(cid, compacts) if use_compacts else 1.0
                        effective_monthly = lvt_monthly_rate * lvt_mod
                        d = bland[b['id']] * effective_monthly
                        if ledger.balances[b['id']].cash >= d:
                            ledger.transfer(b['id'], 'trust', 'lvt', d)
                    except Exception as e:
                        _log.warning('Step %d LVT b %s: %s', step, b['id'], e)

            elif tax_type == 'income':
                # Income tax on wages
                for w in workers:
                    try:
                        if hasattr(ledger, 'step'):
                            step_transfers = [t for t in ledger.transfers if t.step == step and t.mechanism == 'wage' and t.entity_id == w['id']]
                            for t in step_transfers:
                                wage = t.amount
                                tax = wage * income_tax_rate
                                if tax > 0:
                                    try:
                                        ledger.transfer(w['id'], 'sys', 'income_tax', tax)
                                    except Exception:
                                        pass
                    except Exception:
                        pass

            # ── 6. Dividend (if LVT) ──────────────────────────────
            if tax_type == 'lvt':
                tl = sum(t.amount for t in ledger.transfers if t.step == ledger.step and t.mechanism == 'lvt')
                pc = tl * 0.90 / len(wid) if tl > 0 else 0
                if tl * 0.10 > 0:
                    try:
                        ledger.transfer('trust', 'ally', 'skim', tl * 0.10)
                    except Exception:
                        pass
                for w_id in wid:
                    if pc > 0:
                        try:
                            ledger.transfer('trust', w_id, 'dividend', pc)
                        except Exception:
                            pass
            else:
                pc = 0.0

            # ── 7. Courts ──────────────────────────────────────────
            for b in businesses:
                try:
                    cid = bmap.get(b['id'], 'compact_0')
                    lit_rate = get_compact_litigation_rate(cid, compacts) if use_compacts else ACCIDENT_PROBABILITY
                except Exception:
                    lit_rate = ACCIDENT_PROBABILITY

                if rng.random() < lit_rate:
                    try:
                        pl = rng.choice(wid)
                        amt = rng.uniform(1000, 20000)
                        c = create_case(pl, b['id'], amt, rng.uniform(0.3, 0.8), 0.1)
                        courts.route_case(c, step=step)
                    except Exception:
                        pass
            courts.tick(step)

            # ── 8. Welfare (if income tax system) ──────────────────
            if tax_type == 'income' and income_tax_rate > 0:
                total_tax = sum(t.amount for t in ledger.transfers if t.step == step and t.mechanism == 'income_tax')
                welfare = total_tax * 0.15
                if welfare > 0:
                    per = welfare / len(wid)
                    for w_id in wid:
                        try:
                            ledger.transfer('sys', w_id, 'welfare', per)
                        except Exception:
                            pass

            ledger.close_step()

        except Exception as e:
            _log.error('Fatal at step %d: %s', step, e)
            try:
                ledger.close_step()
            except Exception:
                pass
            break

        # ── Report ────────────────────────────────────────────────
        if step % REPORT_INTERVAL == 0:
            ww = [ledger.balances[i].cash for i in wid if i in ledger.balances]
            if ww:
                sw = sorted(ww); n = len(sw)
                g = (2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
                hist['gini'].append(round(g, 4))
                hist['wealth'].append(sum(b.cash for b in ledger.balances.values()))
                hist['wmin'].append(min(ww))
                hist['wmean'].append(np.mean(ww))
                hist['div'].append(pc)

    # ── Final metrics ─────────────────────────────────────────────
    ww = [ledger.balances[i].cash for i in wid if i in ledger.balances]
    if ww:
        sw = sorted(ww); n = len(sw)
        g = (2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
    else:
        g = 0.0

    return {
        'name': name,
        'wealth': sum(b.cash for b in ledger.balances.values()),
        'gini': round(g, 4),
        'w_mean': round(np.mean(ww), 2) if ww else 0,
        'w_min': round(min(ww), 2) if ww else 0,
        'w_max': round(max(ww), 2) if ww else 0,
        'div': round(pc, 2),
        'txns': len(ledger.transfers),
        'steps': STEPS,
        'config': {k: v for k, v in config.items() if isinstance(v, (str, int, float, bool))},
    }


# ═══════════════════════════════════════════════════════════════════════
#  Experiment configurations
# ═══════════════════════════════════════════════════════════════════════

def build_experiments():
    """Return a list of config dicts, one per system/scenario."""
    exps = []

    # Phase 0 baseline (replicates comparison_batch.py LS)
    exps.append({
        'system_name': 'Phase0_LS_Baseline',
        'use_adversarial': False,
        'use_pooled_insurance': False,
        'use_events': False,
        'use_compacts': False,
        'use_endogenous_tfp': False,
        'tax_type': 'lvt',
        'lvt_rate': 0.03,
        'income_tax_rate': 0.0,
        'corp_tax_rate': 0.0,
    })

    # Phase 3a: LS + adversarial
    exps.append({
        'system_name': 'LS_Adversarial',
        'use_adversarial': True,
        'use_pooled_insurance': False,
        'use_events': False,
        'use_compacts': False,
        'use_endogenous_tfp': False,
        'tax_type': 'lvt',
        'lvt_rate': 0.03,
    })

    # Phase 3b: LS + adversarial + pooled insurance
    exps.append({
        'system_name': 'LS_PooledIns',
        'use_adversarial': True,
        'use_pooled_insurance': True,
        'use_events': False,
        'use_compacts': False,
        'use_endogenous_tfp': False,
        'tax_type': 'lvt',
        'lvt_rate': 0.03,
    })

    # Phase 3c: LS + full (adversarial + pooled + compacts + events)
    exps.append({
        'system_name': 'LS_Full',
        'use_adversarial': True,
        'use_pooled_insurance': True,
        'use_events': True,
        'use_compacts': True,
        'use_endogenous_tfp': True,
        'tax_type': 'lvt',
        'lvt_rate': 0.03,
    })

    # US-style with adversarial (for comparison)
    exps.append({
        'system_name': 'US_Adversarial',
        'use_adversarial': True,
        'use_pooled_insurance': False,
        'use_events': True,
        'use_compacts': True,
        'use_endogenous_tfp': True,
        'tax_type': 'income',
        'income_tax_rate': 0.20,
        'corp_tax_rate': 0.21,
    })

    return exps


# ═══════════════════════════════════════════════════════════════════════
#  Runner
# ═══════════════════════════════════════════════════════════════════════

def run_batch(seeds, experiments):
    results = {e['system_name']: [] for e in experiments}
    total = len(seeds) * len(experiments)
    t0 = time.time()

    for exp in experiments:
        name = exp['system_name']
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")

        for seed in seeds:
            pop = gen_population(seed)
            r = run_phase3(*pop, seed, exp)
            results[name].append(r)
            print(f"  seed {seed:3d}: Gini={r['gini']:.4f}  Mean=${r['w_mean']:>9,.0f}  "
                  f"Div=${r['div']:>6.2f}  Steps={r['steps']}")

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    return results


def summarize(results):
    print(f"\n{'='*120}")
    print("  PHASE 3 COMPARISON")
    print('='*120)

    header = f"{'System':<28} {'Mean Wealth':>12} {'Min Wealth':>12} {'Max Wealth':>12} {'Gini Mean':>10} {'Gini SD':>9} {'Dividend':>10} {'Steps':>8}"
    print(header)
    print('-'*120)

    for sys_name in results:
        runs = results[sys_name]
        w_means = [r['w_mean'] for r in runs]
        w_mins = [r['w_min'] for r in runs]
        w_maxs = [r['w_max'] for r in runs]
        ginis = [r['gini'] for r in runs]
        divs = [r['div'] for r in runs]
        steps = runs[0]['steps'] if runs else 0

        print(f"{sys_name:<28} "
              f"${np.mean(w_means):>10,.0f} ± ${np.std(w_means):>7,.0f} "
              f"${np.mean(w_mins):>10,.0f} "
              f"${np.mean(w_maxs):>10,.0f} "
              f"{np.mean(ginis):>8.4f}  ±{np.std(ginis):>6.4f} "
              f"${np.mean(divs):>7.2f} "
              f"{steps:>8}")

    # Ranking
    print(f"\n{'Rank by Mean Worker Wealth':^80}")
    print('-'*80)
    ranked = sorted([(np.mean([r['w_mean'] for r in results[sn]]), sn) for sn in results], reverse=True)
    for i, (val, name) in enumerate(ranked, 1):
        print(f"  {i}. {name:<30} ${val:>10,.0f}")

    print(f"\n{'Rank by Lowest Inequality (Gini)':^80}")
    print('-'*80)
    ranked = sorted([(np.mean([r['gini'] for r in results[sn]]), sn) for sn in results])
    for i, (val, name) in enumerate(ranked, 1):
        print(f"  {i}. {name:<30} {val:.4f}")


if __name__ == '__main__':
    seeds = SEEDS
    if '--quick' in sys.argv:
        seeds = list(range(1, 3))

    experiments = build_experiments()
    print(f"Running {len(seeds)} seeds × {len(experiments)} experiments = {len(seeds)*len(experiments)} simulations")
    print(f"Each: {STEPS} steps (40 years) with 50 workers, 10 businesses")

    results = run_batch(seeds, experiments)
    summarize(results)

    # Save
    os.makedirs('output', exist_ok=True)
    with open('output/phase3_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to output/phase3_results.json")
