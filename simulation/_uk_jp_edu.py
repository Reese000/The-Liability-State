"""Calibrate edu_var for UK and Japan with stacking."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

# === UK: PISA ~500 → edu_var ~0.50 ===
UK60 = {'system_name':'UK_1960','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.50,'welfare_rate':0.04,
    'healthcare_gdp_share':0.04,'skill_premium_growth':0.008,
    'union_coverage':0.40,'capital_income_share':0.05,
    'import_competition':0.02,'use_progressive_tax':True,
    'housing_wealth_concentration':0.15,'financial_services_premium':0.10,
    'inheritance_rate':0.0}
UK20 = {'system_name':'UK_2020','tax_type':'income',
    'income_tax_rate':0.25,'corp_tax_rate':0.19,'welfare_rate':0.12,
    'healthcare_gdp_share':0.10,'skill_premium_growth':0.018,
    'union_coverage':0.22,'capital_income_share':0.18,
    'import_competition':0.15,'use_progressive_tax':True,
    'housing_wealth_concentration':0.40,'financial_services_premium':0.25,
    'inheritance_rate':0.0}

print("=" * 60)
print("UK — PISA ~500, edu_var ~0.50")
print("=" * 60)
print(f"{'ev':>4} {'d60':>4} {'Gini60':>8} {'Err60':>7} {'d20':>4} {'Gini20':>8} {'Err20':>7} {'Delta':>7} {'Trend':>8}")
for ev in [0.0, 0.3, 0.5, 0.7]:
    for d60 in [1.0, 1.5, 2.0]:
        for d20 in [2.0, 2.5, 3.0, 3.5]:
            cfg60 = dict(UK60, education_variance=ev, wage_dispersion_mult=d60)
            cfg20 = dict(UK20, education_variance=ev, wage_dispersion_mult=d20)
            w,r,b = gen_population(42); r60 = run_phase8(w,r,b,42,cfg60)
            w2,r2,b2 = gen_population(42); r20 = run_phase8(w2,r2,b2,42,cfg20)
            delta = r20['gini'] - r60['gini']
            trend = 'RISING' if delta>0.02 else ('FALLING' if delta<-0.02 else 'STABLE')
            e60 = abs(r60['gini']-0.28); e20 = abs(r20['gini']-0.42)
            ok = " <<<" if trend=='RISING' and e60<0.03 and e20<0.03 else ""
            print(f" {ev:.1f} {d60:.1f} {r60['gini']:.4f} {e60:.4f} {d20:.1f} {r20['gini']:.4f} {e20:.4f} {delta:+.4f} {trend:>8}{ok}")

# === Japan: PISA ~520 → edu_var ~0.55 ===
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

print("\n" + "=" * 60)
print("JAPAN — PISA ~520, edu_var ~0.55")
print("=" * 60)
print(f"{'ev':>4} {'d60':>4} {'Gini60':>8} {'Err60':>7} {'d20':>4} {'Gini20':>8} {'Err20':>7} {'Delta':>7} {'Trend':>8}")
for ev in [0.0, 0.3, 0.55, 0.7]:
    for d60 in [1.5, 2.0, 2.5, 3.0]:
        for d20 in [2.0, 2.5, 3.0, 3.5]:
            cfg60 = dict(JP60, education_variance=ev, wage_dispersion_mult=d60)
            cfg20 = dict(JP20, education_variance=ev, wage_dispersion_mult=d20)
            w,r,b = gen_population(42); r60 = run_phase8(w,r,b,42,cfg60)
            w2,r2,b2 = gen_population(42); r20 = run_phase8(w2,r2,b2,42,cfg20)
            delta = r20['gini'] - r60['gini']
            trend = 'RISING' if delta>0.02 else ('FALLING' if delta<-0.02 else 'STABLE')
            e60 = abs(r60['gini']-0.35); e20 = abs(r20['gini']-0.40)
            ok = " <<<" if trend=='RISING' and e60<0.02 and e20<0.02 else ""
            print(f" {ev:.1f} {d60:.1f} {r60['gini']:.4f} {e60:.4f} {d20:.1f} {r20['gini']:.4f} {e20:.4f} {delta:+.4f} {trend:>8}{ok}")

print("\nDone.")
