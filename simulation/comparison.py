"""
comparison.py — Calibrated system comparison.
1 step = 1 month. All flows scaled consistently.
Same agents, three rule sets. No doctoring.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from src.core.ledger import LedgerEngine, EntityType

SEED = 42
STEPS = 240  # 20 years monthly
REPORT_INTERVAL = 12  # yearly

# Time calibration
HOURS_PER_STEP = 160  # full-time monthly hours
LVT_ANNUAL_RATE = 0.03  # 3% annually
LVT_MONTHLY_RATE = LVT_ANNUAL_RATE / 12  # 0.25% monthly


def create_population(seed=SEED):
    """Deterministic agent population — same across all runs."""
    rng = np.random.RandomState(seed)
    workers = []
    for i in range(20):
        hourly_wage = rng.uniform(12, 35)  # $12-35/hr (realistic range)
        workers.append({
            'id': f'w{i:03d}',
            'hourly_wage': hourly_wage,
            'monthly_income': hourly_wage * HOURS_PER_STEP,
            'land_value': rng.uniform(20000, 150000),  # $20K-$150K real land
            'risk': rng.uniform(0.01, 0.25),
            'honesty': rng.uniform(0.3, 0.95),
            'inertia': rng.uniform(0.05, 0.25),
            'cash': rng.uniform(10000, 60000),  # realistic savings
        })
    businesses = []
    for i in range(5):
        businesses.append({
            'id': f'b{i:03d}',
            'cash': rng.uniform(100000, 500000),
            'capital': rng.uniform(100000, 400000),
            'tfp': rng.uniform(1.0, 2.0),
            'markup': rng.uniform(1.1, 1.3),
            'liability': rng.uniform(0.01, 0.08),
        })
    return workers, businesses


def make_ledger():
    L = LedgerEngine(step_log=False)
    L.register_entity('_sys', EntityType.SYSTEM, initial_cash=500_000_000)
    L.register_entity('_trust', EntityType.TRUST)
    L.register_entity('_ally', EntityType.ALLIANCE)
    return L


def run_ls(workers, businesses):
    """Liability State: LVT at 0.25%/month, private courts, insurance, Harberger."""
    from src.mechanics.courts import CourtSystem, Court, create_case
    from src.mechanics.insurance import InsuranceMarket

    ledger = make_ledger()
    for w in workers:
        ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
    for b in businesses:
        ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])

    # Insurance
    insurance = InsuranceMarket(ledger, base_rate=0.05, loading_factor=1.3)
    insurance.register_insurer('ins_a', 500000)
    insurance.register_insurer('ins_b', 400000)

    # Courts
    courts = CourtSystem()
    courts.register_court(Court('fast', 'Fast Court', 0.03, 3, 0.7, 0.0))
    
    rng = np.random.RandomState(SEED)
    # Fixed land values (no Harberger — transparent LVT collection)
    worker_land = {w['id']: w['land_value'] for w in workers}
    biz_land = {b['id']: rng.uniform(50000, 200000) for b in businesses}
    
    wid = [w['id'] for w in workers]
    bid = [b['id'] for b in businesses]
    history = {'step': [], 'wealth': [], 'gini': [], 'lit': [], 'pcr': [], 'lvt': [], 'div': []}

    for step in range(1, STEPS + 1):
        ledger.begin_step()

        # Labor — workers earn monthly wage
        for w in workers:
            lab = w['monthly_income'] * rng.uniform(0.9, 1.0)  # slight unemployment risk
            if lab > 0:
                ledger.transfer('_sys', w['id'], 'wage', lab)

        # Businesses — hire, produce, sell
        for b in businesses:
            rev = b['tfp'] * (b['capital'] ** 0.3) * (8 ** 0.7) * b['markup']
            wage_bill = sum(w['monthly_income'] * 0.05 for w in workers)  # simplified
            profit = rev - wage_bill
            if profit > 0:
                ledger.transfer('_sys', b['id'], 'rev', profit)
                inv = profit * 0.3
                if inv > 0:
                    ledger.transfer(b['id'], '_sys', 'invest', inv)
                    b['capital'] += inv

        # Insurance
        for w in workers:
            try:
                p = insurance.price_policy(w['id'], w['risk'], 50000)
                if p < w['cash'] * 0.1:
                    insurance.purchase_policy(w['id'], 'ins_a', w['risk'], 50000)
            except:
                pass
        insurance.run_step()

        # LVT + Dividend (transparent manual collection)
        for w in workers:
            lvt_due = worker_land[w['id']] * LVT_MONTHLY_RATE
            if ledger.balances[w['id']].cash >= lvt_due:
                ledger.transfer(w['id'], '_trust', 'lvt', lvt_due)
            else:
                # Shortfall recorded as liability
                bs = ledger.balances[w['id']]
                bs.outstanding_liability += lvt_due - bs.cash
                if bs.cash > 0:
                    ledger.transfer(w['id'], '_trust', 'lvt', bs.cash)
        for b in businesses:
            lvt_due = biz_land[b['id']] * LVT_MONTHLY_RATE
            if ledger.balances[b['id']].cash >= lvt_due:
                ledger.transfer(b['id'], '_trust', 'lvt', lvt_due)

        total_lvt = sum(t.amount for t in ledger.transfers
                        if t.step == ledger.step and t.mechanism == 'lvt')
        skim = total_lvt * 0.10
        dividend_pool = total_lvt * 0.90
        if skim > 0:
            ledger.transfer('_trust', '_ally', 'alliance_skim', skim)
        per_capita = dividend_pool / len(wid) if len(wid) else 0
        for w_id in wid:
            if per_capita > 0:
                ledger.transfer('_trust', w_id, 'dividend', per_capita)

        # Accidents → court
        for b in businesses:
            if rng.random() < 0.02:
                pl = rng.choice(wid)
                amt = rng.uniform(1000, 20000)
                c = create_case(pl, b['id'], amt, rng.uniform(0.3, 0.8), b['liability'])
                courts.route_case(c, step=step)
        courts.tick(step)

        ledger.close_step()

        if step % REPORT_INTERVAL == 0:
            ww = [ledger.balances[i].cash for i in wid]
            sw = sorted(ww);
            n = len(sw)
            g = (2 * sum((i + 1) * v for i, v in enumerate(sw)) / (n * sum(sw))) - (n + 1) / n if n and sum(
                sw) else 0
            pm = sum(t.amount for t in ledger.transfers if t.mechanism == 'premium')
            cm = sum(t.amount for t in ledger.transfers if t.mechanism == 'claim')
            tl = sum(t.amount for t in ledger.transfers if t.mechanism == 'lvt')
            td = sum(t.amount for t in ledger.transfers
                     if t.step == step and t.mechanism == 'dividend')
            history['step'].append(step)
            history['wealth'].append(sum(b.cash for b in ledger.balances.values()))
            history['gini'].append(round(g, 4))
            history['lit'].append(round(courts.system_summary()['total_cases_filed'] / 20, 4))
            history['pcr'].append(round(pm / max(cm, 0.01), 4))
            history['lvt'].append(round(tl, 2))
            history['div'].append(round(td / len(wid), 2))

    ww = [ledger.balances[i].cash for i in wid]
    sw = sorted(ww);
    n = len(sw)
    g = (2 * sum((i + 1) * v for i, v in enumerate(sw)) / (n * sum(sw))) - (n + 1) / n if n and sum(sw) else 0
    return {'sys': 'Liability State', 'wealth': sum(b.cash for b in ledger.balances.values()),
            'gini': round(g, 4), 'w_mean': np.mean(ww), 'w_min': min(ww), 'w_max': max(ww),
            'transfers': len(ledger.transfers), 'cases': courts.system_summary()['total_cases_filed'],
            'avg_dividend': history['div'][-1] if history['div'] else 0, 'history': history}


def run_us(workers, businesses):
    """US-style: income tax, limited liability, regulation."""
    ledger = make_ledger()
    for w in workers:
        ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
    for b in businesses:
        ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])

    from src.mechanics.courts import Court, create_case
    court = Court('govt', 'Government Court', 0.05, 10, 0.6, 0.05)

    rng = np.random.RandomState(SEED)
    wid = [w['id'] for w in workers]
    history = {'step': [], 'wealth': [], 'gini': [], 'lit': [], 'pcr': [], 'lvt': [], 'div': []}

    for step in range(1, STEPS + 1):
        ledger.begin_step()

        for w in workers:
            pre_tax = w['monthly_income'] * rng.uniform(0.9, 1.0)
            income_tax = pre_tax * 0.20  # 20% effective income tax
            after_tax = pre_tax - income_tax
            if pre_tax > 0:
                ledger.transfer('_sys', w['id'], 'wage', after_tax)
                ledger.transfer(w['id'], '_sys', 'income_tax', income_tax)

        for b in businesses:
            rev = b['tfp'] * (b['capital'] ** 0.3) * (8 ** 0.7) * b['markup']
            compliance = rev * 0.05  # regulatory overhead
            profit = rev - compliance
            if profit > 0:
                corp_tax = profit * 0.21
                after_tax = profit - corp_tax
                ledger.transfer('_sys', b['id'], 'rev', after_tax)
                ledger.transfer(b['id'], '_sys', 'corp_tax', corp_tax)
                inv = after_tax * 0.3
                if inv > 0:
                    ledger.transfer(b['id'], '_sys', 'invest', inv)
                    b['capital'] += inv

        for b in businesses:
            if rng.random() < 0.02:
                pl = rng.choice(wid)
                amt = rng.uniform(1000, 20000) * 0.3  # liability cap
                c = create_case(pl, b['id'], amt, rng.uniform(0.3, 0.8), b['liability'])
                court.file_case(c, step)
                court.tick(step)
                if c.verdict in ('PLAINTIFF_WINS', 'SPLIT'):
                    a = min(amt * rng.uniform(0.5, 1.0), b['cash'] * 0.2)
                    if a > 0:
                        ledger.transfer(b['id'], pl, 'damages', a)

        ledger.close_step()

        if step % REPORT_INTERVAL == 0:
            ww = [ledger.balances[i].cash for i in wid]
            sw = sorted(ww);
            n = len(sw)
            g = (2 * sum((i + 1) * v for i, v in enumerate(sw)) / (n * sum(sw))) - (n + 1) / n if n and sum(
                sw) else 0
            history['step'].append(step)
            history['wealth'].append(sum(b.cash for b in ledger.balances.values()))
            history['gini'].append(round(g, 4))
            history['lit'].append(round(len(court.get_active_cases()) / 20, 4))

    ww = [ledger.balances[i].cash for i in wid]
    sw = sorted(ww);
    n = len(sw)
    g = (2 * sum((i + 1) * v for i, v in enumerate(sw)) / (n * sum(sw))) - (n + 1) / n if n and sum(sw) else 0
    return {'sys': 'US-style', 'wealth': sum(b.cash for b in ledger.balances.values()),
            'gini': round(g, 4), 'w_mean': np.mean(ww), 'w_min': min(ww), 'w_max': max(ww),
            'transfers': len(ledger.transfers), 'history': history}


def run_lf(workers, businesses):
    """Laissez-faire: no tax, no courts, no insurance."""
    ledger = make_ledger()
    for w in workers:
        ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
    for b in businesses:
        ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])

    rng = np.random.RandomState(SEED)
    wid = [w['id'] for w in workers]
    history = {'step': [], 'wealth': [], 'gini': [], 'lit': [], 'pcr': [], 'lvt': [], 'div': []}

    for step in range(1, STEPS + 1):
        ledger.begin_step()

        for w in workers:
            income = w['monthly_income'] * rng.uniform(0.9, 1.0)
            if income > 0:
                ledger.transfer('_sys', w['id'], 'wage', income)

        for b in businesses:
            rev = b['tfp'] * (b['capital'] ** 0.3) * (8 ** 0.7) * b['markup']
            ledger.transfer('_sys', b['id'], 'rev', rev)
            inv = rev * 0.3
            if inv > 0:
                ledger.transfer(b['id'], '_sys', 'invest', inv)
                b['capital'] += inv

        ledger.close_step()

        if step % REPORT_INTERVAL == 0:
            ww = [ledger.balances[i].cash for i in wid]
            sw = sorted(ww);
            n = len(sw)
            g = (2 * sum((i + 1) * v for i, v in enumerate(sw)) / (n * sum(sw))) - (n + 1) / n if n and sum(
                sw) else 0
            history['step'].append(step)
            history['wealth'].append(sum(b.cash for b in ledger.balances.values()))
            history['gini'].append(round(g, 4))

    ww = [ledger.balances[i].cash for i in wid]
    sw = sorted(ww);
    n = len(sw)
    g = (2 * sum((i + 1) * v for i, v in enumerate(sw)) / (n * sum(sw))) - (n + 1) / n if n and sum(sw) else 0
    return {'sys': 'Laissez-Faire', 'wealth': sum(b.cash for b in ledger.balances.values()),
            'gini': round(g, 4), 'w_mean': np.mean(ww), 'w_min': min(ww), 'w_max': max(ww),
            'transfers': len(ledger.transfers), 'history': history}


def print_table(results):
    print("\n" + "=" * 80)
    print("  SYSTEM COMPARISON — IDENTICAL AGENTS, 240 STEPS (20 YEARS)")
    print(f"  1 step = 1 month. LVT = {LVT_ANNUAL_RATE*100:.0f}%/year ({LVT_MONTHLY_RATE*100:.2f}%/month)")
    print("=" * 80)
    metrics = [
        ('Final Total Wealth', 'wealth', '${:,.0f}'),
        ('Worker Wealth Mean', 'w_mean', '${:,.0f}'),
        ('Worker Wealth Min', 'w_min', '${:,.0f}'),
        ('Worker Wealth Max', 'w_max', '${:,.0f}'),
        ('Gini Coefficient', 'gini', '{:.4f}'),
        ('Avg Monthly Dividend', 'avg_dividend', '${:,.2f}'),
        ('Total Transfers', 'transfers', '{:,}'),
    ]
    h = f"{'Metric':<30}" + "".join(f"  {r['sys'][:20]:>20}" for r in results)
    print(h);
    print("-" * 80)
    for name, key, fmt in metrics:
        row = f"{name:<30}"
        for r in results:
            if key in r:
                row += f"  {fmt.format(r[key]):>20}"
            else:
                row += f"  {'N/A':>20}"
        print(row)

    print(f"\n{'Gini Over Time':<30}" + "".join(f"  {r['sys'][:20]:>20}" for r in results))
    print("-" * 80)
    for s in [12, 60, 120, 180, 240]:  # years 1, 5, 10, 15, 20
        row = f"{'Year '+str(s//12):<30}"
        for res in results:
            h = res['history']
            if s in h['step']:
                row += f"  {h['gini'][h['step'].index(s)]:>20.4f}"
            else:
                row += f"  {'—':>20}"
        print(row)

    # Worker income check
    print(f"\n{'Worker Income Check':<30}")
    print("-" * 80)
    for w in workers[:3]:
        print(f"  {w['id']}: ${w['hourly_wage']:.0f}/hr × 160hrs = ${w['monthly_income']:,.0f}/mo, "
              f"land=${w['land_value']:,.0f}")


if __name__ == '__main__':
    workers, businesses = create_population()
    print(f"Population: {len(workers)} workers, {len(businesses)} businesses")
    print(f"Worker income range: ${min(w['monthly_income'] for w in workers):,.0f}"
          f" — ${max(w['monthly_income'] for w in workers):,.0f}/month")
    print(f"Land value range: ${min(w['land_value'] for w in workers):,.0f}"
          f" — ${max(w['land_value'] for w in workers):,.0f}")
    print(f"LVT: {LVT_ANNUAL_RATE*100:.0f}%/year, {LVT_MONTHLY_RATE*100:.2f}%/month\n")

    results = []
    for name, fn in [('Liability State', run_ls), ('US-style', run_us), ('Laissez-Faire', run_lf)]:
        print(f"Running {name}...", end=' ', flush=True)
        try:
            r = fn(workers, businesses)
            print(f"Gini={r['gini']}")
            if 'avg_dividend' in r:
                print(f"  Avg Dividend: ${r['avg_dividend']:.2f}/month")
            results.append(r)
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback;
            traceback.print_exc()

    if len(results) == 3:
        print_table(results)
        os.makedirs('output', exist_ok=True)
        with open('output/comparison.json', 'w') as f:
            json.dump([{k: v for k, v in r.items() if k != 'history'} for r in results], f, indent=2)
