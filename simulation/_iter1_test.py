import sys; sys.path.insert(0, 'src')
from comparison_phase8 import run_phase8, gen_population
import numpy as np

print("=== FRANCE TREND FIX ===")

# France 1960s config
fr_1960s = dict(tax_type='income', income_tax_rate=0.25, corp_tax_rate=0.50, welfare_rate=0.08,
                healthcare_gdp_share=0.04, use_progressive_tax=True, child_benefit_taper=0.05,
                unemployment_rate=0.02, informal_share=0.08, wage_dispersion_mult=1.2,
                inheritance_rate=0.0)

w, r, b = gen_population(42)
r60 = run_phase8(w, r, b, 42, dict(fr_1960s, system_name='FR_1960'))
print("1960s wd=1.2: Gini={:.4f} Actual=0.35 Delta={:+.4f}".format(r60['gini'], r60['gini']-0.35))

# France 2020s config
fr_2020s = dict(tax_type='income', income_tax_rate=0.45, corp_tax_rate=0.25, welfare_rate=0.20,
                healthcare_gdp_share=0.11, use_progressive_tax=True, child_benefit_taper=0.50,
                unemployment_rate=0.08, informal_share=0.12, wage_dispersion_mult=1.0,
                skill_premium_growth=0.008, union_coverage=0.25, capital_income_share=0.12,
                import_competition=0.15, elite_capture_intensity=0.05, inheritance_rate=0.0)

w2, r2, b2 = gen_population(42)
r20 = run_phase8(w2, r2, b2, 42, dict(fr_2020s, system_name='FR_2020'))
print("2020s wd=1.0: Gini={:.4f} Actual=0.30 Delta={:+.4f}".format(r20['gini'], r20['gini']-0.30))

delta = r20['gini'] - r60['gini']
trend = 'FALLING' if delta < -0.02 else ('RISING' if delta > 0.02 else 'STABLE')
print("Trend: {} (actual FALLING) delta={:+.4f} {}".format(trend, delta, 'PASS' if trend == 'FALLING' else 'FAIL'))

# Try wd=1.3
fr_1960s_13 = dict(fr_1960s, wage_dispersion_mult=1.3)
w3, r3, b3 = gen_population(42)
r60_13 = run_phase8(w3, r3, b3, 42, dict(fr_1960s_13, system_name='FR_1960_13'))
print("\n1960s wd=1.3: Gini={:.4f} Delta={:+.4f}".format(r60_13['gini'], r60_13['gini']-0.35))
delta2 = r20['gini'] - r60_13['gini']
trend2 = 'FALLING' if delta2 < -0.02 else ('RISING' if delta2 > 0.02 else 'STABLE')
print("Trend: {} (actual FALLING) delta={:+.4f} {}".format(trend2, delta2, 'PASS' if trend2 == 'FALLING' else 'FAIL'))

# Try wd=1.5
fr_1960s_15 = dict(fr_1960s, wage_dispersion_mult=1.5)
w4, r4, b4 = gen_population(42)
r60_15 = run_phase8(w4, r4, b4, 42, dict(fr_1960s_15, system_name='FR_1960_15'))
print("\n1960s wd=1.5: Gini={:.4f} Delta={:+.4f}".format(r60_15['gini'], r60_15['gini']-0.35))
delta3 = r20['gini'] - r60_15['gini']
trend3 = 'FALLING' if delta3 < -0.02 else ('RISING' if delta3 > 0.02 else 'STABLE')
print("Trend: {} (actual FALLING) delta={:+.4f} {}".format(trend3, delta3, 'PASS' if trend3 == 'FALLING' else 'FAIL'))

# Verify wage ratios
print("\n=== 90/10 RATIOS ===")
for label, wr in [("wd=1.0 FR2020", w2), ("wd=1.2 FR1960", w), ("wd=1.3 FR1960", w3), ("wd=1.5 FR1960", w4)]:
    h = [ww['hourly'] for ww in wr]
    p10 = float(np.percentile(h, 10))
    p90 = float(np.percentile(h, 90))
    print("  {}: 90/10={:.2f}x p10=${:.0f} p90=${:.0f}".format(label, p90/p10, p10, p90))
