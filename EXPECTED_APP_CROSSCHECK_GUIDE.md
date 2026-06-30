# Expected App Cross-Check Guide

Use this document to manually verify the app after entering or selecting the synthetic audit counterparties.

Source audit run:
`data/audit_runs/full_model_audit_20260625_123321`

Tolerance:
- Ratios should match almost exactly.
- PD/LGD/EAD/EL should be very close.
- Monte Carlo values can move if rerun with a different seed, but ordering and bounds should remain logical.
- Market values can change if live market data is refreshed.

---

## 1. Audit Single Strong Flag Carrier

### Requested Credit Terms

| Field | Expected Value |
|---|---:|
| Requested Limit | $22.0M |
| Existing Approved Limit Input | $18.0M |
| Invoice Amount | $2.1M |
| Fuel Volume | 720,000 |
| Fuel Price | $2.75 |
| Outstanding Receivables | $5.0M |
| Requested Tenor | 30 days |
| Utilization Rate | 45% |
| Requested Security | Letter of Credit |

### Financial Statement Table

| Data Point | Expected Value |
|---|---:|
| Fiscal Period | 2026 FY |
| Period Type | Annual |
| Revenue | $4,800.0M |
| EBITDA | $864.0M |
| EBIT | $708.5M |
| Interest Expense | $86.4M |
| Net Income | $360.0M |
| Cash | $624.0M |
| Current Assets | $1,512.0M |
| Total Assets | $5,853.7M |
| Current Liabilities | $864.0M |
| Total Debt | $1,152.0M |
| Total Liabilities | $2,400.0M |
| Equity | $3,453.7M |

### Ratio Table

| Ratio | Expected Value |
|---|---:|
| Current Ratio | 1.75 |
| Quick Ratio | 1.33 |
| Cash Ratio | 0.72 |
| Working Capital | $648.0M |
| Debt / Equity | 0.33 |
| Debt / EBITDA | 1.33 |
| Liabilities / Assets | 41.0% |
| Interest Coverage | 8.20 |
| Operating Margin | 14.76% |
| Net Margin | 7.50% |
| ROA | 6.15% |
| ROE | 10.42% |

### Trend Layer

| Data Point | Expected Value |
|---|---|
| Period Count | 1 |
| History Status | insufficient_history |
| History Frequency | annual |
| Latest Period | 2026 FY |
| Overlay Direction | neutral |
| PD Multiplier | 1.00 |
| LGD Add-On | 0.00 |

### Quant / Monte Carlo Table

| Data Point | Expected Value |
|---|---:|
| Final PD | 4.50% |
| Structural PD | ~0.00% |
| ML PD | 17.99% |
| Risk Grade | BB |
| Model Confidence | 82.01% |
| Distance to Default | 6.22 |
| Asset Value Proxy | $5,853.7M |
| Debt Threshold | $1,152.0M |
| Asset Volatility | 26.31% |
| LGD | 17.42% |
| EAD | $5.63M |
| Expected Loss | $44.1K |
| Monte Carlo EL | $45.0K |
| VaR 95 | $0 |
| ES 95 | $45.0K |
| VaR 99 | $1.10M |
| ES 99 | $1.22M |

### Credit Recommendation Table

| Data Point | Expected Value |
|---|---|
| Approval Status | CONDITIONAL APPROVAL |
| Risk Grade | BB |
| Recommended Limit | $19.58M |
| Recommended Tenor | 30 days |
| Required Security | Corporate Guarantee or Partial Deposit |
| Limit Haircut | 11% |
| Policy Score | 1.5 |
| Key Drivers | Moderate PD; structural and ML PD disagree |
| Mitigants | Strong liquidity, short tenor, LC/collateral support |

### Graph Expectations

| Graph | What It Should Look Like |
|---|---|
| Financial Trend | Only one usable period or limited history indication. No strong multi-year curve. |
| Ratio Heatmap | Strong liquidity and coverage; low leverage pressure. |
| Market Charts | Same global market charts for all counterparties unless market data refreshed. |
| PD / Quant Visuals | Structural PD should look near zero while ML PD is visibly higher. |
| Monte Carlo Histogram | Mostly concentrated near zero loss; small tail. VaR 95 can be zero, ES 95 around expected loss. |
| Credit Recommendation | Conditional approval with high recommended limit relative to requested limit. |

---

## 2. Audit Single Leveraged Regional Airline

### Requested Credit Terms

| Field | Expected Value |
|---|---:|
| Requested Limit | $9.0M |
| Existing Approved Limit Input | $5.5M |
| Invoice Amount | $1.15M |
| Fuel Volume | 410,000 |
| Fuel Price | $2.81 |
| Outstanding Receivables | $3.2M |
| Requested Tenor | 45 days |
| Utilization Rate | 72% |
| Requested Security | Guarantee |

### Ratio Table

| Ratio | Expected Value |
|---|---:|
| Current Ratio | 0.82 |
| Quick Ratio | 0.81 |
| Cash Ratio | 0.19 |
| Working Capital | -$30.8M |
| Debt / Equity | 4.35 |
| Debt / EBITDA | 10.40 |
| Liabilities / Assets | 85.28% |
| Interest Coverage | 1.05 |
| Operating Margin | 6.15% |
| Net Margin | -1.80% |
| ROA | -1.48% |
| ROE | -10.03% |

### Quant / Monte Carlo Table

| Data Point | Expected Value |
|---|---:|
| Final PD | 43.08% |
| Structural PD | 30.63% |
| ML PD | 80.43% |
| Risk Grade | CCC |
| Model Confidence | 50.19% |
| Distance to Default | 0.51 |
| LGD | 34.94% |
| EAD | $3.98M |
| Expected Loss | $598.3K |
| VaR 95 | $1.59M |
| ES 95 | $1.66M |

### Credit Recommendation Table

| Data Point | Expected Value |
|---|---|
| Approval Status | REJECT / PREPAYMENT ONLY |
| Risk Grade | CCC |
| Recommended Limit | $1.35M |
| Recommended Tenor | 0 days |
| Required Security | Prepayment or Confirmed LC |
| Limit Haircut | 85% |
| Policy Score | 10.0 |
| Key Drivers | Very high PD, weak liquidity, high leverage, weak coverage, high tail loss |

### Graph Expectations

| Graph | What It Should Look Like |
|---|---|
| Ratio Heatmap | Liquidity, leverage, and coverage should look weak. |
| PD Visuals | Structural and ML PD both high; ML PD higher. |
| Monte Carlo Histogram | Much wider than strong case; visible tail with VaR/ES around $1.6M. |
| Recommendation Visuals | Large haircut from requested limit to recommended limit. |

---

## 3. Audit Multi Improving Airline

### Requested Credit Terms

| Field | Expected Value |
|---|---:|
| Requested Limit | $16.0M |
| Existing Approved Limit Input | $13.5M |
| Invoice Amount | $1.8M |
| Fuel Volume | 640,000 |
| Fuel Price | $2.82 |
| Outstanding Receivables | $4.0M |
| Requested Tenor | 30 days |
| Utilization Rate | 48% |
| Requested Security | Letter of Credit |

### Latest Financial Statement Table

| Data Point | Expected Value |
|---|---:|
| Latest Period | 2026 FY |
| Period Count | 5 |
| Revenue | $3,100.0M |
| EBITDA | $511.5M |
| EBIT | $419.4M |
| Interest Expense | $79.1M |
| Net Income | $198.4M |
| Cash | $325.5M |
| Current Assets | $825.8M |
| Total Debt | $1,054.0M |
| Equity | $1,920.5M |

### Ratio Table

| Ratio | Expected Value |
|---|---:|
| Current Ratio | 1.48 |
| Quick Ratio | 1.19 |
| Cash Ratio | 0.58 |
| Debt / EBITDA | 2.06 |
| Interest Coverage | 5.31 |
| Operating Margin | 13.53% |
| Net Margin | 6.40% |

### Trend Layer

| Data Point | Expected Value |
|---|---:|
| History Status | available |
| Frequency | annual |
| Revenue CAGR | 14.56% |
| Latest Revenue Growth | 12.73% |
| EBITDA Margin Trend | +2.13 pp |
| Net Margin Trend | +1.35 pp |
| Debt Growth | -5.56% |
| Leverage Trend | -1.42 |
| Interest Coverage Trend | +0.97 |
| Current Ratio Trend | +0.14 |
| Direction | improving |
| PD Multiplier | 0.85 |
| LGD Add-On | 0.00 |

### Quant / Recommendation

| Data Point | Expected Value |
|---|---:|
| Final PD | 4.11% |
| Structural PD | ~0.00% |
| ML PD | 17.82% |
| LGD | 16.73% |
| EAD | $4.75M |
| Expected Loss | $32.6K |
| VaR 95 | $0 |
| ES 95 | $31.0K |
| Recommended Limit | $14.24M |
| Tenor | 30 days |
| Status | CONDITIONAL APPROVAL |
| Grade | BB |

### Graph Expectations

| Graph | What It Should Look Like |
|---|---|
| Multi-Year Financial Trend | Revenue and EBITDA slope upward; debt gradually lower. |
| Ratio Heatmap | Improving liquidity and coverage. |
| Trend Feature Panel | Direction should say improving; PD multiplier below 1.0. |
| Monte Carlo Histogram | Low-loss concentration similar to strong case. |

---

## 4. Audit Multi Deteriorating Airline

### Requested Credit Terms

| Field | Expected Value |
|---|---:|
| Requested Limit | $18.0M |
| Existing Approved Limit Input | $8.0M |
| Invoice Amount | $2.25M |
| Fuel Volume | 790,000 |
| Fuel Price | $2.85 |
| Outstanding Receivables | $6.8M |
| Requested Tenor | 60 days |
| Utilization Rate | 78% |
| Requested Security | Guarantee |

### Latest Financial Statement Table

| Data Point | Expected Value |
|---|---:|
| Latest Period | 2026 FY |
| Period Count | 5 |
| Revenue | $1,880.0M |
| EBITDA | $84.6M |
| EBIT | $69.4M |
| Interest Expense | $115.6M |
| Net Income | -$90.2M |
| Cash | $58.3M |
| Current Assets | $257.2M |
| Total Debt | $1,541.6M |
| Equity | $262.3M |

### Ratio Table

| Ratio | Expected Value |
|---|---:|
| Current Ratio | 0.76 |
| Quick Ratio | 0.78 |
| Cash Ratio | 0.17 |
| Working Capital | -$81.2M |
| Debt / Equity | 5.88 |
| Debt / EBITDA | 18.22 |
| Liabilities / Assets | 88.56% |
| Interest Coverage | 0.60 |
| Operating Margin | 3.69% |
| Net Margin | -4.80% |

### Trend Layer

| Data Point | Expected Value |
|---|---:|
| History Status | available |
| Frequency | annual |
| Revenue CAGR | -10.27% |
| Latest Revenue Growth | -11.32% |
| EBITDA Margin Trend | -2.88 pp |
| Net Margin Trend | -2.58 pp |
| Debt Growth | +56.35% |
| Leverage Trend | +4.02 |
| Interest Coverage Trend | -1.14 |
| Current Ratio Trend | -0.18 |
| Direction | deteriorating |
| PD Multiplier | 1.38 |
| Asset Volatility Add-On | 3.04 pp |
| LGD Add-On | 3.80 pp |

### Quant / Recommendation

| Data Point | Expected Value |
|---|---:|
| Final PD | 62.68% |
| Structural PD | 38.47% |
| ML PD | 98.02% |
| LGD | 40.66% |
| EAD | $7.36M |
| Expected Loss | $1.88M |
| VaR 95 | $3.49M |
| ES 95 | $3.64M |
| Recommended Limit | $2.70M |
| Tenor | 0 days |
| Security | Prepayment or Confirmed LC |
| Status | REJECT / PREPAYMENT ONLY |
| Grade | CCC |

### Graph Expectations

| Graph | What It Should Look Like |
|---|---|
| Multi-Year Financial Trend | Revenue and EBITDA fall; debt rises. |
| Ratio Heatmap | Liquidity, leverage, and coverage should look very weak. |
| Trend Feature Panel | Direction should be deteriorating; PD multiplier above 1.0. |
| Monte Carlo Histogram | Wide loss distribution; VaR/ES materially higher than expected loss. |
| Recommendation | Very large haircut and rejection/prepayment decision. |

---

## 5. Audit Quarterly Seasonal Recovery

### Requested Credit Terms

| Field | Expected Value |
|---|---:|
| Requested Limit | $11.0M |
| Existing Approved Limit Input | $8.8M |
| Invoice Amount | $1.32M |
| Fuel Volume | 470,000 |
| Fuel Price | $2.81 |
| Outstanding Receivables | $3.3M |
| Requested Tenor | 30 days |
| Utilization Rate | 52% |
| Requested Security | Letter of Credit |

### Latest Financial Statement Table

| Data Point | Expected Value |
|---|---:|
| Latest Period | 2026 Q2 |
| Period Count | 6 |
| Frequency | quarterly |
| Revenue | $470.0M |
| EBITDA | $72.9M |
| EBIT | $59.7M |
| Interest Expense | $14.8M |
| Net Income | $22.6M |
| Cash | $42.8M |
| Current Assets | $116.7M |
| Total Debt | $197.4M |
| Equity | $253.6M |

### Ratio Table

| Ratio | Expected Value |
|---|---:|
| Current Ratio | 1.38 |
| Quick Ratio | 1.12 |
| Cash Ratio | 0.51 |
| Debt / Equity | 0.78 |
| Debt / EBITDA | 2.71 |
| Interest Coverage | 4.03 |
| Operating Margin | 12.71% |
| Net Margin | 4.80% |

### Trend Layer

| Data Point | Expected Value |
|---|---:|
| History Status | available |
| Frequency | quarterly |
| Latest Revenue Growth | 8.05% |
| EBITDA Margin Trend | +1.70 pp |
| Net Margin Trend | +1.16 pp |
| Debt Growth | +9.79% |
| Leverage Trend | -1.12 |
| Interest Coverage Trend | +0.54 |
| Current Ratio Trend | +0.09 |
| Direction | improving |
| PD Multiplier | 0.934 |
| LGD Add-On | 0.00 |

### Quant / Recommendation

| Data Point | Expected Value |
|---|---:|
| Final PD | 5.16% |
| Structural PD | 0.03% |
| ML PD | 21.29% |
| LGD | 17.05% |
| EAD | $3.79M |
| Expected Loss | $33.3K |
| VaR 95 | $506.1K |
| ES 95 | $663.1K |
| Recommended Limit | $8.91M |
| Tenor | 30 days |
| Security | Corporate Guarantee or Partial Deposit |
| Status | CONDITIONAL APPROVAL |
| Grade | BB |

### Graph Expectations

| Graph | What It Should Look Like |
|---|---|
| Quarterly Financial Trend | Revenue rises from Q1 2025 to Q2 2026 with seasonal recovery. |
| Ratio Heatmap | Healthy but not as strong as the flag carrier. |
| Trend Feature Panel | Frequency should be quarterly and direction improving. |
| Monte Carlo Histogram | Mostly low loss with a visible tail around $0.5M-$0.7M. |
| Recommendation | Conditional approval, lower limit than requested, security required. |

---

## Global Market Page Expectations

These values can change when live data is refreshed.

| Section | Expected Behavior |
|---|---|
| Market Regime | Clean label like Balanced Market, Mixed Market, Fuel-Cost Pressure, Macro Pressure, or Risk-Off Market. It should not show raw labels like Risk-Off 3 as the main title. |
| Market Snapshot | Brent, USD/INR, Jet Fuel, Volatility, Overall Risk cards should show latest value and previous-date-to-latest-date change window. |
| Brent vs Jet Fuel Chart | Two smooth indexed lines. Brent and jet fuel should not be identical; jet fuel may move with lag because it uses EIA/latest available data. |
| USD/INR Chart | Single USD/INR line with tight Y-axis. It may still be nearly flat if FX movement is tiny, but axis values should make the small movement readable. |
| Key Market Signals | Six rows: Fuel Prices, USD/INR, Interest Rates, Inflation, Air Passenger Demand, Freight/Trade Activity. |
| Impact on Selected Airline | Badges for fuel pressure, FX exposure, margin pressure, credit quality, external risk. |
| Live Market Watch | Should not include Gold or Inflation as cards. Should include Brent, WTI, Jet Fuel, DXY, VIX, S&P 500, US 10Y, Baltic Dry, Global PMI, IATA Traffic. |

---

## Co-Pilot Questions To Ask After Checking

1. Why did this counterparty receive this risk grade?
2. Explain how final PD is calculated from structural PD and ML PD.
3. Why does structural PD differ so much from ML PD here?
4. How is expected loss calculated for this counterparty?
5. Why did the deteriorating airline get rejected?
6. How does the multi-year trend layer affect PD and LGD?
7. Why is the improving airline still only conditionally approved?
8. Why is prepayment or confirmed LC required?
9. What does current ratio mean and how does it affect the decision?
10. Why is expected shortfall higher than VaR?
11. How does fuel price affect airline credit risk?
12. Which data points caused the recommended limit haircut?
