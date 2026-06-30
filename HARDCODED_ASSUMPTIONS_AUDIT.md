# Hardcoded Assumptions Audit

This file lists the main hardcoded assumptions in the project and whether each is realistic.

## Overall Assessment

The project is realistic as an explainable student/demo credit risk engine. It is not production-calibrated. The strongest parts are the deterministic financial ratios, expected loss formula, market-data-driven stress index, and audit trail. The weakest parts are the hardcoded PD proxy coefficients, LGD coefficients, credit-policy haircuts, collateral scores, and Monte Carlo dependence assumptions.

In an interview, say:

> "I made the assumptions explicit and stored them in model outputs. For production, I would calibrate PD, LGD, collateral recovery, policy haircuts, and portfolio correlation using historical defaults, recoveries, payment behavior, and bank policy data."

## 1. Financial Ratio Engine

File: `api/shared/financial_ratios.py`

| Assumption | Where Used | Realistic? | Comment |
|---|---|---|---|
| Missing denominator or zero denominator returns `None` instead of estimating | All ratio calculations | Yes | This is realistic and conservative. It avoids fake ratios. |
| `total_debt` can be derived from short-term debt + current portion of long-term debt + long-term debt | Debt ratios | Yes | Reasonable accounting fallback. |
| Quick assets can be `current_assets - inventory` when cash/receivables are incomplete | Quick ratio | Yes | Standard fallback, though direct cash + receivables is cleaner. |

Verdict: realistic. This is one of the strongest parts of the project.

## 2. Market Stress Index

File: `api/market_data/stress_index.py`

| Assumption | Where Used | Realistic? | Comment |
|---|---|---|---|
| Brent, WTI, heating oil, and jet fuel proxies represent fuel cost stress | Stress components | Mostly yes | Realistic for a fuel credit project, but direct jet fuel/bunker data is better. |
| Heating oil can proxy jet fuel when direct jet fuel data is missing | Stress index and scenarios | Reasonable proxy | Common practical proxy, but imperfect. |
| S&P 500 losses represent risk-off stress | Stress component | Yes | Broad but reasonable. |
| DXY return represents USD/FX stress | Stress component | Yes | Good general proxy, especially for fuel trades priced in USD. |
| Gold return represents safe-haven stress | Stress component | Reasonable | Directionally useful, not always clean. |
| Freight losses represent trade slowdown | Stress component | Reasonable | Useful for shipping/trade exposure. |
| Components are standardized using z-scores | Stress index | Yes | Standard risk practice. |
| PCA first component represents common market stress | Stress index | Yes | Realistic technique, but interpretation must be monitored. |
| PC1 is flipped if negatively correlated with average stress | Stress index | Yes | Practical sign-control step. |
| PC1 is scaled using 1st and 99th percentiles to a 0-100 score | Stress index | Reasonable | Good for dashboards; production would validate stress buckets. |
| Stress buckets: Calm <20, Normal <40, Elevated <60, Stressed <80, Crisis >=80 | Stress labels | Demo-realistic | Clear and intuitive, but arbitrary without calibration. |

Verdict: method is realistic, thresholds and proxy choices need validation.

## 3. Market Regime Detection

File: `api/market_data/regime_detection.py`

| Assumption | Where Used | Realistic? | Comment |
|---|---|---|---|
| Number of regimes defaults to 4 | KMeans/GMM/HMM-style regime model | Reasonable | Common choice, but should be selected via validation. |
| KMeans is default regime model | Regime detection | Reasonable for demo | Production may prefer HMM/GMM with stability testing. |
| Labels like Commodity Stress, USD Stress, Risk-Off, Crisis are assigned from cluster averages | Regime interpretation | Reasonable | Good explainability layer, but label rules are heuristic. |
| HMM-style smoothing is lightweight Markov smoothing, not a full HMM | Optional regime smoothing | Demo only | Useful, but should not be presented as a full calibrated HMM. |

Verdict: directionally realistic, but clustering labels are analyst heuristics.

## 4. PD Model - Market Context Defaults

File: `api/machine_learning/pd_model.py`

| Assumption | Where Used | Realistic? | Comment |
|---|---|---|---|
| Default stress index = `50` if market stress is missing | `MarketContext` | Demo only | Neutral default is convenient, but production should block or flag stale/missing market context. |
| Default risk-free rate = `4%` if no 10Y yield is available | Structural PD | Reasonable fallback | Acceptable as documented fallback, but production should use current curve data. |
| Default time horizon = `1 year` | PD horizon | Yes | Standard PD horizon. |
| Missing z-score components default to `0` | Market context | Reasonable | Means neutral market contribution; should be flagged. |

Verdict: acceptable for demo; production should use live/current market data and stricter missing-data controls.

## 5. PD Model - Vulnerability Scores

File: `api/machine_learning/pd_model.py`

| Assumption | Where Used | Realistic? | Comment |
|---|---|---|---|
| Airline commodity sensitivity = `0.65 + 0.25 * oil_component` | PD vulnerability | Directionally realistic | Airlines are fuel-sensitive, but coefficients are not calibrated. |
| Airline FX sensitivity = `0.45 + 0.25 * fx_component` | PD vulnerability | Directionally realistic | Fuel and aircraft costs often USD-linked. Needs calibration by geography. |
| Airline macro sensitivity = `0.40 + 0.35 * stress_component` | PD vulnerability | Directionally realistic | Airlines are cyclical, but coefficients are heuristic. |
| Shipping/marine commodity sensitivity = `0.55 + 0.20 * oil_component` | PD vulnerability | Directionally realistic | Reasonable, but varies by contract pass-through. |
| Fuel trader/distributor commodity sensitivity = `0.40 + 0.25 * oil_component` | PD vulnerability | Mixed | Traders can be very sensitive to inventory/working capital; this may understate risk. |
| Oil component divides z-score sum by `4`; FX/freight divide by `3` | Vulnerability scaling | Heuristic | Simple normalization, not statistically calibrated. |

Verdict: good explanatory mapping, not production-calibrated.

## 6. PD Model - Asset Value and Debt Threshold

File: `api/machine_learning/pd_model.py`

| Assumption | Where Used | Realistic? | Comment |
|---|---|---|---|
| Asset value proxy = accounting `total_assets` | Merton structural PD | Weak but explainable | True Merton model needs market-implied asset value. Book assets are a rough private-company proxy. |
| If total assets missing, asset value = `1.5 * revenue` | Merton structural PD fallback | Demo only | Very rough. Industry multiples vary widely. |
| Debt threshold = `total_debt` | Merton structural PD | Reasonable simplification | Merton often uses short-term debt + part of long-term debt. Total debt may overstate threshold. |
| If total debt missing, debt threshold = debt components | Merton fallback | Yes | Accounting fallback is reasonable. |
| If debt data missing, debt threshold = `60% * total_liabilities` | Merton fallback | Demo only | Arbitrary proxy. Should be replaced with real debt extraction. |
| If missing, asset/debt values default to `1.0` | Merton fallback | Not production-realistic | Prevents crashes but can create meaningless PD. Should block model run instead. |

Verdict: explainable for private-company demo; weak for production Merton modeling.

## 7. PD Model - Asset Volatility Proxy

File: `api/machine_learning/pd_model.py`

Formula:

```text
asset_volatility =
    0.18
  + 0.08 * min(leverage, 5)
  + 0.12 * stress
  + 0.10 * average_vulnerability
  + 0.05 * liquidity_weakness
```

| Assumption | Realistic? | Comment |
|---|---|---|
| Base asset volatility = `18%` | Plausible but uncalibrated | Could be okay for large corporates; airlines can be higher. |
| Leverage coefficient = `0.08` | Heuristic | Directionally right, not calibrated. |
| Stress coefficient = `0.12` | Heuristic | Directionally right. |
| Vulnerability coefficient = `0.10` | Heuristic | Directionally right. |
| Liquidity weakness coefficient = `0.05` | Heuristic | Directionally right. |
| Volatility clipped between `8%` and `95%` | Reasonable guardrail | Prevents impossible values, but bounds are judgmental. |

Verdict: useful proxy, but one of the biggest calibration gaps.

## 8. PD Model - Logistic Proxy PD

File: `api/machine_learning/pd_model.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| Logistic intercept = `-3.40` | Not production-realistic | Needs training on observed defaults. |
| Debt/EBITDA coefficient = `0.20` | Directionally realistic | Coefficient is arbitrary. |
| Debt/equity coefficient = `0.15` | Directionally realistic | Coefficient is arbitrary. |
| Weak liquidity starts below current ratio `1.20` | Reasonable | Common credit heuristic. |
| Low cash starts below cash ratio `0.50` | Conservative | Could be too strict for many companies. |
| Weak interest coverage starts below `3.0x` | Conservative but plausible | Banks often monitor below 2x-3x. |
| Negative margin coefficient = `2.00` | Directionally realistic | Arbitrary severity. |
| Market stress coefficient = `1.25` | Heuristic | Could dominate PD under stress; needs validation. |
| Commodity/FX/macro coefficients = `0.55`, `0.35`, `0.45` | Heuristic | Directionally useful, not calibrated. |
| Missing ratios fallback to neutral-ish values like debt/EBITDA `4.0`, cash ratio `0.4`, net margin `3%` | Demo only | Production should not silently substitute too many values. |

Verdict: good interview/demo explainability; not a true ML model unless trained/recalibrated.

## 9. PD Model - Final Blend and Distress Floors

File: `api/machine_learning/pd_model.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| Final PD = `65% structural + 35% ML proxy` | Reasonable design, arbitrary weights | Good to anchor structural model, but weights need backtesting. |
| If trained artifact exists, ML PD = `50% rule proxy + 50% trained model` | Demo-realistic | Sensible transition design, but weight needs validation. |
| Model disagreement if absolute divergence >= `7%` or relative ratio >= `3x` | Reasonable heuristic | Good analyst-review trigger. |
| Negative equity PD floor = `16%` | Directionally realistic | Exact number arbitrary. |
| Liabilities/assets >= `1.0` PD floor = `18%` | Directionally realistic | Exact number arbitrary. |
| Liabilities/assets >= `0.90` PD floor = `8%` | Directionally realistic | Exact number arbitrary. |
| PD clipped between `0.000001` and `0.999` | Reasonable | Numerical guardrail. |
| Confidence = `1 - divergence`, clipped `5%` to `99%` | Demo only | Simple but not statistically valid confidence. |

Verdict: sensible risk controls, but floors and weights are hardcoded policy assumptions.

## 10. LGD Model - Trade Exposure Defaults

File: `api/machine_learning/loss_model.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| Default payment tenor = `30 days` | Yes | Common trade-credit term. |
| Default utilization = `50%` | Reasonable fallback | Better to use historical utilization. |
| Default collateral = unsecured | Conservative | Realistic if no security data is provided. |
| Default country risk score = `2.0` | Demo only | Needs country-risk scale definition. |
| Default seniority score = `2.0` | Demo only | Needs legal/recovery seniority definition. |
| Default liquidity score = `0.50` if missing | Demo only | Should be linked to financial ratios. |

Verdict: workable defaults, but should be data-driven in production.

## 11. LGD Model - Collateral Strength

File: `api/machine_learning/loss_model.py` and `api/credit_decision/engine.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| Letter of credit strength = `0.90` | Reasonable | Strong bank-backed protection. Depends on issuing bank and confirmation. |
| Confirmed LC = `0.95` in decision engine | Reasonable | Stronger than ordinary LC. |
| Cash deposit = `0.80` | Conservative/possibly low | If legally perfected cash collateral, could be closer to 1.0. |
| Guarantee = `0.65` or bank guarantee = `0.70` | Reasonable | Depends heavily on guarantor quality. |
| Secured collateral = `0.55` | Rough proxy | Depends on collateral type, lien, liquidation value. |
| Unsecured = `0.05` | Reasonable low protection | Directionally correct. |
| Unknown collateral = `0.20` | Demo only | Needs mapping or analyst review. |

Verdict: directionally realistic, but should be calibrated by actual recoveries and legal enforceability.

## 12. LGD Formula

File: `api/machine_learning/loss_model.py`

Formula:

```text
lgd =
    0.62
  - 0.42 * collateral_strength
  - 0.08 * liquidity
  + 0.035 * max(country_risk - 2, 0)
  - 0.025 * max(seniority - 2, 0)
  + 0.06 * max(tenor - 30, 0) / 90
```

| Assumption | Realistic? | Comment |
|---|---|---|
| Base LGD = `62%` | Plausible | Corporate unsecured LGDs often around 40%-70%, but fuel trade recoveries vary. |
| Collateral can reduce LGD by up to `42%` | Directionally realistic | Exact effect needs recovery data. |
| Liquidity reduces LGD by up to `8%` | Weakly realistic | Liquidity affects default risk more than recovery, but still useful. |
| Country risk adds `3.5%` per point above 2 | Heuristic | Needs country-risk scale. |
| Seniority reduces `2.5%` per point above 2 | Heuristic | Needs legal seniority calibration. |
| Tenor add-on maxes roughly `6%` over 90 extra days | Reasonable but arbitrary | Longer tenor increases exposure/recovery uncertainty. |
| Unsecured LGD floor = `55%` | Reasonable | Plausible for unsecured corporate trade exposure. |
| LGD clipped between `1%` and `99%` | Reasonable guardrail | Prevents impossible values. |
| If trained LGD exists, final LGD = `65% business rule + 35% trained model` | Reasonable transition design | Weight is arbitrary. |

Verdict: directionally realistic, not empirically calibrated.

## 13. EAD and Drawdown

File: `api/machine_learning/loss_model.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| Invoice exposure = invoice amount | Yes | Direct exposure measure. |
| If invoice missing, invoice exposure = fuel volume * fuel price | Yes | Good trade-finance fallback. |
| Expected drawdown = invoice exposure * utilization * max(1, tenor/30) | Reasonable | Captures longer payment cycles; needs validation against receivable aging. |
| EAD capped by approved/requested credit limit | Usually yes | Realistic if controls prevent limit breaches. Real portfolios can exceed limits. |
| If no limit, EAD is uncapped and warned | Yes | Good warning. |

Verdict: realistic enough for a trade-credit demo.

## 14. Scenario Generator

File: `api/portfolio_risk/scenario_generator.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| Base case = 50th percentile | Yes | Median scenario. |
| Normal volatility = 75th percentile | Reasonable | Conservative normal case. |
| Adverse = 90th percentile | Yes | Standard stress quantile. |
| Severe downside = 95th percentile | Yes | Standard. |
| Tail = 99th percentile | Yes | Standard. |
| Upper-tail adverse for fuel, DXY, VIX, rates, stress | Yes | Directionally correct. |
| Lower-tail adverse for S&P 500 and freight | Yes | Directionally correct. |
| Same-regime scenario filtering only if >= `60` observations | Reasonable | Avoids tiny samples; threshold is arbitrary. |
| Jet fuel proxy fallback to heating oil; marine fuel fallback to crude oil | Reasonable proxy | Useful when direct data unavailable. |

Verdict: quite realistic for scenario construction, as it is data-driven.

## 15. Monte Carlo - Scenario Adjustments

File: `api/portfolio_risk/monte_carlo.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| Commodity pressure averages positive Brent, jet fuel, marine fuel z-scores | Reasonable | Ignores beneficial negative shocks. Good adverse-stress design. |
| Macro pressure averages VIX, rates, stress, negative S&P, negative freight | Reasonable | Directionally correct. |
| Combined pressure divides weighted sum by `3` | Heuristic | Simple normalization, not calibrated. |
| PD multiplier = `exp(0.18 * combined_pressure)` | Directionally realistic | Coefficient is arbitrary. |
| LGD add-on = `0.035 * pressure * (1 - collateral_strength)` | Directionally realistic | Coefficient arbitrary but sensible collateral interaction. |
| EAD multiplier = `1 + min(0.035 * commodity_pressure, 0.30)` | Directionally realistic | Fuel price increases invoice exposure; 30% cap arbitrary. |
| Adjusted PD clipped `0.01%` to `95%` | Reasonable guardrail | Prevents impossible simulation values. |
| Adjusted LGD clipped `1%` to `99%` | Reasonable. | Standard guardrail. |

Verdict: good stress mechanics, but coefficients are heuristic.

## 16. Monte Carlo - Default Correlation and Simulation

File: `api/portfolio_risk/monte_carlo.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| Default correlation = `0.06 + 0.18*stress + 0.025*min(stress_z + vix_z, 6)` | Directionally realistic | Correlation rises in stress, but formula is arbitrary. |
| Correlation clipped between `3%` and `55%` | Reasonable guardrail | Needs historical default correlation calibration. |
| Gaussian copula default dependence by default | Common but limited | Widely used, but underestimates tail dependence. |
| Optional t-copula degrees of freedom default = `5` | Reasonable | Captures fatter tails, but should be calibrated. |
| Random seed default = `202607` | Good for reproducibility | Fine for demo/testing. |
| LGD draw standard deviation = max(`3%`, `10% * LGD`) | Heuristic | Needs recovery volatility data. |
| EAD draw standard deviation = max(`1`, `5% * EAD`) | Heuristic | Needs utilization/exposure volatility data. |
| Default simulations = `1000` | OK for demo | Production would use more, e.g. 10k-100k depending use. |
| Compatibility fallback PD = `5%`, LGD = `60%`, exposure = `1,000,000` for dataframe helper | Demo only | Should not be used for real decisions. |

Verdict: realistic structure, but dependence and stochastic assumptions are not calibrated.

## 17. Credit Decision Engine - Risk Grade Mapping

File: `api/credit_decision/engine.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| A if PD < `1%` | Reasonable internal mapping | Not agency rating equivalent. |
| BBB if PD `1%-3%` | Reasonable | Internal proxy. |
| BB if PD `3%-7%` | Reasonable | Internal proxy. |
| B if PD `7%-15%` | Reasonable | Internal proxy. |
| CCC if PD >= `15%` | Reasonable | Internal proxy. |

Verdict: usable internal grade mapping, but should never be called agency rating.

## 18. Credit Decision Engine - Policy Haircuts

File: `api/credit_decision/engine.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| PD >= 15% adds `40%` haircut and `4` score | Directionally realistic | Exact haircut should come from credit policy. |
| PD 7%-15% adds `28%` haircut | Directionally realistic | Hardcoded policy. |
| PD 3%-7% adds `16%` haircut | Directionally realistic | Hardcoded policy. |
| PD 1%-3% adds `7%` haircut | Directionally realistic | Hardcoded policy. |
| LGD >= 70% adds `18%`; LGD >=55% adds `10%` | Directionally realistic | Needs recovery/loss appetite calibration. |
| Stress >=80 adds `15%`; stress >=65 adds `10%` | Reasonable | Thresholds are arbitrary. |
| Current ratio <1.0 adds `14%`; <1.25 adds `7%` | Reasonable | Common liquidity thresholds, haircut arbitrary. |
| Debt/EBITDA >4.0 adds `8%` | Reasonable | 4x is common leverage concern. |
| Interest coverage <2.0 adds `8%` | Reasonable | 2x is common minimum concern. |
| Tenor >60 days adds `8%` | Reasonable for trade credit | Haircut arbitrary. |
| Scenario loss ratio >=25% adds `15%`; >=10% adds `8%` | Directionally realistic | Needs portfolio loss appetite. |
| Model disagreement adds `5%` | Good governance control | Arbitrary amount. |
| Strong collateral subtracts `10%`; moderate subtracts `5%` | Directionally realistic | Needs policy calibration. |
| Total haircut clipped at `90%` | Reasonable | Avoids negative limits while still allowing severe reduction. |

Verdict: sensible rulebook, but clearly policy-proxy, not bank-approved.

## 19. Credit Decision Engine - Tenor, Security, Approval

File: `api/credit_decision/engine.py`

| Assumption | Realistic? | Comment |
|---|---|---|
| A can receive up to 90 days | Reasonable | Depends on product and counterparty. |
| BBB up to 60 days | Reasonable | Common trade-credit style. |
| BB up to 45 days | Reasonable | Conservative. |
| B up to 30 days | Reasonable | Conservative. |
| CCC gets 0 days/prepayment | Realistic | High-risk names usually require cash/LC/prepay. |
| CCC or score >6 requires prepayment/confirmed LC | Realistic | Good conservative policy. |
| PD >=7% requires standby LC or guarantee | Reasonable | Exact threshold policy-dependent. |
| Approval rejected if grade CCC, score >6.5, or recommended limit <=0 | Conservative and realistic | Good for demo. |

Verdict: realistic as a conservative internal policy, but must be approved by a real credit policy team.

## 20. Frontend Display Fallbacks

File: `frontend/app.js`

| Assumption | Realistic? | Comment |
|---|---|---|
| UI sometimes displays fallback values when backend output is missing | Demo only | Good for visual continuity, but real systems should clearly show missing data. |
| Default requested terms, labels, and placeholder statuses are used in the UI | Demo only | Should not be confused with stored model outputs. |

Verdict: fine for a dashboard demo; backend stored outputs are what matter.

## What Is Most Realistic

- Financial ratio formulas
- Expected loss formula: `PD * LGD * EAD`
- EAD based on receivables plus expected drawdown
- Market stress from z-scores and PCA
- Historical quantile scenario generation
- Storing model versions, assumptions, warnings, and input references

## What Is Least Production-Realistic

- Logistic PD coefficients
- Asset volatility proxy coefficients
- Vulnerability score coefficients
- PD blend weights
- PD distress floors
- LGD business-rule coefficients
- Collateral strength scores
- Policy haircuts and policy score thresholds
- Default correlation formula
- LGD/EAD stochastic draw assumptions
- Silent fallback values for missing model inputs

## How To Say This In An Interview

Use this answer:

> "The project intentionally uses transparent hardcoded assumptions because the goal is explainability and auditability. The financial ratios and expected loss formula are standard. The market stress index is data-driven through z-scores and PCA. But the PD proxy coefficients, LGD coefficients, collateral scores, policy haircuts, and Monte Carlo dependence assumptions are heuristic. I documented these assumptions in the model outputs. In production, I would calibrate them using historical default data, recovery data, receivable aging, collateral recovery experience, market backtesting, and approved credit policy thresholds."

