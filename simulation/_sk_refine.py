"""Fix SK 1980s level — currently d=1.5 gives Gini 0.305 vs target 0.33 (7.5% err)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

SK80 = {'system_name':'SK_1980','tax_type':'income',
    'income_tax_rate':0.20,'corp_tax_rate':0.50,'welfare_rate':0.03,
    'healthcare_gdp_share':0.03,'education_gdp_share':0.05,
    'skill_premium_growth':0.005,'union_coverage':0.15,
    'capital_income_share':0.10,'import_competition':0.05,
    'elite_capture_intensity':0.10,'informal_share':0.22,'inheritance_rate':0.0}
SK20 = {'system_name':'SK_2020','tax_type':'income',
    'income_tax_rate':0.30,'corp_tax_rate':0.25,'welfare_rate':0.12,
    'healthcare_gdp_share':0.08,'education_gdp_share':0.05,
    'skill_premium_growth':0.010,'union_coverage':0.10,
    'capital_income_share':0.15,'import_competition':0.15,
    'elite_capture_intensity':0.15,'informal_share':0.22,'inheritance_rate':0.0}

print("SK 1980s (target 0.33):")
for d in [1.5, 1.6, 1.7, 1.8]:
    cfg = dict(SK80, wage_dispersion_mult=d)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={d:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.33):.4f}")

print("SK 2020s (target 0.33):")
for d in [1.5, 1.6, 1.7]:
    cfg = dict(SK20, wage_dispersion_mult=d)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={d:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.33):.4f}")

print("\nBest combos (STABLE trend):")
for d80 in [1.6, 1.7, 1.8]:
    for d20 in [1.5, 1.6]:
        cfg80 = dict(SK80, wage_dispersion_mult=d80)
        cfg20 = dict(SK20, wage_dispersion_mult=d20)
        w,r,b = gen_population(42); r80 = run_phase8(w,r,b,42,cfg80)
        w2,r2,b2 = gen_population(42); r20 = run_phase8(w2,r2,b2,42,cfg20)
        delta = r20['gini'] - r80['gini']
        trend = 'STABLE' if abs(delta)<=0.02 else ('RISING' if delta>0 else 'FALLING')
        err80 = abs(r80['gini']-0.33)
        err20 = abs(r20['gini']-0.33)
        ok = " <<<" if trend=='STABLE' and err80<0.02 and err20<0.02 else ""
        print(f"  d80={d80:.1f} d20={d20:.1f} -> Gini80={r80['gini']:.4f} Gini20={r20['gini']:.4f} delta={delta:.4f} trend={trend} err80={err80:.4f} err20={err20:.4f}{ok}")
