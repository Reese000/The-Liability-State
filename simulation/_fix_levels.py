#!/usr/bin/env python3
"""Fix level errors for Brazil, China, US — calibrate wage_disp."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population

# Brazil: 1960s target 0.57, 2020s target 0.53
# Current: d=3.0, d=2.5
print("=" * 60)
print("BRAZIL")
print("=" * 60)
BR60 = {'system_name':'BR_1960','tax_type':'income',
    'income_tax_rate':0.15,'corp_tax_rate':0.30,'welfare_rate':0.05,
    'healthcare_gdp_share':0.03,'skill_premium_growth':0.001,
    'union_coverage':0.25,'capital_income_share':0.15,'import_competition':0.02,
    'elite_capture_intensity':0.30,'patrimonial_wealth':0.8,
    'informal_share':0.45,'inheritance_rate':0.0}
BR20 = {'system_name':'BR_2020','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.34,'welfare_rate':0.16,
    'healthcare_gdp_share':0.06,'skill_premium_growth':0.008,
    'union_coverage':0.20,'capital_income_share':0.22,'import_competition':0.12,
    'use_progressive_tax':True,'elite_capture_intensity':0.20,
    'patrimonial_wealth':0.2,'informal_share':0.38,'inheritance_rate':0.0}

print("1960s (target 0.57):")
for wd in [2.5, 3.0, 3.5, 4.0]:
    cfg = dict(BR60, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.57):.4f}")

print("2020s (target 0.53):")
for wd in [2.0, 2.5, 3.0, 3.5]:
    cfg = dict(BR20, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.53):.4f}")

# China: 1980s target 0.28, 2000s target 0.43, 2020s target 0.36
# Current: d=1.0, d=2.0, d=1.5
print("\n" + "=" * 60)
print("CHINA")
print("=" * 60)
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
for wd in [1.0, 1.2, 1.5, 1.8]:
    cfg = dict(CN80, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.28):.4f}")

print("2000s (target 0.43):")
for wd in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
    cfg = dict(CN00, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.43):.4f}")

print("2020s (target 0.36):")
for wd in [1.2, 1.5, 1.8, 2.0, 2.5]:
    cfg = dict(CN20, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.36):.4f}")

# US: 1960s target 0.35, 2020s target 0.48
print("\n" + "=" * 60)
print("US")
print("=" * 60)
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

print("1960s (target 0.35):")
for wd in [1.0, 1.2, 1.5, 1.8, 2.0]:
    cfg = dict(US60, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.35):.4f}")

print("2020s (target 0.48):")
for wd in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
    cfg = dict(US20, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.48):.4f}")

# Japan: 1960s target 0.35, 2020s target 0.40
print("\n" + "=" * 60)
print("JAPAN")
print("=" * 60)
JP60 = {'system_name':'JP_1960','tax_type':'income',
    'income_tax_rate':0.15,'corp_tax_rate':0.42,'welfare_rate':0.04,
    'healthcare_gdp_share':0.03,'skill_premium_growth':0.001,
    'union_coverage':0.35,'capital_income_share':0.10,
    'import_competition':0.05,'use_progressive_tax':True,
    'elite_capture_intensity':0.05,'informal_share':0.10,'inheritance_rate':0.0}
JP20 = {'system_name':'JP_2020','tax_type':'income',
    'income_tax_rate':0.30,'corp_tax_rate':0.30,'welfare_rate':0.18,
    'healthcare_gdp_share':0.11,'skill_premium_growth':0.008,
    'union_coverage':0.17,'capital_income_share':0.22,
    'import_competition':0.20,'use_progressive_tax':True,
    'elite_capture_intensity':0.18,'informal_share':0.35,'inheritance_rate':0.0}

print("1960s (target 0.35):")
for wd in [1.5, 2.0, 2.5, 3.0]:
    cfg = dict(JP60, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.35):.4f}")

print("2020s (target 0.40):")
for wd in [2.0, 2.5, 3.0, 3.5]:
    cfg = dict(JP20, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.40):.4f}")

# UK: 1960s target 0.28, 2020s target 0.42
print("\n" + "=" * 60)
print("UK")
print("=" * 60)
UK60 = {'system_name':'UK_1960','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.50,'welfare_rate':0.04,
    'healthcare_gdp_share':0.04,'skill_premium_growth':0.008,
    'union_coverage':0.40,'capital_income_share':0.05,
    'import_competition':0.02,'use_progressive_tax':True,
    'housing_wealth_concentration':0.15,
    'financial_services_premium':0.10,'inheritance_rate':0.0}
UK20 = {'system_name':'UK_2020','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.19,'welfare_rate':0.12,
    'healthcare_gdp_share':0.10,'skill_premium_growth':0.018,
    'union_coverage':0.22,'capital_income_share':0.18,
    'import_competition':0.15,'use_progressive_tax':True,
    'housing_wealth_concentration':0.40,
    'financial_services_premium':0.25,'inheritance_rate':0.0}

print("1960s (target 0.28):")
for wd in [1.0, 1.2, 1.5, 1.8]:
    cfg = dict(UK60, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.28):.4f}")

print("2020s (target 0.42):")
for wd in [1.5, 2.0, 2.5, 3.0]:
    cfg = dict(UK20, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.42):.4f}")

print("\nDone.")
