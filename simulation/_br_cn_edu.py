"""Calibrate edu_var for Brazil and China."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

# === BRAZIL — PISA ~400, edu_var ~0.40 (low quality, high variance) ===
BR60 = {'system_name':'BR_1960','tax_type':'income',
    'income_tax_rate':0.15,'corp_tax_rate':0.30,'welfare_rate':0.05,
    'healthcare_gdp_share':0.03,'skill_premium_growth':0.001,
    'union_coverage':0.25,'capital_income_share':0.15,'import_competition':0.02,
    'elite_capture_intensity':0.30,'patrimonial_wealth':0.40,
    'informal_share':0.45,'inheritance_rate':0.0}
BR20 = {'system_name':'BR_2020','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.34,'welfare_rate':0.16,
    'healthcare_gdp_share':0.06,'skill_premium_growth':0.008,
    'union_coverage':0.20,'capital_income_share':0.22,'import_competition':0.12,
    'use_progressive_tax':True,'elite_capture_intensity':0.20,
    'patrimonial_wealth':0.2,'informal_share':0.38,'inheritance_rate':0.0}

print("BRAZIL 1960s (target 0.57, pat=0.40):")
for ev in [0.0, 0.2, 0.4]:
    for d in [1.0, 2.0, 3.0]:
        cfg = dict(BR60, education_variance=ev, wage_dispersion_mult=d)
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        err = abs(res['gini']-0.57)
        ok = " <<<" if err < 0.02 else ""
        print(f"  ev={ev:.1f} d={d:.1f} -> Gini={res['gini']:.4f} err={err:.4f}{ok}")

print("BRAZIL 2020s (target 0.53, pat=0.20):")
for ev in [0.0, 0.2, 0.4]:
    for d in [2.0, 3.0, 4.0]:
        cfg = dict(BR20, education_variance=ev, wage_dispersion_mult=d)
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        err = abs(res['gini']-0.53)
        ok = " <<<" if err < 0.02 else ""
        print(f"  ev={ev:.1f} d={d:.1f} -> Gini={res['gini']:.4f} err={err:.4f}{ok}")

# === CHINA — PISA ~590 (selective), edu_var ~0.60 ===
CN80 = {'system_name':'CN_1980','tax_type':'income',
    'income_tax_rate':0.05,'corp_tax_rate':0.55,'welfare_rate':0.01,
    'healthcare_gdp_share':0.02,'informal_share':0.05,
    'skill_premium_growth':0.002,'union_coverage':0.40,
    'capital_income_share':0.05,'import_competition':0.02,
    'elite_capture_intensity':0.05,'inheritance_rate':0.0}
CN00 = {'system_name':'CN_2000','tax_type':'income',
    'income_tax_rate':0.10,'corp_tax_rate':0.33,'welfare_rate':0.03,
    'healthcare_gdp_share':0.03,'informal_share':0.40,
    'skill_premium_growth':0.015,'union_coverage':0.15,
    'capital_income_share':0.20,'import_competition':0.15,
    'elite_capture_intensity':0.20,'inheritance_rate':0.0}
CN20 = {'system_name':'CN_2020','tax_type':'income',
    'income_tax_rate':0.15,'corp_tax_rate':0.25,'welfare_rate':0.07,
    'healthcare_gdp_share':0.05,'informal_share':0.25,
    'skill_premium_growth':0.012,'union_coverage':0.15,
    'capital_income_share':0.22,'import_competition':0.20,
    'elite_capture_intensity':0.25,'inheritance_rate':0.0}

print("\nCHINA 1980s (target 0.28):")
for ev in [0.0, 0.3, 0.6]:
    for d in [1.0, 1.5, 2.0]:
        cfg = dict(CN80, education_variance=ev, wage_dispersion_mult=d)
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        err = abs(res['gini']-0.28)
        ok = " <<<" if err < 0.02 else ""
        print(f"  ev={ev:.1f} d={d:.1f} -> Gini={res['gini']:.4f} err={err:.4f}{ok}")

print("CHINA 2000s (target 0.43):")
for ev in [0.0, 0.3, 0.6]:
    for d in [2.0, 2.5, 3.0]:
        cfg = dict(CN00, education_variance=ev, wage_dispersion_mult=d)
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        err = abs(res['gini']-0.43)
        ok = " <<<" if err < 0.02 else ""
        print(f"  ev={ev:.1f} d={d:.1f} -> Gini={res['gini']:.4f} err={err:.4f}{ok}")

print("CHINA 2020s (target 0.36):")
for ev in [0.0, 0.3, 0.6]:
    for d in [1.5, 1.8, 2.0]:
        cfg = dict(CN20, education_variance=ev, wage_dispersion_mult=d)
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        err = abs(res['gini']-0.36)
        ok = " <<<" if err < 0.02 else ""
        print(f"  ev={ev:.1f} d={d:.1f} -> Gini={res['gini']:.4f} err={err:.4f}{ok}")

print("\nDone.")
