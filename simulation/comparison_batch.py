"""
comparison_batch.py — Batched multi-system comparison framework.

Runs N seeds for each system, collects statistics, reports means and variances.
Systems modeled:
  1. Liability State (full: LVT, Dividend, private courts, insurance, guild mutual)
  2. US-style (income tax, regulation, limited liability, welfare, public courts)
  3. Nordic Social Democracy (high tax, strong welfare state, unions, public courts)
  4. Singapore-style (mandatory savings, state-led development, property tax)
  5. Pure Georgist (LVT + flat dividend, no LS legal/insurance system)
  6. Laissez-Faire (no tax, no courts, no insurance)
"""
import sys, os, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from src.core.ledger import LedgerEngine, EntityType

SEEDS = list(range(1, 21))  # 20 seeds per system
STEPS = 240  # 20 years monthly
REPORT_INTERVAL = 12

LVT_ANNUAL_RATE = 0.03
LVT_MONTHLY_RATE = LVT_ANNUAL_RATE / 12
HOURS_PER_STEP = 160

# ─── Singapore Model Constants ──────────────────────────────────
SINGAPORE_CPF_EMPLOYEE_RATE = 0.20     # Employee CPF contribution (% of gross)
SINGAPORE_CPF_EMPLOYER_RATE = 0.17     # Employer CPF contribution (% of gross)
SINGAPORE_CPF_TOTAL_RATE = SINGAPORE_CPF_EMPLOYEE_RATE + SINGAPORE_CPF_EMPLOYER_RATE  # 0.37
SINGAPORE_PROPERTY_ANNUAL = 0.05       # Annual property tax rate (5%)
SINGAPORE_PROPERTY_MONTHLY = SINGAPORE_PROPERTY_ANNUAL / 12  # 0.4167% monthly
SINGAPORE_CORP_TAX_RATE = 0.17         # Corporate tax rate (17%)
SINGAPORE_WELFARE_SHARE = 0.10         # Fraction of tax revenue for welfare
SINGAPORE_CPF_WITHDRAWAL_RATE = 0.005  # Monthly CPF withdrawal rate (0.5%)
SINGAPORE_LITIGATION_RATE = 0.01       # Per-business litigation probability
SINGAPORE_WAGE_BILL_ESTIMATE = 5000.0  # Estimated monthly wage bill per business

# ─── Mutualist Model Constants ──────────────────────────────────
MUTUAL_RISK_MULTIPLIER = 0.8           # Risk premium discount vs for-profit (no profit margin)
MUTUAL_LOADING_FACTOR = 1.1            # Mutual pool loading (1.1 vs 1.3 for private)
MUTUAL_COVERAGE_LIMIT = 50000.0        # Standard coverage amount per policy
MUTUAL_PREMIUM_CAP_RATIO = 0.15        # Max premium as fraction of cash balance
MUTUAL_ACCIDENT_PROB_MULTIPLIER = 0.3  # Accident probability = risk * this
MUTUAL_POOL_EXHAUSTION_RATIO = 0.9     # Fraction of remaining pool paid when exhausted

# ─── General Model Constants ────────────────────────────────────
BUSINESS_WAGE_BILL = 5000.0            # Monthly wage bill per business
INVESTMENT_RATE = 0.3                  # Fraction of profit reinvested
WAGE_VARIABILITY = (0.92, 1.0)         # Range for stochastic wage variation
ACCIDENT_PROBABILITY = 0.02            # Per-business litigation probability (LS)
COURT_ACCIDENT_PROBABILITY = 0.02      # Per-business accident probability


def make_ledger():
    L = LedgerEngine(step_log=False)
    L.register_entity('sys', EntityType.SYSTEM, initial_cash=500_000_000)
    L.register_entity('trust', EntityType.TRUST)
    L.register_entity('ally', EntityType.ALLIANCE)
    return L


def gen_population(seed):
    """Deterministic agent population per seed."""
    rng = np.random.RandomState(seed)
    workers = []
    for i in range(50):  # 50 workers for better stats
        hourly = rng.uniform(10, 40)
        workers.append({
            'id': f'w{i:03d}', 'hourly': hourly,
            'monthly': hourly * HOURS_PER_STEP,
            'land': rng.uniform(20000, 200000),
            'risk': rng.uniform(0.01, 0.25),
            'cash': rng.uniform(10000, 80000),
        })
    businesses = []
    for i in range(10):
        businesses.append({
            'id': f'b{i:03d}', 'cash': rng.uniform(100000, 500000),
            'capital': rng.uniform(100000, 400000),
            'tfp': rng.uniform(1.0, 2.0), 'markup': rng.uniform(1.1, 1.3),
        })
    return workers, businesses


# ─── SYSTEM RUNNERS ─────────────────────────────────────────────

def run_ls(workers, businesses, seed):
    """Liability State: LVT 3% annual, Dividend, private courts, insurance, guild mutuals."""
    from src.mechanics.courts import CourtSystem, Court, create_case
    from src.mechanics.insurance import InsuranceMarket
    ledger = make_ledger()
    rng = np.random.RandomState(seed)
    for w in workers: ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
    for b in businesses: ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])

    insurance = InsuranceMarket(ledger, base_rate=0.05, loading_factor=1.3)
    insurance.register_insurer('ins_a', 500000); insurance.register_insurer('ins_b', 400000)
    courts = CourtSystem()
    courts.register_court(Court('fast', 'Fast Court', 0.03, 3, 0.7, 0.0))

    wland = {w['id']: w['land'] for w in workers}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}
    wid = [w['id'] for w in workers]
    hist = {'gini':[], 'wealth':[], 'wmin':[], 'wmean':[], 'div':[]}

    for step in range(1, STEPS+1):
        ledger.begin_step()
        # Wages
        for w in workers:
            inc = w['monthly'] * rng.uniform(0.92, 1.0)
            if inc > 0: ledger.transfer('sys', w['id'], 'wage', inc)
        # Business
        for b in businesses:
            rev = b['tfp']*(b['capital']**0.3)*(8**0.7)*b['markup']
            profit = rev - 5000
            if profit > 0:
                ledger.transfer('sys', b['id'], 'rev', profit)
                inv = profit*0.3
                if inv > 0: ledger.transfer(b['id'], 'sys', 'invest', inv); b['capital'] += inv
        # Insurance
        for w in workers:
            try:
                p = insurance.price_policy(w['id'], w['risk'], 50000)
                if p < w['cash']*0.1: insurance.purchase_policy(w['id'], 'ins_a', w['risk'], 50000)
            except: pass
        insurance.run_step()
        # LVT
        for w in workers:
            d = wland[w['id']]*LVT_MONTHLY_RATE
            if ledger.balances[w['id']].cash >= d:
                ledger.transfer(w['id'], 'trust', 'lvt', d)
        # Guild mutual contribution (2% of income)
        for w in workers:
            inc = w['monthly'] * rng.uniform(0.92, 1.0)
            mutual = inc * 0.02
            if ledger.balances[w['id']].cash >= mutual:
                ledger.transfer(w['id'], 'trust', 'mutual', mutual)
        for b in businesses:
            d = bland[b['id']]*LVT_MONTHLY_RATE
            if ledger.balances[b['id']].cash >= d:
                ledger.transfer(b['id'], 'trust', 'lvt', d)
        # Dividend
        tl = sum(t.amount for t in ledger.transfers if t.step==ledger.step and t.mechanism in ('lvt','mutual'))
        pc = tl*0.90/len(wid)
        if tl*0.10>0: ledger.transfer('trust', 'ally', 'skim', tl*0.10)
        for w_id in wid:
            if pc>0: ledger.transfer('trust', w_id, 'dividend', pc)
        # Courts
        for b in businesses:
            if rng.random()<0.02:
                pl = rng.choice(wid)
                c = create_case(pl, b['id'], rng.uniform(1000,20000), rng.uniform(0.3,0.8), 0.1)
                courts.route_case(c, step=step)
        courts.tick(step)
        ledger.close_step()
        if step%REPORT_INTERVAL==0:
            ww=[ledger.balances[i].cash for i in wid]
            sw=sorted(ww); n=len(sw)
            g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
            hist['gini'].append(round(g,4)); hist['wealth'].append(sum(b.cash for b in ledger.balances.values()))
            hist['wmin'].append(min(ww)); hist['wmean'].append(np.mean(ww))
            hist['div'].append(pc)
    ww=[ledger.balances[i].cash for i in wid]
    sw=sorted(ww); n=len(sw)
    g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
    return {'name':'Liability State','wealth':sum(b.cash for b in ledger.balances.values()),
            'gini':round(g,4),'w_mean':round(np.mean(ww),2),'w_min':round(min(ww),2),
            'w_max':round(max(ww),2),'div':round(pc,2),'txns':len(ledger.transfers)}


def run_us(workers, businesses, seed):
    """US-style: 20% income tax, 21% corp tax, 5% regulatory overhead,
    welfare spending (15% of tax revenue), limited liability (cap at 30%),
    public courts."""
    from src.mechanics.courts import Court, create_case
    ledger = make_ledger()
    rng = np.random.RandomState(seed)
    for w in workers: ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
    for b in businesses: ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])
    court = Court('govt','Govt Court',0.05,10,0.6,0.05)
    wid = [w['id'] for w in workers]
    hist = {'gini':[],'wealth':[],'wmin':[],'wmean':[],'div':[]}

    for step in range(1, STEPS+1):
        ledger.begin_step()
        total_tax = 0.0
        for w in workers:
            pre = w['monthly'] * rng.uniform(0.92, 1.0)
            tax = pre*0.20; after = pre-tax
            if pre>0: ledger.transfer('sys', w['id'], 'wage', after); ledger.transfer(w['id'], 'sys', 'tax', tax)
            total_tax += tax
        for b in businesses:
            rev = b['tfp']*(b['capital']**0.3)*(8**0.7)*b['markup']
            compliance = rev*0.05; profit = rev-compliance
            if profit>0:
                ct = profit*0.21; after = profit-ct
                ledger.transfer('sys', b['id'], 'rev', after); ledger.transfer(b['id'], 'sys', 'tax', ct)
                total_tax += ct
                inv = after*0.3
                if inv>0: ledger.transfer(b['id'], 'sys', 'invest', inv); b['capital'] += inv
        # Welfare: 15% of tax revenue distributed as welfare payments
        welfare = total_tax*0.15
        if welfare>0:
            per = welfare/len(wid)
            for w_id in wid: ledger.transfer('sys', w_id, 'welfare', per)
        # Courts
        for b in businesses:
            if rng.random()<0.02:
                pl = rng.choice(wid)
                amt = rng.uniform(1000,20000)*0.3
                c = create_case(pl, b['id'], amt, rng.uniform(0.3,0.8), 0.1)
                court.file_case(c, step); court.tick(step)
                if c.verdict in ('PLAINTIFF_WINS','SPLIT'):
                    a = min(amt*rng.uniform(0.5,1.0), b['cash']*0.2)
                    if a>0: ledger.transfer(b['id'], pl, 'damages', a)
        ledger.close_step()
        if step%REPORT_INTERVAL==0:
            ww=[ledger.balances[i].cash for i in wid]
            sw=sorted(ww); n=len(sw)
            g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
            hist['gini'].append(round(g,4)); hist['wealth'].append(sum(b.cash for b in ledger.balances.values()))
            hist['wmin'].append(min(ww)); hist['wmean'].append(np.mean(ww))
    ww=[ledger.balances[i].cash for i in wid]
    sw=sorted(ww); n=len(sw)
    g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
    return {'name':'US-style','wealth':sum(b.cash for b in ledger.balances.values()),
            'gini':round(g,4),'w_mean':round(np.mean(ww),2),'w_min':round(min(ww),2),
            'w_max':round(max(ww),2),'div':0,'txns':len(ledger.transfers)}


def run_nordic(workers, businesses, seed):
    """Nordic Social Democracy: 45% progressive income tax, strong welfare (transfers
    30% of revenue back to citizens), strong unions (wage bargaining = +15% wages),
    public courts, heavy regulation (10% overhead)."""
    from src.mechanics.courts import Court, create_case
    ledger = make_ledger()
    rng = np.random.RandomState(seed)
    for w in workers: ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
    for b in businesses: ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])
    court = Court('govt','Nordic Court',0.03,5,0.8,0.0)
    wid = [w['id'] for w in workers]
    hist = {'gini':[],'wealth':[],'wmin':[],'wmean':[],'div':[]}

    for step in range(1, STEPS+1):
        ledger.begin_step()
        total_tax = 0.0
        # Union wage premium: +15%
        for w in workers:
            union_wage = w['monthly']*1.15
            pre = union_wage * rng.uniform(0.92, 1.0)
            tax_rate = 0.30 if pre < 3000 else 0.45  # progressive
            tax = pre*tax_rate; after = pre-tax
            if pre>0: ledger.transfer('sys', w['id'], 'wage', after); ledger.transfer(w['id'], 'sys', 'tax', tax)
            total_tax += tax
        for b in businesses:
            rev = b['tfp']*(b['capital']**0.3)*(8**0.7)*b['markup']
            reg = rev*0.10; profit = rev-reg
            if profit>0:
                ct = profit*0.25; after = profit-ct
                ledger.transfer('sys', b['id'], 'rev', after); ledger.transfer(b['id'], 'sys', 'tax', ct)
                total_tax += ct
                inv = after*0.3
                if inv>0: ledger.transfer(b['id'], 'sys', 'invest', inv); b['capital'] += inv
        # Strong welfare: 30% of tax revenue redistributed
        welfare = total_tax*0.30
        if welfare>0:
            per = welfare/len(wid)
            for w_id in wid: ledger.transfer('sys', w_id, 'welfare', per)
        # Courts
        for b in businesses:
            if rng.random()<0.015:
                pl = rng.choice(wid)
                c = create_case(pl, b['id'], rng.uniform(1000,15000), rng.uniform(0.3,0.8), 0.1)
                court.file_case(c, step); court.tick(step)
                if c.verdict in ('PLAINTIFF_WINS','SPLIT'):
                    a = min(rng.uniform(1000,15000)*rng.uniform(0.5,1.0), b['cash']*0.3)
                    if a>0: ledger.transfer(b['id'], pl, 'damages', a)
        ledger.close_step()
        if step%REPORT_INTERVAL==0:
            ww=[ledger.balances[i].cash for i in wid]
            sw=sorted(ww); n=len(sw)
            g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
            hist['gini'].append(round(g,4)); hist['wealth'].append(sum(b.cash for b in ledger.balances.values()))
            hist['wmin'].append(min(ww)); hist['wmean'].append(np.mean(ww))
    ww=[ledger.balances[i].cash for i in wid]
    sw=sorted(ww); n=len(sw)
    g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
    return {'name':'Nordic Social Democracy','wealth':sum(b.cash for b in ledger.balances.values()),
            'gini':round(g,4),'w_mean':round(np.mean(ww),2),'w_min':round(min(ww),2),
            'w_max':round(max(ww),2),'div':0,'txns':len(ledger.transfers)}


def run_georgist(workers, businesses, seed):
    """Pure Georgist: LVT 3% annual, flat per-capita Dividend, no LS legal/insurance system.
    Single public court. No insurance requirement."""
    from src.mechanics.courts import Court, create_case
    ledger = make_ledger()
    rng = np.random.RandomState(seed)
    for w in workers: ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
    for b in businesses: ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])
    court = Court('govt','Public Court',0.03,5,0.7,0.0)
    wland = {w['id']: w['land'] for w in workers}
    bland = {b['id']: rng.uniform(50000,200000) for b in businesses}
    wid = [w['id'] for w in workers]
    hist = {'gini':[],'wealth':[],'wmin':[],'wmean':[],'div':[]}

    for step in range(1, STEPS+1):
        ledger.begin_step()
        for w in workers:
            inc = w['monthly']*rng.uniform(0.92,1.0)
            if inc>0: ledger.transfer('sys', w['id'], 'wage', inc)
        for b in businesses:
            rev = b['tfp']*(b['capital']**0.3)*(8**0.7)*b['markup']
            ledger.transfer('sys', b['id'], 'rev', rev)
            inv = rev*0.3
            if inv>0: ledger.transfer(b['id'], 'sys', 'invest', inv); b['capital'] += inv
        # LVT only (no insurance, no guilds)
        for w in workers:
            d = wland[w['id']]*LVT_MONTHLY_RATE
            if ledger.balances[w['id']].cash >= d: ledger.transfer(w['id'], 'trust', 'lvt', d)
        for b in businesses:
            d = bland[b['id']]*LVT_MONTHLY_RATE
            if ledger.balances[b['id']].cash >= d: ledger.transfer(b['id'], 'trust', 'lvt', d)
        # Dividend (no skim — pure Georgist)
        tl = sum(t.amount for t in ledger.transfers if t.step==ledger.step and t.mechanism=='lvt')
        pc = tl/len(wid)
        for w_id in wid:
            if pc>0: ledger.transfer('trust', w_id, 'dividend', pc)
        for b in businesses:
            if rng.random()<0.02:
                pl = rng.choice(wid)
                c = create_case(pl, b['id'], rng.uniform(1000,20000), rng.uniform(0.3,0.8), 0.1)
                court.file_case(c, step); court.tick(step)
        ledger.close_step()
        if step%REPORT_INTERVAL==0:
            ww=[ledger.balances[i].cash for i in wid]
            sw=sorted(ww); n=len(sw)
            g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
            hist['gini'].append(round(g,4)); hist['wealth'].append(sum(b.cash for b in ledger.balances.values()))
            hist['wmin'].append(min(ww)); hist['wmean'].append(np.mean(ww))
            hist['div'].append(pc)
    ww=[ledger.balances[i].cash for i in wid]
    sw=sorted(ww); n=len(sw)
    g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
    return {'name':'Pure Georgist','wealth':sum(b.cash for b in ledger.balances.values()),
            'gini':round(g,4),'w_mean':round(np.mean(ww),2),'w_min':round(min(ww),2),
            'w_max':round(max(ww),2),'div':round(pc,2),'txns':len(ledger.transfers)}


def run_lf(workers, businesses, seed):
    """Laissez-faire: no tax, no courts, no insurance, no welfare."""
    ledger = make_ledger()
    rng = np.random.RandomState(seed)
    for w in workers: ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
    for b in businesses: ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])
    wid = [w['id'] for w in workers]
    hist = {'gini':[],'wealth':[],'wmin':[],'wmean':[],'div':[]}

    for step in range(1, STEPS+1):
        ledger.begin_step()
        for w in workers:
            inc = w['monthly']*rng.uniform(0.92,1.0)
            if inc>0: ledger.transfer('sys', w['id'], 'wage', inc)
        for b in businesses:
            rev = b['tfp']*(b['capital']**0.3)*(8**0.7)*b['markup']
            ledger.transfer('sys', b['id'], 'rev', rev)
            inv = rev*0.3
            if inv>0: ledger.transfer(b['id'], 'sys', 'invest', inv); b['capital'] += inv
        ledger.close_step()
        if step%REPORT_INTERVAL==0:
            ww=[ledger.balances[i].cash for i in wid]
            sw=sorted(ww); n=len(sw)
            g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
            hist['gini'].append(round(g,4)); hist['wealth'].append(sum(b.cash for b in ledger.balances.values()))
            hist['wmin'].append(min(ww)); hist['wmean'].append(np.mean(ww))
    ww=[ledger.balances[i].cash for i in wid]
    sw=sorted(ww); n=len(sw)
    g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
    return {'name':'Laissez-Faire','wealth':sum(b.cash for b in ledger.balances.values()),
            'gini':round(g,4),'w_mean':round(np.mean(ww),2),'w_min':round(min(ww),2),
            'w_max':round(max(ww),2),'div':0,'txns':len(ledger.transfers)}


# ─── NEW MODEL 6: SINGAPORE-STYLE ─────────────────────────────

def run_singapore(workers, businesses, seed):
    """Singapore-style: 30% mandatory savings (CPF), state-led housing,
    low welfare (10% of tax revenue), high property taxes (5% annual on land).
    Central Provident Fund: forced savings split between employer+employee."""
    import logging
    _log = logging.getLogger('run_singapore')
    from src.mechanics.courts import Court, create_case
    ledger = make_ledger()
    rng = np.random.RandomState(seed)
    for w in workers:
        try:
            ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
        except Exception as e:
            _log.warning('Failed to register worker %s: %s', w['id'], e)
    for b in businesses:
        try:
            ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])
        except Exception as e:
            _log.warning('Failed to register business %s: %s', b['id'], e)
    court = Court('state','State Court',0.02,8,0.8,0.0)

    wland = {w['id']: w['land'] for w in workers}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}
    wid = [w['id'] for w in workers]
    cpf_balances = {w['id']: 0.0 for w in workers}
    hist = {'gini':[], 'wealth':[], 'wmin':[], 'wmean':[], 'div':[]}

    for step in range(1, STEPS+1):
        try:
            ledger.begin_step()
            total_tax = 0.0
            for w in workers:
                try:
                    gross = w['monthly'] * rng.uniform(*WAGE_VARIABILITY)
                    employee_cpf = gross * SINGAPORE_CPF_EMPLOYEE_RATE
                    employer_cpf = gross * SINGAPORE_CPF_EMPLOYER_RATE
                    take_home = gross - employee_cpf
                    if gross > 0 and take_home >= 0:
                        ledger.transfer('sys', w['id'], 'wage', take_home)
                        cpf_balances[w['id']] += (employee_cpf + employer_cpf)
                except Exception as e:
                    _log.warning('Step %d wage failed for %s: %s', step, w['id'], e)
            for b in businesses:
                try:
                    rev = b['tfp']*(b['capital']**0.3)*(8**0.7)*b['markup']
                    cpf_contrib = SINGAPORE_WAGE_BILL_ESTIMATE * SINGAPORE_CPF_EMPLOYER_RATE
                    profit = rev - cpf_contrib
                    if profit > 0:
                        ct = profit*SINGAPORE_CORP_TAX_RATE
                        after = profit-ct
                        ledger.transfer('sys', b['id'], 'rev', after)
                        ledger.transfer(b['id'], 'sys', 'tax', ct)
                        total_tax += ct
                        inv = after*INVESTMENT_RATE
                        if inv > 0:
                            ledger.transfer(b['id'], 'sys', 'invest', inv)
                            b['capital'] += inv
                except Exception as e:
                    _log.warning('Step %d business failed for %s: %s', step, b['id'], e)
            for w in workers:
                try:
                    d = wland[w['id']] * SINGAPORE_PROPERTY_MONTHLY
                    if ledger.balances[w['id']].cash >= d:
                        ledger.transfer(w['id'], 'sys', 'property_tax', d)
                        total_tax += d
                except Exception as e:
                    _log.warning('Step %d prop tax failed for %s: %s', step, w['id'], e)
            for b in businesses:
                try:
                    d = bland[b['id']] * SINGAPORE_PROPERTY_MONTHLY
                    if ledger.balances[b['id']].cash >= d:
                        ledger.transfer(b['id'], 'sys', 'property_tax', d)
                        total_tax += d
                except Exception as e:
                    _log.warning('Step %d biz prop tax failed for %s: %s', step, b['id'], e)
            welfare = total_tax * SINGAPORE_WELFARE_SHARE
            if welfare > 0:
                per = welfare/len(wid)
                for w_id in wid:
                    try:
                        ledger.transfer('sys', w_id, 'welfare', per)
                    except Exception as e:
                        _log.warning('Step %d welfare failed for %s: %s', step, w_id, e)
            for w in workers:
                try:
                    withdraw = cpf_balances[w['id']] * SINGAPORE_CPF_WITHDRAWAL_RATE
                    if withdraw > 0:
                        ledger.transfer('sys', w['id'], 'cpf_withdrawal', withdraw)
                        cpf_balances[w['id']] -= withdraw
                except Exception as e:
                    _log.warning('Step %d CPF withdraw failed for %s: %s', step, w['id'], e)
            for b in businesses:
                if rng.random() < SINGAPORE_LITIGATION_RATE:
                    try:
                        pl = rng.choice(wid)
                        c = create_case(pl, b['id'], rng.uniform(1000,15000), rng.uniform(0.4,0.9), 0.3)
                        court.file_case(c, step); court.tick(step)
                        if c.verdict in ('PLAINTIFF_WINS','SPLIT'):
                            a = min(rng.uniform(500,10000)*rng.uniform(0.5,1.0), b['cash']*0.3)
                            if a > 0:
                                ledger.transfer(b['id'], pl, 'damages', a)
                    except Exception as e:
                        _log.warning('Step %d court failed: %s', step, e)
            ledger.close_step()
        except Exception as e:
            _log.error('Fatal at step %d: %s', step, e)
            ledger.close_step()
            break
        if step % REPORT_INTERVAL == 0:
            ww=[ledger.balances[i].cash for i in wid if i in ledger.balances]
            if ww:
                sw=sorted(ww); n=len(sw)
                g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
                hist['gini'].append(round(g,4))
                hist['wealth'].append(sum(b.cash for b in ledger.balances.values()))
                hist['wmin'].append(min(ww)); hist['wmean'].append(np.mean(ww)); hist['div'].append(0)
    ww=[ledger.balances[i].cash for i in wid if i in ledger.balances]
    cpf_total = sum(cpf_balances.get(w['id'], 0) for w in workers)
    if ww:
        sw=sorted(ww); n=len(sw)
        g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
    else:
        g = 0.0
    return {'name':'Singapore-style','wealth':sum(b.cash for b in ledger.balances.values()) + cpf_total,
            'gini':round(g,4),'w_mean':round(np.mean(ww),2) if ww else 0,
            'w_min':round(min(ww),2) if ww else 0,
            'w_max':round(max(ww),2) if ww else 0,'div':0,'txns':len(ledger.transfers)}


# ─── NEW MODEL 7: MUTUALIST LS ─────────────────────────────────

def run_mutualist(workers, businesses, seed):
    """Mutualist Liability State: same as LS but guild mutuals replace
    private insurers. Workers contribute to a pooled mutual fund that
    pays claims collectively. Tests whether mutual ownership solves
    adverse selection better than for-profit insurance."""
    import logging
    _log = logging.getLogger('run_mutualist')
    from src.mechanics.courts import CourtSystem, Court, create_case
    ledger = make_ledger()
    rng = np.random.RandomState(seed)
    for w in workers:
        try:
            ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])
        except Exception as e:
            _log.warning('Failed to register worker %s: %s', w['id'], e)
    for b in businesses:
        try:
            ledger.register_entity(b['id'], EntityType.BUSINESS, initial_cash=b['cash'])
        except Exception as e:
            _log.warning('Failed to register business %s: %s', b['id'], e)

    courts = CourtSystem()
    courts.register_court(Court('fast', 'Mutual Court', 0.02, 3, 0.75, 0.0))

    wland = {w['id']: w['land'] for w in workers}
    bland = {b['id']: rng.uniform(50000, 200000) for b in businesses}
    wid = [w['id'] for w in workers]
    mutual_pool = 0.0; mutual_contrib = 0.0; mutual_payouts = 0.0
    hist = {'gini':[], 'wealth':[], 'wmin':[], 'wmean':[], 'div':[]}
    pool_exhaustion_count = 0

    for step in range(1, STEPS+1):
        try:
            ledger.begin_step()
            for w in workers:
                try:
                    inc = w['monthly'] * rng.uniform(*WAGE_VARIABILITY)
                    if inc > 0:
                        ledger.transfer('sys', w['id'], 'wage', inc)
                except Exception as e:
                    _log.warning('Step %d wage failed for %s: %s', step, w['id'], e)
            for b in businesses:
                try:
                    rev = b['tfp']*(b['capital']**0.3)*(8**0.7)*b['markup']
                    profit = rev - BUSINESS_WAGE_BILL
                    if profit > 0:
                        ledger.transfer('sys', b['id'], 'rev', profit)
                        inv = profit*INVESTMENT_RATE
                        if inv > 0:
                            ledger.transfer(b['id'], 'sys', 'invest', inv)
                            b['capital'] += inv
                except Exception as e:
                    _log.warning('Step %d business failed for %s: %s', step, b['id'], e)
            # Mutual insurance
            for w in workers:
                try:
                    risk_based = w['risk'] * MUTUAL_RISK_MULTIPLIER
                    premium = risk_based * MUTUAL_LOADING_FACTOR * MUTUAL_COVERAGE_LIMIT / 12
                    if premium < ledger.balances[w['id']].cash * MUTUAL_PREMIUM_CAP_RATIO:
                        ledger.transfer(w['id'], 'trust', 'mutual_contrib', premium)
                        mutual_contrib += premium; mutual_pool += premium
                except Exception as e:
                    _log.warning('Step %d mutual contrib failed for %s: %s', step, w['id'], e)
            # Claims
            total_claims = 0.0
            for w in workers:
                try:
                    if rng.random() < w['risk'] * MUTUAL_ACCIDENT_PROB_MULTIPLIER:
                        claim = rng.uniform(500, 15000)
                        if mutual_pool >= claim:
                            ledger.transfer('trust', w['id'], 'mutual_claim', claim)
                            mutual_pool -= claim; total_claims += claim
                        else:
                            pool_exhaustion_count += 1
                            partial = mutual_pool * MUTUAL_POOL_EXHAUSTION_RATIO
                            if partial > 0:
                                ledger.transfer('trust', w['id'], 'mutual_claim', partial)
                                mutual_pool -= partial; total_claims += partial
                            if pool_exhaustion_count == 1:
                                _log.warning('Mutual pool exhausted at step %d, paying partial claims', step)
                except Exception as e:
                    _log.warning('Step %d claim failed for %s: %s', step, w['id'], e)
            mutual_payouts += total_claims
            # LVT
            for w in workers:
                try:
                    d = wland[w['id']]*LVT_MONTHLY_RATE
                    if ledger.balances[w['id']].cash >= d:
                        ledger.transfer(w['id'], 'trust', 'lvt', d)
                except Exception as e:
                    _log.warning('Step %d LVT failed for %s: %s', step, w['id'], e)
            for b in businesses:
                try:
                    d = bland[b['id']]*LVT_MONTHLY_RATE
                    if ledger.balances[b['id']].cash >= d:
                        ledger.transfer(b['id'], 'trust', 'lvt', d)
                except Exception as e:
                    _log.warning('Step %d biz LVT failed for %s: %s', step, b['id'], e)
            # Dividend
            tl = sum(t.amount for t in ledger.transfers if t.step==ledger.step and t.mechanism=='lvt')
            pc = tl*0.90/len(wid) if tl > 0 else 0
            if tl*0.10 > 0:
                try:
                    ledger.transfer('trust', 'ally', 'skim', tl*0.10)
                except Exception as e:
                    _log.warning('Step %d skim failed: %s', step, e)
            for w_id in wid:
                if pc > 0:
                    try:
                        ledger.transfer('trust', w_id, 'dividend', pc)
                    except Exception as e:
                        _log.warning('Step %d dividend failed for %s: %s', step, w_id, e)
            # Courts
            for b in businesses:
                if rng.random() < ACCIDENT_PROBABILITY:
                    try:
                        pl = rng.choice(wid)
                        c = create_case(pl, b['id'], rng.uniform(1000,20000), rng.uniform(0.3,0.8), 0.1)
                        courts.route_case(c, step=step)
                    except Exception as e:
                        _log.warning('Step %d court route failed: %s', step, e)
            courts.tick(step)
            ledger.close_step()
        except Exception as e:
            _log.error('Fatal at step %d: %s', step, e)
            ledger.close_step()
            break
        if step % REPORT_INTERVAL == 0:
            ww=[ledger.balances[i].cash for i in wid if i in ledger.balances]
            if ww:
                sw=sorted(ww); n=len(sw)
                g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
                hist['gini'].append(round(g,4))
                hist['wealth'].append(sum(b.cash for b in ledger.balances.values()))
                hist['wmin'].append(min(ww)); hist['wmean'].append(np.mean(ww)); hist['div'].append(pc)
    ww=[ledger.balances[i].cash for i in wid if i in ledger.balances]
    if ww:
        sw=sorted(ww); n=len(sw)
        g=(2*sum((i+1)*v for i,v in enumerate(sw))/(n*sum(sw)))-(n+1)/n if n and sum(sw) else 0
    else:
        g = 0.0
    _log.info('Mutual pool: contrib=%.0f, payouts=%.0f, final=%.0f, exhaustions=%d',
              mutual_contrib, mutual_payouts, mutual_pool, pool_exhaustion_count)
    return {'name':'Mutualist LS','wealth':sum(b.cash for b in ledger.balances.values()),
            'gini':round(g,4),'w_mean':round(np.mean(ww),2) if ww else 0,
            'w_min':round(min(ww),2) if ww else 0,
            'w_max':round(max(ww),2) if ww else 0,'div':round(pc,2),'txns':len(ledger.transfers)}


# ─── BATCH RUNNER ───────────────────────────────────────────────

SYSTEMS = [run_ls, run_us, run_nordic, run_singapore, run_georgist, run_mutualist, run_lf]
SYSTEM_NAMES = ['Liability State', 'US-style', 'Nordic Social Democracy',
                'Singapore-style', 'Pure Georgist', 'Mutualist LS', 'Laissez-Faire']


def run_batch(seeds=SEEDS):
    """Run all systems across all seeds."""
    results = {name: [] for name in SYSTEM_NAMES}
    total = len(seeds) * len(SYSTEMS)

    for i, sys_fn in enumerate(SYSTEMS):
        sys_name = SYSTEM_NAMES[i]
        print(f"\n{'='*60}")
        print(f"  {sys_name}")
        print(f"{'='*60}")
        for seed in seeds:
            pop = gen_population(seed)
            r = sys_fn(*pop, seed)
            results[sys_name].append(r)
            print(f"  seed {seed:3d}: Gini={r['gini']:.4f}  Mean=${r['w_mean']:>9,.0f}  "
                  f"Min=${r['w_min']:>9,.0f}  Div=${r['div']:>6.2f}")
    return results


def summarize(results):
    """Compute aggregate statistics across seeds for each system."""
    print("\n" + "=" * 100)
    print("  FINAL COMPARISON — 20 SEEDS × 5 SYSTEMS × 240 STEPS (20 YEARS)")
    print("=" * 100)

    header = f"{'System':<28} {'Mean Wealth':>12} {'Min Wealth':>12} {'Max Wealth':>12} {'Gini Mean':>10} {'Gini SD':>9} {'Dividend':>10} {'Txns':>8}"
    print(header)
    print("-" * 100)

    for sys_name in SYSTEM_NAMES:
        runs = results[sys_name]
        w_means = [r['w_mean'] for r in runs]
        w_mins = [r['w_min'] for r in runs]
        w_maxs = [r['w_max'] for r in runs]
        ginis = [r['gini'] for r in runs]
        divs = [r['div'] for r in runs]
        txnss = [r['txns'] for r in runs]

        print(f"{sys_name:<28} "
              f"${np.mean(w_means):>10,.0f} ± ${np.std(w_means):>7,.0f} "
              f"${np.mean(w_mins):>10,.0f} "
              f"${np.mean(w_maxs):>10,.0f} "
              f"{np.mean(ginis):>8.4f}  ±{np.std(ginis):>6.4f} "
              f"${np.mean(divs):>7.2f} "
              f"{np.mean(txnss):>7,.0f}")

    # Rank by mean wealth
    print(f"\n{'Rank by Mean Worker Wealth':^80}")
    print("-" * 80)
    ranked = sorted([(np.mean([r['w_mean'] for r in results[sn]]), sn) for sn in SYSTEM_NAMES], reverse=True)
    for i, (val, name) in enumerate(ranked, 1):
        print(f"  {i}. {name:<30} ${val:>10,.0f}")

    print(f"\n{'Rank by Lowest Inequality (Gini)':^80}")
    print("-" * 80)
    ranked = sorted([(np.mean([r['gini'] for r in results[sn]]), sn) for sn in SYSTEM_NAMES])
    for i, (val, name) in enumerate(ranked, 1):
        print(f"  {i}. {name:<30} {val:.4f}")


if __name__ == '__main__':
    args = sys.argv[1:]
    seeds = SEEDS
    if len(args) > 0 and args[0] == '--quick':
        seeds = list(range(1, 6))  # 5 seeds for testing

    print(f"Running {len(seeds)} seeds × {len(SYSTEMS)} systems = {len(seeds)*len(SYSTEMS)} simulations")
    print(f"Each: {STEPS} steps (20 years) with 50 workers, 10 businesses")
    t0 = time.time()

    results = run_batch(seeds)

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    summarize(results)

    # Save
    os.makedirs('output', exist_ok=True)
    with open('output/batch_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to output/batch_results.json")
