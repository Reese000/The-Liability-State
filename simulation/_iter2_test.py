import sys; sys.path.insert(0, 'src')
from comparison_phase8 import run_phase8, gen_population
import numpy as np

print("=== JAPAN: period-varying informal_share (non-regular workers) ===")

results = []
for wd_60, inf_60, wd_20, inf_20, label in [
    (1.5, 0.10, 1.8, 0.35, "wd1.5/1.8 inf0.10/0.35"),
    (2.0, 0.10, 2.5, 0.35, "wd2.0/2.5 inf0.10/0.35"),
    (1.5, 0.15, 2.0, 0.38, "wd1.5/2.0 inf0.15/0.38"),
    (2.0, 0.10, 2.0, 0.35, "wd2.0/2.0 inf0.10/0.35"),
]:
    cfg_60 = dict(tax_type='income', income_tax_rate=0.15, corp_tax_rate=0.42, welfare_rate=0.04,
                 healthcare_gdp_share=0.03, use_progressive_tax=True, elite_capture_intensity=0.05,
                 skill_premium_growth=0.001, union_coverage=0.35, capital_income_share=0.10,
                 import_competition=0.05, informal_share=inf_60,
                 wage_dispersion_mult=wd_60, inheritance_rate=0.0,
                 system_name='JP_60')
    cfg_20 = dict(tax_type='income', income_tax_rate=0.30, corp_tax_rate=0.30, welfare_rate=0.18,
                 healthcare_gdp_share=0.11, use_progressive_tax=True, elite_capture_intensity=0.18,
                 skill_premium_growth=0.008, union_coverage=0.17, capital_income_share=0.22,
                 import_competition=0.20, informal_share=inf_20,
                 wage_dispersion_mult=wd_20, inheritance_rate=0.0,
                 system_name='JP_20')
    
    w,r,b = gen_population(42)
    res60 = run_phase8(w,r,b,42, cfg_60)
    w2,r2,b2 = gen_population(42)
    res20 = run_phase8(w2,r2,b2,42, cfg_20)
    
    delta = res20['gini'] - res60['gini']
    trend = 'RISING' if delta > 0.02 else ('FALLING' if delta < -0.02 else 'STABLE')
    status = 'PASS' if trend == 'RISING' else 'FAIL'
    results.append((label, res60['gini'], res20['gini'], delta, trend, status))
    
    print("  {}: 1960s={:.4f} 2020s={:.4f} delta={:+.4f} trend={} {}".format(
        label, res60['gini'], res20['gini'], delta, trend, status))

print()
print("=== SUMMARY ===")
for label, g60, g20, d, trend, status in results:
    print("  {}: 1960s={:.4f} 2020s={:.4f} actual 0.35->0.40 {}".format(
        label, g60, g20, status))
