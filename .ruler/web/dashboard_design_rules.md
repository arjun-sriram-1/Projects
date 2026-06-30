# Dashboard UI/UX Rules

Use this ruler only for Streamlit dashboard layout, visual design, page UX, component behavior, and presentation. It governs `web/` work. It does not change backend models, APIs, database schema, or quantitative methods.

This ruler is based on the V2 product requirements, the existing V2 dashboard ruler, and the two UI/UX manuals:

- `output_AI_Trade_Finance_Streamlit_UltraDark_Manual.pdf`
- `output_AI_Trade_Finance_UI_UX_Manual.pdf`

## Product Intent

The dashboard is an institutional credit analyst workstation for fuel trade credit risk.

Primary analyst question:

> Can we safely extend fuel trade credit to this counterparty, and under what credit limit, tenor, collateral/security, and monitoring conditions?

The interface must feel like a professional trade finance/risk terminal, not a consumer SaaS app, not a marketing page, and not a generic Streamlit demo.

Priority order:

1. Functional credit workflow completion
2. Clarity of credit decision and data readiness
3. Explainability in analyst language
4. Sophisticated dark visual polish
5. Compact high-density layout
6. Responsive behavior without overlap or clipping

## Non-Negotiable UI Rules

- Use FastAPI through `web/api_client.py`; never connect `web/` directly to Postgres.
- Do not calculate backend model values in Streamlit.
- Display backend outputs; do not invent missing recommendations, PD, LGD, EAD, VaR, ES, or memo claims.
- No raw HTML may appear on screen. Any HTML rendered with `unsafe_allow_html=True` must be escaped for user/backend text.
- No raw JSON in normal analyst views. JSON is allowed only in a collapsed `Technical details` expander.
- Do not show table names, SQL, DB URLs, `.env`, API keys, prompts, or secrets.
- Empty/missing data must be shown clearly as a user-facing workflow state.
- Buttons must trigger clear backend actions only.
- The first screen must be useful without reading instructions.

## Visual Paradigm

Use an ultra-dark, sophisticated, high-density financial interface.

Style keywords:

- institutional
- ultra-dark slate
- high-density matrix
- restrained
- precise
- flat grid
- trade finance terminal
- credit committee ready

Avoid:

- light dashboard themes
- purple gradients
- decorative blobs/orbs/bokeh
- oversized hero sections
- cartoon or playful visuals
- generic SaaS landing-page copy
- large empty whitespace
- nested decorative cards
- excessive shadows or glass effects

## Color System

Use these tokens as the design source of truth.

| Token | Hex | Usage |
|---|---:|---|
| Canvas Background | `#05070F` or `#0B0F19` | Main app background / viewport |
| Sidebar Canvas | `#0B0F19` | Persistent navigation panel |
| Surface Background | `#111827` | Cards, panels, module blocks |
| Raised Surface | `#151F32` | KPI cards, active panels, table headers |
| Soft Surface | `#0F1422` | Alternating table rows / secondary blocks |
| Component Border | `#1E293B` | Card borders, grid lines, input borders |
| Interactive Border | `#111726` | Fine chart/table separators |
| Positive / Approved | `#00E096` | Approved states, safe limits, positive drivers |
| System / Info | `#3B82F6` | Merton/market/model links, neutral system state |
| Warning / Elevated | `#F59E0B` | Model disagreement, elevated stress, watch states |
| Critical / Danger | `#EF4444` | Rejection, severe tail loss, default/high risk |
| Text Primary | `#FFFFFF` | Headers, major values, key callouts |
| Text Secondary | `#C1C7D0` | Body copy, normal data values |
| Text Muted | `#8994A5` | Metadata, captions, helper text |
| Code / Trace Text | `#E2E8F0` | Run IDs, technical references in expanders |

State color mapping:

- Approved / low / completed / healthy: green/teal.
- Conditional / watch / elevated / medium: amber.
- Rejected / high / crisis / failed: red.
- Informational / neutral model system: blue.
- Missing/unavailable: muted slate, not red unless it is a risk failure.

## Typography

Use system-native fonts for speed and consistency.

Primary stack:

```css
Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif
```

Monospace stack for run IDs or technical traceability only:

```css
"Courier New", Monaco, Consolas, monospace
```

Scale:

| Element | Size Guidance | Weight | Color |
|---|---:|---:|---|
| Page title | 24-32px | 700-780 | `#FFFFFF` |
| Section title | 18-22px | 650-750 | `#FFFFFF` |
| KPI value | 22-28px | 760-800 | `#FFFFFF` |
| KPI label | 11-12px uppercase | 700 | `#8994A5` |
| Body text | 14-15px | 400-500 | `#C1C7D0` |
| Table cells | 12-13px | 400-500 | `#C1C7D0` |
| Captions | 12-13px | 400 | `#8994A5` |

Rules:

- Do not use hero-scale typography except for core decision or limit values.
- Keep letter spacing normal except small uppercase KPI labels may use slight positive spacing.
- Long text must wrap; never clip.
- Numeric values should be visually prominent but not oversized.

## Global Layout

Use a persistent left navigation and a single active task canvas.

Recommended structure:

- Sidebar navigation, approximately 240px desktop width.
- Top page header with product name and API health status.
- Context bar showing selected counterparty, counterparty ID, and date range.
- Page-level KPI strip near the top.
- One primary analytical task per page.
- Supporting tables/charts below the summary.

Spacing:

- Outer page padding: compact, about 24-32px desktop.
- Card padding: 14-16px.
- Inter-card gap: 12px.
- Border radius: 4-10px. Prefer crisp institutional corners over pillowy cards.
- Avoid whole-page floating card wrappers.
- Avoid nested cards unless the nested element is repeated content or a technical expander.

Cards:

- Use cards for KPIs, decision panels, status modules, data summary blocks, alert records, and chart containers.
- Do not put a whole page inside one giant white/blank container.
- KPI cards should have consistent height within a row.
- KPI cards must not display raw HTML.

## Responsive Rules

Primary target is laptop/desktop analyst workflow. Tablet and mobile must remain readable for review/monitoring.

Required behavior:

- KPI cards wrap from 4 columns to 2 columns to 1 column.
- Charts use container width.
- Tables scroll inside their own region, not the whole page.
- Sidebar may collapse through Streamlit behavior; labels must stay concise.
- Text in cards and alerts must wrap.
- Buttons must remain reachable and not overlap.
- No horizontal page-level scrolling except inside dataframes/tables.
- Page context remains visible and compact.

Validation breakpoints:

- Desktop: 1440px
- Laptop: 1280px
- Tablet: 768px
- Mobile: 390px

## Button Rules

Buttons must be few, clear, and tied to backend actions.

Primary action buttons:

- `Refresh Recommendation`
- `Upload and extract`
- `Calculate / refresh ratios`
- `Calculate PD`
- `Calculate LGD / EAD / EL`
- `Run forecast`
- `Run Monte Carlo`
- `Calculate Hedge Sensitivity`
- `Generate memo text`
- `Export DOCX / PDF memo`
- `Export risk report PDF`
- `Generate validation report`
- `Analyze supplied alert sources`

Button design:

- Primary backend action: blue or teal filled button.
- Destructive/high-risk actions: avoid unless explicitly required; use red only for real risk/destructive action.
- Secondary actions: subdued dark surface with border.
- Disabled buttons must explain why through nearby caption/help text.
- Button labels must be verbs, not vague labels like `Submit`.
- Do not use many buttons in one panel; group controls before the action button.

## Inputs And Controls

Use familiar Streamlit controls:

- Sidebar radio for page navigation.
- Number input for counterparty ID, simulation count, seed, horizon, tenor, exposure amounts.
- Text input for display labels/company filters.
- Selectbox for model type, document type, collateral/security, scenario type, copula type.
- Multiselect for market series and severity filters.
- Slider for bounded numeric values like utilization, PD, LGD, hedge ratio, rolling window.
- File uploader for PDFs only.
- Tabs for subviews within the same workflow.
- Expanders only for optional or technical details.

Rules:

- Use clear labels and short helper text.
- Default values must be safe and useful for the sample counterparty ID `180` where relevant.
- Do not ask users to enter DB IDs unless the backend requires it; prefer business labels and selected context.
- For technical IDs/run IDs, show in metadata or technical expanders.

## Tables And Data Grids

Use tables for dense numeric records only.

Table rules:

- Dark table header background `#151F32`.
- Cell text uses `#C1C7D0`.
- Header text uses muted uppercase/semi-bold style.
- Alternate row background may use `#0F1422`.
- Numeric balances align right where possible.
- Status badges align center.
- Long text columns should wrap or be summarized.
- Do not use tables for narrative summaries.
- Do not use tables for Executive Overview `Data Used`; use summary cards or natural language.

Data table use cases:

- Financial metrics ledger.
- Ratio outputs.
- Scenario matrix.
- Monte Carlo percentile table.
- Alert table.
- Validation metrics.

Avoid tables for:

- Executive explanation.
- Copilot answers.
- Decision narrative.
- Data-used summaries unless the page is explicitly a ledger/detail page.

## Chart Rules

Charts should explain risk, not decorate.

General:

- Plotly charts must use dark backgrounds matching the app.
- Gridlines use muted border color.
- Titles must be concise and specific.
- Axis labels must include units where relevant.
- VaR/Expected Shortfall markers use dashed amber/red vertical lines where available.
- Forecasts must be labeled as model estimates, not facts.
- Do not show giant charts that push the decision below the first viewport.

Preferred charts:

- Line charts for market series and forecast paths.
- Histogram/density for loss distributions.
- Bar charts for PCA loadings, factor contributions, feature contributions.
- Waterfall chart for credit limit deductions when backend provides the components.
- Gauge/thermometer for stress index when practical in Streamlit.

## Traceability And Explainability

Every model output should have an analyst-readable trace summary.

Preferred visible format:

- Data type used.
- Date/range used.
- Backend model/service used.
- Decision supported.

Good examples:

- `FY2025 financial ratios and latest market stress were used for PD classification.`
- `Market stress is available through 2026-06-12.`
- `The latest t-Copula Monte Carlo run was used for VaR and Expected Shortfall.`

Avoid by default:

- Table names.
- Raw SQL.
- Raw JSON.
- Database IDs.
- Guardrail text.
- Prompt text.

Technical traceability:

- Allowed only in collapsed expanders named `Technical details`, `Model assumptions`, or `Input references`.
- Use monospace only for run IDs, version strings, and technical references.
- Never expose secrets.

## Page-Specific Rules

### 1. Executive Overview

Purpose: immediate portfolio/counterparty executive status.

Show at top:

- Credit decision status.
- Final PD.
- Expected Loss.
- Market Stress.
- Regime.
- Alert count.
- Portfolio VaR 99.
- Expected Shortfall 99.

Rules:

- Must not show raw `<div>` or raw JSON.
- Must not show `Data Used` as a table.
- `Data Used` must be summary cards or short narrative blocks.
- If credit decision is missing, show `No decision yet` and next action, not `Unavailable` as a failure.
- Decision snapshot should show approval status, risk grade, recommended limit, tenor, security, and key risk drivers when available.
- Active alerts should show a compact list/table only if alerts exist.
- Do not overcrowd with all model internals.

Recommended layout:

- KPI deck: two rows of up to 4 KPI cards.
- Split section: Active Alerts left, Decision Snapshot right.
- Data Used: 4 compact cards: market context, credit model inputs, exposure/collateral inputs, tail-risk simulation.

### 2. Counterparty Workspace

Purpose: main analyst file for one counterparty.

Show:

- Selected counterparty and ID from context.
- Workflow completion status.
- Latest PD, LGD, EAD, Expected Loss.
- Latest recommendation summary.
- Missing data checklist and next backend step.

Rules:

- Use status badges for each workflow step.
- Missing records are workflow status, not app errors.
- Do not duplicate all details from PD/LGD or Credit Decision pages.
- Recommended limit/tenor/security should be visible if available.

### 3. Financial Extraction

Purpose: audit uploaded PDF extraction and ratios.

Show:

- Upload panel for PDF.
- Document status and extraction confidence.
- Extracted financial metrics.
- Missing critical fields and extraction warnings.
- Ratio calculation action.
- Latest ratios.

Preferred layout:

- Left 25-30% document/audit panel.
- Right 70-75% metric/ratio ledger.

Rules:

- Do not hide low confidence.
- Warnings must be visible.
- Upload button must clearly say it runs backend extraction.
- Ratio groups should be visually organized: Liquidity, Leverage, Solvency/Coverage, Profitability.

### 4. Market Intelligence

Purpose: commodity/macro context for credit risk.

Show:

- Market stress index and level.
- Regime label and confidence.
- Market data date range.
- Selected market series chart.
- Commodity factors: volatility, spreads, correlations.
- Forecasts: ARIMA, VAR, GARCH outputs from backend.

Rules:

- Forecasts are estimates and must be labeled that way.
- Market data date range must always be visible.
- Use dark Plotly chart theme.
- Avoid ticker clutter unless there is enough data and space.

### 5. PD / LGD / EAD Models

Purpose: inspect credit model outputs, not final decision.

Show:

- Structural PD, ML PD, Final PD.
- Classification label and confidence.
- Model disagreement/divergence.
- Feature contributions.
- Predicted LGD, EAD, Expected Loss.
- Model assumptions and data used.
- Backend calculation controls.

Rules:

- If Merton/ML PD divergence exceeds 5 percentage points, show amber warning.
- Do not calculate PD/LGD in UI.
- Display assumptions in expanders unless essential.
- Keep calculation input controls compact and grouped.

### 6. Scenario And Monte Carlo

Purpose: stress/tail-risk analysis.

Show:

- Scenario list/matrix.
- Scenario type.
- Number of simulations.
- Copula type: Gaussian or t-Copula.
- Degrees of freedom when t-Copula is selected.
- VaR 95/99.
- Expected Shortfall 95/99.
- Default correlation.
- Tail-dependence note.
- Hedging sensitivity.

Rules:

- Simulation configuration must be a compact top control strip.
- t-Copula selection must make tail dependence clear.
- Loss distribution chart should show VaR/ES markers when backend data supports it.
- Do not run very heavy default simulations on page load.
- User-triggered runs need spinner/loading state.

### 7. Credit Decision

Purpose: final underwriting recommendation.

This is the most important page.

Show prominently:

- Approval status.
- Risk grade.
- Recommended credit limit.
- Recommended tenor.
- Required security/collateral.
- Expected Loss.
- Key risk drivers.
- Mitigating factors.
- Financial/model/scenario inputs used.

Preferred layout:

- Left 40%: Credit authorization summary panel.
- Right 60%: Credit waterfall or model input explanation if waterfall data is not available.

Rules:

- Do not calculate or alter recommendation in dashboard.
- `Refresh Recommendation` calls backend only.
- Missing recommendation must show required backend outputs and next action.
- Use green/teal border for approval, amber for conditional/watch, red for rejection/high risk.
- Required security should be uppercase badge if important.

### 8. Monitoring Alerts

Purpose: early warning monitoring.

Show:

- Alert counts by severity.
- Severity, reason, category, counterparty, metric, value, threshold/baseline, date.
- Severity filter.
- Backend warnings if source records are missing.

Rules:

- Do not create alerts in UI.
- Alerts come from monitoring APIs.
- No active alerts should be a calm green/neutral state, not an empty page.

### 9. AI Copilot

Purpose: clean analyst chat.

Show:

- Selected counterparty context.
- Suggested questions.
- Chat messages.
- Compact `Data used` expander per answer.

Rules:

- Keep it clean: no guardrail panel, no grounding debug panel, no database table names.
- Copilot answers should follow: short answer first, explanation second, data used third, caveat if needed.
- Data used should be natural analyst language: financial period, market date range, scenario run type, recommendation date, policy document if relevant.
- Database references only if user explicitly asks for technical traceability.

### 10. Credit Memo / Reporting

Purpose: generate formal outputs.

Show:

- Latest decision/PD/EL summary.
- Memo generation control.
- Memo export control.
- Risk report export control.
- Output file paths after generation.

Rules:

- Memo text must come from backend/RAG/reporting service.
- If memo is unavailable, show backend reason clearly.
- Do not invent memo numbers.
- PDF/DOCX export buttons must be explicit.

### 11. Model Validation

Purpose: show validation report and limitations.

Show:

- Validation scope.
- Metrics.
- Sanity checks.
- Assumptions.
- Limitations.
- Markdown report.

Rules:

- Default deterministic sample arrays may be used only as demo validation input.
- Real validation requires user-supplied benchmark arrays or stored validation data.
- Assumptions and limitations must be easy to find.

## Component Specifications

### KPI Card

Required content:

- Uppercase label.
- Prominent value.
- Short helper/subtext.

Rules:

- Use dark surface and border.
- Text must be escaped.
- No raw HTML leakage.
- Helper text must not exceed one or two short lines.
- Cards wrap responsively.

### Status Badge

Rules:

- Small pill with semantic color.
- Use for approval status, risk grade, workflow completion, alert severity, stress level.
- Badge text must be short.

### Decision Panel

Rules:

- Used for final recommendation or executive snapshot.
- Must contain business terms: limit, tenor, security, status.
- Use semantic border color when practical.
- Avoid raw JSON.

### Data Summary Card

Rules:

- Use instead of tables for narrative data lineage.
- Include Data, Date/Range, Used For.
- Never show table names by default.

### Technical Expander

Rules:

- Collapsed by default.
- Label must be precise: `Technical details`, `Model assumptions`, or `Input references`.
- May contain JSON only when useful for debugging or audit.

## Streamlit Implementation Rules

- `st.set_page_config(layout="wide")` must be used.
- Theme CSS must be injected before page content renders.
- Keep reusable UI in `web/components/`.
- Keep all API calls in `web/api_client.py`.
- Page files in `web/pages/` should focus on layout and display only.
- Do not put SQLAlchemy, DB sessions, DB URLs, or backend model formulas in `web/`.
- Prefer `st.columns`, `st.tabs`, `st.expander`, `st.dataframe`, `st.plotly_chart`, and `st.chat_message` where appropriate.
- For custom HTML, escape backend/user values with `html.escape` or equivalent.
- Test page imports after UI changes.

## QA Checklist Before Finishing UI Work

- Dark background applied globally.
- Sidebar is readable and not washed out.
- KPI cards do not leak HTML.
- No raw JSON appears in normal views.
- Executive Overview does not show `Data Used` as a table.
- Credit Decision page clearly shows missing vs available backend outputs.
- Data used is analyst-friendly and hides table names by default.
- Buttons are clear backend actions.
- Empty/error states are readable on dark background.
- Charts use dark backgrounds and readable axes.
- Tables do not cause page-level horizontal scroll.
- Copilot remains clean and chat-first.
- No secrets or `.env` values are visible.
- `pytest tests/test_dashboard.py -q` passes.
- Full `pytest -q` passes when the change is broad.
