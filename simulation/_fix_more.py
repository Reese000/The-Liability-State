#!/usr/bin/env python3
"""Apply calibrated params to test_iter5_final.py for Brazil, China, US."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population

# === BRAZIL: patrimonial_wealth too strong for 1960s ===
# Best: pat=0.4, d=2.0 for 1960s (Gini 0.572 vs 0.57)
# 2020s: d=4.0 gives Gini 0.526 (target 0.53)
print("=== BRAZIL CALIBRATION ===")

BR60 = {'system_name':'BR_1960','tax_type':'income',
    'income_tax_rate':0.15,'corp_tax_rate':0.30,'welfare_rate':0.05,
    'healthcare_gdp_share':0.03,'skill_premium_growth':0.001,
    'union_coverage':0.25,'capital_income_share':0.15,'import_competition':0.02,
    'elite_capture_intensity':0.30,'informal_share':0.45,'inheritance_rate':0.0}
BR20 = {'system_name':'BR_2020','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.34,'welfare_rate':0.16,
    'healthcare_gdp_share':0.06,'skill_premium_growth':0.008,
    'union_coverage':0.20,'capital_income_share':0.22,'import_competition':0.12,
    'use_progressive_tax':True,'elite_capture_intensity':0.20,
    'informal_share':0.38,'inheritance_rate':0.0}

# Refine 1960s
print("1960s target 0.57:")
for pat in [0.35, 0.38, 0.40, 0.42, 0.45]:
    cfg = dict(BR60, patrimonial_wealth=pat, wage_dispersion_mult=2.0)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  pat={pat:.2f} d=2.0 -> Gini={res['gini']:.4f} err={abs(res['gini']-0.57):.4f}")

# Refine 2020s
print("2020s target 0.53:")
for wd in [3.5, 4.0, 4.5, 5.0]:
    cfg = dict(BR20, patrimonial_wealth=0.2, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.53):.4f}")

# Best combo
print("\nBest combo:")
for pat in [0.38, 0.40]:
    for d20 in [3.5, 4.0, 4.5]:
        cfg60 = dict(BR60, patrimonial_wealth=pat, wage_dispersion_mult=2.0)
        cfg20 = dict(BR20, patrimonial_wealth=0.2, wage_dispersion_mult=d20)
        w,r,b = gen_population(42); r60 = run_phase8(w,r,b,42,cfg60)
        w2,r2,b2 = gen_population(42); r20 = run_phase8(w2,r2,b2,42,cfg20)
        delta = r20['gini'] - r60['gini']
        trend = 'FALLING' if delta < -0.02 else ('RISING' if delta > 0.02 else 'STABLE')
        print(f"  pat={pat:.2f} d20={d20:.1f} -> Gini60={r60['gini']:.4f} Gini20={r20['gini']:.4f} delta={delta:.4f} trend={trend}")

# === CHINA: use our calibrated values ===
print("\n=== CHINA CALIBRATION ===")
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

cfg80 = dict(CN80, wage_dispersion_mult=1.5)
cfg00 = dict(CN00, wage_dispersion_mult=2.5)
cfg20 = dict(CN20, wage_dispersion_mult=1.8)
w,r,b = gen_population(42)
r80 = run_phase8(w,r,b,42,cfg80)
w2,r2,b2 = gen_population(42)
r00 = run_phase8(w2,r2,b2,42,cfg00)
w3,r3,b3 = gen_population(42)
r20 = run_phase8(w3,r3,b3,42,cfg20)
print(f"1980: d=1.5 -> Gini={r80['gini']:.4f} (target 0.28)")
print(f"2000: d=2.5 -> Gini={r00['gini']:.4f} (target 0.43)")
print(f"2020: d=1.8 -> Gini={r20['gini']:.4f} (target 0.36)")
ch_delta1 = r00['gini'] - r80['gini']
ch_delta2 = r20['gini'] - r00['gini']
print(f"1980->2000: delta={ch_delta1:.4f} {'RISING' if ch_delta1>0.02 else 'OK'}")
print(f"2000->2020: delta={ch_delta2:.4f} {'FALLING' if ch_delta2<-0.02 else 'NEED FALLING'}")

# === US: extended scan for higher wage_disp ===
print("\n=== US EXTENDED SCAN ===")
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
for wd in [3.0, 4.0, 5.0, 6.0]:
    cfg = dict(US60, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f}")

print("2020s (target 0.48):")
for wd in [4.0, 5.0, 6.0, 7.0, 8.0]:
    cfg = dict(US20, wage_dispersion_mult=wd)
    w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f}")

print("Done.")
