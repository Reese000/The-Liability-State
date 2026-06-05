"""Calibrate country-specific progressive tax brackets."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population, US_BRACKETS

# France 1960s baseline (current US brackets)
FR60 = {'system_name':'FR_1960','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.50,'welfare_rate':0.05,
    'healthcare_gdp_share':0.04,'use_progressive_tax':True,
    'child_benefit_taper':0.02,'unemployment_rate':0.02,
    'informal_share':0.08,'wage_dispersion_mult':3.3,
    'skill_premium_growth':0.001,'union_coverage':0.25,
    'capital_income_share':0.04,'import_competition':0.03,
    'elite_capture_intensity':0.02,'inheritance_rate':0.0}

# French-style brackets: 10% up to 1x median, 25% 1-2x, 40% 2-4x, 50% 4x+
FRENCH = [(0, 1.0, 0.10), (1.0, 2.0, 0.25), (2.0, 4.0, 0.40), (4.0, float('inf'), 0.50)]

print("=" * 60)
print("FRANCE 1960s — bracket comparison")
print("=" * 60)
cfg_us = dict(FR60)
cfg_fr = dict(FR60, progressive_tax_brackets=FRENCH)
w,r,b = gen_population(42)
r_us = run_phase8(w,r,b,42,cfg_us)
w2,r2,b2 = gen_population(42)
r_fr = run_phase8(w2,r2,b2,42,cfg_fr)
print(f"US brackets:  Gini={r_us['gini']:.4f}  Mean=${r_us['w_mean']:>8,.0f}")
print(f"French brackets: Gini={r_fr['gini']:.4f}  Mean=${r_fr['w_mean']:>8,.0f}")

# France 2020s
FR20 = {'system_name':'FR_2020','tax_type':'income',
    'income_tax_rate':0.45,'corp_tax_rate':0.25,'welfare_rate':0.20,
    'healthcare_gdp_share':0.11,'use_progressive_tax':True,
    'child_benefit_taper':0.50,'unemployment_rate':0.08,
    'informal_share':0.12,'wage_dispersion_mult':1.6,
    'skill_premium_growth':0.008,'union_coverage':0.25,
    'capital_income_share':0.12,'import_competition':0.15,
    'elite_capture_intensity':0.05,'inheritance_rate':0.0}
cfg_us20 = dict(FR20)
cfg_fr20 = dict(FR20, progressive_tax_brackets=FRENCH)
w,r,b = gen_population(42)
r_us20 = run_phase8(w,r,b,42,cfg_us20)
w2,r2,b2 = gen_population(42)
r_fr20 = run_phase8(w2,r2,b2,42,cfg_fr20)
print(f"\nFrance 2020s:")
print(f"US brackets:  Gini={r_us20['gini']:.4f}  Mean=${r_us20['w_mean']:>8,.0f}")
print(f"French brackets: Gini={r_fr20['gini']:.4f}  Mean=${r_fr20['w_mean']:>8,.0f}")

# Try adjusted French brackets to keep Gini close to target (0.35/0.30)
for label, br in [
    ("FR mild",  [(0, 1.0, 0.08), (1.0, 2.0, 0.22), (2.0, 4.0, 0.35), (4.0, float('inf'), 0.45)]),
    ("FR mid",   [(0, 1.0, 0.10), (1.0, 2.0, 0.22), (2.0, 4.0, 0.35), (4.0, float('inf'), 0.45)]),
    ("FR steep", [(0, 1.0, 0.12), (1.0, 2.0, 0.28), (2.0, 4.0, 0.40), (4.0, float('inf'), 0.50)]),
]:
    cfg60 = dict(FR60, progressive_tax_brackets=br)
    cfg20 = dict(FR20, progressive_tax_brackets=br)
    w,r,b = gen_population(42); r60 = run_phase8(w,r,b,42,cfg60)
    w2,r2,b2 = gen_population(42); r20 = run_phase8(w2,r2,b2,42,cfg20)
    delta = r20['gini'] - r60['gini']
    trend = 'FALLING' if delta<-0.02 else ('STABLE' if abs(delta)<=0.02 else 'RISING')
    print(f"\n{label} brackets:")
    print(f"  1960s: Gini={r60['gini']:.4f} (target 0.35, err={abs(r60['gini']-0.35):.4f})")
    print(f"  2020s: Gini={r20['gini']:.4f} (target 0.30, err={abs(r20['gini']-0.30):.4f})")
    print(f"  Delta: {delta:.4f}  Trend: {trend}")

print("\nDone.")
