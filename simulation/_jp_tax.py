"""Japan tax bracket calibration."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

JP60 = {'system_name':'JP_1960','tax_type':'income',
    'income_tax_rate':0.15,'corp_tax_rate':0.42,'welfare_rate':0.04,
    'healthcare_gdp_share':0.03,'use_progressive_tax':True,
    'skill_premium_growth':0.001,'union_coverage':0.35,
    'capital_income_share':0.10,'import_competition':0.05,
    'elite_capture_intensity':0.05,'informal_share':0.10,
    'education_variance':0.3,'wage_dispersion_mult':2.0,'inheritance_rate':0.0}
JP20 = {'system_name':'JP_2020','tax_type':'income',
    'income_tax_rate':0.30,'corp_tax_rate':0.30,'welfare_rate':0.18,
    'healthcare_gdp_share':0.11,'use_progressive_tax':True,
    'skill_premium_growth':0.008,'union_coverage':0.17,
    'capital_income_share':0.22,'import_competition':0.20,
    'elite_capture_intensity':0.18,'informal_share':0.35,
    'education_variance':0.3,'wage_dispersion_mult':2.0,'inheritance_rate':0.0}

# Japanese brackets: moderate progressive
JAPAN_BR = [(0, 1.0, 0.12), (1.0, 2.0, 0.20), (2.0, 4.0, 0.30), (4.0, float('inf'), 0.45)]

# Also try UK-style (similar to US but with fewer brackets)
UK_BR = [(0, 1.0, 0.10), (1.0, 3.0, 0.20), (3.0, float('inf'), 0.40)]

for label, br in [("US", None), ("Japan", JAPAN_BR), ("UK", UK_BR)]:
    cfg60 = dict(JP60) if br is None else dict(JP60, progressive_tax_brackets=br)
    cfg20 = dict(JP20) if br is None else dict(JP20, progressive_tax_brackets=br)
    w,r,b = gen_population(42); r60 = run_phase8(w,r,b,42,cfg60)
    w2,r2,b2 = gen_population(42); r20 = run_phase8(w2,r2,b2,42,cfg20)
    delta = r20['gini'] - r60['gini']
    trend = 'RISING' if delta>0.02 else ('FALLING' if delta<-0.02 else 'STABLE')
    print(f"{label} brackets:")
    print(f"  60s: Gini={r60['gini']:.4f} (target 0.35, err={abs(r60['gini']-0.35):.4f})")
    print(f"  20s: Gini={r20['gini']:.4f} (target 0.40, err={abs(r20['gini']-0.40):.4f})")
    print(f"  Trend: {trend} (delta={delta:.4f})")
    print()

print("Done.")
