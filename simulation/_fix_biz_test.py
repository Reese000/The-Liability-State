import sys; sys.path.insert(0, 'src')
from comparison_phase4 import BUSINESS_WAGE_BILL
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS
import numpy as np

print("===== BUSINESS PROFIT BUG FIX ====")

w, r, b = gen_population(42)
tc = sum(bb['capital'] for bb in b)

print("\nCURRENT (L=8):")
total_profit = 0
for bb in b:
    ms = bb['capital'] / tc
    markup = 1 + (1.3 - 1) * ms
    rev = bb['tfp'] * (bb['capital'] ** 0.3) * (8 ** 0.7) * markup
    prof = rev - BUSINESS_WAGE_BILL
    if prof > 0: total_profit += prof * (1 - 0.21)
    status = 'OK' if prof > 0 else 'LOSS'
    print(f"  {bb['id']}: rev={rev:.0f} wbill={BUSINESS_WAGE_BILL} profit={prof:.0f} [{status}]")
print(f"  Total after-tax profit: {total_profit:.0f}")

print("\nFIXED (L=500):")
total_profit2 = 0
for bb in b:
    ms = bb['capital'] / tc
    markup = 1 + (1.3 - 1) * ms
    rev = bb['tfp'] * (bb['capital'] ** 0.3) * (500 ** 0.7) * markup
    prof = rev - BUSINESS_WAGE_BILL
    if prof > 0: total_profit2 += prof * (1 - 0.21)
    status = 'OK' if prof > 0 else 'LOSS'
    print(f"  {bb['id']}: rev={rev:.0f} wbill={BUSINESS_WAGE_BILL} profit={prof:.0f} [{status}]")
print(f"  Total after-tax profit: {total_profit2:.0f}")

scale = (500 ** 0.7) / (8 ** 0.7)
print(f"\nScale factor: {scale:.1f}x")
print(f"Capital income pool at 30%: ${total_profit2 * 0.3:.0f}/step")

# Run full sim to verify Gini impact
print("\n=== FULL SIM TEST ===")
cfg = PHASE8_CONFIGS['US_Style']
w, r, b = gen_population(42)
res = run_phase8(w, r, b, 42, cfg)
print(f"Original: Gini={res['gini']:.4f} Mean=${res['w_mean']:,.0f} Wealth=${res['wealth']:,}")
