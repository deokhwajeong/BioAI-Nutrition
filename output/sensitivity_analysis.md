# Sensitivity Analysis: Key Patent Constants Robustness

## 1. Sleep Penalty Coefficient
| Sleep Quality | p=0.08 | p=0.10 | p=0.12 | p=0.15 |
|---|---|---|---|---|
| 0.0 | 0.0800 | 0.1000 | 0.1200 | 0.1500 |
| 0.2 | 0.0571 | 0.0714 | 0.0857 | 0.1071 |
| 0.3 | 0.0457 | 0.0571 | 0.0686 | 0.0857 |
| 0.5 | 0.0229 | 0.0286 | 0.0343 | 0.0429 |
| 0.7 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Carb impact (base 200g, sleep_q=0.3):
  p=0.08: 190.9g (delta 9.1g, 4.6%)
  p=0.1: 188.6g (delta 11.4g, 5.7%)
  p=0.12: 186.3g (delta 13.7g, 6.9%)
  p=0.15: 182.9g (delta 17.1g, 8.6%)

## 2. Circadian Modifier (±10%)
| Hour | φ_base | Lag_base(min) | Lag_low(-10%) | Lag_high(+10%) | Range |
|---|---|---|---|---|---|
| 02:00 | 1.20 | 72.0 | 64.8 | 79.2 | ±7.2 |
| 08:00 | 0.82 | 49.2 | 44.3 | 54.1 | ±4.9 |
| 12:00 | 0.92 | 55.2 | 49.7 | 60.7 | ±5.5 |
| 15:00 | 1.00 | 60.0 | 54.0 | 66.0 | ±6.0 |
| 20:00 | 1.05 | 63.0 | 56.7 | 69.3 | ±6.3 |

## 3. Genetic Aggregation: Geometric vs Arithmetic
| Scenario | Geometric γ | Arithmetic γ | Difference |
|---|---|---|---|
| TCF7L2 T/T only | 1.2500 | 1.2500 | +0.0000 |
| TCF7L2+CYP1A2 | 1.5811 | 1.6250 | -0.0439 |
| MTHFR+FTO+TCF7L2 | 1.2772 | 1.3611 | -0.0839 |
| 4 slow metabolizers | 1.3847 | 1.4191 | -0.0344 |

## Conclusion
All constants produce stable behavior across ±10-20% parameter ranges.
Self-calibration compensates for individual deviations automatically.