#!/usr/bin/env python3
"""Fix Brazil (patrimonial_wealth too strong) and US/China with edu_var."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population

print("="*60)
print("Brazil: reduce patrimonial_wealth")
print("="*60)
BR60 = {'system_name':'BR_1960','tax_type':'income',
    'income_tax_rate':0.15,'corp_tax_rate':0.30,'welfare_rate':0.05,
    'healthcare_gdp_share':0.03,'skill_premium_growth':0.001,
    'union_coverage':0.25,'capital_income_share':0.15,'import_competition':0.02,
    'elite_capture_intensity':0.30,
    'informal_share':0.45,'inheritance_rate':0.0}
BR20 = {'system_name':'BR_2020','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.34,'welfare_rate':0.16,
    'healthcare_gdp_share':0.06,'skill_premium_growth':0.008,
    'union_coverage':0.20,'capital_income_share':0.22,'import_competition':0.12,
    'use_progressive_tax':True,'elite_capture_intensity':0.20,
    'informal_share':0.38,'inheritance_rate':0.0}

print("1960s (target 0.57) with varying patrimonial:")
for pat in [0.2, 0.3, 0.4, 0.5, 0.6]:
    cfg = dict(BR60, patrimonial_wealth=pat, wage_dispersion_mult=2.0)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  pat={pat:.1f} d=2.0 -> Gini={res['gini']:.4f}")

print("2020s (target 0.53) with wage_disp scan:")
for wd in [2.0, 2.5, 3.0, 3.5, 4.0]:
    cfg = dict(BR20, patrimonial_wealth=0.2, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f}")

print("\n"+"="*60)
print("China: fix all 3 periods")
print("="*60)
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

print("1980s (target 0.28):")
for wd in [1.2, 1.5, 1.8]:
    cfg = dict(CN80, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f}")

print("2000s (target 0.43):")
for wd in [2.0, 2.5, 3.0]:
    cfg = dict(CN00, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f}")

print("2020s (target 0.36):")
for wd in [1.5, 1.8, 2.0]:
    cfg = dict(CN20, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f}")

print("\n"+"="*60)
print("US: try education_variance mechanism")
print("="*60)
US60 = {'system_name':'US_1960','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.52,'welfare_rate':0.03,
    'healthcare_gdp_share':0.05,'skill_premium_growth':0.005,
    'union_coverage':0.35,'capital_income_share':0.05,
    'import_competition':0.02,'use_progressive_tax':True,
    'elite_capture_intensity':0.05,'inheritance_rate':0.0}
US20 = {'system_name':'US_2020','tax_type':'income',
    'income_tax_rate':0.22,'corp_tax_rate':0.21,'welfare_rate':0.14,
    'healthcare_gdp_share':0.18,'skill_premium_growth':0.018,
    'union_coverage':0.10,'capital_income_share':0.18,
    'import_competition':0.20,'use_progressive_tax':True,
    'elite_capture_intensity':0.15,'inheritance_rate':0.0}

print("1960s (target 0.35) with edu_var:")
for ev in [0.0, 0.3, 0.5, 0.7]:
    cfg = dict(US60, education_variance=ev, wage_dispersion_mult=1.0)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  ev={ev:.1f} d=1.0 -> Gini={res['gini']:.4f}")

print("\n2020s (target 0.48) with edu_var:")
for ev in [0.0, 0.3, 0.5, 0.7, 0.9]:
    cfg = dict(US20, education_variance=ev, wage_dispersion_mult=1.0)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  ev={ev:.1f} d=1.0 -> Gini={res['gini']:.4f}")

print("\nUS 1960s: combined edu_var + wage_disp:")
for ev in [0.3, 0.5]:
    for wd in [1.2, 1.5, 1.8]:
        cfg = dict(US60, education_variance=ev, wage_dispersion_mult=wd)
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        ok = " <<<" if abs(res['gini']-0.35) < 0.02 else ""
        print(f"  ev={ev:.1f} d={wd:.1f} -> Gini={res['gini']:.4f}{ok}")

print("\nUS 2020s: combined edu_var + wage_disp:")
for ev in [0.3, 0.5, 0.7]:
    for wd in [1.5, 2.0, 2.5]:
        cfg = dict(US20, education_variance=ev, wage_dispersion_mult=wd)
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        ok = " <<<" if abs(res['gini']-0.48) < 0.02 else ""
        print(f"  ev={ev:.1f} d={wd:.1f} -> Gini={res['gini']:.4f}{ok}")

print("\nDone.")
