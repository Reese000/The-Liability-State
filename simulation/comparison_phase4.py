#!/usr/bin/env python3
"""Phase 4 economic simulator — adds 8 dynamics to Phase 3 framework.

Dynamics: corruption, income-effect complacency, bureaucratic bloat,
monopolization, banking/credit, inheritance, enforcement quality,
information asymmetry. All toggleable, empirically grounded, loop-integrated.
"""
import sys, os, json, time, logging
import numpy as np
logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")

# ─── Constants ──────────────────────────────────────────────
SEEDS = list(range(1, 6)); STEPS = 480; REPORT_INTERVAL = 12; HOURS_PER_STEP = 160
LVT_ANNUAL_RATE = 0.03; LVT_MONTHLY_RATE = LVT_ANNUAL_RATE / 12
INVESTMENT_RATE = 0.3; BUSINESS_WAGE_BILL = 5000.0; WAGE_VARIABILITY = (0.92, 1.0)
ACCIDENT_PROBABILITY = 0.02; TFP_TAX_ELASTICITY = -0.15; LABOR_SUPPLY_ELASTICITY = 0.2
ADMIN_OVERHEAD_BY_TAX = {'lvt': 0.01, 'income': 0.08, 'vat': 0.05, 'corp': 0.06, 'none': 0.0}

# ─── Population & Helpers ──────────────────────────────────
def gen_population(seed):
    rng = np.random.RandomState(seed)
    w = [{"id":f"w{i:03d}","hourly":rng.uniform(10,40),"monthly":rng.uniform(10,40)*HOURS_PER_STEP,
          "land":rng.uniform(20000,200000),"risk":rng.uniform(0.01,0.25),"cash":rng.uniform(10000,80000),
          "honesty":rng.uniform(0.3,0.95),"inertia":rng.uniform(0.05,0.25),"concealment":rng.uniform(0,0.2)}
         for i in range(50)]
    r = [{"id":f"r{i:03d}","cash":rng.uniform(80000,200000),"land":rng.uniform(50000,300000)} for i in range(15)]
    b = [{"id":f"b{i:03d}","cash":rng.uniform(100000,500000),"capital":rng.uniform(100000,400000),
          "tfp":rng.uniform(1.0,2.0),"markup":rng.uniform(1.1,1.3),"honesty":rng.uniform(0.3,0.9)} for i in range(10)]
    return w, r, b

def compute_gini(ws):
    if not ws: return 0.0
    s, n = sorted(ws), len(ws)
    return 0.0 if n < 1 or sum(s) == 0 else round((2*sum((i+1)*v for i,v in enumerate(s))/(n*sum(s)))-(n+1)/n, 4)

# ═══════════════════════════════════════════════════════════
#  Phase 4 Simulation
# ═══════════════════════════════════════════════════════════
def run_phase4(workers, retirees, businesses, seed, config):
    """Phase 4: signature identical to run_phase3. Adds 8 config keys for new dynamics."""
    C = config.get
    name = C('system_name', 'Phase4')
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
    # Phase 4 config
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

    _log = logging.getLogger(f'p4_{name[:12]}')
    rng = np.random.RandomState(seed)
    lvt_m = (lvt_r/12) if tx == 'lvt' else 0.0

    # Setup balances
    bal = {e['id']: e['cash'] for e in workers+retirees+businesses}
    bal.update({'sys': 500_000_000, 'trust': 0, 'bank': 0})
    wid = [w['id'] for w in workers]; rid = [r['id'] for r in retirees]
    all_c = wid + rid
    wland = {w['id']: w['land'] for w in workers}
    rland = {r['id']: r['land'] for r in retirees}
    bland = {b['id']: rng.uniform(50000,200000) for b in businesses}
    cum_tr = {a: 0.0 for a in all_c}
    hist = {'gini':[],'wealth':[],'wmin':[],'wmean':[],'div':[]}
    pc = 0.0

    def xf(fr, to, mech, amt):
        if amt <= 0 or fr not in bal or to not in bal: return
        amt = min(amt, bal[fr])
        if amt <= 0: return
        bal[fr] -= amt; bal[to] += amt

    for step in range(1, STEPS+1):
        try:
            dmult = 0.85 if (ue and step == STEPS//4) else 1.0
            # 1. Wages + income effect
            sw = {}
            for w in workers:
                after = w['hourly']*(1-inc_tx) if tx == 'income' else w['hourly']
                lr = (after/w['hourly'])**LABOR_SUPPLY_ELASTICITY if w['hourly']>0 else 1.0
                if ie > 0:
                    ti = cum_tr[w['id']]
                    bi = w['monthly']*lr
                    if bi+ti > 0:
                        lr *= max(.5, 1-ie*ti/(bi+ti))
                inc = w['monthly']*lr*rng.uniform(*WAGE_VARIABILITY)*un_p
                if inc > 0 and bal['sys'] >= inc:
                    xf('sys', w['id'], 'wage', inc); sw[w['id']] = inc
            # 2. Business + monopolization
            tc = sum(b['capital'] for b in businesses) or 1
            for b in businesses:
                sb = 0.0
                if eos > 0 and b['capital'] > 50000:
                    sb = eos*np.log(b['capital']/50000)
                etfp = b['tfp']*(1+sb)
                ms = b['capital']/tc
                mm = 1+(mmm-1)*ms
                rev = etfp*(b['capital']**0.3)*(8**0.7)*mm*dmult
                prof = rev - BUSINESS_WAGE_BILL
                if prof > 0:
                    tax = prof*corp_tx if tx == 'income' and corp_tx > 0 else 0
                    at = prof - tax
                    if tax > 0: xf(b['id'], 'sys', 'ctax', tax)
                    eir = INVESTMENT_RATE*(1+bnk*0.05) if (bnk > 0 and bal.get('bank',0) > 0) else INVESTMENT_RATE
                    eir = min(1, eir)
                    inv = at*eir
                    if inv > 0: b['capital'] += inv
                    if uwc and sw:
                        cp = at - inv
                        if cp > 0.01:
                            tw = sum(sw.values())
                            if tw > 0:
                                mt = min(w['monthly'] for w in workers)*wrc
                                for w in workers:
                                    wid_, wg = w['id'], sw.get(w['id'], 0)
                                    act = min(cp*(wg/tw), max(0, mt-wg))
                                    if act > 0.01: xf(b['id'], wid_, 'coop', act)
                    else:
                        ret = at - inv
                        if ret > 0: xf('sys', b['id'], 'ret', ret)
            # 3. Insurance + info asymmetry
            epm, tuf = 1+inf*0.5, 1-inf*0.3
            for w in workers:
                if rng.random() < tuf:
                    prem = w['monthly']*0.05*epm
                    if bal.get(w['id'],0) >= prem:
                        xf(w['id'], 'sys', 'prem', prem)
                        if rng.random() < ACCIDENT_PROBABILITY:
                            cl = rng.uniform(1000,20000)
                            po = min(cl, bal['sys'])
                            if po > 0: xf('sys', w['id'], 'claim', po)
            # 4. Adversarial (placeholder for compat)
            if ua: pass
            # 5. Tax + corruption
            tt = 0.0; clk = 1-corr*0.4
            if uv:
                for w in workers:
                    v = sw.get(w['id'],0)*vat_r*clk
                    if v > 0: xf(w['id'], 'sys', 'vat', v); tt += v
            elif tx == 'lvt':
                for el, lm in [(workers,wland),(retirees,rland),(businesses,bland)]:
                    for e in el:
                        d = lm[e['id']]*lvt_m*clk
                        if d > 0 and bal.get(e['id'],0) >= d*0.5:
                            c = min(d, bal[e['id']])
                            xf(e['id'], 'trust', 'lvt', c); tt += c
            elif tx == 'income':
                for w in workers:
                    t = sw.get(w['id'],0)*inc_tx*clk
                    if t > 0: xf(w['id'], 'sys', 'itax', t); tt += t
            # 6. Bloat
            ac = tt*blt
            if ac > 0: xf('sys', 'trust', 'bloat', ac)
            # 7. Dividend
            pc = 0.0
            if tx == 'lvt' and tt > 0:
                nd = tt*(1-blt)
                pc = nd*0.9/len(all_c) if nd > 0 else 0
                if pc > 0:
                    for c in all_c: xf('trust', c, 'div', pc); cum_tr[c] += pc
            # 8. Courts + enforcement
            elt = ACCIDENT_PROBABILITY*enq
            for b in businesses:
                if rng.random() < elt:
                    pl = rng.choice(wid)
                    amt = rng.uniform(1000,20000)
                    if rng.random() < enq:
                        pay = min(amt, bal.get(b['id'],0))
                        if pay > 0: xf(b['id'], pl, 'judge', pay)
            # 9. Welfare
            if tx == 'income' and inc_tx > 0:
                wp = tt*wel_r*(1-blt)
                if wp > 0:
                    pw = wp/len(all_c)
                    for c in all_c: xf('sys', c, 'welf', pw); cum_tr[c] += pw
            # 10. CPF
            if cpf_r > 0:
                cpf_t = sum(sw.get(w['id'],0)*cpf_r for w in workers)
                if cpf_t > 0:
                    pcpf = cpf_t/len(wid)
                    for w_id in wid: xf('sys', w_id, 'cpf', pcpf)
            # 11. Banking
            if bnk > 0:
                db = sum(bal.get(a,0)*0.1 for a in all_c)
                for a in all_c:
                    ip = bal.get(a,0)*0.1*irt
                    if ip > 0 and bal['bank'] >= ip: xf('bank', a, 'int', ip)
                lp = db*bnk*0.01
                for b in businesses:
                    cs = b['capital']/tc
                    loan = lp*cs
                    if loan > 0 and bal['bank'] >= loan:
                        xf('bank', b['id'], 'loan', loan)
                        b['capital'] += loan*0.5
                        bal['bank'] += loan*0.02
            # 12. Enforcement
            for w in workers:
                if corr > 0 and rng.random() < dpr*enq:
                    pen = w['monthly']*corr*0.2*(1-enq)
                    if pen > 0 and bal.get(w['id'],0) >= pen:
                        xf(w['id'], 'sys', 'pen', pen)
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
            _log.error("Step %d: %s", step, e); break

    # Post-sim: Inheritance
    if ihr > 0:
        for w in workers:
            bq = bal.get(w['id'],0)*ihr
            pw = bq/len(wid) if wid else 0
            if pw > 0:
                for w_id in wid: xf(w['id'], w_id, 'inherit', pw)

    ww = [bal[i] for i in wid if i in bal]
    return {'name':name, 'wealth':sum(bal.values()), 'gini':round(compute_gini(ww),4) if ww else 0,
            'w_mean':round(np.mean(ww),2) if ww else 0, 'w_min':round(min(ww),2) if ww else 0,
            'w_max':round(max(ww),2) if ww else 0, 'div':round(pc,2), 'txns':0, 'steps':STEPS}

# ═══════════════════════════════════════════════════════════
#  System Configurations — 10 systems
# ═══════════════════════════════════════════════════════════
# Each tuple: (tax_type, lvt_rate, inc_tx, corp_tx, welfare, union, cpf,
#              ua, up, ue, uwc, wrc, uv, vat,
#              corr, ie, blt, eos, mmm, bnk, irt, ihr, enq, dpr, inf)
def _mk(name, *v):
    """Build config dict from compact tuple."""
    (tx,lvt_r,itx,ctx,wf,up,cpf,ua,up_,ue,uwc,wrc,uv,vr,
     cr,ie,bl,eos,mm,bnk,irt,ihr,eq,dp,inf) = v
    base = {'system_name':name,'tax_type':tx,'lvt_rate':lvt_r,'income_tax_rate':itx,'corp_tax_rate':ctx,
            'welfare_rate':wf,'union_premium':up,'cpf_rate':cpf,
            'use_adversarial':ua,'use_pooled_insurance':up_,'use_events':ue,
            'use_endogenous_tfp':True,'use_compacts':True,
            'use_worker_coop':uwc,'wage_ratio_cap':wrc,'use_vat':uv,'vat_rate':vr,
            'corruption_level':cr,'income_effect_labor':ie,'admin_overhead':bl,
            'economies_of_scale':eos,'monopoly_markup_max':mm,'banking_multiplier':bnk,
            'interest_rate':irt,'inheritance_rate':ihr,'enforcement_quality':eq,
            'detection_probability_base':dp,'information_asymmetry':inf}
    return base

SYSTEM_CONFIGS = {
    'LS_Full':          _mk('LS_Full',         'lvt',0.03,0,0,0.0,1.0,0,  1,1,1,0,5,0,0,     .02,.02,.01,.05,1.2,0,0,.1,.95,.7,.10),
    'US_Style':         _mk('US_Style',        'income',0,.20,.21,.15,1.0,0,  1,0,1,0,5,0,0,   .15,.08,.08,.08,1.4,3,.003,.25,.7,.5,.35),
    'Nordic':           _mk('Nordic',          'income',0,.35,.21,.30,1.15,0, 1,0,1,0,5,0,0,   .05,.10,.06,.06,1.3,2.5,.003,.20,.85,.6,.20),
    'Singapore':        _mk('Singapore',       'income',.05,.05,.17,.10,1.0,.37,1,0,1,0,5,0,0, .01,.03,.04,.07,1.35,4,.004,.30,.9,.8,.15),
    'Pure_Georgist':    _mk('Pure_Georgist',   'lvt',0.03,0,0,0,1.0,0,      0,0,0,0,5,0,0,     .01,.0,.01,.0,1.1,0,0,.0,.5,.3,.0),
    'Mutualist_LS':     _mk('Mutualist_LS',    'lvt',0.03,0,0,0,1.0,0,      0,1,0,0,5,0,0,     .01,.01,.01,.02,1.1,0,0,.05,.85,.6,.05),
    'Laissez_Faire':    _mk('Laissez_Faire',   'none',0,0,0,0,1.0,0,         0,0,0,0,5,0,0,     .0,.0,.0,.15,1.6,5,.01,.5,.2,.1,.5),
    'Worker_Coop':      _mk('Worker_Coop',     'lvt',0.03,0,0,0,1.0,0,      1,1,1,1,5,0,0,     .02,.02,.01,.04,1.1,1,.002,.08,.9,.6,.08),
    'UBI_VAT':          _mk('UBI_VAT',         'none',0,0,0,0,1.0,0,         1,1,1,0,5,1,.20,  .08,.12,.05,.06,1.3,2,.003,.15,.75,.5,.20),
    'Dual_Compact_LS':  _mk('Dual_Compact_LS','lvt',0.03,0,0,0,1.0,0,       1,1,1,0,5,0,0,     .02,.02,.01,.05,1.2,0,0,.10,.95,.7,.10),
}
for name, cfg in SYSTEM_CONFIGS.items():
    if name == 'Laissez_Faire': continue
    # Dual compact flag on Dual_Compact_LS
    if 'Dual_Compact' in name:
        cfg['use_dual_compact'] = True
        cfg['use_compacts'] = True

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
            r = run_phase4(*pop, seed, cfg)
            results[name].append(r)
            print(f"  s{seed}: G={r['gini']:.4f} M=${r['w_mean']:>8,.0f} D=${r['div']:>5.2f}")
    print(f"\nTime: {time.time()-t0:.0f}s")
    return results

def summarize(results):
    print(f"\n{'='*100}\n  PHASE 4 — 10 SYSTEMS\n{'='*100}")
    print(f"{'System':<22} {'Mean$':>10} {'Gini':>8} {'Div':>8}")
    print("-"*100)
    for sn in results:
        rs = results[sn]
        wm, gs, ds = [r['w_mean'] for r in rs], [r['gini'] for r in rs], [r['div'] for r in rs]
        print(f"{sn:<22} ${np.mean(wm):>7,.0f} {np.mean(gs):>.4f}±{np.std(gs):.4f} ${np.mean(ds):>5.2f}")
    for label, key, rev in [("Mean Wealth", 'w_mean', True), ("Low Gini", 'gini', False)]:
        ranked = sorted([(np.mean([r[key] for r in results[sn]]), sn) for sn in results], reverse=rev)
        print(f"\n{label:^70}")
        for i, (v, n) in enumerate(ranked, 1): print(f"  {i}. {n:<25} {v:>9,.4f}")

def main():
    seeds = list(range(1, 3)) if '--quick' in sys.argv else SEEDS
    cfg = list(SYSTEM_CONFIGS.values())
    print(f"Phase4: {len(seeds)} seeds × {len(cfg)} systems = {len(seeds)*len(cfg)} sims")
    r = run_batch(seeds, cfg)
    summarize(r)
    os.makedirs("output", exist_ok=True)
    json.dump(r, open("output/phase4_results.json","w"), indent=2)
    print("Saved: output/phase4_results.json")

if __name__ == '__main__':
    main()
