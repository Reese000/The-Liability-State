import sys; sys.path.insert(0, 'src')
from comparison_phase4 import BUSINESS_WAGE_BILL
import numpy as np

w, r, b = __import__('comparison_phase8', fromlist=['gen_population']).gen_population(42)
tc = sum(bb['capital'] for bb in b)

print("Finding optimal L for business profitability...")
for L in [500, 600, 700, 750, 800, 900, 1000]:
    profitable = 0
    total_profit = 0
    for bb in b:
        ms = bb['capital'] / tc
        markup = 1 + (1.3 - 1) * ms
        rev = bb['tfp'] * (bb['capital'] ** 0.3) * (L ** 0.7) * markup
        prof = rev - BUSINESS_WAGE_BILL
        if prof > 0:
            profitable += 1
            total_profit += prof * (1 - 0.21)
    avg_margin = total_profit / (profitable + 1)
    print(f"  L={L}: {profitable}/10 profitable, total_after_tax_profit=${total_profit:.0f}")

print()
# Let me compute theoretical L for zero-profit at lowest-capital business
lowest_k = min(bb['capital'] for bb in b)
lowest_tfp = min(bb['tfp'] for bb in b)
ms = lowest_k / tc
markup = 1 + (1.3 - 1) * ms
k03 = lowest_k ** 0.3
# rev = tfp * k03 * L^0.7 * markup = BUSINESS_WAGE_BILL
L_needed = (BUSINESS_WAGE_BILL / (lowest_tfp * k03 * markup)) ** (1/0.7)
print(f"Theoretical L for smallest business break-even: L ≈ {L_needed:.0f}")
