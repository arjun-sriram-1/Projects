# Full Model Audit Report

Run timestamp: `2026-06-25T12:34:22.090701Z`
Backend: `http://127.0.0.1:8010`
Backed up counterparties: `10`
Deleted counterparties before audit: `10`
Synthetic scenarios run: `10`
Total checks: `300`
Failures: `0`

## Summary

PASS: no failing checks.

## Scenario Results

### Audit Single Strong Flag Carrier

- Mode: `single_year`
- Counterparty ID: `276`
- Periods loaded: `1`
- Final PD: `4.4964%`
- Structural PD / ML PD: `0.0001%` / `17.9853%`
- LGD / EAD / EL: `17.42%` / `$5,625,540` / `$44,063`
- Recommended limit/security/status: `$19,580,000` / `Corporate Guarantee or Partial Deposit` / `CONDITIONAL APPROVAL`
- Trend status/frequency: `insufficient_history` / `annual`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 1 vs 1 |
| latest snapshot selected | PASS | 2026 FY |
| history frequency populated | PASS | annual |
| trend period count | PASS | 1 |
| single-year trend overlay neutral/limited | PASS | insufficient_history |
| current ratio formula | PASS | got 1.75 expected 1.75 |
| debt/EBITDA formula | PASS | got 1.333333 expected 1.3333333333333333 |
| interest coverage formula | PASS | got 8.2 expected 8.2 |
| latest ratios endpoint matches | PASS | 281 |
| PD range | PASS | 0.04496396 |
| structural PD range | PASS | 1e-06 |
| ML PD range | PASS | 0.17985283 |
| latest PD endpoint matches | PASS | 231 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 44062.64660592016 expected 44062.64660592016 |
| EAD within exposure cap | PASS | EAD 5625540.21 cap 22000000.0 |
| LGD range | PASS | 0.17419745 |
| latest loss endpoint matches | PASS | 199 |
| Monte Carlo run generated | PASS | db4c9af8-c21d-482d-acda-42655eb3a11f |
| Monte Carlo EL non-negative | PASS | 45024.96843419585 |
| Monte Carlo VaR capped to exposure | PASS | VaR 0.0 reference 22000000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 45024.96843419585 reference 22000000.0 |
| Monte Carlo tail order | PASS | VaR 0.0 ES 45024.96843419585 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 19580000.0 vs 22000000 |
| recommendation latest endpoint matches | PASS | 158 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 0.0 <= 22000000.0 |
| recommendation ES bounded | PASS | 45024.97 <= 22000000.0 |
| chart data available | PASS | {'financial_trend_points': 1, 'pd_forecast_inputs': {'base_pd': 0.04496396, 'scenario_pd_proxy': 0.04496396}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 0.0, 'p75': 0.0, 'p90': 0.0, 'p95': 0.0, 'p99': 1098709.71589445, 'max': 1505874.3017074887, 'mean': 45024.96843419585, 'std': 210442.88262273377}, 'market_watch_inputs_loaded': 200} |

### Audit Single Leveraged Regional Airline

- Mode: `single_year`
- Counterparty ID: `277`
- Periods loaded: `1`
- Final PD: `43.0777%`
- Structural PD / ML PD: `30.6264%` / `80.4317%`
- LGD / EAD / EL: `34.94%` / `$3,975,531` / `$598,338`
- Recommended limit/security/status: `$1,350,000` / `Prepayment or Confirmed LC` / `REJECT / PREPAYMENT ONLY`
- Trend status/frequency: `insufficient_history` / `annual`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 1 vs 1 |
| latest snapshot selected | PASS | 2026 FY |
| history frequency populated | PASS | annual |
| trend period count | PASS | 1 |
| single-year trend overlay neutral/limited | PASS | insufficient_history |
| current ratio formula | PASS | got 0.82 expected 0.82 |
| debt/EBITDA formula | PASS | got 10.4 expected 10.4 |
| interest coverage formula | PASS | got 1.051282 expected 1.0512820512820513 |
| latest ratios endpoint matches | PASS | 282 |
| PD range | PASS | 0.43077722 |
| structural PD range | PASS | 0.30626398 |
| ML PD range | PASS | 0.80431695 |
| latest PD endpoint matches | PASS | 232 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 598338.4123004134 expected 598338.4123004134 |
| EAD within exposure cap | PASS | EAD 3975531.01 cap 9000000.0 |
| LGD range | PASS | 0.34938078 |
| latest loss endpoint matches | PASS | 200 |
| Monte Carlo run generated | PASS | 0291e2e8-667e-4976-b832-8de479cb7c5e |
| Monte Carlo EL non-negative | PASS | 622532.0552834657 |
| Monte Carlo VaR capped to exposure | PASS | VaR 1592782.4429011366 reference 9000000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 1661318.675834789 reference 9000000.0 |
| Monte Carlo tail order | PASS | VaR 1592782.4429011366 ES 1661318.675834789 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 1350000.0 vs 9000000 |
| recommendation latest endpoint matches | PASS | 159 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 1592782.44 <= 9000000.0 |
| recommendation ES bounded | PASS | 1661318.68 <= 9000000.0 |
| chart data available | PASS | {'financial_trend_points': 1, 'pd_forecast_inputs': {'base_pd': 0.43077722, 'scenario_pd_proxy': 0.43077722}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 0.0, 'p75': 1377797.641802177, 'p90': 1528531.4807007455, 'p95': 1592782.4429011366, 'p99': 1701313.5984759054, 'max': 1876085.8540963044, 'mean': 622532.0552834657, 'std': 704357.8559498673}, 'market_watch_inputs_loaded': 200} |

### Audit Single Startup Carrier

- Mode: `single_year`
- Counterparty ID: `278`
- Periods loaded: `1`
- Final PD: `22.7174%`
- Structural PD / ML PD: `5.4785%` / `74.4339%`
- LGD / EAD / EL: `27.46%` / `$1,292,169` / `$80,602`
- Recommended limit/security/status: `$770,000` / `Prepayment or Confirmed LC` / `REJECT / PREPAYMENT ONLY`
- Trend status/frequency: `insufficient_history` / `annual`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 1 vs 1 |
| latest snapshot selected | PASS | 2026 FY |
| history frequency populated | PASS | annual |
| trend period count | PASS | 1 |
| single-year trend overlay neutral/limited | PASS | insufficient_history |
| current ratio formula | PASS | got 1.02 expected 1.02 |
| debt/EBITDA formula | PASS | got 17.714286 expected 17.714285714285715 |
| interest coverage formula | PASS | got 0.617204 expected 0.6172043010752688 |
| latest ratios endpoint matches | PASS | 283 |
| PD range | PASS | 0.22717389 |
| structural PD range | PASS | 0.05478536 |
| ML PD range | PASS | 0.74433949 |
| latest PD endpoint matches | PASS | 233 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 80602.01725418736 expected 80602.01725418736 |
| EAD within exposure cap | PASS | EAD 1292169.44 cap 3500000.0 |
| LGD range | PASS | 0.27457945 |
| latest loss endpoint matches | PASS | 201 |
| Monte Carlo run generated | PASS | 53dd690f-8b59-4a79-81dd-1b68e4edc0d9 |
| Monte Carlo EL non-negative | PASS | 78479.0177718358 |
| Monte Carlo VaR capped to exposure | PASS | VaR 394831.0037694523 reference 3500000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 416543.63929151924 reference 3500000.0 |
| Monte Carlo tail order | PASS | VaR 394831.0037694523 ES 416543.63929151924 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 770000.0 vs 3500000 |
| recommendation latest endpoint matches | PASS | 160 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 394831.0 <= 3500000.0 |
| recommendation ES bounded | PASS | 416543.64 <= 3500000.0 |
| chart data available | PASS | {'financial_trend_points': 1, 'pd_forecast_inputs': {'base_pd': 0.22717389, 'scenario_pd_proxy': 0.22717389}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 0.0, 'p75': 0.0, 'p90': 364708.02107178915, 'p95': 394831.0037694523, 'p99': 426991.3930774084, 'max': 475456.2678118699, 'mean': 78479.0177718358, 'std': 149628.49974457826}, 'market_watch_inputs_loaded': 200} |

### Audit Single Cargo Airline Stable

- Mode: `single_year`
- Counterparty ID: `279`
- Periods loaded: `1`
- Final PD: `5.7803%`
- Structural PD / ML PD: `0.0309%` / `23.0288%`
- LGD / EAD / EL: `17.76%` / `$4,178,366` / `$42,885`
- Recommended limit/security/status: `$9,720,000` / `Corporate Guarantee or Partial Deposit` / `CONDITIONAL APPROVAL`
- Trend status/frequency: `insufficient_history` / `annual`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 1 vs 1 |
| latest snapshot selected | PASS | 2026 FY |
| history frequency populated | PASS | annual |
| trend period count | PASS | 1 |
| single-year trend overlay neutral/limited | PASS | insufficient_history |
| current ratio formula | PASS | got 1.28 expected 1.28 |
| debt/EBITDA formula | PASS | got 2.896552 expected 2.896551724137931 |
| interest coverage formula | PASS | got 3.774603 expected 3.7746031746031745 |
| latest ratios endpoint matches | PASS | 284 |
| PD range | PASS | 0.05780349 |
| structural PD range | PASS | 0.00030871 |
| ML PD range | PASS | 0.2302878 |
| latest PD endpoint matches | PASS | 234 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 42884.86862916907 expected 42884.86862916907 |
| EAD within exposure cap | PASS | EAD 4178365.51 cap 12000000.0 |
| LGD range | PASS | 0.17755937 |
| latest loss endpoint matches | PASS | 202 |
| Monte Carlo run generated | PASS | 17c1e451-7d24-48da-b966-45336e939f02 |
| Monte Carlo EL non-negative | PASS | 39102.862313283345 |
| Monte Carlo VaR capped to exposure | PASS | VaR 374788.27798441116 reference 12000000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 770550.7443445784 reference 12000000.0 |
| Monte Carlo tail order | PASS | VaR 374788.27798441116 ES 770550.7443445784 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 9720000.0 vs 12000000 |
| recommendation latest endpoint matches | PASS | 161 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 374788.28 <= 12000000.0 |
| recommendation ES bounded | PASS | 770550.74 <= 12000000.0 |
| chart data available | PASS | {'financial_trend_points': 1, 'pd_forecast_inputs': {'base_pd': 0.05780349, 'scenario_pd_proxy': 0.05780349}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 0.0, 'p75': 0.0, 'p90': 0.0, 'p95': 374788.27798441116, 'p99': 876006.7645801014, 'max': 1105641.5499437165, 'mean': 39102.862313283345, 'std': 170566.1350238866}, 'market_watch_inputs_loaded': 200} |

### Audit Single Thin Margin Charter

- Mode: `single_year`
- Counterparty ID: `280`
- Periods loaded: `1`
- Final PD: `18.2086%`
- Structural PD / ML PD: `1.6638%` / `67.8429%`
- LGD / EAD / EL: `57.75%` / `$2,729,325` / `$287,005`
- Recommended limit/security/status: `$600,000` / `Prepayment or Confirmed LC` / `REJECT / PREPAYMENT ONLY`
- Trend status/frequency: `insufficient_history` / `annual`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 1 vs 1 |
| latest snapshot selected | PASS | 2026 FY |
| history frequency populated | PASS | annual |
| trend period count | PASS | 1 |
| single-year trend overlay neutral/limited | PASS | insufficient_history |
| current ratio formula | PASS | got 0.94 expected 0.94 |
| debt/EBITDA formula | PASS | got 9.482759 expected 9.482758620689655 |
| interest coverage formula | PASS | got 1.15297 expected 1.152969696969697 |
| latest ratios endpoint matches | PASS | 285 |
| PD range | PASS | 0.18208555 |
| structural PD range | PASS | 0.01663772 |
| ML PD range | PASS | 0.67842903 |
| latest PD endpoint matches | PASS | 235 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 287004.6211492939 expected 287004.6211492939 |
| EAD within exposure cap | PASS | EAD 2729324.52 cap 6000000.0 |
| LGD range | PASS | 0.5775083 |
| latest loss endpoint matches | PASS | 203 |
| Monte Carlo run generated | PASS | 45bd7fbb-3d95-4991-a3a1-2f864d4e60ea |
| Monte Carlo EL non-negative | PASS | 289522.7490354227 |
| Monte Carlo VaR capped to exposure | PASS | VaR 1687591.5447899094 reference 6000000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 1798261.7164784628 reference 6000000.0 |
| Monte Carlo tail order | PASS | VaR 1687591.5447899094 ES 1798261.7164784628 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 600000.0 vs 6000000 |
| recommendation latest endpoint matches | PASS | 162 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 1687591.54 <= 6000000.0 |
| recommendation ES bounded | PASS | 1798261.72 <= 6000000.0 |
| chart data available | PASS | {'financial_trend_points': 1, 'pd_forecast_inputs': {'base_pd': 0.18208555, 'scenario_pd_proxy': 0.18208555}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 0.0, 'p75': 0.0, 'p90': 1550320.9177435753, 'p95': 1687591.5447899094, 'p99': 1850580.7400258682, 'max': 2087203.7451328328, 'mean': 289522.7490354227, 'std': 615720.9583511066}, 'market_watch_inputs_loaded': 200} |

### Audit Multi Improving Airline

- Mode: `multi_annual`
- Counterparty ID: `281`
- Periods loaded: `5`
- Final PD: `4.1081%`
- Structural PD / ML PD: `0.0004%` / `17.8221%`
- LGD / EAD / EL: `16.73%` / `$4,745,564` / `$32,619`
- Recommended limit/security/status: `$14,240,000` / `Corporate Guarantee or Partial Deposit` / `CONDITIONAL APPROVAL`
- Trend status/frequency: `available` / `annual`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 5 vs 5 |
| latest snapshot selected | PASS | 2026 FY |
| history frequency populated | PASS | annual |
| trend period count | PASS | 5 |
| multi-period trend features active | PASS | 2026 FY |
| current ratio formula | PASS | got 1.48 expected 1.48 |
| debt/EBITDA formula | PASS | got 2.060606 expected 2.0606060606060606 |
| interest coverage formula | PASS | got 5.305882 expected 5.305882352941176 |
| latest ratios endpoint matches | PASS | 290 |
| PD range | PASS | 0.04108075 |
| structural PD range | PASS | 4.04e-06 |
| ML PD range | PASS | 0.17822118 |
| latest PD endpoint matches | PASS | 236 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 32619.125932443134 expected 32619.125932443134 |
| EAD within exposure cap | PASS | EAD 4745563.76 cap 16000000.0 |
| LGD range | PASS | 0.16731934 |
| latest loss endpoint matches | PASS | 204 |
| Monte Carlo run generated | PASS | 74800fd4-ddc3-4897-b206-8f791c757526 |
| Monte Carlo EL non-negative | PASS | 30955.53667662967 |
| Monte Carlo VaR capped to exposure | PASS | VaR 0.0 reference 16000000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 30955.53667662967 reference 16000000.0 |
| Monte Carlo tail order | PASS | VaR 0.0 ES 30955.53667662967 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 14240000.0 vs 16000000 |
| recommendation latest endpoint matches | PASS | 163 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 0.0 <= 16000000.0 |
| recommendation ES bounded | PASS | 30955.54 <= 16000000.0 |
| chart data available | PASS | {'financial_trend_points': 5, 'pd_forecast_inputs': {'base_pd': 0.04108075, 'scenario_pd_proxy': 0.04108075}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 0.0, 'p75': 0.0, 'p90': 0.0, 'p95': 0.0, 'p99': 883102.8723973958, 'max': 1097588.595806195, 'mean': 30955.53667662967, 'std': 156103.96861114667}, 'market_watch_inputs_loaded': 200} |

### Audit Multi Deteriorating Airline

- Mode: `multi_annual`
- Counterparty ID: `282`
- Periods loaded: `5`
- Final PD: `62.6773%`
- Structural PD / ML PD: `38.4661%` / `98.0193%`
- LGD / EAD / EL: `40.66%` / `$7,357,179` / `$1,875,105`
- Recommended limit/security/status: `$2,700,000` / `Prepayment or Confirmed LC` / `REJECT / PREPAYMENT ONLY`
- Trend status/frequency: `available` / `annual`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 5 vs 5 |
| latest snapshot selected | PASS | 2026 FY |
| history frequency populated | PASS | annual |
| trend period count | PASS | 5 |
| multi-period trend features active | PASS | 2026 FY |
| current ratio formula | PASS | got 0.76 expected 0.76 |
| debt/EBITDA formula | PASS | got 18.222222 expected 18.22222222222222 |
| interest coverage formula | PASS | got 0.6 expected 0.6 |
| latest ratios endpoint matches | PASS | 295 |
| PD range | PASS | 0.62677254 |
| structural PD range | PASS | 0.38466132 |
| ML PD range | PASS | 0.98019289 |
| latest PD endpoint matches | PASS | 237 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 1875105.2727782952 expected 1875105.2727782952 |
| EAD within exposure cap | PASS | EAD 7357179.17 cap 18000000.0 |
| LGD range | PASS | 0.40663463 |
| latest loss endpoint matches | PASS | 205 |
| Monte Carlo run generated | PASS | 1194e3af-907c-4d65-8b97-b94c36f7497e |
| Monte Carlo EL non-negative | PASS | 1944038.3041299875 |
| Monte Carlo VaR capped to exposure | PASS | VaR 3488815.125649244 reference 18000000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 3644895.1627013544 reference 18000000.0 |
| Monte Carlo tail order | PASS | VaR 3488815.125649244 ES 3644895.1627013544 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 2700000.0 vs 18000000 |
| recommendation latest endpoint matches | PASS | 164 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 3488815.13 <= 18000000.0 |
| recommendation ES bounded | PASS | 3644895.16 <= 18000000.0 |
| chart data available | PASS | {'financial_trend_points': 5, 'pd_forecast_inputs': {'base_pd': 0.62677254, 'scenario_pd_proxy': 0.62677254}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 2753395.6803003787, 'p75': 3084764.089295525, 'p90': 3344875.2996425587, 'p95': 3488815.125649244, 'p99': 3740467.526772866, 'max': 4024377.409254938, 'mean': 1944038.3041299875, 'std': 1459242.2385252982}, 'market_watch_inputs_loaded': 200} |

### Audit Quarterly Seasonal Recovery

- Mode: `multi_quarterly`
- Counterparty ID: `283`
- Periods loaded: `6`
- Final PD: `5.1639%`
- Structural PD / ML PD: `0.0276%` / `21.2876%`
- LGD / EAD / EL: `17.05%` / `$3,786,762` / `$33,338`
- Recommended limit/security/status: `$8,910,000` / `Corporate Guarantee or Partial Deposit` / `CONDITIONAL APPROVAL`
- Trend status/frequency: `available` / `quarterly`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 6 vs 6 |
| latest snapshot selected | PASS | 2026 Q2 |
| history frequency populated | PASS | quarterly |
| trend period count | PASS | 6 |
| multi-period trend features active | PASS | 2026 Q2 |
| current ratio formula | PASS | got 1.38 expected 1.38 |
| debt/EBITDA formula | PASS | got 2.709677 expected 2.7096774193548385 |
| interest coverage formula | PASS | got 4.034921 expected 4.034920634920635 |
| latest ratios endpoint matches | PASS | 301 |
| PD range | PASS | 0.0516388 |
| structural PD range | PASS | 0.00027601 |
| ML PD range | PASS | 0.21287554 |
| latest PD endpoint matches | PASS | 238 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 33337.5482148809 expected 33337.5482148809 |
| EAD within exposure cap | PASS | EAD 3786762.17 cap 11000000.0 |
| LGD range | PASS | 0.1704863 |
| latest loss endpoint matches | PASS | 206 |
| Monte Carlo run generated | PASS | f6cf4c0a-a5fe-4c7b-a01b-b604caaf58a5 |
| Monte Carlo EL non-negative | PASS | 36137.68799649575 |
| Monte Carlo VaR capped to exposure | PASS | VaR 506140.86281713215 reference 11000000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 663083.2416308188 reference 11000000.0 |
| Monte Carlo tail order | PASS | VaR 506140.86281713215 ES 663083.2416308188 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 8910000.0 vs 11000000 |
| recommendation latest endpoint matches | PASS | 165 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 506140.86 <= 11000000.0 |
| recommendation ES bounded | PASS | 663083.24 <= 11000000.0 |
| chart data available | PASS | {'financial_trend_points': 6, 'pd_forecast_inputs': {'base_pd': 0.0516388, 'scenario_pd_proxy': 0.0516388}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 0.0, 'p75': 0.0, 'p90': 0.0, 'p95': 506140.86281713215, 'p99': 758444.9700795766, 'max': 909810.9586599944, 'mean': 36137.68799649575, 'std': 150005.974166694}, 'market_watch_inputs_loaded': 200} |

### Audit Quarterly Volatile Low Cost

- Mode: `multi_quarterly`
- Counterparty ID: `284`
- Periods loaded: `6`
- Final PD: `44.2769%`
- Structural PD / ML PD: `17.5820%` / `98.0178%`
- LGD / EAD / EL: `42.57%` / `$3,447,841` / `$649,927`
- Recommended limit/security/status: `$1,050,000` / `Prepayment or Confirmed LC` / `REJECT / PREPAYMENT ONLY`
- Trend status/frequency: `available` / `quarterly`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 6 vs 6 |
| latest snapshot selected | PASS | 2026 Q2 |
| history frequency populated | PASS | quarterly |
| trend period count | PASS | 6 |
| multi-period trend features active | PASS | 2026 Q2 |
| current ratio formula | PASS | got 0.79 expected 0.79 |
| debt/EBITDA formula | PASS | got 12.727273 expected 12.727272727272727 |
| interest coverage formula | PASS | got 0.859048 expected 0.8590476190476191 |
| latest ratios endpoint matches | PASS | 307 |
| PD range | PASS | 0.44276857 |
| structural PD range | PASS | 0.17582011 |
| ML PD range | PASS | 0.9801782 |
| latest PD endpoint matches | PASS | 239 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 649927.1869925028 expected 649927.1869925028 |
| EAD within exposure cap | PASS | EAD 3447840.66 cap 7000000.0 |
| LGD range | PASS | 0.42573635 |
| latest loss endpoint matches | PASS | 207 |
| Monte Carlo run generated | PASS | 25377389-54dc-46b3-9a6c-2c935919075e |
| Monte Carlo EL non-negative | PASS | 627575.5578749246 |
| Monte Carlo VaR capped to exposure | PASS | VaR 1675213.7459406918 reference 7000000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 1755240.577764198 reference 7000000.0 |
| Monte Carlo tail order | PASS | VaR 1675213.7459406918 ES 1755240.577764198 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 1050000.0 vs 7000000 |
| recommendation latest endpoint matches | PASS | 166 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 1675213.75 <= 7000000.0 |
| recommendation ES bounded | PASS | 1755240.58 <= 7000000.0 |
| chart data available | PASS | {'financial_trend_points': 6, 'pd_forecast_inputs': {'base_pd': 0.44276857, 'scenario_pd_proxy': 0.44276857}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 0.0, 'p75': 1435517.2743056482, 'p90': 1593996.6690845464, 'p95': 1675213.7459406918, 'p99': 1798275.3210523657, 'max': 2007634.2614468427, 'mean': 627575.5578749246, 'std': 737790.7684163444}, 'market_watch_inputs_loaded': 200} |

### Audit Mixed Annual Quarterly Flag Carrier

- Mode: `mixed_annual_quarterly`
- Counterparty ID: `285`
- Periods loaded: `5`
- Final PD: `5.1978%`
- Structural PD / ML PD: `0.0008%` / `20.6815%`
- LGD / EAD / EL: `16.76%` / `$5,500,996` / `$47,927`
- Recommended limit/security/status: `$16,200,000` / `Corporate Guarantee or Partial Deposit` / `CONDITIONAL APPROVAL`
- Trend status/frequency: `available` / `mixed`
- Check result: `PASS (30/30 passed)`

| Check | Status | Detail |
|---|---:|---|
| history period count | PASS | 5 vs 5 |
| latest snapshot selected | PASS | 2026 Q2 |
| history frequency populated | PASS | mixed |
| trend period count | PASS | 5 |
| multi-period trend features active | PASS | 2026 Q2 |
| current ratio formula | PASS | got 1.46 expected 1.46 |
| debt/EBITDA formula | PASS | got 2.160494 expected 2.1604938271604937 |
| interest coverage formula | PASS | got 5.060571 expected 5.0605714285714285 |
| latest ratios endpoint matches | PASS | 312 |
| PD range | PASS | 0.05197839 |
| structural PD range | PASS | 8.23e-06 |
| ML PD range | PASS | 0.20681529 |
| latest PD endpoint matches | PASS | 240 |
| PD has market sensitivities | PASS |  |
| expected loss formula | PASS | got 47927.42845810074 expected 47927.42845810074 |
| EAD within exposure cap | PASS | EAD 5500995.6 cap 20000000.0 |
| LGD range | PASS | 0.16761775 |
| latest loss endpoint matches | PASS | 208 |
| Monte Carlo run generated | PASS | 6ced903a-ef96-452e-a78c-0ebcb270b3cc |
| Monte Carlo EL non-negative | PASS | 49609.13749318238 |
| Monte Carlo VaR capped to exposure | PASS | VaR 586130.5288859442 reference 20000000.0 |
| Monte Carlo ES capped to exposure | PASS | ES 966799.7036449468 reference 20000000.0 |
| Monte Carlo tail order | PASS | VaR 586130.5288859442 ES 966799.7036449468 |
| recommendation generated | PASS |  |
| recommended limit bounded | PASS | 16200000.0 vs 20000000 |
| recommendation latest endpoint matches | PASS | 167 |
| recommendation PD/EL coherence | PASS |  |
| recommendation VaR bounded | PASS | 586130.53 <= 20000000.0 |
| recommendation ES bounded | PASS | 966799.7 <= 20000000.0 |
| chart data available | PASS | {'financial_trend_points': 5, 'pd_forecast_inputs': {'base_pd': 0.05197839, 'scenario_pd_proxy': 0.05197839}, 'monte_carlo_histogram': {'min': 0.0, 'p50': 0.0, 'p75': 0.0, 'p90': 0.0, 'p95': 586130.5288859442, 'p99': 1075555.6164982496, 'max': 1412915.0402160739, 'mean': 49609.13749318238, 'std': 214537.45627089706}, 'market_watch_inputs_loaded': 200} |
