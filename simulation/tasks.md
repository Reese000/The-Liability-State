# Tasks: Liability State — Final Authoritative Ranking

## Strategic Context
After fixing the govt_service_productivity bug (was using treasury stock instead of tax flow), CPF externalities are now correctly calibrated. Singapore's CPF-inflated 'sys' balance no longer double-counts as government services.

## Authoritative Ranking (2 seeds × 11 systems, 15 mechanisms)
| Rank | System | Mean Wealth | Gini | vs LS_Full | Key Driver |
|:----:|--------|:-----------:|:----:|:----------:|------------|
| 1 | **Harberger_Georgist** | **$1,614,959** | 0.416 | +$259K | Forced-sale land concentration |
| 2 | **Singapore** | **$1,492,089** | 0.197 | +$136K | CPF with realistic externalities |
| 3 | Dual_Compact_LS | $1,483,180 | 0.328 | +$127K | Compact competition |
| 4 | Worker_Coop | $1,426,918 | 0.268 | +$71K | Profit distribution |
| 5 | Pure_Georgist | $1,374,237 | 0.304 | +$18K | Pure LVT + Dividend |
| 6 | Mutualist_LS | $1,371,659 | 0.289 | +$16K | Guild mutual insurance |
| 7 | LS_Full | $1,356,039 | 0.269 | baseline | Full LS system |
| 8 | UBI_VAT | $1,086,297 | 0.284 | −$270K | VAT + UBI |
| 9 | US_Style | $930,713 | 0.300 | −$425K | Income tax drag |
| 10 | Nordic | $904,603 | 0.292 | −$451K | High tax, high services |
| 11 | Laissez-Faire | $530,883 | 0.445 | −$825K | Zero government |

## Key Changes from Bug Fix
1. **Singapore drops from #1 to #2**: CPF externalities (0.10/0.08/0.05) reduce wealth from $2.16M to $1.49M. Gov service bug fix removed $670K of artificial CPF advantage.
2. **Harberger_Georgist takes #1**: Forced-sale + self-assessment mechanism + super-wealthy creates land concentration that makes land-owning workers wealthier.
3. **US/Nordic rise from govt service fix**: Rescaled base_g from 100K to 5K for proper flow-based calibration. US went from $819K to $931K, Nordic from $741K to $905K.
4. **LS cluster tight**: All LVT systems within $1.36-1.48M, confirming tax base > institutional flavor.

## Bugs Fixed
- **govt_service_productivity**: Was using `bal['sys'] + bal['trust']` (treasury stock). CPF contributions accumulated in 'sys', inflating Singapore's apparent government services by $550K+. Fixed to use `step_metrics['total_tax'] * 12` (annualized tax flow) with rescaled base_g=5000.

## Tests
- 9/9 backtests PASS
- 33+17+51 = 101 mechanism tests pass
