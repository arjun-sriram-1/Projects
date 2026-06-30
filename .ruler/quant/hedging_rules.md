# Hedging Sensitivity Rules

Use these rules only for hedge impact, commodity/FX sensitivity, and before/after risk analysis.

Purpose:

- Hedging sensitivity shows how oil or FX hedges may reduce credit exposure indirectly.
- Hedge analysis is a sensitivity tool, not a guarantee of loss reduction.

Required inputs:

- counterparty_id or portfolio segment
- exposure
- commodity_sensitivity_score or FX sensitivity
- hedge_type
- hedge_notional
- hedge_ratio
- scenario_market_move
- hedge_price or reference_price when available

Required outputs:

- unhedged_exposure
- hedge_payoff
- hedged_exposure
- unhedged_expected_loss
- hedged_expected_loss
- exposure_reduction
- expected_loss_reduction
- before_after_metrics
- assumptions
- warnings

Rules:

- Do not reduce PD directly just because a hedge exists.
- Hedge payoff may reduce effective exposure or scenario loss, depending on the model design.
- Show before and after metrics side by side.
- Explain basis risk, hedge ratio, and missing data assumptions.
- Hedge results must be connected to scenarios or stored exposure data.

Validation:

- A zero hedge ratio should produce no hedge benefit.
- Larger valid hedge notional should not increase hedged exposure all else equal.
- Oil or FX move direction must be consistent with the hedge payoff sign.
- Hedge benefit must not exceed the modeled exposure unless explicitly capped and documented.
