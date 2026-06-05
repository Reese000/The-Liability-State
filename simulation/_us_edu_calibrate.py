"""Calibrate US with stacked education_variance + wage_dispersion_mult."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

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

print("=" * 70)
print("US CALIBRATION — stacked education_variance + wage_disp")
print("=" * 70)

print("\n1960s (target 0.35):")
print(f"{'ev':>5} {'d':>5} {'Gini':>8} {'Err':>6}")
print("-" * 30)
for ev in [0.0, 0.3, 0.5, 0.7]:
    for d in [1.0, 2.0, 3.0, 4.0, 5.0]:
        cfg = dict(US60, education_variance=ev, wage_dispersion_mult=d)
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        err = abs(res['gini'] - 0.35)
        ok = " <<<" if err < 0.02 else ""
        print(f" {ev:.1f} {d:.1f} {res['gini']:>.4f} {err:.4f}{ok}")

print("\n2020s (target 0.48):")
print(f"{'ev':>5} {'d':>5} {'Gini':>8} {'Err':>6}")
print("-" * 30)
for ev in [0.0, 0.3, 0.5, 0.7, 0.9]:
    for d in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]:
        cfg = dict(US20, education_variance=ev, wage_dispersion_mult=d)
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        err = abs(res['gini'] - 0.48)
        ok = " <<<" if err < 0.03 else ""
        print(f" {ev:.1f} {d:.1f} {res['gini']:>.4f} {err:.4f}{ok}")

# Best combo trend check
print("\n--- Best combos (RISING trend check) ---")
for ev60 in [0.3, 0.5, 0.7]:
    for d60 in [2.0, 3.0]:
        for ev20 in [0.5, 0.7]:
            for d20 in [3.0, 4.0, 5.0]:
                cfg60 = dict(US60, education_variance=ev60, wage_dispersion_mult=d60)
                cfg20 = dict(US20, education_variance=ev20, wage_dispersion_mult=d20)
                w,r,b = gen_population(42); r60 = run_phase8(w,r,b,42,cfg60)
                w2,r2,b2 = gen_population(42); r20 = run_phase8(w2,r2,b2,42,cfg20)
                delta = r20['gini'] - r60['gini']
                trend = 'RISING' if delta > 0.02 else ('FALLING' if delta < -0.02 else 'STABLE')
                err60 = abs(r60['gini'] - 0.35)
                err20 = abs(r20['gini'] - 0.48)
                if trend == 'RISING' and err60 < 0.04 and err20 < 0.04:
                    print(f"  ev60={ev60:.1f} d60={d60:.1f} ev20={ev20:.1f} d20={d20:.1f} -> "
                          f"Gini60={r60['gini']:.4f} Gini20={r20['gini']:.4f} "
                          f"err60={err60:.4f} err20={err20:.4f} delta={delta:.4f}")

print("\nDone.")
