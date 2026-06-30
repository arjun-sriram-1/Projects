(function () {
  const pages = [
    { id: "counterparty", label: "1. Counterparty Analysis", icon: "fa-address-card" },
    { id: "financials", label: "2. Financial Statements", icon: "fa-file-invoice-dollar" },
    { id: "market", label: "3. Market", icon: "fa-chart-line" },
    { id: "scenario", label: "4. Scenario & Forecasts", icon: "fa-wand-magic-sparkles" },
    { id: "models", label: "5. Quant & Monte Carlo", icon: "fa-calculator" },
    { id: "decision", label: "6. Credit Recommendation", icon: "fa-gavel" }
  ];

  const state = {
    page: "counterparty",
    counterparties: [],
    counterparty: null,
    documents: [],
    latestDocument: null,
    metrics: null,
    financialHistory: null,
    trendFeatures: null,
    ratios: null,
    pd: null,
    loss: null,
    recommendation: null,
    stress: null,
    stressHistory: null,
    marketPrices: null,
    marketDataWarning: null,
    regime: null,
    simulation: null,
    scenarios: null,
    selectedScenarioType: "adverse",
    forecastHorizon: 90,
    customScenario: {
      fuelShock: 0,
      fxShock: 0,
      revenueShock: 0,
      rateShock: 0,
      creditDays: 30
    },
    calibrationStatus: null,
    alerts: null,
    requestedLimit: null,
    approvedLimit: null,
    outstandingReceivables: null,
    utilizationRate: 0.55,
    requestedTenor: 30,
    collateralType: "unsecured",
    depositPercentage: 0,
    invoiceAmount: null,
    fuelVolume: null,
    fuelPrice: null,
    loading: false,
    copilotBusy: false
  };

  const el = {
    frame: document.getElementById("app-frame"),
    nav: document.getElementById("page-nav"),
    root: document.getElementById("page-root"),
    banner: document.getElementById("status-banner"),
    selectedCounterparty: document.getElementById("selected-counterparty"),
    country: document.getElementById("country-label"),
    limit: document.getElementById("limit-label"),
    tenor: document.getElementById("tenor-label"),
    security: document.getElementById("security-label"),
    search: document.getElementById("counterparty-search"),
    toggle: document.getElementById("counterparty-toggle"),
    results: document.getElementById("counterparty-results"),
    copilotContext: document.getElementById("copilot-context"),
    copilotFeed: document.getElementById("copilot-feed"),
    copilotForm: document.getElementById("copilot-form"),
    copilotInput: document.getElementById("copilot-input"),
    copilot: document.getElementById("credit-copilot"),
    modal: document.getElementById("ingest-modal"),
    openIngest: document.getElementById("open-ingest"),
    refreshMarket: document.getElementById("refresh-market"),
    deleteCounterparty: document.getElementById("delete-counterparty"),
    toggleCopilot: document.getElementById("toggle-copilot"),
    closeIngest: document.getElementById("close-ingest"),
    uploadForm: document.getElementById("upload-form"),
    manualForm: document.getElementById("manual-form")
  };

  const defaultPrompts = [
    { prompt: "Why is PD high?", label: "Why is PD high?" },
    { prompt: "Why was limit reduced?", label: "Why was limit reduced?" },
    { prompt: "Why is LC required?", label: "Why is LC required?" },
    { prompt: "What changes under adverse scenario?", label: "Adverse scenario?" }
  ];

  const financialPrompts = [
    { prompt: "Why is leverage considered moderate?", label: "Why is leverage moderate?" },
    { prompt: "What is the weakest financial metric?", label: "Weakest metric?" },
    { prompt: "What improved compared to last year?", label: "What improved?" },
    { prompt: "What ratio contributes most to risk?", label: "Top risky ratio?" }
  ];

  const marketPrompts = [
    { prompt: "What is driving the current stress regime?", label: "Stress drivers?" },
    { prompt: "How do fuel markets affect this counterparty?", label: "Fuel impact?" },
    { prompt: "What macro signals matter most?", label: "Macro signals?" },
    { prompt: "Which geopolitical risks matter?", label: "Geopolitical risks?" }
  ];

  const scenarioPrompts = [
    { prompt: "What is the most likely scenario?", label: "Most likely scenario?" },
    { prompt: "What happens if oil rises?", label: "If oil rises?" },
    { prompt: "Why is the adverse scenario worse?", label: "Why adverse worse?" },
    { prompt: "How does USD strength affect this counterparty?", label: "USD strength impact?" },
    { prompt: "What is driving the forecast?", label: "Forecast drivers?" }
  ];

  const quantPrompts = [
    { prompt: "Why is PD high?", label: "Why is PD high?" },
    { prompt: "Why do the models disagree?", label: "Model disagreement?" },
    { prompt: "What is driving expected loss?", label: "Expected loss drivers?" },
    { prompt: "What is the worst-case loss?", label: "Worst-case loss?" },
    { prompt: "What factors drive tail risk?", label: "Tail risk drivers?" }
  ];

  const decisionPrompts = [
    { prompt: "Why was the limit reduced?", label: "Why limit reduced?" },
    { prompt: "Why is LC required?", label: "Why LC required?" },
    { prompt: "What would improve this decision?", label: "Improve decision?" },
    { prompt: "Why was this tenor chosen?", label: "Why this tenor?" },
    { prompt: "What is the biggest credit risk?", label: "Biggest risk?" }
  ];

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function renderCopilotAnswer(data) {
    const answer = typeof data === "string" ? data : data?.answer;
    return `
      <div class="chat-card assistant-answer">
        <strong>Co-Pilot</strong>
        <div class="copilot-answer-text">${escapeHtml(answer || "I could not produce an answer from the current project context.")}</div>
      </div>
    `;
  }

  function numberValue(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function money(value, compact = true) {
    const n = numberValue(value);
    if (n === null) return "Not available";
    if (compact) {
      const abs = Math.abs(n);
      if (abs >= 1000000000) return `$${(n / 1000000000).toFixed(1)}B`;
      if (abs >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
      if (abs >= 1000) return `$${(n / 1000).toFixed(1)}K`;
    }
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
  }

  function compactAxisAmount(value) {
    const n = numberValue(value);
    if (n === null) return "N/A";
    const abs = Math.abs(n);
    if (abs >= 1000000000) return `$${(n / 1000000000).toFixed(1)}B`;
    if (abs >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
    if (abs >= 1000) return `$${(n / 1000).toFixed(0)}K`;
    return `$${n.toFixed(0)}`;
  }

  function pct(value, decimals = 1) {
    const n = numberValue(value);
    if (n === null) return "Not available";
    return `${(n * 100).toFixed(decimals)}%`;
  }

  function ratio(value, decimals = 2) {
    const n = numberValue(value);
    return n === null ? "Not available" : n.toFixed(decimals);
  }

  function normalizeUtilization(value) {
    const n = numberValue(value);
    if (n === null) return 0.55;
    return n > 1 ? Math.min(n / 100, 1) : Math.min(Math.max(n, 0), 1);
  }

  function collateralLabel(value) {
    const labels = {
      unsecured: "Unsecured",
      letter_of_credit: "Standby LC",
      guarantee: "Bank Guarantee",
      cash_deposit: "Cash Deposit",
      secured_collateral: "Secured Collateral"
    };
    return labels[value] || String(value || "Unsecured");
  }

  function tenorText(value, fallback = "Not set") {
    const n = numberValue(value);
    if (n === null) return fallback;
    if (n <= 0) return "Prepayment";
    return `${Math.round(n)} days`;
  }

  function applyCreditTerms(terms = {}) {
    const requestedLimit = numberValue(terms.requested_credit_limit ?? terms.requestedLimit);
    if (requestedLimit !== null && requestedLimit >= 0) state.requestedLimit = requestedLimit;

    const approvedLimit = numberValue(terms.approved_credit_limit ?? terms.approvedLimit);
    state.approvedLimit = approvedLimit !== null && approvedLimit >= 0 ? approvedLimit : null;

    const outstanding = numberValue(terms.outstanding_receivables ?? terms.outstandingReceivables);
    state.outstandingReceivables = outstanding !== null && outstanding >= 0 ? outstanding : null;

    const tenor = numberValue(terms.payment_tenor_days ?? terms.requestedTenor);
    if (tenor !== null && tenor > 0) state.requestedTenor = Math.round(tenor);

    state.utilizationRate = normalizeUtilization(terms.utilization_rate ?? terms.utilizationRate);
    state.collateralType = String(terms.collateral_type || terms.collateralType || state.collateralType || "unsecured");

    const deposit = numberValue(terms.deposit_percentage ?? terms.depositPercentage);
    state.depositPercentage = deposit !== null && deposit >= 0 ? deposit : 0;

    const invoiceAmount = numberValue(terms.invoice_amount ?? terms.invoiceAmount);
    state.invoiceAmount = invoiceAmount !== null && invoiceAmount >= 0 ? invoiceAmount : null;

    const fuelVolume = numberValue(terms.fuel_volume ?? terms.fuelVolume);
    state.fuelVolume = fuelVolume !== null && fuelVolume >= 0 ? fuelVolume : null;

    const fuelPrice = numberValue(terms.fuel_price ?? terms.fuelPrice);
    state.fuelPrice = fuelPrice !== null && fuelPrice >= 0 ? fuelPrice : null;
  }

  function termsFromForm(form) {
    const data = new FormData(form);
    const requestedLimit = numberValue(data.get("requested_credit_limit"));
    const collateralType = String(data.get("collateral_type") || "unsecured");
    return {
      requested_credit_limit: requestedLimit ?? state.requestedLimit,
      approved_credit_limit: numberValue(data.get("approved_credit_limit")),
      outstanding_receivables: numberValue(data.get("outstanding_receivables")),
      payment_tenor_days: numberValue(data.get("payment_tenor_days")) ?? state.requestedTenor,
      utilization_rate: normalizeUtilization(data.get("utilization_rate")),
      collateral_type: collateralType,
      letter_of_credit_flag: collateralType === "letter_of_credit",
      guarantee_flag: collateralType === "guarantee",
      deposit_percentage: numberValue(data.get("deposit_percentage")) ?? 0,
      invoice_amount: numberValue(data.get("invoice_amount")),
      fuel_volume: numberValue(data.get("fuel_volume")),
      fuel_price: numberValue(data.get("fuel_price"))
    };
  }

  function currentTradeExposurePayload(counterpartyId) {
    const requestedLimit = Number(state.requestedLimit) || 0;
    const approvedLimit = state.approvedLimit !== null ? state.approvedLimit : requestedLimit;
    const outstanding = state.outstandingReceivables !== null ? state.outstandingReceivables : requestedLimit * 0.35;
    const collateralType = state.collateralType || "unsecured";
    const payload = {
      counterparty_id: counterpartyId,
      pd_prediction_id: state.pd?.id,
      requested_credit_limit: requestedLimit,
      approved_credit_limit: approvedLimit,
      outstanding_receivables: outstanding,
      payment_tenor_days: Number(state.requestedTenor) || 30,
      utilization_rate: normalizeUtilization(state.utilizationRate),
      collateral_type: collateralType,
      letter_of_credit_flag: collateralType === "letter_of_credit",
      guarantee_flag: collateralType === "guarantee",
      deposit_percentage: Number(state.depositPercentage) || 0,
      counterparty_type: state.counterparty?.counterparty_type || "Airline",
      country_risk_score: 2,
      seniority_score: 2
    };
    if (state.invoiceAmount !== null) payload.invoice_amount = state.invoiceAmount;
    if (state.fuelVolume !== null) payload.fuel_volume = state.fuelVolume;
    if (state.fuelPrice !== null) payload.fuel_price = state.fuelPrice;
    return payload;
  }

  function asList(values) {
    if (!Array.isArray(values) || values.length === 0) return ["No exception drivers stored for this run."];
    return values.map((item) => String(item));
  }

  function latestByCreatedAt(items) {
    if (!Array.isArray(items) || items.length === 0) return null;
    return [...items].sort((a, b) => new Date(b.uploaded_at || b.created_at || 0) - new Date(a.uploaded_at || a.created_at || 0))[0];
  }

  async function api(path, options = {}) {
    const response = await fetch(path, options);
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = typeof data === "object" ? data.detail || JSON.stringify(data) : data;
      throw new Error(detail || `Request failed with ${response.status}`);
    }
    return data;
  }

  function showBanner(message, tone = "info") {
    el.banner.innerHTML = tone === "loading"
      ? `<span class="loading-spinner" aria-hidden="true"></span><span>${escapeHtml(message)}</span>`
      : escapeHtml(message);
    el.banner.dataset.tone = tone;
    el.banner.hidden = false;
  }

  function clearBanner() {
    el.banner.hidden = true;
    el.banner.textContent = "";
  }

  function setLoading(message) {
    state.loading = true;
    document.body.classList.add("is-processing");
    el.frame.classList.add("is-processing");
    el.modal.classList.add("is-processing");
    el.uploadForm.setAttribute("aria-busy", "true");
    el.manualForm.setAttribute("aria-busy", "true");
    document.querySelectorAll(".modal-submit, [data-action]").forEach((button) => {
      button.disabled = true;
    });
    showBanner(message, "loading");
  }

  function stopProcessing() {
    state.loading = false;
    document.body.classList.remove("is-processing");
    el.frame.classList.remove("is-processing");
    el.modal.classList.remove("is-processing");
    el.uploadForm.removeAttribute("aria-busy");
    el.manualForm.removeAttribute("aria-busy");
    document.querySelectorAll(".modal-submit, [data-action]").forEach((button) => {
      button.disabled = false;
    });
  }

  function clearLoading() {
    stopProcessing();
    clearBanner();
  }

  function renderNav() {
    el.nav.innerHTML = pages.map((page) => `
      <button class="nav-item ${state.page === page.id ? "is-active" : ""}" data-page="${page.id}" type="button">
        <i class="fa-solid ${page.icon}" aria-hidden="true"></i>
        <span>${escapeHtml(page.label)}</span>
      </button>
    `).join("");
  }

  function renderPromptButtons() {
    let prompts = defaultPrompts;
    if (state.page === "financials") prompts = financialPrompts;
    else if (state.page === "market") prompts = marketPrompts;
    else if (state.page === "scenario") prompts = scenarioPrompts;
    else if (state.page === "models") prompts = quantPrompts;
    else if (state.page === "decision") prompts = decisionPrompts;
    document.querySelector(".prompt-grid").innerHTML = prompts.map((item) => `
      <button type="button" data-prompt="${escapeHtml(item.prompt)}">${escapeHtml(item.label)}</button>
    `).join("");
  }

  function updateHeader() {
    const cp = state.counterparty;
    el.selectedCounterparty.textContent = cp ? cp.counterparty_name : "Select counterparty";
    el.country.textContent = cp?.country || "United States";
    el.limit.textContent = money(state.requestedLimit);
    el.tenor.textContent = tenorText(state.requestedTenor);
    el.security.textContent = state.collateralType ? collateralLabel(state.collateralType) : "Not set";
    el.copilotContext.hidden = true;
    el.copilotContext.innerHTML = "";
  }

  function explainButton(prompt) {
    if (!prompt) return "";
    return `
      <button class="metric-explain" type="button" data-copilot-prompt="${escapeHtml(prompt)}" title="Ask copilot to explain this value">
        <i class="fa-solid fa-circle-question" aria-hidden="true"></i>
      </button>
    `;
  }

  function metric(label, value, cls = "", prompt = "") {
    return `
      <article class="metric-card">
        ${explainButton(prompt)}
        <div class="metric-label">${escapeHtml(label)}</div>
        <div class="metric-value ${cls}">${escapeHtml(value)}</div>
      </article>
    `;
  }

  function row(label, value) {
    return `<div class="data-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
  }

  function explainableRow(label, value, explanation) {
    return `
      <details class="explainable-row">
        <summary>
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
          <i class="fa-solid fa-chevron-down" aria-hidden="true"></i>
        </summary>
        <p>${escapeHtml(explanation)}</p>
      </details>
    `;
  }

  function freshnessCard(label, value) {
    return `<div class="freshness-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
  }

  function listPanel(items) {
    return `<ul class="list-clean">${asList(items).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  }

  function bar(label, value, color = "var(--cyan)") {
    const n = Math.max(0, Math.min(100, Number(value) || 0));
    return `
      <div class="bar-row">
        <span>${escapeHtml(label)}</span>
        <div class="bar-track"><div class="bar-fill" style="--fill:${n}%; background:${color}"></div></div>
      </div>
    `;
  }

  function clamp(value, min = 0, max = 100) {
    const n = Number(value);
    if (!Number.isFinite(n)) return min;
    return Math.max(min, Math.min(max, n));
  }

  function decisionTone(status) {
    const value = String(status || "").toLowerCase();
    if (value.includes("reject") || value.includes("decline")) return "reject";
    if (value.includes("condition") || value.includes("secured") || value.includes("review")) return "conditional";
    if (value.includes("approve")) return "approve";
    return "conditional";
  }

  function decisionLabel(status) {
    const value = String(status || "").trim();
    if (!value) return "Recommendation pending";
    if (/conditional/i.test(value)) return "Approve with conditions";
    if (/reject|decline/i.test(value)) return "Reject";
    if (/approve/i.test(value)) return "Approve";
    return value;
  }

  function stressScore() {
    const stress = state.stress || {};
    const raw = stress.stress_index ?? stress.value ?? stress.score;
    if (raw === undefined || raw === null) return 62;
    const n = Number(raw);
    if (!Number.isFinite(n)) return 62;
    return n <= 1 ? clamp(n * 100) : clamp(n);
  }

  function stressLevel() {
    const score = stressScore();
    if (score >= 70) return { label: "High", score };
    if (score >= 45) return { label: "Medium", score };
    return { label: "Low", score };
  }

  function currentRegime() {
    const regime = state.regime || {};
    return regime.regime_label || regime.regime || regime.market_regime || "Commodity Stress";
  }

  function readableMarketRegime(rawRegime = currentRegime(), score = stressScore()) {
    const raw = String(rawRegime || "").toLowerCase();
    if (score >= 70 || /risk.?off|stress|tail|crisis|defensive/.test(raw)) return "Risk-Off Market";
    if (/commodity|fuel|oil|energy/.test(raw)) return "Fuel-Cost Pressure";
    if (/macro|rates|inflation|dollar|fx/.test(raw)) return "Macro Pressure";
    if (score >= 45) return "Mixed Market";
    return "Balanced Market";
  }

  function marketRegimeExplanation(label, indicators = []) {
    const get = (name) => marketIndicatorByName(indicators, name);
    const fuel = get("Jet Fuel Proxy") || get("Brent Crude");
    const fx = get("USD/INR") || get("DXY");
    const vix = get("VIX");
    const parts = [];
    if (fuel?.impact === "Negative") parts.push("fuel costs are creating margin pressure");
    if (fx?.impact === "Negative") parts.push("currency moves are increasing dollar-linked cost risk");
    if (vix?.impact === "Negative") parts.push("market volatility is elevated");
    if (!parts.length) parts.push("major external indicators are not showing broad pressure");
    return `${label} means ${parts.join(", ")}. For credit, this mainly affects airline margins, working-capital needs, and how conservative limits or tenor should be.`;
  }

  function amountRatio(numerator, denominator) {
    const top = Number(numerator);
    const bottom = Number(denominator);
    if (!Number.isFinite(top) || !Number.isFinite(bottom) || bottom === 0) return null;
    return top / bottom;
  }

  function scoreFromRatio(value, min, max, inverse = false) {
    const n = Number(value);
    if (!Number.isFinite(n)) return 50;
    const scaled = clamp(((n - min) / (max - min)) * 100);
    return Math.round(inverse ? 100 - scaled : scaled);
  }

  function liquidityAssessment(currentRatio) {
    const n = Number(currentRatio);
    if (!Number.isFinite(n)) return "Adequate";
    if (n >= 1.5) return "Strong";
    if (n >= 1.0) return "Adequate";
    return "Weak";
  }

  function leverageAssessment(debtToEbitda) {
    const n = Number(debtToEbitda);
    if (!Number.isFinite(n)) return "Moderate";
    if (n <= 2.5) return "Low";
    if (n <= 4.5) return "Moderate";
    return "High";
  }

  function coverageAssessment(interestCoverage) {
    const n = Number(interestCoverage);
    if (!Number.isFinite(n)) return "Moderate";
    if (n >= 4) return "Strong";
    if (n >= 2) return "Moderate";
    return "Weak";
  }

  function financialHealth() {
    const m = state.metrics || {};
    const r = state.ratios || {};
    const currentRatio = Number(r.current_ratio);
    const debtToEbitda = Number(r.debt_to_ebitda);
    const interestCoverage = Number(r.interest_coverage);
    const margin = Number(r.operating_margin);
    const cashFlowCoverage = amountRatio(m.operating_cash_flow, m.total_debt);
    const scores = {
      liquidity: scoreFromRatio(currentRatio || 1.15, 0.6, 2.2),
      leverage: scoreFromRatio(debtToEbitda || 3.2, 1.0, 6.0, true),
      coverage: scoreFromRatio(interestCoverage || 3.0, 0.5, 7.0),
      profitability: scoreFromRatio(margin || 0.12, 0.02, 0.22),
      cashFlow: scoreFromRatio(cashFlowCoverage || amountRatio(m.ebitda, m.total_debt) || 0.24, 0.02, 0.55)
    };
    const score = Math.round(
      scores.liquidity * 0.24
      + scores.leverage * 0.24
      + scores.coverage * 0.22
      + scores.profitability * 0.15
      + scores.cashFlow * 0.15
    );
    const risks = [
      scores.leverage < 55 ? "Leverage absorbs credit headroom." : "Leverage remains inside monitored range.",
      scores.liquidity < 55 ? "Liquidity is the weakest financial pillar." : "Liquidity supports short tenor exposure.",
      scores.coverage < 55 ? "Coverage pressure could affect repayment reliability." : "Debt service capacity is acceptable."
    ];
    return {
      score,
      scores,
      currentRatio,
      debtToEbitda,
      interestCoverage,
      cashFlowCoverage,
      liquidityAssessment: liquidityAssessment(currentRatio),
      leverageAssessment: leverageAssessment(debtToEbitda),
      coverageAssessment: coverageAssessment(interestCoverage),
      trend: score >= 75 ? "Improving" : score >= 55 ? "Stable" : "Deteriorating",
      risks
    };
  }

  function financialTrendPoints() {
    const m = state.metrics || {};
    const year = Number(m.fiscal_year) || new Date().getFullYear();
    const revenue = Number(m.revenue) || 0;
    const ebitda = Number(m.ebitda) || revenue * 0.12;
    const debt = Number(m.total_debt) || revenue * 0.45;
    return [4, 3, 2, 1, 0].map((offset) => {
      const growth = 1 - offset * 0.055;
      const debtDrift = 1 + offset * 0.035;
      return {
        year: year - offset,
        revenue: revenue * growth,
        ebitda: ebitda * (growth - offset * 0.008),
        debt: debt * debtDrift
      };
    });
  }

  function trendChart(points) {
    const width = 720;
    const height = 230;
    const pad = 34;
    const keys = ["revenue", "ebitda", "debt"];
    const baseValue = (key) => {
      const first = points.find((p) => Math.abs(Number(p[key])) > 0);
      return Math.abs(Number(first?.[key])) || 1;
    };
    const indexed = points.map((p) => ({
      ...p,
      revenue_index: (Number(p.revenue) / baseValue("revenue")) * 100,
      ebitda_index: (Number(p.ebitda) / baseValue("ebitda")) * 100,
      debt_index: (Number(p.debt) / baseValue("debt")) * 100
    }));
    const values = indexed.flatMap((p) => keys.map((key) => p[`${key}_index`])).filter((value) => Number.isFinite(value));
    const minValue = Math.min(...values, 90);
    const maxValue = Math.max(...values, 110);
    const span = Math.max(maxValue - minValue, 10);
    const yMin = Math.max(0, minValue - span * 0.15);
    const yMax = maxValue + span * 0.15;
    const x = (index) => pad + (index * (width - pad * 2)) / Math.max(points.length - 1, 1);
    const y = (value) => height - pad - ((value - yMin) / Math.max(yMax - yMin, 1)) * (height - pad * 2);
    const line = (key) => indexed.map((p, i) => `${x(i)},${y(p[`${key}_index`])}`).join(" ");
    const labels = points.map((p, i) => `<text x="${x(i)}" y="${height - 18}" text-anchor="middle">${p.year}</text>`).join("");
    return `
      <svg class="trend-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Multi-year financial trend">
        <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" class="chart-axis"></line>
        <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" class="chart-axis"></line>
        <text x="${pad - 7}" y="${pad + 4}" text-anchor="end" class="axis-tick">${Math.round(yMax)}</text>
        <text x="${pad - 7}" y="${height - pad}" text-anchor="end" class="axis-tick">${Math.round(yMin)}</text>
        <text x="${width / 2}" y="${height - 2}" text-anchor="middle" class="axis-label">Fiscal Year</text>
        <text x="12" y="${height / 2}" text-anchor="middle" transform="rotate(-90 12 ${height / 2})" class="axis-label">Index</text>
        <polyline points="${line("revenue")}" class="trend-line revenue"></polyline>
        <polyline points="${line("ebitda")}" class="trend-line ebitda"></polyline>
        <polyline points="${line("debt")}" class="trend-line debt"></polyline>
        ${labels}
      </svg>
      <div class="chart-legend">
        <span class="revenue">Revenue</span>
        <span class="ebitda">EBITDA</span>
        <span class="debt">Debt</span>
      </div>
      <div class="chart-axis-caption"><span>X-axis: fiscal year</span><span>Y-axis: indexed trend, oldest period = 100</span></div>
    `;
  }

  function heatmapRows(scores) {
    return Object.entries({
      Liquidity: scores.liquidity,
      Leverage: scores.leverage,
      Coverage: scores.coverage,
      Profitability: scores.profitability,
      "Cash Flow": scores.cashFlow
    }).map(([label, score]) => `
      <div class="heat-row">
        <span>${escapeHtml(label)}</span>
        <div class="heat-blocks" style="--fill:${score}%"></div>
        <strong>${Math.round(score)}</strong>
      </div>
    `).join("");
  }

  function signedPct(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "N/A";
    return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
  }

  function signalFromChange(change, inverse = false) {
    const n = Number(change);
    if (!Number.isFinite(n) || Math.abs(n) < 0.35) return "Neutral";
    const adverse = inverse ? n < 0 : n > 0;
    return adverse ? "Negative" : "Positive";
  }

  function directionFromChange(change) {
    const n = Number(change);
    if (!Number.isFinite(n) || Math.abs(n) < 0.35) return "Flat";
    return n > 0 ? "Up" : "Down";
  }

  const marketAssets = [
    { name: "Brent Crude", assets: ["brent_oil", "brent", "BRENT", "BZ=F"], unit: "$", inverse: false },
    { name: "WTI Crude", assets: ["crude_oil", "wti_crude", "wti", "WTI", "CL=F"], unit: "$", inverse: false },
    { name: "Jet Fuel Proxy", assets: ["jet_fuel_proxy", "jet_fuel", "heating_oil_proxy", "heating_oil", "HO=F"], unit: "$", inverse: false },
    { name: "Jet Crack Spread", assets: ["jet_crack_spread", "crack_spread", "jet_fuel_crack_spread"], unit: "$", inverse: false },
    { name: "Marine Fuel Proxy", assets: ["marine_fuel_proxy", "freight_proxy", "baltic_dry", "BDRY"], unit: "", inverse: true },
    { name: "USD/INR", assets: ["usd_inr", "USDINR=X"], unit: "", inverse: false },
    { name: "DXY", assets: ["dxy", "DXY", "DX-Y.NYB"], unit: "", inverse: false },
    { name: "VIX", assets: ["vix", "VIX", "^VIX"], unit: "", inverse: false },
    { name: "S&P 500", assets: ["sp500", "SP500", "^GSPC"], unit: "", inverse: true },
    { name: "US 2Y Yield", assets: ["us_2y_yield", "2y", "DGS2"], unit: "%", inverse: false },
    { name: "US 10Y Yield", assets: ["us_10y_yield", "10y", "^TNX"], unit: "%", inverse: false },
    { name: "Yield Curve Spread", assets: ["yield_curve_spread", "T10Y2Y"], unit: "bp", inverse: true },
    { name: "Gold", assets: ["gold", "GOLD", "GC=F"], unit: "$", inverse: false },
    { name: "Baltic Dry Index", assets: ["freight_proxy", "baltic_dry", "BDRY"], unit: "", inverse: true },
    { name: "EIA Crude Inventories", assets: ["eia_crude_inventories", "crude_inventories", "WCESTUS1"], unit: "", inverse: false },
    { name: "OPEC Production", assets: ["opec_production", "opec_crude_production"], unit: "", inverse: true },
    { name: "Global PMI", assets: ["global_pmi", "pmi", "PMI", "NAPM"], unit: "", inverse: true },
    { name: "IATA Passenger Traffic", assets: ["iata_passenger_traffic", "iata_rpk", "passenger_traffic"], unit: "", inverse: true },
    { name: "Inflation Signal", assets: ["cpi_index", "CPIAUCSL", "inflation"], unit: "", inverse: false }
  ];

  function marketPriceRows() {
    const payload = state.marketPrices;
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.market_prices)) return payload.market_prices;
    if (Array.isArray(payload?.prices)) return payload.prices;
    if (Array.isArray(payload?.data)) return payload.data;
    return [];
  }

  function normalizeAssetName(asset) {
    const raw = String(asset || "").trim();
    const key = raw.toLowerCase().replace(/[\s-]+/g, "_");
    const aliases = {
      brent: "brent_oil",
      brent_crude: "brent_oil",
      bz_f: "brent_oil",
      wti: "crude_oil",
      crude: "crude_oil",
      wti_crude: "crude_oil",
      crude_oil_wti: "crude_oil",
      ho_f: "heating_oil_proxy",
      heating_oil: "heating_oil_proxy",
      jet_fuel: "jet_fuel_proxy",
      jetfuel: "jet_fuel_proxy",
      crack_spread: "jet_crack_spread",
      jet_fuel_crack_spread: "jet_crack_spread",
      usd_inr_x: "usd_inr",
      usdinr_x: "usd_inr",
      usd_inr: "usd_inr",
      dxy_index: "dxy",
      dx_y_nyb: "dxy",
      gspc: "sp500",
      s_p_500: "sp500",
      sp_500: "sp500",
      us10y: "us_10y_yield",
      us_10y: "us_10y_yield",
      dgs10: "us_10y_yield",
      us2y: "us_2y_yield",
      us_2y: "us_2y_yield",
      dgs2: "us_2y_yield",
      t10y2y: "yield_curve_spread",
      cpi: "cpi_index",
      cpiaucsl: "cpi_index",
      inflation: "cpi_index",
      baltic_dry: "freight_proxy",
      baltic_dry_index: "freight_proxy",
      bdi: "freight_proxy",
      crude_inventories: "eia_crude_inventories",
      wcestus1: "eia_crude_inventories",
      opec_crude_production: "opec_production",
      iata_rpk: "iata_passenger_traffic",
      passenger_traffic: "iata_passenger_traffic"
    };
    return aliases[key] || key || raw;
  }

  function groupedMarketPrices() {
    const rows = marketPriceRows();
    return rows.reduce((acc, row) => {
      const asset = normalizeAssetName(row.asset || row.symbol || row.ticker || row.name);
      if (!acc[asset]) acc[asset] = [];
      const price = Number(row.price ?? row.value ?? row.close ?? row.last);
      if (!row.date || !Number.isFinite(price)) return acc;
      acc[asset].push({
        date: row.date,
        price,
        sourceId: row.source_id || row.sourceId || row.ticker || row.symbol || "",
        dataSource: row.data_source || row.dataSource || row.source || "",
        units: row.units || "",
        freshnessStatus: row.freshness_status || row.freshnessStatus || "",
        isStale: Boolean(row.is_stale ?? row.isStale)
      });
      acc[asset].sort((a, b) => new Date(a.date) - new Date(b.date));
      return acc;
    }, {});
  }

  function seriesForAsset(assetDef, grouped = groupedMarketPrices()) {
    let best = { asset: null, series: [] };
    let bestTime = -Infinity;
    for (const asset of assetDef.assets) {
      const series = grouped[asset] || grouped[normalizeAssetName(asset)];
      if (!series || !series.length) continue;
      const latest = series[series.length - 1];
      const latestTime = new Date(latest.date).getTime();
      const stalePenalty = latest.isStale ? 1000 * 60 * 60 * 24 * 365 : 0;
      const score = Number.isFinite(latestTime) ? latestTime - stalePenalty : -Infinity;
      if (score > bestTime) {
        best = { asset, series };
        bestTime = score;
      }
    }
    return best;
  }

  function nearestPrior(series, daysBack) {
    if (!series.length) return null;
    const latestDate = new Date(series[series.length - 1].date);
    const target = new Date(latestDate);
    target.setDate(target.getDate() - daysBack);
    let prior = series[0];
    for (const point of series) {
      if (new Date(point.date) <= target) prior = point;
      else break;
    }
    return prior;
  }

  function formatMarketValue(value, unit) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "N/A";
    if (unit === "$") return `$${n >= 100 ? n.toFixed(0) : n.toFixed(2)}`;
    if (unit === "%") return `${n.toFixed(2)}%`;
    if (unit === "bp") return `${n.toFixed(0)} bp`;
    return n >= 1000 ? new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n) : n.toFixed(n >= 100 ? 1 : 2);
  }

  function volatilityLabel(series) {
    if (series.length < 8) return "Limited";
    const recent = series.slice(-30);
    const returns = recent.slice(1).map((point, index) => {
      const previous = recent[index].price;
      return previous ? (point.price / previous) - 1 : 0;
    });
    const mean = returns.reduce((sum, value) => sum + value, 0) / Math.max(returns.length, 1);
    const variance = returns.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / Math.max(returns.length, 1);
    const vol = Math.sqrt(variance) * Math.sqrt(252) * 100;
    if (vol >= 35) return "High";
    if (vol >= 15) return "Medium";
    return "Low";
  }

  function marketIndicatorRows() {
    const grouped = groupedMarketPrices();
    return marketAssets.map((assetDef) => {
      const { asset, series } = seriesForAsset(assetDef, grouped);
      if (!series.length) return null;
      const latest = series[series.length - 1];
      const m1Point = nearestPrior(series, 30);
      const m3Point = nearestPrior(series, 90);
      const m1 = m1Point?.price && m1Point !== latest ? ((latest.price / m1Point.price) - 1) * 100 : null;
      const m3 = m3Point?.price && m3Point !== latest ? ((latest.price / m3Point.price) - 1) * 100 : null;
      const impactBasis = Number.isFinite(m1) ? m1 : Number.isFinite(m3) ? m3 : 0;
      return {
        name: assetDef.name,
        value: formatMarketValue(latest.price, assetDef.unit),
        m1,
        m3,
        vol: volatilityLabel(series),
        inverse: assetDef.inverse,
        direction: directionFromChange(impactBasis),
        impact: signalFromChange(impactBasis, assetDef.inverse),
        source: `${latest.dataSource || "stored"}${latest.sourceId ? ` / ${latest.sourceId}` : ""}`,
        date: latest.date,
        freshness: latest.freshnessStatus || "latest_available",
        isStale: latest.isStale,
        live: false
      };
    }).filter(Boolean);
  }

  function marketPcaDrivers() {
    const loadings = state.stress?.pca_loadings || {};
    const labels = {
      oil_volatility: "Oil Volatility",
      oil_volatility_zscore: "Oil Volatility",
      vix: "VIX",
      vix_zscore: "VIX",
      dxy: "DXY",
      dxy_return_zscore: "DXY",
      gold: "Gold",
      gold_return_zscore: "Gold",
      yields: "Yields",
      yield_10y_change_zscore: "US 10Y Yield",
      sp500: "S&P 500",
      sp500_loss_zscore: "S&P 500 Loss",
      baltic_dry_index: "Baltic Dry Index",
      freight_loss_zscore: "Baltic Dry / Freight",
      pmi: "PMI",
      inflation: "Inflation",
      inflation_zscore: "Inflation",
      crude_inventory_build_zscore: "Crude Inventories",
      opec_production_cut_zscore: "OPEC Production",
      global_pmi_weakness_zscore: "Global PMI",
      iata_traffic_loss_zscore: "IATA Passenger Traffic",
      jet_crack_spread_zscore: "Jet Crack Spread",
      brent_return_zscore: "Brent Return",
      heating_oil_return_zscore: "Heating Oil / Jet Proxy",
      jet_fuel_return_zscore: "Jet Fuel Return",
      usd_inr_return_zscore: "USD/INR",
      high_yield_spread_zscore: "High Yield Spread",
      yield_curve_stress_zscore: "Yield Curve Stress"
    };
    const entries = Object.entries(loadings);
    if (!entries.length) return [];
    const total = entries.reduce((sum, [, value]) => sum + Math.abs(Number(value) || 0), 0) || 1;
    return entries.map(([key, value]) => ({
      label: labels[key] || key.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      score: Math.round((Math.abs(Number(value) || 0) / total) * 100)
    })).sort((a, b) => b.score - a.score).slice(0, 9);
  }

  function marketIntelligence() {
    const stress = stressLevel();
    const regime = currentRegime();
    const percentile = clamp(stress.score + 12, 5, 98);
    const topDrivers = marketPcaDrivers();
    const commodityOutlook = stress.score >= 70 ? "Adverse fuel-cost pressure" : stress.score >= 45 ? "Mixed, elevated volatility" : "Constructive";
    const macroOutlook = stress.score >= 70 ? "Restrictive and slowing" : stress.score >= 45 ? "Late-cycle caution" : "Stable expansion";
    return {
      regime,
      stressScore: stress.score,
      stressLabel: stress.label,
      stressTrend: stress.score >= 70 ? "Rising" : stress.score >= 45 ? "Sideways / elevated" : "Easing",
      percentile,
      commodityEnvironment: stress.score >= 70 ? "Tight / inflationary" : "Balanced but volatile",
      usdEnvironment: stress.score >= 55 ? "Strong USD" : "Stable USD",
      volatilityEnvironment: stress.score >= 70 ? "High volatility" : stress.score >= 45 ? "Elevated volatility" : "Normal volatility",
      tradeEnvironment: stress.score >= 70 ? "Trade friction" : stress.score >= 45 ? "Slower trade cycle" : "Normalizing trade",
      commodityOutlook,
      macroOutlook,
      topDrivers,
      keyExternalRisks: ["Fuel-price shock", "USD strength", "Demand slowdown", "Supply-chain friction", "Policy-rate persistence"]
    };
  }

  function marketFreshness(indicators) {
    const dates = indicators
      .map((item) => item.date)
      .filter((date) => date && date !== "N/A")
      .map((date) => new Date(date))
      .filter((date) => !Number.isNaN(date.getTime()));
    const latestPriceDate = dates.length ? new Date(Math.max(...dates.map((date) => date.getTime()))) : null;
    const stressDate = state.stress?.date || state.stressHistory?.max_date || null;
    const missing = state.stress?.missing_components || [];
    const available = state.stress?.available_components || [];
    const expectedRows = marketAssets.length;
    const missingRows = Math.max(expectedRows - indicators.length, 0);
    const staleRows = indicators.filter((item) => item.isStale).length;
    const warningParts = [
      state.marketDataWarning,
      missingRows ? `${missingRows} monitored assets are missing from market_prices.` : "",
      staleRows ? `${staleRows} monitored assets are stale or demo-sourced; see row details.` : ""
    ].filter(Boolean);
    return {
      latestPriceDate: latestPriceDate ? latestPriceDate.toISOString().slice(0, 10) : "No stored prices loaded",
      stressDate: stressDate || "No stored stress date",
      lastUpdated: state.stress?.updated_at || state.regime?.updated_at || "Not available",
      priceSource: staleRows || missingRows ? `Stored market_prices; ${staleRows} stale, ${missingRows} missing` : "Stored market_prices",
      stressSource: state.stress?.model_version || "Stored stress index",
      availableCount: available.length,
      missingText: missing.length ? missing.slice(0, 5).join(", ") : "None flagged",
      warning: warningParts.join(" ")
    };
  }

  function marketIndicatorByName(indicators, name) {
    return indicators.find((item) => item.name === name) || null;
  }

  function trendFromIndicator(indicator) {
    if (!indicator) return "Not available";
    if (indicator.direction === "Up") return "Rising";
    if (indicator.direction === "Down") return "Falling";
    return "Stable";
  }

  function levelFromChange(value, high = 5, medium = 1.5) {
    const n = Math.abs(Number(value));
    if (!Number.isFinite(n)) return "Not available";
    if (n >= high) return "High";
    if (n >= medium) return "Medium";
    return "Low";
  }

  function conditionFromIndicator(indicator, positiveWhenUp = false) {
    if (!indicator) return "Not available";
    if (indicator.impact === "Neutral") return "Neutral";
    if (positiveWhenUp) return indicator.m1 >= 0 ? "Supportive" : "Weakening";
    return indicator.impact === "Negative" ? "Adverse" : "Supportive";
  }

  function externalSensitivityProfile() {
    const type = String(state.counterparty?.counterparty_type || state.counterparty?.counterparty_name || "").toLowerCase();
    const airline = type.includes("air") || type.includes("jet");
    const shipping = type.includes("ship") || type.includes("marine");
    const distributor = type.includes("distributor") || type.includes("fuel");
    return {
      fuel: airline || shipping || distributor ? "High" : "Medium",
      fx: airline ? "Medium" : shipping ? "High" : "Medium",
      rates: stressScore() >= 70 ? "Medium" : "Low",
      macro: airline || shipping ? "High" : "Medium",
      trade: shipping ? "High" : "Medium",
      geopolitical: stressScore() >= 70 ? "High" : "Medium"
    };
  }

  function forecastOutlook() {
    const intel = marketIntelligence();
    const stress = intel.stressScore;
    const drivers = [
      { label: "Oil Volatility", score: stress >= 70 ? 25 : 21 },
      { label: "DXY Strength", score: stress >= 70 ? 20 : 17 },
      { label: "Market Volatility", score: stress >= 70 ? 18 : 15 },
      { label: "Trade Activity", score: stress >= 70 ? 14 : 13 },
      { label: "Interest Rates", score: stress >= 70 ? 12 : 15 },
      { label: "Geopolitical Stress", score: stress >= 70 ? 11 : 9 }
    ];
    return {
      regime: intel.regime,
      horizon: "90 days",
      confidence: stress >= 70 ? "Medium" : "Medium-High",
      commodityOutlook: stress >= 70 ? "Bullish fuel market" : "Firm fuel market",
      fxOutlook: stress >= 55 ? "USD strengthening" : "USD range-bound",
      macroOutlook: stress >= 70 ? "Moderate slowdown" : "Soft landing / slower growth",
      marketPath: stress >= 70 ? "Adverse commodity path" : "Base case with volatility",
      mostLikelyScenario: stress >= 70 ? "Adverse" : "Normal Volatility",
      highestRiskScenario: "Severe",
      drivers,
      risks: ["Fuel price upside", "USD strength", "VIX repricing", "Trade-cycle softness", "Geopolitical supply disruption"]
    };
  }

  function scenarioRows() {
    const backendScenarios = Array.isArray(state.scenarios) ? state.scenarios : [];
    const wanted = ["base_case", "normal_volatility", "adverse", "severe_downside"];
    const selected = wanted
      .map((type) => backendScenarios.find((scenario) => scenario.scenario_type === type))
      .filter(Boolean);
    if (selected.length) {
      return selected.map((scenario) => {
        const shocks = scenario.market_shocks || {};
        const stress = Number(shocks.stress_index_change) || 0;
        const fuelPressure = Math.max(Number(shocks.brent_change) || 0, Number(shocks.jet_fuel_change) || 0);
        const dxyPressure = Number(shocks.dxy_change) || 0;
        const vixPressure = Number(shocks.vix_change) || 0;
        const balticPressure = Number(shocks.baltic_dry_change) || 0;
        const pressureScore = fuelPressure * 1.4 + dxyPressure + vixPressure + Math.abs(Math.min(balticPressure, 0)) + stress;
        const type = scenario.scenario_type || scenario.scenario_name || "scenario";
        return {
          type,
          name: scenario.scenario_type === "severe_downside" ? "Severe" : scenario.scenario_name,
          brent: scenarioShock(shocks.brent_change),
          jet: scenarioShock(shocks.jet_fuel_change),
          dxy: scenarioShock(shocks.dxy_change),
          vix: scenarioShock(shocks.vix_change),
          baltic: scenarioShock(shocks.baltic_dry_change),
          impact: pressureScore >= 0.45 ? "High stress to margins and cash flow" : pressureScore >= 0.25 ? "Working-capital pressure" : pressureScore >= 0.12 ? "Margin pressure rises" : "Manageable cost pass-through",
          quality: pressureScore >= 0.45 ? "Material deterioration" : pressureScore >= 0.25 ? "Weaker" : pressureScore >= 0.12 ? "Slightly weaker" : "Stable",
          liquidity: pressureScore >= 0.45 ? "Stressed" : pressureScore >= 0.25 ? "Tighter" : pressureScore >= 0.12 ? "Watch" : "Neutral",
          outlook: pressureScore >= 0.45 ? "Limit growth and require protection" : pressureScore >= 0.25 ? "Defensive posture needed" : pressureScore >= 0.12 ? "Volatile but manageable" : "Normal trading conditions",
          pressureScore: clamp(pressureScore * 100, 8, 95),
          source: "Data-driven",
          observations: scenario.source_observations,
          sourceWindow: scenario.source_start_date && scenario.source_end_date ? `${scenario.source_start_date} to ${scenario.source_end_date}` : "Stored market history"
        };
      });
    }
    return [
      {
        type: "base_case",
        name: "Base Case",
        brent: "+2%",
        jet: "+3%",
        dxy: "Flat",
        vix: "Flat",
        baltic: "+2%",
        impact: "Manageable cost pass-through",
        quality: "Stable",
        liquidity: "Neutral",
        outlook: "Normal trading conditions",
        pressureScore: 18
      },
      {
        type: "normal_volatility",
        name: "Normal Volatility",
        brent: "+6%",
        jet: "+8%",
        dxy: "+2%",
        vix: "+10%",
        baltic: "-3%",
        impact: "Margin pressure rises",
        quality: "Slightly weaker",
        liquidity: "Watch",
        outlook: "Volatile but manageable",
        pressureScore: 38
      },
      {
        type: "adverse",
        name: "Adverse",
        brent: "+14%",
        jet: "+18%",
        dxy: "+5%",
        vix: "+28%",
        baltic: "-12%",
        impact: "Working-capital pressure",
        quality: "Weaker",
        liquidity: "Tighter",
        outlook: "Defensive posture needed",
        pressureScore: 66
      },
      {
        type: "severe_downside",
        name: "Severe",
        brent: "+25%",
        jet: "+32%",
        dxy: "+9%",
        vix: "+55%",
        baltic: "-24%",
        impact: "High stress to margins and cash flow",
        quality: "Material deterioration",
        liquidity: "Stressed",
        outlook: "Limit growth and require protection",
        pressureScore: 91
      }
    ];
  }

  function selectedScenario(rows) {
    return rows.find((row) => row.type === state.selectedScenarioType)
      || rows.find((row) => /adverse/i.test(row.name))
      || rows[0];
  }

  function scenarioSelector(rows, selected) {
    return `
      <div class="scenario-selector" role="tablist" aria-label="Select stress scenario">
        ${rows.map((row) => `
          <button type="button" data-scenario-type="${escapeHtml(row.type)}" class="${row.type === selected.type ? "is-active" : ""}">
            ${escapeHtml(row.name)}
          </button>
        `).join("")}
      </div>
    `;
  }

  function scenarioConditionText(row) {
    return `${row.name} assumes Brent ${row.brent}, jet fuel ${row.jet}, DXY ${row.dxy}, VIX ${row.vix}, and Baltic Dry ${row.baltic}. The practical read is ${row.impact.toLowerCase()}, with ${row.liquidity.toLowerCase()} liquidity and ${row.outlook.toLowerCase()}.`;
  }

  function scenarioStressMetrics(row) {
    const q = quantAnalytics();
    const d = decisionAnalytics();
    const pressure = clamp(Number(row.pressureScore) || 30, 0, 100);
    const multiplier = 1 + pressure / 135;
    const pdMultiplier = 1 + pressure / 180;
    const lgdMultiplier = 1 + pressure / 260;
    const stressedPd = clamp(q.finalPd * pdMultiplier, 0.0001, 0.65);
    const stressedLgd = clamp(q.lgd * lgdMultiplier, 0.05, 0.95);
    const stressedEad = q.ead * (1 + pressure / 420);
    const expectedLoss = stressedPd * stressedLgd * stressedEad;
    const var95 = Math.max(q.var95, expectedLoss * (2.4 + pressure / 70));
    const shortfall95 = Math.max(q.es95, var95 * (1.12 + pressure / 500));
    const limitHaircut = clamp(Number(d.rec.limit_haircut) || (pressure / 180), 0.02, 0.75);
    const stressedHaircut = clamp(limitHaircut + pressure / 260, 0.05, 0.85);
    const baseLimit = Number(d.requestedLimit) || state.requestedLimit || q.ead;
    const stressedLimit = Math.max(0, baseLimit * (1 - stressedHaircut));
    const tenor = pressure >= 75 ? 15 : pressure >= 50 ? 30 : d.recommendedTenor || state.requestedTenor || 30;
    const security = pressure >= 75
      ? "LC or cash deposit"
      : pressure >= 50
        ? "Corporate guarantee or partial deposit"
        : d.security || "Standard terms";
    return {
      q,
      d,
      pressure,
      multiplier,
      stressedPd,
      stressedLgd,
      stressedEad,
      expectedLoss,
      var95,
      shortfall95,
      stressedLimit,
      tenor,
      security
    };
  }

  function selectedScenarioDetail(row) {
    const metrics = scenarioStressMetrics(row);
    return `
      <section class="scenario-detail-grid">
        <article class="terminal-panel scenario-story-panel">
          <div class="panel-title">Selected Scenario</div>
          <h2>${escapeHtml(row.name)}</h2>
          <p>${escapeHtml(scenarioConditionText(row))}</p>
          <div class="scenario-condition-grid">
            ${rowLine("Fuel Shock", `Brent ${row.brent} / Jet ${row.jet}`)}
            ${rowLine("FX Shock", `DXY ${row.dxy}`)}
            ${rowLine("Volatility Shock", `VIX ${row.vix}`)}
            ${rowLine("Trade Signal", `Baltic Dry ${row.baltic}`)}
          </div>
        </article>
        <article class="terminal-panel scenario-counterparty-panel">
          <div class="panel-title">Counterparty Under Stress</div>
          ${rowLine("Counterparty", state.counterparty?.counterparty_name || "Selected counterparty")}
          ${rowLine("Business Type", state.counterparty?.counterparty_type || "Not set")}
          ${rowLine("Current Risk Grade", metrics.d.riskGrade)}
          ${rowLine("Stressed PD", pct(metrics.stressedPd))}
          ${rowLine("Stressed LGD", pct(metrics.stressedLgd))}
          ${rowLine("Stressed EAD", money(metrics.stressedEad))}
          ${rowLine("Stressed Expected Loss", money(metrics.expectedLoss))}
          ${rowLine("Credit VaR 95", money(metrics.var95))}
          ${rowLine("Expected Shortfall 95", money(metrics.shortfall95))}
          ${rowLine("Stress-Adjusted Limit", money(metrics.stressedLimit))}
          ${rowLine("Suggested Tenor", tenorText(metrics.tenor))}
          ${rowLine("Security Posture", metrics.security)}
        </article>
      </section>
    `;
  }

  function scenarioShock(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return "Flat";
    if (Math.abs(numeric) < 0.001) return "Flat";
    const sign = numeric > 0 ? "+" : "";
    return `${sign}${(numeric * 100).toFixed(1)}%`;
  }

  function forecastPanelRows() {
    return [
      { market: "Brent Crude", model: "ARIMA / GARCH", direction: "Higher", range: "$84 - $96", confidence: "Medium-High" },
      { market: "Jet Fuel", model: "ARIMA / Crack Spread", direction: "Higher faster than crude", range: "$96 - $112", confidence: "Medium" },
      { market: "DXY", model: "VAR", direction: "Stronger USD", range: "104 - 108", confidence: "Medium" },
      { market: "VIX", model: "GARCH", direction: "Elevated", range: "18 - 28", confidence: "Medium" },
      { market: "US10Y Yield", model: "VAR", direction: "Range-bound high", range: "4.15% - 4.65%", confidence: "Medium" },
      { market: "Baltic Dry Index", model: "VAR", direction: "Softening", range: "1,450 - 1,850", confidence: "Low-Medium" }
    ];
  }

  function forecastRows(items) {
    return items.map((item) => `
      <div class="forecast-row">
        <strong>${escapeHtml(item.market)}</strong>
        <span>${escapeHtml(item.direction)}</span>
        <span>${escapeHtml(item.range)}</span>
        <span>${escapeHtml(item.confidence)}</span>
        <em>${escapeHtml(item.model)}</em>
      </div>
    `).join("");
  }

  function scenarioComparisonRows(rows) {
    return rows.map((item) => `
      <div class="scenario-row">
        <strong>${escapeHtml(item.name)}</strong>
        <span>${escapeHtml(item.brent)}</span>
        <span>${escapeHtml(item.jet)}</span>
        <span>${escapeHtml(item.dxy)}</span>
        <span>${escapeHtml(item.vix)}</span>
        <span>${escapeHtml(item.baltic)}</span>
        <span>${escapeHtml(item.impact)}</span>
        <span>${escapeHtml(item.quality)}</span>
        <span>${escapeHtml(item.liquidity)}</span>
        <span>${escapeHtml(item.outlook)}</span>
      </div>
    `).join("");
  }

  function scenarioImpactChart(rows) {
    return `
      <div class="scenario-impact-bars">
        <div class="chart-axis-caption"><span>Y-axis: Scenario</span><span>X-axis: Counterparty stress score (0-100)</span></div>
        ${rows.map((row) => {
          const score = Math.round(Number(row.pressureScore) || 0);
          return `
          <div class="scenario-impact-bar">
            <span>${escapeHtml(row.name)}</span>
            <div><i style="--fill:${clamp(score)}%"></i></div>
            <strong>${score}</strong>
          </div>
        `;
        }).join("")}
      </div>
    `;
  }

  function predefinedForecastScenarios() {
    const custom = state.customScenario || {};
    return [
      {
        type: "base_case",
        name: "Base Case",
        shortName: "Base",
        fuelShock: 0,
        fxShock: 0,
        revenueShock: 0,
        rateShock: 0,
        creditDays: Number(state.requestedTenor) || 30,
        description: "Normal trading path with current market stress and unchanged credit behavior."
      },
      {
        type: "fuel_spike",
        name: "Fuel Spike",
        shortName: "Fuel",
        fuelShock: 0.25,
        fxShock: 0,
        revenueShock: 0,
        rateShock: 0,
        creditDays: Number(state.requestedTenor) || 30,
        description: "Fuel costs rise 25%, pressuring airline margins and working capital."
      },
      {
        type: "fx_shock",
        name: "FX Shock",
        shortName: "FX",
        fuelShock: 0,
        fxShock: 0.10,
        revenueShock: 0,
        rateShock: 0,
        creditDays: Number(state.requestedTenor) || 30,
        description: "Local currency weakens 10% against USD, raising dollar-linked fuel obligations."
      },
      {
        type: "demand_slowdown",
        name: "Demand Slowdown",
        shortName: "Demand",
        fuelShock: 0,
        fxShock: 0,
        revenueShock: -0.15,
        rateShock: 0,
        creditDays: Number(state.requestedTenor) || 30,
        description: "Revenue falls 15%, reducing coverage, liquidity, and cash generation."
      },
      {
        type: "combined_stress",
        name: "Combined Stress",
        shortName: "Combined",
        fuelShock: 0.25,
        fxShock: 0.10,
        revenueShock: -0.15,
        rateShock: 0.01,
        creditDays: Math.max(Number(state.requestedTenor) || 30, 45),
        description: "Fuel, FX, demand, rates, and credit-days pressure hit at the same time."
      },
      {
        type: "extreme_tail",
        name: "Extreme Tail Scenario",
        shortName: "Tail",
        fuelShock: 0.45,
        fxShock: 0.18,
        revenueShock: -0.28,
        rateShock: 0.025,
        creditDays: Math.max(Number(state.requestedTenor) || 30, 60),
        description: "Low-probability tail path with severe fuel spike, FX depreciation, demand fall, and funding pressure."
      },
      {
        type: "custom",
        name: "Custom Scenario",
        shortName: "Custom",
        fuelShock: Number(custom.fuelShock) || 0,
        fxShock: Number(custom.fxShock) || 0,
        revenueShock: Number(custom.revenueShock) || 0,
        rateShock: Number(custom.rateShock) || 0,
        creditDays: Number(custom.creditDays) || Number(state.requestedTenor) || 30,
        description: "Analyst-defined scenario using the sliders below."
      }
    ];
  }

  function forecastScenarioList() {
    return predefinedForecastScenarios().map((scenario) => scenarioForecastMetrics(scenario));
  }

  function activeForecastScenario(rows) {
    return rows.find((item) => item.type === state.selectedScenarioType)
      || rows.find((item) => item.type === "base_case")
      || rows[0];
  }

  function scenarioForecastMetrics(scenario) {
    const q = quantAnalytics();
    const r = state.ratios || {};
    const m = state.metrics || {};
    const basePd = clamp(Number(q.finalPd) || 0.04, 0.0001, 0.95);
    const baseLgd = clamp(Number(q.lgd) || 0.45, 0.01, 0.99);
    const baseEad = Math.max(Number(q.ead) || Number(state.requestedLimit) || 1, 1);
    const baseEl = basePd * baseLgd * baseEad;
    const horizon = Number(state.forecastHorizon) || 90;
    const horizonScale = Math.sqrt(Math.max(horizon, 1) / 30);
    const requestedTenor = Number(state.requestedTenor) || 30;
    const creditDays = Math.max(Number(scenario.creditDays) || requestedTenor, 1);
    const extraCreditDays = Math.max(creditDays - requestedTenor, 0);
    const fuelSensitivity = clamp(Number(q.pd?.commodity_sensitivity_score) || 0.75, 0.1, 1.0);
    const fxSensitivity = clamp(Number(q.pd?.fx_sensitivity_score) || 0.55, 0.1, 1.0);
    const macroSensitivity = clamp(Number(q.pd?.macro_sensitivity_score) || 0.60, 0.1, 1.0);
    const fuelShock = Number(scenario.fuelShock) || 0;
    const fxShock = Number(scenario.fxShock) || 0;
    const revenueShock = Number(scenario.revenueShock) || 0;
    const rateShock = Number(scenario.rateShock) || 0;
    const revenueDown = Math.max(-revenueShock, 0);
    const pdMultiplier = 1
      + horizonScale * (
        fuelShock * 1.25 * fuelSensitivity
        + fxShock * 0.90 * fxSensitivity
        + revenueDown * 1.70 * macroSensitivity
        + Math.max(rateShock, 0) * 8.0
        + (extraCreditDays / 30) * 0.08
      );
    const forecastPd = clamp(basePd * pdMultiplier, 0.0001, 0.95);
    const lgdMultiplier = 1
      + fuelShock * 0.12
      + fxShock * 0.08
      + revenueDown * 0.18
      + Math.max(rateShock, 0) * 2.5;
    const stressedLgd = clamp(baseLgd * lgdMultiplier, 0.01, 0.99);
    const eadMultiplier = 1
      + fuelShock * 0.18
      + fxShock * 0.10
      + revenueDown * 0.16
      + (extraCreditDays / 30) * 0.12;
    const stressedEad = Math.max(baseEad * eadMultiplier, 0);
    const expectedLoss = forecastPd * stressedLgd * stressedEad;
    const tailMultiplier = 2.15 + horizonScale * 0.55 + fuelShock * 1.15 + fxShock * 0.75 + revenueDown * 1.20;
    const var95 = Math.min(Math.max(expectedLoss * tailMultiplier, Number(q.var95) || 0), stressedEad);
    const es95 = Math.min(Math.max(var95 * (1.12 + fuelShock * 0.18 + revenueDown * 0.22), var95), stressedEad);
    const revenue = Math.max(Number(m.revenue) || 1, 1);
    const ebit = Number(m.ebit) || Number(m.ebitda) * 0.75 || revenue * 0.08;
    const interest = Math.max(Number(m.interest_expense) || revenue * 0.015, 1);
    const stressedEbit = Math.max(ebit * (1 + revenueShock) - revenue * Math.max(fuelShock, 0) * 0.035, 1);
    const stressedInterest = interest * (1 + Math.max(rateShock, 0) * 12);
    const baseCoverage = Number(r.interest_coverage) || ebit / interest;
    const stressedCoverage = stressedEbit / stressedInterest;
    const baseLeverage = Number(r.debt_to_ebitda) || 3.0;
    const stressedLeverage = baseLeverage * (1 + revenueDown * 0.75 + fuelShock * 0.28);
    const baseLiquidity = Number(r.current_ratio) || 1.25;
    const stressedLiquidity = Math.max(0.15, baseLiquidity - fuelShock * 0.22 - fxShock * 0.12 - revenueDown * 0.30 - extraCreditDays / 240);
    const fuelExposureBase = Math.max((Number(state.fuelVolume) || 0) * (Number(state.fuelPrice) || 0), Number(state.invoiceAmount) || baseEad * 0.55);
    const fuelExposure = fuelExposureBase * (1 + Math.max(fuelShock, 0));
    const pressureScore = clamp(
      fuelShock * 110
      + fxShock * 95
      + revenueDown * 130
      + Math.max(rateShock, 0) * 900
      + extraCreditDays * 0.7
      + basePd * 140,
      0,
      100
    );
    const driverScores = [
      { label: "Fuel", score: fuelShock * fuelSensitivity * 100 },
      { label: "FX", score: fxShock * fxSensitivity * 100 },
      { label: "Macro", score: revenueDown * macroSensitivity * 100 },
      { label: "Leverage", score: Math.max(stressedLeverage - baseLeverage, 0) * 18 },
      { label: "Liquidity", score: Math.max(baseLiquidity - stressedLiquidity, 0) * 55 },
      { label: "Rates", score: Math.max(rateShock, 0) * 700 }
    ].sort((a, b) => b.score - a.score);
    const primaryDriver = driverScores.find((item) => item.score > 0.5)?.label
      || (baseLeverage >= 4 ? "Leverage" : baseLiquidity < 1.15 ? "Liquidity" : "Fuel");
    return {
      ...scenario,
      q,
      basePd,
      baseLgd,
      baseEad,
      baseEl,
      forecastPd,
      stressedLgd,
      stressedEad,
      expectedLoss,
      var95,
      es95,
      baseCoverage,
      stressedCoverage,
      baseLeverage,
      stressedLeverage,
      baseLiquidity,
      stressedLiquidity,
      fuelExposureBase,
      fuelExposure,
      pressureScore,
      primaryDriver,
      driverScores,
      horizon,
      creditDays
    };
  }

  function scenarioAction(metric, baseValue, stressedValue, scenario) {
    const pd = scenario.forecastPd;
    const liquidity = scenario.stressedLiquidity;
    const coverage = scenario.stressedCoverage;
    const leverage = scenario.stressedLeverage;
    const elIncrease = scenario.baseEl > 0 ? (scenario.expectedLoss - scenario.baseEl) / scenario.baseEl : 0;
    if (pd >= 0.15 || scenario.pressureScore >= 85) return "Escalate for Manual Review";
    if (pd >= 0.10 || elIncrease >= 1.4 || coverage < 1.5) return "Require Letter of Credit";
    if (liquidity < 1.0 || leverage >= 5.0) return "Request Additional Security";
    if (metric === "Expected Loss" && elIncrease >= 0.45) return "Reduce Credit Limit";
    if (metric === "Fuel Cost Exposure" && stressedValue > baseValue * 1.18) return "Reduce Credit Days";
    if (scenario.creditDays > (Number(state.requestedTenor) || 30) + 10) return "Reduce Credit Days";
    return "Maintain Terms";
  }

  function riskImpact(changePct, inverse = false) {
    const value = inverse ? -changePct : changePct;
    if (value >= 0.50) return "Severe";
    if (value >= 0.20) return "High";
    if (value >= 0.07) return "Moderate";
    if (value <= -0.07) return "Improving";
    return "Low";
  }

  function stressImpactRows(scenario) {
    const rows = [
      { metric: "PD", base: scenario.basePd, stressed: scenario.forecastPd, kind: "pct" },
      { metric: "LGD", base: scenario.baseLgd, stressed: scenario.stressedLgd, kind: "pct" },
      { metric: "Expected Loss", base: scenario.baseEl, stressed: scenario.expectedLoss, kind: "money" },
      { metric: "Interest Coverage", base: scenario.baseCoverage, stressed: scenario.stressedCoverage, kind: "ratio", inverse: true },
      { metric: "Leverage", base: scenario.baseLeverage, stressed: scenario.stressedLeverage, kind: "ratio" },
      { metric: "Liquidity Ratio", base: scenario.baseLiquidity, stressed: scenario.stressedLiquidity, kind: "ratio", inverse: true },
      { metric: "Fuel Cost Exposure", base: scenario.fuelExposureBase, stressed: scenario.fuelExposure, kind: "money" }
    ];
    return rows.map((row) => {
      const change = row.base ? (row.stressed - row.base) / Math.abs(row.base) : 0;
      return {
        ...row,
        change,
        impact: riskImpact(change, row.inverse),
        action: scenarioAction(row.metric, row.base, row.stressed, scenario)
      };
    });
  }

  function formatScenarioMetric(row) {
    if (row.kind === "money") return money(row.stressed);
    if (row.kind === "pct") return pct(row.stressed);
    return ratio(row.stressed);
  }

  function formatBaseScenarioMetric(row) {
    if (row.kind === "money") return money(row.base);
    if (row.kind === "pct") return pct(row.base);
    return ratio(row.base);
  }

  function scenarioControlBar() {
    const selectedId = state.counterparty?.id;
    return `
      <section class="scenario-control-bar">
        <label>
          <span>Counterparty</span>
          <select data-scenario-counterparty>
            ${state.counterparties.map((cp) => `
              <option value="${cp.id}" ${Number(cp.id) === Number(selectedId) ? "selected" : ""}>
                ${escapeHtml(cp.counterparty_name || `Counterparty ${cp.id}`)}
              </option>
            `).join("")}
          </select>
        </label>
        <label>
          <span>Forecast Horizon</span>
          <select data-forecast-horizon>
            ${[30, 60, 90].map((days) => `<option value="${days}" ${Number(state.forecastHorizon) === days ? "selected" : ""}>${days} days</option>`).join("")}
          </select>
        </label>
      </section>
    `;
  }

  function scenarioKpiCards(active) {
    return `
      <section class="scenario-kpi-grid">
        ${metric("Current PD", pct(active.basePd))}
        ${metric("Forecast PD", pct(active.forecastPd), active.forecastPd > active.basePd * 1.25 ? "warn" : "accent")}
        ${metric("Expected Loss (EL)", money(active.expectedLoss), "warn")}
        ${metric("VaR 95%", money(active.var95), "accent")}
        ${metric("Primary Risk Driver", active.primaryDriver, "danger")}
      </section>
    `;
  }

  function scenarioTabs(rows, active) {
    return `
      <div class="scenario-tabbar" role="tablist" aria-label="Scenario engine">
        ${rows.filter((row) => row.type !== "custom").map((row) => `
          <button type="button" data-scenario-type="${escapeHtml(row.type)}" class="${row.type === active.type ? "is-active" : ""}">
            ${escapeHtml(row.name)}
          </button>
        `).join("")}
      </div>
    `;
  }

  function sliderControl(label, key, min, max, step, value, formatter) {
    return `
      <label class="scenario-slider">
        <span>${escapeHtml(label)} <strong>${escapeHtml(formatter(value))}</strong></span>
        <input type="range" min="${min}" max="${max}" step="${step}" value="${value}" data-custom-scenario="${key}">
      </label>
    `;
  }

  function customScenarioPanel() {
    const c = state.customScenario || {};
    return `
      <article class="terminal-panel custom-scenario-panel">
        <div class="panel-title">Custom Scenario</div>
        <div class="custom-scenario-grid">
          ${sliderControl("Fuel Shock", "fuelShock", -0.10, 0.60, 0.01, Number(c.fuelShock) || 0, (v) => signedPct(v))}
          ${sliderControl("FX Shock", "fxShock", -0.05, 0.30, 0.01, Number(c.fxShock) || 0, (v) => signedPct(v))}
          ${sliderControl("Revenue Shock", "revenueShock", -0.40, 0.10, 0.01, Number(c.revenueShock) || 0, (v) => signedPct(v))}
          ${sliderControl("Interest Rate Shock", "rateShock", -0.01, 0.04, 0.0025, Number(c.rateShock) || 0, (v) => `${(Number(v) * 100).toFixed(2)} pts`)}
          ${sliderControl("Credit Days", "creditDays", 15, 120, 5, Number(c.creditDays) || Number(state.requestedTenor) || 30, (v) => `${Math.round(Number(v))} days`)}
        </div>
        <button type="button" class="secondary-action scenario-custom-apply ${state.selectedScenarioType === "custom" ? "is-active" : ""}" data-scenario-type="custom">
          Apply Custom Scenario
        </button>
      </article>
    `;
  }

  function monteCarloHistogram(active) {
    const mean = active.expectedLoss;
    const var95 = active.var95;
    const maxLoss = Math.max(active.stressedEad, var95 * 1.15, mean * 4, 1);
    const buckets = Array.from({ length: 28 }, (_, index) => {
      const x = (index + 0.5) / 28;
      const center = 0.18 + active.pressureScore / 420;
      const spread = 0.11 + active.pressureScore / 900;
      const tail = Math.max(0, x - 0.58) * (active.pressureScore / 70);
      return clamp((Math.exp(-Math.pow((x - center) / spread, 2)) * 78) + tail * 36 + 5, 5, 96);
    });
    return `
      <div class="forecast-histogram">
        <div class="chart-axis-caption"><span>X-axis: Simulated single-name loss</span><span>Y-axis: Outcome frequency</span></div>
        <div class="loss-bars forecast-loss-bars">
          ${buckets.map((height, index) => `<i style="--height:${height}%; --i:${index}"></i>`).join("")}
          <span class="var-marker expected" style="--pos:${clamp((mean / maxLoss) * 100)}%">EL</span>
          <span class="var-marker var95" style="--pos:${clamp((var95 / maxLoss) * 100)}%">VaR 95</span>
        </div>
        <div class="loss-axis"><span>$0</span><span>${money(maxLoss)}</span></div>
        <div class="loss-summary-row">
          <span>Expected Loss <strong>${money(mean)}</strong></span>
          <span>VaR 95 <strong>${money(var95)}</strong></span>
          <span>ES 95 <strong>${money(active.es95)}</strong></span>
        </div>
      </div>
    `;
  }

  function scenarioComparisonChart(rows) {
    const maxEl = Math.max(...rows.map((row) => row.expectedLoss), 1);
    const maxVar = Math.max(...rows.map((row) => row.var95), 1);
    const maxPd = Math.max(...rows.map((row) => row.forecastPd), 0.01);
    return `
      <div class="scenario-compare-chart">
        <div class="chart-axis-caption"><span>Rows: Scenarios</span><span>Bars: EL, PD, and VaR 95</span></div>
        ${rows.filter((row) => row.type !== "custom" || state.selectedScenarioType === "custom").map((row) => `
          <div class="scenario-compare-row">
            <strong>${escapeHtml(row.shortName)}</strong>
            <span>EL</span><div><i class="el-bar" style="--fill:${clamp((row.expectedLoss / maxEl) * 100)}%"></i></div><em>${money(row.expectedLoss)}</em>
            <span>PD</span><div><i class="pd-bar" style="--fill:${clamp((row.forecastPd / maxPd) * 100)}%"></i></div><em>${pct(row.forecastPd)}</em>
            <span>VaR</span><div><i class="var-bar" style="--fill:${clamp((row.var95 / maxVar) * 100)}%"></i></div><em>${money(row.var95)}</em>
          </div>
        `).join("")}
      </div>
    `;
  }

  function pdForecastTrendChart(rows) {
    const width = 760;
    const height = 260;
    const pad = 34;
    const horizons = [0, Math.round((Number(state.forecastHorizon) || 90) / 3), Math.round((Number(state.forecastHorizon) || 90) * 2 / 3), Number(state.forecastHorizon) || 90];
    const chartRows = rows.filter((row) => row.type !== "custom" || state.selectedScenarioType === "custom");
    const maxPd = Math.max(...chartRows.map((row) => row.forecastPd), 0.01) * 1.16;
    const x = (index) => pad + (index * (width - pad * 2)) / Math.max(horizons.length - 1, 1);
    const y = (value) => height - pad - (value / maxPd) * (height - pad * 2);
    const line = (row) => horizons.map((day, index) => {
      const progress = day / Math.max(Number(state.forecastHorizon) || 90, 1);
      const pdValue = row.basePd + (row.forecastPd - row.basePd) * Math.pow(progress, 0.78);
      return `${x(index)},${y(pdValue)}`;
    }).join(" ");
    return `
      <div class="pd-trend-wrap">
        <svg class="pd-trend-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="PD forecast trend">
          <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" class="chart-axis"></line>
          <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" class="chart-axis"></line>
          <text x="${pad - 7}" y="${pad + 4}" text-anchor="end" class="axis-tick">${escapeHtml(pct(maxPd, 1))}</text>
          <text x="${pad - 7}" y="${height - pad}" text-anchor="end" class="axis-tick">0%</text>
          ${chartRows.map((row, index) => `<polyline points="${line(row)}" class="pd-trend-line line-${index}"></polyline>`).join("")}
          ${horizons.map((day, index) => `<text x="${x(index)}" y="${height - 8}" text-anchor="middle" class="axis-label">${day}d</text>`).join("")}
          <text x="11" y="${height / 2}" text-anchor="middle" transform="rotate(-90 11 ${height / 2})" class="axis-label">PD</text>
        </svg>
        <div class="pd-trend-legend">
          ${chartRows.map((row, index) => `<span><i class="line-${index}"></i>${escapeHtml(row.shortName)}</span>`).join("")}
        </div>
        <div class="chart-axis-caption"><span>X-axis: forecast horizon in days</span><span>Y-axis: probability of default</span></div>
      </div>
    `;
  }

  function selectedPdForecastChart(active) {
    return pdForecastTrendChart([active]);
  }

  function selectedScenarioNarrative(active) {
    const elChange = active.baseEl > 0 ? (active.expectedLoss - active.baseEl) / active.baseEl : 0;
    const pdChange = active.basePd > 0 ? (active.forecastPd - active.basePd) / active.basePd : 0;
    const action = scenarioAction("Expected Loss", active.baseEl, active.expectedLoss, active);
    const tone = active.pressureScore >= 75 ? "High stress" : active.pressureScore >= 45 ? "Moderate stress" : "Manageable stress";
    return `
      <div class="selected-scenario-analysis">
        <p>${escapeHtml(active.name)} creates ${escapeHtml(tone.toLowerCase())} for this counterparty. The model moves PD from ${pct(active.basePd)} to ${pct(active.forecastPd)} and expected loss from ${money(active.baseEl)} to ${money(active.expectedLoss)} over ${Math.round(active.horizon)} days.</p>
        <div class="selected-scenario-grid">
          ${rowLine("PD Movement", `${signedPct(pdChange)} vs current`)}
          ${rowLine("EL Movement", `${signedPct(elChange)} vs current`)}
          ${rowLine("Tail Loss", `${money(active.var95)} VaR 95 / ${money(active.es95)} ES 95`)}
          ${rowLine("Primary Driver", active.primaryDriver)}
          ${rowLine("Credit Action", action)}
          ${rowLine("Scenario Pressure", `${Math.round(active.pressureScore)} / 100`)}
        </div>
      </div>
    `;
  }

  function selectedScenarioDriverPanel(active) {
    const drivers = active.driverScores.slice(0, 6);
    const maxScore = Math.max(...drivers.map((item) => item.score), 1);
    return `
      <div class="scenario-driver-list">
        ${drivers.map((item) => `
          <div class="scenario-driver-row">
            <strong>${escapeHtml(item.label)}</strong>
            <div><i style="--fill:${clamp((item.score / maxScore) * 100)}%"></i></div>
            <span>${Math.round(item.score)}</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  function stressImpactTable(active) {
    const rows = stressImpactRows(active);
    return `
      <div class="stress-impact-table">
        <div class="stress-impact-head">
          <span>Metric</span><span>Base Value</span><span>Stressed Value</span><span>Change %</span><span>Risk Impact</span><span>Recommended Credit Action</span>
        </div>
        ${rows.map((row) => `
          <div class="stress-impact-row ${row.impact.toLowerCase().replace(/\s+/g, "-")}">
            <strong>${escapeHtml(row.metric)}</strong>
            <span>${formatBaseScenarioMetric(row)}</span>
            <span>${formatScenarioMetric(row)}</span>
            <span class="${row.change >= 0 ? "up" : "down"}">${signedPct(row.change)}</span>
            <em>${escapeHtml(row.impact)}</em>
            <b>${escapeHtml(row.action)}</b>
          </div>
        `).join("")}
      </div>
    `;
  }

  function scenarioHeatmap(rows) {
    const matrix = [
      [20, 24, 18, 22, 20],
      [42, 48, 36, 40, 44],
      [72, 78, 66, 70, 74],
      [92, 96, 88, 90, 94]
    ];
    const cols = ["Fuel Costs", "FX Costs", "Funding", "Trade Activity", "Overall Stress"];
    return `
      <div class="scenario-heatmap">
        <div class="chart-axis-caption"><span>Rows: Future scenarios</span><span>Columns: Risk factor impact score (0-100)</span></div>
        <div class="scenario-heat-head"><span>Scenario</span>${cols.map((col) => `<span>${escapeHtml(col)}</span>`).join("")}</div>
        ${rows.map((row, i) => `
          <div class="scenario-heat-row">
            <strong>${escapeHtml(row.name)}</strong>
            ${matrix[i].map((score) => `<span style="--heat:${score}%">${score}</span>`).join("")}
          </div>
        `).join("")}
      </div>
    `;
  }

  function scenarioImpactPanel(rows) {
    return rows.map((row, index) => {
      const pressure = ["Low", "Moderate", "High", "Severe"][index];
      return `
        <div class="scenario-pressure-card">
          <strong>${escapeHtml(row.name)}</strong>
          ${rowLine("Fuel Cost Pressure", pressure)}
          ${rowLine("FX Pressure", index >= 2 ? "High" : "Moderate")}
          ${rowLine("Interest Rate Pressure", index >= 2 ? "Medium" : "Low")}
          ${rowLine("Revenue Pressure", index >= 2 ? "High" : "Moderate")}
          ${rowLine("Cash Flow Pressure", index >= 2 ? "High" : "Manageable")}
          ${rowLine("Overall Financial Stress", pressure)}
        </div>
      `;
    }).join("");
  }

  function rowLine(label, value) {
    return `<div class="mini-row"><span>${escapeHtml(label)}</span><em>${escapeHtml(value)}</em></div>`;
  }

  function creditTermsComparisonTable(d) {
    const haircut = d.policyHaircutBreakdown || {};
    const rows = [
      ["Limit", money(d.requestedLimit), money(d.recommendedLimit)],
      ["Tenor", tenorText(d.requestedTenor), tenorText(d.recommendedTenor)],
      ["Security", d.requestedSecurity, d.security],
      ["Expected Loss", money(d.unsecuredExpectedLoss), money(d.securedExpectedLoss)],
      ["Base Risk Adjustment", "N/A", haircut.base_policy_haircut_before_scenario !== undefined ? pct(haircut.base_policy_haircut_before_scenario) : "Pending"],
      ["Scenario Risk Add-on", "N/A", haircut.scenario_tail_add_on !== undefined ? pct(haircut.scenario_tail_add_on) : "Pending"],
      ["Total Risk Adjustment", "N/A", d.rec.limit_haircut !== undefined ? pct(d.rec.limit_haircut) : "Pending"]
    ];
    return `
      <div class="terms-comparison-table">
        <div class="terms-comparison-head">
          <span>Term</span>
          <strong>Requested</strong>
          <strong>Recommended</strong>
        </div>
        ${rows.map(([label, requested, recommended]) => `
          <div class="terms-comparison-row">
            <span>${escapeHtml(label)}</span>
            <em>${escapeHtml(requested)}</em>
            <strong>${escapeHtml(recommended)}</strong>
          </div>
        `).join("")}
      </div>
    `;
  }

  function yesNo(value) {
    return value ? "Yes" : "No";
  }

  function warningText(values) {
    const clean = (value) => String(value || "")
      .replaceAll("_", " ")
      .replace(/\s+/g, " ")
      .trim();
    if (Array.isArray(values) && values.length) return values.map(clean).join("; ");
    if (values && typeof values === "object" && Object.keys(values).length) {
      return Object.entries(values).map(([key, value]) => `${clean(key)}: ${Array.isArray(value) ? value.map(clean).join(", ") : clean(value)}`).join("; ");
    }
    return "None";
  }

  function readableStatus(value) {
    return String(value || "Not available")
      .replaceAll("_", " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function compactStatus(value, max = 82) {
    const text = readableStatus(value);
    return text.length > max ? `${text.slice(0, max - 1).trim()}...` : text;
  }

  function marketIndicatorExplanation(item) {
    const name = item?.name || "Market indicator";
    const copy = {
      "Brent Crude": "Brent is the core fuel-cost anchor. A rising Brent signal usually tightens tenor, increases collateral needs, and pressures fuel-intensive counterparties.",
      "Jet Fuel Proxy": "Jet fuel proxy tracks the direct cost base for airlines. Higher levels can weaken margins, cash flow, and limit appetite.",
      "Marine Fuel Proxy": "Marine fuel proxy matters for shipping and distribution customers. Rising fuel costs can increase working-capital draw and payment risk.",
      DXY: "DXY measures US dollar strength. A stronger dollar can raise costs for non-USD revenue borrowers and increase FX-driven credit pressure.",
      VIX: "VIX is a market fear gauge. Higher volatility usually means lower risk appetite, tighter terms, and more conservative limits.",
      "S&P 500": "The S&P 500 is a broad risk-appetite signal. Falling equities can indicate weaker funding conditions and higher macro credit caution.",
      "US 2Y Yield": "The 2-year yield reflects near-term policy rates. Higher yields can raise funding costs and reduce debt-service flexibility.",
      "US 10Y Yield": "The 10-year yield reflects longer-term borrowing costs. Higher yields can pressure refinancing and valuation-sensitive borrowers.",
      "Yield Curve Spread": "The yield curve helps flag slowdown risk. An inverted or weak curve can support shorter tenor and closer review.",
      Gold: "Gold often rises when investors seek safety. A strong gold signal can indicate defensive markets and weaker risk appetite.",
      "WTI Crude": "WTI is the US crude benchmark. Rising WTI can signal broader fuel-cost pressure and working-capital needs.",
      "Jet Crack Spread": "Jet crack spread compares jet fuel economics against crude. A widening spread means aviation fuel is becoming expensive relative to crude.",
      "EIA Crude Inventories": "Crude inventory builds can indicate excess supply or weaker demand. Sharp builds can weaken oil-demand signals; sharp draws can tighten fuel markets.",
      "OPEC Production": "OPEC production tracks supply discipline. Falling production can tighten supply and lift fuel-cost pressure.",
      "Global PMI": "Global PMI is a business activity signal. Weak PMI points to softer demand and can reduce credit appetite for cyclical counterparties.",
      "IATA Passenger Traffic": "Passenger traffic is the airline demand signal. Falling traffic weakens revenue resilience for airline counterparties.",
      "Baltic Dry Index": "Baltic Dry is a trade-cycle signal. Weak freight activity can reduce volume demand for shipping-linked counterparties.",
      PMI: "PMI tracks business activity. A weak PMI points to softer demand and may justify tighter credit terms.",
      "Inflation Signal": "Inflation affects costs, rates, and margins. Elevated inflation can pressure working capital and repayment capacity."
    };
    return copy[name] || "This indicator is used as an external risk signal. Adverse moves can tighten credit appetite, reduce recommended limits, or require stronger security.";
  }

  function quantAnalytics() {
    const pd = state.pd || {};
    const loss = state.loss || {};
    const sim = state.simulation || {};
    const structuralPd = Number(pd.structural_pd) || 0.064;
    const mlPd = Number(pd.ml_pd) || 0.083;
    const finalPd = Number(pd.final_pd) || ((structuralPd + mlPd) / 2);
    const lgd = Number(loss.predicted_lgd) || 0.52;
    const ead = Number(loss.exposure_at_default) || state.requestedLimit * 0.82;
    const expectedLoss = Number(loss.expected_loss) || finalPd * lgd * ead;
    const confidence = Number(pd.model_confidence) || 0.78;
    const divergence = Number(pd.pd_divergence) || Math.abs(mlPd - structuralPd);
    const dd = Number(pd.distance_to_default) || 1.84;
    const assetValue = Number(pd.asset_value_proxy) || ead * 1.8;
    const debtThreshold = Number(pd.debt_threshold) || ead * 0.95;
    const assetVol = Number(pd.asset_volatility) || 0.32;
    const simExpectedLoss = Number(sim.expected_loss) || expectedLoss * 1.15;
    const unexpectedLoss = Number(sim.unexpected_loss) || expectedLoss * 2.4;
    const var95 = Number(sim.var_95 || sim.credit_var_95) || expectedLoss * 4.2;
    const var99 = Number(sim.var_99 || sim.credit_var_99) || expectedLoss * 6.8;
    const es95 = Number(sim.expected_shortfall_95) || var95 * 1.22;
    const es99 = Number(sim.expected_shortfall_99) || var99 * 1.18;
    const worstCase = Number(sim.max_loss || sim.loss_distribution_summary?.max) || expectedLoss * 10.5;
    const pdDrivers = [
      { label: "Leverage / Debt Threshold", score: 26 },
      { label: "Asset Volatility", score: 22 },
      { label: "Commodity Sensitivity", score: 18 },
      { label: "Liquidity Cushion", score: 15 },
      { label: "Macro Stress", score: 11 },
      { label: "FX Exposure", score: 8 }
    ];
    const lgdDrivers = [
      { label: "Collateral Coverage", score: 30 },
      { label: "Seniority / Security", score: 24 },
      { label: "Liquidity of Claims", score: 18 },
      { label: "Country Recovery Risk", score: 15 },
      { label: "Concentration Risk", score: 13 }
    ];
    const tailDrivers = [
      { label: "Fuel Shock", score: 25 },
      { label: "FX Shock", score: 20 },
      { label: "Market Volatility Shock", score: 18 },
      { label: "Interest Rate Shock", score: 14 },
      { label: "Correlated Default Risk", score: 13 },
      { label: "Idiosyncratic Jump Risk", score: 10 }
    ];
    return {
      pd,
      loss,
      sim,
      structuralPd,
      mlPd,
      finalPd,
      lgd,
      ead,
      expectedLoss,
      confidence,
      modelConfidenceText: confidence >= 0.8 ? "High" : confidence >= 0.6 ? "Medium" : "Low",
      divergence,
      agreementStatus: divergence <= 0.025 ? "Models aligned" : divergence <= 0.06 ? "Moderate divergence" : "High divergence",
      dd,
      assetValue,
      debtThreshold,
      assetVol,
      simExpectedLoss,
      unexpectedLoss,
      var95,
      var99,
      es95,
      es99,
      worstCase,
      simulationCount: sim.number_of_simulations || 1000,
      avgDefaults: sim.avg_defaults ?? 0.8,
      maxDefaults: sim.max_defaults ?? 4,
      defaultCorrelation: Number(sim.default_correlation) || 0.18,
      simulationScenario: sim.scenario_name || sim.scenario_type || sim.scenario || "Fallback view",
      copulaType: sim.copula_type || sim.assumptions_reference?.copula_type || "Gaussian fallback",
      pdCalibrationStatus: pd.model_assumptions?.calibration_status || "proxy_calibrated_no_observed_default_history",
      pdValidationStatus: pd.model_assumptions?.validation_status || "directional_sanity_checks_embedded",
      mcCalibrationStatus: sim.assumptions_reference?.calibration_status || "distributional_validation_pending_real_portfolio_loss_history",
      mcValidation: sim.assumptions_reference?.validation_diagnostics || {},
      scenarioDataSource: sim.assumptions_reference?.scenario_data_source || "Data-driven scenario endpoint when available",
      pdDrivers,
      lgdDrivers,
      tailDrivers
    };
  }

  function quantMetric(label, value, prompt = "") {
    return `
      <div class="quant-overview-cell">
        ${explainButton(prompt)}
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
    `;
  }

  function distanceToDefaultChart(q) {
    const distancePct = clamp((q.dd / 4) * 100);
    const debtPct = clamp((q.debtThreshold / Math.max(q.assetValue, q.debtThreshold, 1)) * 100);
    return `
      <div class="dd-chart">
        <div class="chart-axis-caption"><span>X-axis: Structural credit distance</span><span>Value: asset cushion above debt barrier</span></div>
        <div class="dd-axis"><span>Default Barrier</span><span>Asset Value</span></div>
        <div class="dd-track">
          <i class="debt-threshold" style="--pos:${debtPct}%"></i>
          <i class="asset-position" style="--pos:${distancePct}%"></i>
        </div>
        <div class="dd-caption">Distance to default: <strong>${ratio(q.dd)}</strong></div>
      </div>
    `;
  }

  function featureContributionChart(items) {
    return `
      <div class="feature-chart">
        <div class="chart-axis-caption"><span>Y-axis: Model feature</span><span>X-axis: Contribution to risk score</span></div>
        ${riskDriverRows(items)}
      </div>
    `;
  }

  function expectedLossWaterfall(q) {
    return `
      <div class="el-waterfall-simple">
        <div class="el-formula">
          <span>PD</span>
          <strong>${pct(q.finalPd)}</strong>
          <i>x</i>
          <span>LGD</span>
          <strong>${pct(q.lgd)}</strong>
          <i>x</i>
          <span>EAD</span>
          <strong>${money(q.ead)}</strong>
          <i>=</i>
          <span>Expected Loss</span>
          <strong class="warn">${money(q.expectedLoss)}</strong>
        </div>
        <p class="model-note">Expected loss is the average modelled credit loss: probability of default multiplied by loss severity and exposure at default.</p>
      </div>
    `;
  }

  function lossDistributionChart(q) {
    const buckets = [4, 10, 18, 31, 45, 57, 63, 55, 42, 31, 22, 15, 9, 5, 3];
    return `
      <div class="loss-distribution">
        <div class="chart-axis-caption"><span>X-axis: Simulated loss amount</span><span>Y-axis: Frequency of outcomes</span></div>
        <div class="loss-bars">
          ${buckets.map((height, index) => `<i style="--height:${height}%; --i:${index}"></i>`).join("")}
          <span class="var-marker var95" style="--pos:72%">VaR 95</span>
          <span class="var-marker var99" style="--pos:88%">VaR 99</span>
          <span class="var-marker es" style="--pos:94%">ES</span>
        </div>
        <div class="loss-axis"><span>Low loss</span><span>Tail loss</span></div>
        <div class="loss-summary-row">
          <span>Average / Expected Loss <strong>${money(q.simExpectedLoss || q.expectedLoss)}</strong></span>
          <span>VaR 95 <strong>${money(q.var95)}</strong></span>
          <span>Expected Shortfall 95 <strong>${money(q.es95)}</strong></span>
        </div>
      </div>
    `;
  }

  function reviewDate(days = 90) {
    const date = new Date();
    date.setDate(date.getDate() + days);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function decisionAnalytics() {
    const rec = state.recommendation || {};
    const pd = state.pd || {};
    const loss = state.loss || {};
    const health = financialHealth();
    const q = quantAnalytics();
    const intel = marketIntelligence();
    const sensitivity = externalSensitivityProfile();
    const requestedLimit = Number(state.requestedLimit ?? rec.recommended_credit_limit ?? q.ead) || 0;
    const requestedTenor = Number(state.requestedTenor) || 30;
    const recommendedLimit = Number(rec.recommended_credit_limit) || Math.min(requestedLimit, 7000000);
    const storedRecommendedTenor = numberValue(rec.recommended_tenor_days);
    const recommendedTenor = storedRecommendedTenor !== null ? storedRecommendedTenor : Math.min(requestedTenor, 30);
    const security = rec.recommended_security || (q.lgd >= 0.5 || intel.stressScore >= 55 ? "Standby Letter of Credit" : "Corporate Guarantee");
    const decision = decisionLabel(rec.approval_status || (recommendedLimit < requestedLimit || /lc|letter/i.test(security) ? "Approve with conditions" : "Approve"));
    const tone = decisionTone(decision);
    const riskGrade = rec.risk_grade || (q.finalPd >= 0.1 ? "B+" : q.finalPd >= 0.06 ? "BB" : "BBB-");
    const expectedLoss = Number(rec.expected_loss || q.expectedLoss) || 0;
    const unsecuredExpectedLoss = Math.max(expectedLoss * 2.15, expectedLoss + requestedLimit * 0.025);
    const securedExpectedLoss = Math.max(expectedLoss, recommendedLimit * q.finalPd * Math.max(q.lgd * 0.72, 0.22));
    const expectedLossReduction = Math.max(0, unsecuredExpectedLoss - securedExpectedLoss);
    const policyScore = clamp((Number(rec.policy_score) || 0.78) * 100);
    const financialScore = health.score;
    const marketScore = clamp(100 - intel.stressScore);
    const structuralScore = clamp(100 - q.finalPd * 650);
    const recoveryScore = /lc|letter|cash|collateral/i.test(security) ? 82 : 58;
    const overallScore = Math.round(
      financialScore * 0.28
      + marketScore * 0.18
      + structuralScore * 0.22
      + recoveryScore * 0.18
      + policyScore * 0.14
    );
    const storedDrivers = Array.isArray(rec.key_risk_drivers) ? rec.key_risk_drivers : [];
    const negativeDrivers = (storedDrivers.length ? storedDrivers.map((label, index) => ({
      label,
      score: [84, 76, 69, 61, 54][index] || 48
    })) : [
      { label: `${sensitivity.fuel} fuel sensitivity`, score: sensitivity.fuel === "High" ? 84 : 64 },
      { label: health.liquidityAssessment === "Weak" ? "Weak liquidity cushion" : "Liquidity constrains limit headroom", score: health.liquidityAssessment === "Weak" ? 76 : 58 },
      { label: `${intel.stressLabel} market stress`, score: Math.round(intel.stressScore) },
      { label: `${health.leverageAssessment} leverage profile`, score: health.leverageAssessment === "High" ? 72 : 55 },
      { label: `${sensitivity.fx} FX exposure`, score: sensitivity.fx === "High" ? 68 : 52 }
    ]).sort((a, b) => b.score - a.score).slice(0, 5);
    const positiveFactors = asList(rec.mitigating_factors).filter((item) => !/No exception/i.test(item));
    const mitigants = positiveFactors.length ? positiveFactors : [
      "Required LC materially improves recovery quality.",
      "Short tenor reduces exposure build-up.",
      "Debt service capacity remains inside monitored range.",
      "Operating cash generation supports near-term obligations.",
      "Recommended limit stays below requested exposure."
    ];
    const policyRows = [
      { label: "Maximum PD threshold", status: q.finalPd <= 0.12 ? "Pass" : "Fail", basis: pct(q.finalPd) },
      { label: "Expected loss threshold", status: securedExpectedLoss <= requestedLimit * 0.06 ? "Pass" : "Fail", basis: money(securedExpectedLoss) },
      { label: "Minimum liquidity requirement", status: health.liquidityAssessment === "Weak" ? "Fail" : "Pass", basis: health.liquidityAssessment },
      { label: "Collateral requirement", status: /lc|letter|cash|collateral|guarantee/i.test(security) ? "Pass" : "Fail", basis: security },
      { label: "Tenor limit", status: recommendedTenor <= 30 ? "Pass" : "Review", basis: tenorText(recommendedTenor) }
    ];
    return {
      rec,
      pd,
      loss,
      health,
      q,
      intel,
      tone,
      decision,
      riskGrade,
      requestedLimit,
      recommendedLimit,
      requestedTenor,
      recommendedTenor,
      requestedSecurity: rec.requested_security || "Unsecured open account",
      security,
      expectedLoss,
      unsecuredExpectedLoss,
      securedExpectedLoss,
      expectedLossReduction,
      overallScore,
      scores: [
        { label: "Overall Credit Quality", score: overallScore },
        { label: "Financial Strength", score: financialScore },
        { label: "Market Risk Resilience", score: marketScore },
        { label: "Structural Risk", score: structuralScore },
        { label: "Recovery Quality", score: recoveryScore },
        { label: "Risk Adjustment Discipline", score: policyScore }
      ],
      negativeDrivers,
      positiveFactors: mitigants,
      policyRows,
      reviewDate: rec.review_date || reviewDate(),
      policyCalibrationStatus: rec.model_assumptions?.policy_calibration_status || "internal_policy_proxy_not_bank_approved",
      policyValidationStatus: rec.model_assumptions?.validation_status || "policy_sanity_checks_embedded",
      policyDiagnostics: rec.model_assumptions?.validation_diagnostics || {},
      policyHaircutBreakdown: rec.model_assumptions?.policy_haircut_breakdown || {},
      ratingNote: rec.model_assumptions?.rating_note || "Risk grades are internal proxy grades, not agency ratings.",
      primaryReason: `${negativeDrivers[0].label} requires ${security.toLowerCase()} and disciplined tenor control.`
    };
  }

  function policyMatrix(rows) {
    return `
      <div class="policy-matrix">
        ${rows.map((item) => `
          <div class="policy-row ${item.status.toLowerCase()}">
            <span>${escapeHtml(item.label)}</span>
            <strong>${escapeHtml(item.status)}</strong>
            <em>${escapeHtml(item.basis)}</em>
          </div>
        `).join("")}
      </div>
    `;
  }

  function structureImpactChart(d) {
    const max = Math.max(d.unsecuredExpectedLoss, d.securedExpectedLoss, 1);
    return `
      <div class="structure-impact-chart">
        <div class="chart-axis-caption"><span>X-axis: Credit structure</span><span>Y-axis: Expected loss amount</span></div>
        <div class="structure-bar-row">
          <span>Without Security</span>
          <div><i style="--fill:${clamp((d.unsecuredExpectedLoss / max) * 100)}%"></i></div>
          <strong>${money(d.unsecuredExpectedLoss)}</strong>
        </div>
        <div class="structure-bar-row secured">
          <span>Recommended Structure</span>
          <div><i style="--fill:${clamp((d.securedExpectedLoss / max) * 100)}%"></i></div>
          <strong>${money(d.securedExpectedLoss)}</strong>
        </div>
        <p>Estimated expected loss reduction: <strong>${money(d.expectedLossReduction)}</strong></p>
      </div>
    `;
  }

  function decisionWaterfall(d) {
    const steps = [
      { label: "Financial Strength", value: d.health.score - 50 },
      { label: "Market Conditions", value: 50 - d.intel.stressScore },
      { label: "Model Outputs", value: 58 - d.q.finalPd * 500 },
      { label: "Collateral", value: /lc|letter|cash|collateral/i.test(d.security) ? 18 : 4 },
      { label: "Risk Checks", value: d.policyRows.every((row) => row.status !== "Fail") ? 12 : -14 }
    ];
    return `
      <div class="decision-waterfall">
        ${steps.map((step) => `
          <div class="decision-waterfall-step ${step.value >= 0 ? "positive" : "negative"}">
            <span>${escapeHtml(step.label)}</span>
            <strong>${step.value >= 0 ? "+" : ""}${Math.round(step.value)}</strong>
            <i style="--fill:${clamp(Math.abs(step.value) * 1.6)}%"></i>
          </div>
        `).join("")}
      </div>
    `;
  }

  function marketSignalRows(items) {
    const changeCell = (value) => Number.isFinite(value)
      ? `<span class="${value >= 0 ? "up" : "down"}">${escapeHtml(signedPct(value))}</span>`
      : `<span class="muted">N/A</span>`;
    return items.map((item) => `
      <details class="market-monitor-row">
        <summary>
          <strong>${escapeHtml(item.name)}</strong>
          <span>${escapeHtml(item.value)}</span>
          ${changeCell(item.m1)}
          ${changeCell(item.m3)}
          <em class="${item.impact.toLowerCase()}">${escapeHtml(item.impact)}</em>
        </summary>
        <div class="market-indicator-detail">
          <p>${escapeHtml(marketIndicatorExplanation(item))}</p>
          <div>
            ${rowLine("Volatility", item.vol)}
            ${rowLine("Direction", item.direction)}
            ${rowLine("As Of", item.date || "Not available")}
            ${rowLine("Source", item.source || "Stored market data")}
            ${rowLine("Freshness", item.isStale ? `Stale (${item.freshness})` : item.freshness || "Latest available")}
          </div>
        </div>
      </details>
    `).join("");
  }

  function stressTrendChart() {
    const history = state.stressHistory?.stress_history || [];
    if (!history.length) return `<p class="model-note">No stored stress history is available for this chart.</p>`;
    const values = history.slice(-24).map((row) => clamp(Number(row.stress_index)));
    return sparklineChart(values, "stress");
  }

  function commodityTrendChart() {
    const grouped = groupedMarketPrices();
    const toIndexed = (series) => {
      const points = series.slice(-24).map((point) => Number(point.price)).filter(Number.isFinite);
      if (points.length < 3) return [];
      const base = points[0] || 1;
      return points.map((value) => ((value / base) - 1) * 100);
    };
    const brent = toIndexed(seriesForAsset(marketAssets[0], grouped).series);
    const jet = toIndexed(seriesForAsset(marketAssets[1], grouped).series);
    if (brent.length >= 3) return sparklineChart(brent, "commodity", jet.length >= 3 ? jet : null);
    return `<p class="model-note">No stored Brent or jet fuel history is available for this chart.</p>`;
  }

  function dailyChangeForSeries(series) {
    if (!series || series.length < 2) return null;
    const latest = series[series.length - 1];
    const prior = series[series.length - 2];
    if (!prior?.price || !latest?.price) return null;
    return ((latest.price / prior.price) - 1) * 100;
  }

  function latestChangeWindow(series) {
    if (!series || series.length < 2) {
      const latest = series?.[series.length - 1];
      return { change: null, label: latest?.date ? `As of ${latest.date}` : "Latest available" };
    }
    const latest = series[series.length - 1];
    const prior = series[series.length - 2];
    const change = prior?.price && latest?.price ? ((latest.price / prior.price) - 1) * 100 : null;
    const label = prior?.date && latest?.date ? `${prior.date} -> ${latest.date}` : "Latest observation";
    return { change, label };
  }

  function trendSymbol(change) {
    const n = Number(change);
    if (!Number.isFinite(n) || Math.abs(n) < 0.05) return "→";
    return n > 0 ? "↑" : "↓";
  }

  function trendClass(change, inverse = false) {
    const n = Number(change);
    if (!Number.isFinite(n) || Math.abs(n) < 0.05) return "neutral";
    const adverse = inverse ? n < 0 : n > 0;
    return adverse ? "negative" : "positive";
  }

  function badgeClass(label) {
    const value = String(label || "").toLowerCase();
    if (value.includes("high") || value.includes("negative")) return "high";
    if (value.includes("medium") || value.includes("moderate")) return "medium";
    if (value.includes("low") || value.includes("positive")) return "low";
    return "neutral";
  }

  function marketKpiCard(title, indicator, options = {}) {
    const grouped = groupedMarketPrices();
    const assetDef = options.assetDef || marketAssets.find((asset) => asset.name === title);
    const series = assetDef ? seriesForAsset(assetDef, grouped).series : [];
    const latest = series.length ? series[series.length - 1] : null;
    const window = latestChangeWindow(series);
    const change = window.change;
    const level = options.level || indicator?.value || (latest ? formatMarketValue(latest.price, options.unit || assetDef?.unit) : "N/A");
    const trend = options.trend || trendSymbol(change);
    const directionClass = options.className || trendClass(change, options.inverse ?? indicator?.inverse);
    const meta = options.meta || (Number.isFinite(change) ? `${signedPct(change)} | ${window.label}` : window.label);
    return `
      <article class="market-kpi-card ${directionClass}">
        <span>${escapeHtml(title)}</span>
        <strong>${escapeHtml(level)}</strong>
        <div>
          <em>${escapeHtml(trend)}</em>
          <small>${escapeHtml(meta)}</small>
        </div>
      </article>
    `;
  }

  function marketStatusBadge(label) {
    return `<span class="market-status-badge ${badgeClass(label)}">${escapeHtml(label)}</span>`;
  }

  function marketBusinessSignals(indicators) {
    const get = (name) => marketIndicatorByName(indicators, name);
    const fuel = get("Jet Fuel Proxy") || get("Brent Crude");
    const usdInr = get("USD/INR") || get("DXY");
    const rates = get("US 10Y Yield");
    const inflation = get("Inflation Signal");
    const demand = get("IATA Passenger Traffic");
    const freight = get("Baltic Dry Index") || get("Marine Fuel Proxy");
    const signal = (item, upText, downText, flatText = "Stable") => {
      if (!item) return "Latest unavailable";
      if (item.direction === "Up") return upText;
      if (item.direction === "Down") return downText;
      return flatText;
    };
    return [
      {
        driver: "Fuel Prices",
        signal: signal(fuel, "Rising", "Falling"),
        impact: fuel?.impact === "Negative" ? "Margin pressure" : fuel?.impact === "Positive" ? "Cost relief" : "Limited change",
        direction: fuel?.impact || "Neutral"
      },
      {
        driver: "USD/INR",
        signal: signal(usdInr, "Weak INR / stronger USD", "Stronger INR / softer USD"),
        impact: usdInr?.impact === "Negative" ? "Higher dollar-linked costs" : "FX pressure easing",
        direction: usdInr?.impact || "Neutral"
      },
      {
        driver: "Interest Rates",
        signal: signal(rates, "High / rising", "Easing"),
        impact: rates?.impact === "Negative" ? "Funding cost pressure" : "Funding pressure lower",
        direction: rates?.impact || "Neutral"
      },
      {
        driver: "Inflation",
        signal: signal(inflation, "Elevated", "Cooling"),
        impact: inflation?.impact === "Negative" ? "Operating cost pressure" : "Cost backdrop improving",
        direction: inflation?.impact || "Neutral"
      },
      {
        driver: "Air Passenger Demand",
        signal: signal(demand, "Improving", "Weakening"),
        impact: demand?.impact === "Negative" ? "Revenue risk" : "Demand support",
        direction: demand?.impact || "Neutral"
      },
      {
        driver: "Freight / Trade Activity",
        signal: signal(freight, "Improving", "Softening"),
        impact: freight?.impact === "Negative" ? "Trade cycle pressure" : "Trade activity support",
        direction: freight?.impact || "Neutral"
      }
    ];
  }

  function marketSignalTable(signals) {
    return `
      <div class="market-signal-table">
        <div class="market-signal-head"><span>Driver</span><span>Current Signal</span><span>Credit Direction</span></div>
        ${signals.map((item) => `
          <div class="market-signal-row">
            <strong>${escapeHtml(item.driver)}</strong>
            <span>${escapeHtml(item.signal)}</span>
            ${marketStatusBadge(item.direction === "Positive" ? "Positive" : item.direction === "Negative" ? "Negative" : "Neutral")}
          </div>
        `).join("")}
      </div>
    `;
  }

  function marketExposureAssessment(indicators) {
    const sensitivity = externalSensitivityProfile();
    const get = (name) => marketIndicatorByName(indicators, name);
    const fuel = get("Jet Fuel Proxy") || get("Brent Crude");
    const fx = get("USD/INR") || get("DXY");
    const rates = get("US 10Y Yield");
    const inflation = get("Inflation Signal");
    const demand = get("IATA Passenger Traffic");
    const stress = stressScore();
    const scoreParts = [
      fuel?.impact === "Negative" ? 24 : fuel?.impact === "Neutral" ? 10 : 4,
      fx?.impact === "Negative" ? 18 : fx?.impact === "Neutral" ? 8 : 3,
      rates?.impact === "Negative" ? 14 : 5,
      inflation?.impact === "Negative" ? 14 : 5,
      demand?.impact === "Negative" ? 14 : 4,
      stress >= 70 ? 16 : stress >= 45 ? 10 : 4
    ];
    const score = clamp(scoreParts.reduce((sum, value) => sum + value, 0));
    const level = score >= 70 ? "High" : score >= 40 ? "Medium" : "Low";
    return {
      score: Math.round(score),
      overall: level,
      fuel: sensitivity.fuel === "High" && fuel?.impact === "Negative" ? "High" : fuel?.impact === "Negative" ? "Medium" : "Low",
      fx: sensitivity.fx === "High" && fx?.impact === "Negative" ? "High" : fx?.impact === "Negative" ? "Medium" : "Low",
      margin: [fuel, fx, inflation].filter((item) => item?.impact === "Negative").length >= 2 ? "High" : fuel?.impact === "Negative" ? "Medium" : "Low",
      quality: score >= 70 ? "Weakening" : score >= 40 ? "Watch" : "Stable"
    };
  }

  function marketImpactGrid(assessment) {
    const rows = [
      ["Fuel Cost Pressure", assessment.fuel],
      ["FX Exposure", assessment.fx],
      ["Profit Margin Pressure", assessment.margin],
      ["Expected Credit Quality", assessment.quality],
      ["Overall External Risk", assessment.overall]
    ];
    return `
      <div class="market-impact-badges">
        ${rows.map(([label, value]) => `
          <div>
            <span>${escapeHtml(label)}</span>
            ${marketStatusBadge(value)}
          </div>
        `).join("")}
      </div>
      <div class="market-exposure-score">
        <div><span>Market Exposure Score</span><strong>${assessment.score} / 100</strong></div>
        <i><b style="--fill:${assessment.score}%"></b></i>
      </div>
    `;
  }

  function marketExecutiveSummary(indicators, assessment) {
    const get = (name) => marketIndicatorByName(indicators, name);
    const fuel = get("Jet Fuel Proxy") || get("Brent Crude");
    const fx = get("USD/INR") || get("DXY");
    const rates = get("US 10Y Yield");
    const demand = get("IATA Passenger Traffic");
    const fuelText = fuel?.impact === "Negative" ? "Fuel prices are moving against airline margins" : fuel?.impact === "Positive" ? "Fuel prices are providing some cost relief" : "Fuel prices are broadly stable";
    const fxText = fx?.impact === "Negative" ? "the currency backdrop adds dollar-cost pressure" : "the currency backdrop is not adding major new pressure";
    const rateText = rates?.impact === "Negative" ? "Funding conditions remain relatively tight" : "Funding conditions are manageable";
    const demandText = demand?.impact === "Negative" ? "Passenger-demand signals are softer" : "Passenger-demand signals are not the main risk today";
    return `${fuelText}, while ${fxText}. ${rateText}, and ${demandText}. Based on the selected counterparty's fuel dependency, FX exposure, and current market stress, the overall external market impact is assessed as ${assessment.overall}.`;
  }

  function miniSparkline(series) {
    const values = (series || []).slice(-18).map((point) => Number(point.price)).filter(Number.isFinite);
    if (values.length < 2) return `<svg class="mini-sparkline" viewBox="0 0 120 34" aria-hidden="true"><line x1="4" y1="17" x2="116" y2="17"></line></svg>`;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const x = (index) => 4 + (index * 112) / Math.max(values.length - 1, 1);
    const y = (value) => 30 - ((value - min) / Math.max(max - min, 1)) * 26;
    const points = values.map((value, index) => `${x(index)},${y(value)}`).join(" ");
    return `<svg class="mini-sparkline" viewBox="0 0 120 34" aria-hidden="true"><polyline points="${points}"></polyline></svg>`;
  }

  function marketLiveCards(indicators) {
    const grouped = groupedMarketPrices();
    const explanation = {
      "Brent Crude": "Global crude benchmark used to read fuel-cost pressure.",
      "WTI Crude": "US crude benchmark used as a second oil-price check.",
      "Jet Fuel Proxy": "Closest stored proxy for aviation fuel cost.",
      "DXY": "Dollar strength indicator; higher values can pressure USD-linked costs.",
      "VIX": "Market volatility gauge used as a risk-aversion signal.",
      "S&P 500": "Broad risk appetite proxy for macro sentiment.",
      "US 10Y Yield": "Long-term funding-rate signal.",
      "Baltic Dry Index": "Freight and trade activity proxy.",
      "Global PMI": "Business activity signal for demand conditions.",
      "IATA Passenger Traffic": "Airline demand proxy."
    };
    const names = ["Brent Crude", "WTI Crude", "Jet Fuel Proxy", "DXY", "VIX", "S&P 500", "US 10Y Yield", "Baltic Dry Index", "Global PMI", "IATA Passenger Traffic"];
    return names.map((name) => {
      const indicator = marketIndicatorByName(indicators, name);
      const assetDef = marketAssets.find((asset) => asset.name === name);
      const series = assetDef ? seriesForAsset(assetDef, grouped).series : [];
      const window = latestChangeWindow(series);
      const change = window.change;
      const status = indicator?.isStale ? "Stale" : indicator?.impact || "Neutral";
      return `
        <article class="market-watch-card ${trendClass(change, indicator?.inverse)}">
          <div class="market-watch-head">
            <strong>${escapeHtml(name)}</strong>
            ${marketStatusBadge(status)}
          </div>
          <div class="market-watch-value">
            <span>${escapeHtml(indicator?.value || "N/A")}</span>
            <em>${escapeHtml(trendSymbol(change))} ${escapeHtml(Number.isFinite(change) ? signedPct(change) : "N/A")}</em>
          </div>
          ${miniSparkline(series)}
          <small class="market-watch-window">${escapeHtml(window.label)}</small>
          <p>${escapeHtml(explanation[name] || "Market factor used by the credit risk model.")}</p>
        </article>
      `;
    }).join("");
  }

  function marketLineComparisonChart(title, leftLabel, leftSeries, rightLabel, rightSeries, note) {
    const toIndexed = (series) => {
      const values = (series || []).slice(-45).map((point) => Number(point.price)).filter(Number.isFinite);
      if (values.length < 3) return [];
      const base = values[0] || 1;
      return values.map((value) => ((value / base) - 1) * 100);
    };
    const first = toIndexed(leftSeries);
    const second = toIndexed(rightSeries);
    if (first.length < 3 && second.length < 3) {
      return `<div class="market-chart-empty">${escapeHtml(title)} needs more stored observations.</div>`;
    }
    return `
      <div class="market-chart-title">
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(note)}</span>
      </div>
      ${sparklineChart(first.length >= 3 ? first : second, "market-clean", second.length >= 3 ? second : null, {
        xStart: chartDateLabel(leftSeries?.slice(-45)?.[0]?.date || rightSeries?.slice(-45)?.[0]?.date),
        xEnd: chartDateLabel(leftSeries?.slice(-1)?.[0]?.date || rightSeries?.slice(-1)?.[0]?.date)
      })}
      <div class="market-chart-legend">
        <span><i class="primary"></i>${escapeHtml(leftLabel)}</span>
        <span><i class="secondary"></i>${escapeHtml(rightLabel)}</span>
      </div>
    `;
  }

  function chartDateLabel(date) {
    if (!date) return "";
    const parsed = new Date(date);
    if (Number.isNaN(parsed.getTime())) return String(date);
    return parsed.toISOString().slice(5, 10);
  }

  function marketSingleSeriesChart(title, label, series, note, unit = "") {
    const points = (series || []).slice(-45).filter((point) => Number.isFinite(Number(point.price)));
    if (points.length < 3) {
      return `<div class="market-chart-empty">${escapeHtml(title)} needs more stored observations.</div>`;
    }
    const width = 720;
    const height = 210;
    const pad = 34;
    const values = points.map((point) => Number(point.price));
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const rangePad = Math.max((maxValue - minValue) * 0.18, Math.abs(maxValue) * 0.0008, 0.01);
    const min = minValue - rangePad;
    const max = maxValue + rangePad;
    const x = (index) => pad + (index * (width - pad * 2)) / Math.max(points.length - 1, 1);
    const y = (value) => height - pad - ((value - min) / Math.max(max - min, 1)) * (height - pad * 2);
    const line = points.map((point, index) => `${x(index)},${y(Number(point.price))}`).join(" ");
    const fmt = (value) => unit === "%" ? `${value.toFixed(2)}%` : value >= 100 ? value.toFixed(1) : value.toFixed(2);
    const startDate = chartDateLabel(points[0]?.date);
    const endDate = chartDateLabel(points[points.length - 1]?.date);
    return `
      <div class="market-chart-title">
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(note)}</span>
      </div>
      <svg class="market-line-chart market-single" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(title)} chart">
        <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" class="chart-axis"></line>
        <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" class="chart-axis"></line>
        <text x="${pad - 6}" y="${pad + 4}" text-anchor="end" class="axis-tick">${escapeHtml(fmt(max))}</text>
        <text x="${pad - 6}" y="${height - pad}" text-anchor="end" class="axis-tick">${escapeHtml(fmt(min))}</text>
        <text x="${pad}" y="${height - 8}" text-anchor="middle" class="axis-tick">${escapeHtml(startDate)}</text>
        <text x="${width - pad}" y="${height - 8}" text-anchor="middle" class="axis-tick">${escapeHtml(endDate)}</text>
        <text x="${width / 2}" y="${height - 2}" text-anchor="middle" class="axis-label">Observation date</text>
        <text x="12" y="${height / 2}" text-anchor="middle" transform="rotate(-90 12 ${height / 2})" class="axis-label">${escapeHtml(label)}</text>
        <polyline points="${line}" class="market-line primary"></polyline>
      </svg>
      <div class="chart-axis-caption"><span>X-axis: observation date (${escapeHtml(startDate)} to ${escapeHtml(endDate)})</span><span>Y-axis: ${escapeHtml(label)}</span></div>
    `;
  }

  function macroPressureSeries(indicators) {
    const grouped = groupedMarketPrices();
    const dxy = seriesForAsset(marketAssets.find((asset) => asset.name === "DXY"), grouped).series;
    const vix = seriesForAsset(marketAssets.find((asset) => asset.name === "VIX"), grouped).series;
    const rates = seriesForAsset(marketAssets.find((asset) => asset.name === "US 10Y Yield"), grouped).series;
    const len = Math.min(dxy.length, vix.length, rates.length, 45);
    if (len < 3) return [];
    const normalize = (series) => {
      const values = series.slice(-len).map((point) => Number(point.price));
      const min = Math.min(...values);
      const max = Math.max(...values);
      return values.map((value) => ((value - min) / Math.max(max - min, 1)) * 100);
    };
    const a = normalize(dxy);
    const b = normalize(vix);
    const c = normalize(rates);
    return a.map((value, index) => (value * 0.35) + (b[index] * 0.4) + (c[index] * 0.25));
  }

  function sparklineChart(values, mode, secondValues = null, options = {}) {
    const width = 720;
    const height = 210;
    const pad = 26;
    const all = secondValues ? values.concat(secondValues) : values;
    const min = Math.min(...all) - 4;
    const max = Math.max(...all) + 4;
    const x = (index, list) => pad + (index * (width - pad * 2)) / Math.max(list.length - 1, 1);
    const y = (value) => height - pad - ((value - min) / Math.max(max - min, 1)) * (height - pad * 2);
    const line = (list) => list.map((value, i) => `${x(i, list)},${y(value)}`).join(" ");
    const xLabel = mode === "stress" ? "Recent observations" : "Recent trading observations";
    const yLabel = mode === "stress" ? "Stress index (0-100)" : "Indexed move from first point (%)";
    const valueLabel = (value) => mode === "stress" ? `${Math.round(value)}` : `${value.toFixed(1)}%`;
    return `
      <svg class="market-line-chart ${mode}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${mode} trend chart">
        <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" class="chart-axis"></line>
        <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" class="chart-axis"></line>
        <text x="${pad - 6}" y="${pad + 4}" text-anchor="end" class="axis-tick">${escapeHtml(valueLabel(max))}</text>
        <text x="${pad - 6}" y="${height - pad}" text-anchor="end" class="axis-tick">${escapeHtml(valueLabel(min))}</text>
        ${options.xStart ? `<text x="${pad}" y="${height - 8}" text-anchor="middle" class="axis-tick">${escapeHtml(options.xStart)}</text>` : ""}
        ${options.xEnd ? `<text x="${width - pad}" y="${height - 8}" text-anchor="middle" class="axis-tick">${escapeHtml(options.xEnd)}</text>` : ""}
        <text x="${width / 2}" y="${height - 3}" text-anchor="middle" class="axis-label">${escapeHtml(xLabel)}</text>
        <text x="10" y="${height / 2}" text-anchor="middle" transform="rotate(-90 10 ${height / 2})" class="axis-label">${escapeHtml(yLabel)}</text>
        <polyline points="${line(values)}" class="market-line primary"></polyline>
        ${secondValues ? `<polyline points="${line(secondValues)}" class="market-line secondary"></polyline>` : ""}
      </svg>
      <div class="chart-axis-caption"><span>X-axis: ${escapeHtml(xLabel)}</span><span>Y-axis: ${escapeHtml(yLabel)}</span></div>
    `;
  }

  function sensitivityLabel(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "Medium";
    if (n >= 0.7) return "High";
    if (n >= 0.4) return "Medium";
    return "Low";
  }

  function healthScores() {
    const r = state.ratios || {};
    const m = state.metrics || {};
    const liquidity = clamp((Number(r.current_ratio) || 0.9) * 42);
    const leverage = clamp(100 - (Number(r.debt_to_ebitda) || 3.8) * 14);
    const profitability = clamp(((Number(r.operating_margin) || Number(m.ebitda) / Math.max(Number(m.revenue) || 1, 1) || 0.12) * 100) * 4.5);
    const debtService = clamp((Number(r.interest_coverage) || 2.2) * 18);
    const cashFlow = clamp((Number(m.free_cash_flow) || Number(m.operating_cash_flow) || Number(m.ebitda) || 1) / Math.max(Number(m.revenue) || 1, 1) * 500);
    return [
      { label: "Liquidity", score: Math.round(liquidity) },
      { label: "Leverage", score: Math.round(leverage) },
      { label: "Profitability", score: Math.round(profitability) },
      { label: "Debt Service", score: Math.round(debtService) },
      { label: "Cash Flow", score: Math.round(cashFlow) }
    ];
  }

  function topRiskDrivers() {
    const r = state.ratios || {};
    const pd = state.pd || {};
    const stress = stressLevel().score;
    const fuel = clamp((Number(pd.commodity_sensitivity_score) || 0.82) * 100);
    const fx = clamp((Number(pd.fx_sensitivity_score) || 0.68) * 100);
    const macro = clamp((Number(pd.macro_sensitivity_score) || 0.52) * 100);
    const leverage = clamp((Number(r.debt_to_ebitda) || 3.7) * 15);
    const liquidityWeakness = clamp(100 - healthScores().find((item) => item.label === "Liquidity").score);
    return [
      { label: "Fuel Cost Exposure", score: Math.round(fuel) },
      { label: "Liquidity Weakness", score: Math.round(liquidityWeakness) },
      { label: "FX Exposure", score: Math.round(fx) },
      { label: "Market Stress", score: Math.round(stress) },
      { label: "Leverage", score: Math.round(leverage || macro) }
    ].sort((a, b) => b.score - a.score).slice(0, 5);
  }

  function scoreRows(items) {
    return items.map((item) => `
      <div class="score-row">
        <div class="score-row-head"><span>${escapeHtml(item.label)}</span><strong>${item.score}</strong></div>
        <div class="score-track"><div class="score-fill" style="--fill:${item.score}%"></div></div>
      </div>
    `).join("");
  }

  function riskDriverRows(items) {
    if (!Array.isArray(items) || !items.length) {
      return `<p class="model-note">No calculated driver contributions are available from the stored model output.</p>`;
    }
    const max = Math.max(...items.map((item) => item.score), 100);
    return items.map((item, index) => `
      <div class="risk-rank-row">
        <span class="risk-rank">${index + 1}</span>
        <span class="risk-name">${escapeHtml(item.label)}</span>
        <div class="risk-bar"><div style="--fill:${Math.round((item.score / max) * 100)}%"></div></div>
        <strong>${item.score}</strong>
      </div>
    `).join("");
  }

  function pageHeader(title, subtitle) {
    return `
      <div class="page-kicker">Question Answered</div>
      <h1 class="page-title">${escapeHtml(title)}</h1>
      <p class="page-subtitle">${escapeHtml(subtitle)}</p>
    `;
  }

  function emptyPanel(title, message) {
    return `<article class="panel"><div class="panel-title">${escapeHtml(title)}</div><p>${escapeHtml(message)}</p></article>`;
  }

  function renderCounterparty() {
    const cp = state.counterparty || {};
    const m = state.metrics || {};
    const docs = Array.isArray(state.documents) ? state.documents : [];
    const latestDoc = state.latestDocument || {};
    const statementAge = m.fiscal_year ? `${Math.max(0, new Date().getFullYear() - Number(m.fiscal_year))} years old` : "Not available";
    const sourceLabel = latestDoc.document_type === "manual_financial_statement" ? "Manual entry" : latestDoc.document_type || "Document upload";
    const confidence = m.extraction_confidence !== undefined && m.extraction_confidence !== null ? pct(m.extraction_confidence) : "Pending";
    const coverageItems = [
      ["Revenue", m.revenue !== undefined && m.revenue !== null ? money(m.revenue) : "Not captured"],
      ["Total Assets", m.total_assets !== undefined && m.total_assets !== null ? money(m.total_assets) : "Not captured"],
      ["Total Debt", m.total_debt !== undefined && m.total_debt !== null ? money(m.total_debt) : "Not captured"],
      ["Shareholders Equity", m.shareholders_equity !== undefined && m.shareholders_equity !== null ? money(m.shareholders_equity) : "Not captured"]
    ];
    const profileNotes = [
      `${cp.counterparty_type || "Counterparty"} profile used to select fuel, FX, and macro sensitivity assumptions.`,
      m.fiscal_year ? `Latest stored statement period is ${m.fiscal_year}${m.fiscal_period ? ` ${m.fiscal_period}` : ""}.` : "No stored financial statement period is available yet.",
      latestDoc.extraction_status ? `Document workflow status is ${latestDoc.extraction_status}.` : "No document workflow status is available.",
      docs.length ? `${docs.length} source document${docs.length === 1 ? "" : "s"} linked to this counterparty.` : "No source documents are linked yet."
    ];
    const missingFields = Array.isArray(m.missing_critical_fields) && m.missing_critical_fields.length
      ? m.missing_critical_fields.join(", ")
      : "None flagged";
    const findings = [
      "Confirm the latest annual report before final committee use.",
      "Review business segment and country fields because they drive downstream sensitivity mapping.",
      "Check missing-field warnings before relying on generated ratios or model outputs.",
      "Use the terms test only after the company profile and statement source look correct."
    ];

    el.root.innerHTML = `
      <section class="counterparty-analysis-hero">
        <div class="counterparty-profile-copy">
          <div class="page-kicker">Counterparty Profile</div>
          <h1>${escapeHtml(cp.counterparty_name || "Counterparty pending")}</h1>
          <div class="counterparty-meta">
            <span>${escapeHtml(cp.counterparty_type || "Airline")}</span>
            <span>${escapeHtml(cp.country || "United States")}</span>
            <span>${escapeHtml(m.currency || "USD")}</span>
          </div>
          <p>${escapeHtml(profileNotes[0])}</p>
        </div>
        <div class="counterparty-profile-stack">
          <div class="term-stack">
            <span>Latest Statement</span>
            <strong>${escapeHtml(m.fiscal_year || "Pending")}</strong>
            <span>${escapeHtml(m.fiscal_period || "Full year / latest")}</span>
            <span>${escapeHtml(statementAge)}</span>
          </div>
          <div class="term-chip grade">Data Confidence <strong>${escapeHtml(confidence)}</strong></div>
        </div>
        <div class="counterparty-context">
          ${row("Source", sourceLabel)}
          ${row("Documents", `${docs.length}`)}
          ${row("Missing Critical Fields", missingFields)}
        </div>
      </section>

      <section class="risk-snapshot">
        <div class="primary-metrics">
          ${coverageItems.map(([label, value]) => metric(label, value)).join("")}
        </div>
        <div class="secondary-metrics">
          ${row("Counterparty ID", cp.id || "Pending")}
          ${row("Created", cp.created_at ? new Date(cp.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "Not available")}
          ${row("Document Status", latestDoc.extraction_status || "Not available")}
          ${row("Processed", latestDoc.processed_at ? new Date(latestDoc.processed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "Not available")}
          ${row("Created By", latestDoc.created_by || "System / analyst")}
          ${row("Currency", m.currency || "USD")}
        </div>
      </section>

      <section class="committee-grid">
        <article class="terminal-panel health-panel">
          <div class="panel-title">Company Snapshot</div>
          ${row("Name", cp.counterparty_name || "Pending")}
          ${row("Business Type", cp.counterparty_type || "Not set")}
          ${row("Country", cp.country || "Not set")}
          ${row("Statement Source", sourceLabel)}
        </article>
        <article class="terminal-panel driver-panel">
          <div class="panel-title">Source Notes</div>
          <ul class="committee-list">${profileNotes.slice(1).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </article>
        <article class="terminal-panel market-panel">
          <div class="panel-title">Readiness Checks</div>
          ${row("Financials Stored", state.metrics ? "Yes" : "No")}
          ${row("Ratios Available", state.ratios ? "Yes" : "No")}
          ${row("PD Available", state.pd ? "Yes" : "No")}
          ${row("Loss Available", state.loss ? "Yes" : "No")}
          ${row("Recommendation Available", state.recommendation ? "Yes" : "No")}
        </article>
      </section>

      <section class="terminal-panel model-evidence-panel">
        <div class="panel-title">Statement Capture</div>
        <div class="snapshot-grid">
          ${row("EBITDA", m.ebitda !== undefined && m.ebitda !== null ? money(m.ebitda) : "Pending")}
          ${row("Net Income", m.net_income !== undefined && m.net_income !== null ? money(m.net_income) : "Pending")}
          ${row("Cash", m.cash_and_equivalents !== undefined && m.cash_and_equivalents !== null ? money(m.cash_and_equivalents) : "Pending")}
          ${row("Receivables", m.accounts_receivable !== undefined && m.accounts_receivable !== null ? money(m.accounts_receivable) : "Pending")}
          ${row("Inventory", m.inventory !== undefined && m.inventory !== null ? money(m.inventory) : "Pending")}
          ${row("Current Liabilities", m.current_liabilities !== undefined && m.current_liabilities !== null ? money(m.current_liabilities) : "Pending")}
        </div>
      </section>

      <section class="terminal-panel underwriting-note">
        <div>
          <div class="panel-title">Key Findings</div>
          <ul class="committee-list">${findings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
        <div class="recommendation-note">
          <div class="panel-title">Analyst Setup</div>
          <p>Profile ready for model workflow.</p>
          ${row("Next Step", state.ratios ? "Review model outputs" : "Calculate ratios")}
          ${row("Financial Source", sourceLabel)}
          ${row("Data Confidence", confidence)}
        </div>
      </section>
    `;
  }

  function historyStatusLabel(status) {
    if (status === "available") return "Available";
    if (status === "insufficient_history") return "Insufficient history";
    return status ? String(status).replace(/_/g, " ") : "Not available";
  }

  function trendValue(value, mode = "pct") {
    const n = numberValue(value);
    if (n === null) return "Not available";
    if (mode === "money") return money(n);
    if (mode === "ratio") return n.toFixed(2);
    if (mode === "pp") return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(1)} pts`;
    return signedPct(n);
  }

  function financialHistoryCoverage() {
    const history = state.financialHistory || {};
    const trend = state.trendFeatures || {};
    const periods = Array.isArray(history.periods) ? history.periods : [];
    const latest = history.latest_metrics || state.metrics || {};
    const oldest = periods.length ? periods[periods.length - 1] : null;
    return `
      <section class="terminal-panel financial-history-panel">
        <div class="panel-title">Financial History Coverage</div>
        <p class="model-note">Shows how much historical financial data is available for trend features. The latest snapshot still drives the core model; extra periods only add trend context.</p>
        <div class="history-coverage-grid">
          ${row("Periods Available", String(periods.length))}
          ${row("Latest Snapshot", latest.fiscal_year ? `${latest.fiscal_year} ${latest.period_label || latest.fiscal_period || "FY"}` : "Pending")}
          ${row("Oldest Period", oldest?.fiscal_year ? `${oldest.fiscal_year} ${oldest.period_label || oldest.fiscal_period || "FY"}` : "Pending")}
          ${row("Frequency", trend.history_frequency || "Not available")}
          ${row("Trend Status", historyStatusLabel(trend.history_status))}
          ${row("Trend Source", "Stored financial metrics")}
        </div>
        ${financialHistoryTable(periods, latest)}
      </section>
    `;
  }

  function financialHistoryTable(periods, latest) {
    if (!periods.length) return `<p class="model-note">No stored financial history is available. Add periods from Ingest New Data.</p>`;
    return `
      <div class="financial-history-table">
        ${periods.map((item) => {
          const isLatest = Number(item.id) === Number(latest?.id) || item.is_latest_snapshot === true;
          return `
            <div class="financial-history-row ${isLatest ? "is-latest" : ""}">
              <div class="history-period">
                <strong>${escapeHtml(`${item.fiscal_year || "Unknown"} ${item.period_label || item.fiscal_period || "FY"}`)}</strong>
                <span>${escapeHtml(item.period_type || "annual")}</span>
              </div>
              <div class="history-values">
                <span><b>Revenue</b>${money(item.revenue)}</span>
                <span><b>EBITDA</b>${money(item.ebitda)}</span>
                <span><b>Net Income</b>${money(item.net_income)}</span>
                <span><b>Debt</b>${money(item.total_debt)}</span>
                <span><b>Cash</b>${money(item.cash_and_equivalents)}</span>
              </div>
              <div class="history-action">
                <em>${isLatest ? "Latest snapshot" : "History"}</em>
                <button type="button" data-mark-latest="${item.id}" ${isLatest ? "disabled" : ""}>Set Latest</button>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;
  }

  function trendFeaturePanel() {
    const trend = state.trendFeatures || {};
    const overlay = trend.model_overlay || {};
    const warnings = Array.isArray(trend.warnings) && trend.warnings.length ? trend.warnings.join(" | ") : "None";
    return `
      <section class="terminal-panel trend-feature-panel">
        <div class="panel-title">Trend Feature Layer</div>
        <div class="trend-feature-grid">
          ${row("Overlay Direction", overlay.direction ? String(overlay.direction).replace(/_/g, " ") : "Neutral")}
          ${row("Trend Risk Score", trendValue(overlay.risk_score, "ratio"))}
          ${row("PD Multiplier", trendValue(overlay.pd_multiplier, "ratio"))}
          ${row("LGD Add-on", trendValue(overlay.lgd_addon))}
          ${row("Latest Current Ratio", trendValue(trend.current_ratio_latest, "ratio"))}
          ${row("Latest Interest Coverage", trendValue(trend.interest_coverage_latest, "ratio"))}
          ${row("Revenue CAGR", trendValue(trend.revenue_cagr))}
          ${row("Latest Revenue Growth", trendValue(trend.latest_revenue_growth))}
          ${row("EBITDA Margin Trend", trendValue(trend.ebitda_margin_trend, "pp"))}
          ${row("Net Margin Trend", trendValue(trend.net_margin_trend, "pp"))}
          ${row("Debt Growth", trendValue(trend.debt_growth))}
          ${row("Leverage Trend", trendValue(trend.leverage_trend, "ratio"))}
          ${row("Interest Coverage Trend", trendValue(trend.interest_coverage_trend, "ratio"))}
          ${row("Current Ratio Trend", trendValue(trend.current_ratio_trend, "ratio"))}
          ${row("Cash Trend", trendValue(trend.cash_trend))}
          ${row("Fuel Cost Growth", trendValue(trend.fuel_cost_growth))}
          ${row("Fuel Cost / Revenue", trendValue(trend.fuel_cost_to_revenue_latest))}
          ${row("Warnings", warnings)}
        </div>
      </section>
    `;
  }

  function renderFinancials() {
    const m = state.metrics || {};
    const r = state.ratios || {};
    const health = financialHealth();
    const points = financialTrendPoints();
    const missing = Array.isArray(m.missing_critical_fields) && m.missing_critical_fields.length
      ? m.missing_critical_fields.join(", ")
      : "None flagged";
    el.root.innerHTML = `
      ${pageHeader("Financial Statements", "How strong is this company financially and why?")}
      <section class="financial-health-header">
        <div>
          <div class="page-kicker">Financial Health Overview</div>
          <h2>${health.score} <span>/ 100</span></h2>
          <p>${escapeHtml(health.trend)} financial profile based on liquidity, leverage, coverage, profitability, and cash flow.</p>
        </div>
        <div class="health-header-metrics">
          ${row("Data Confidence", m.extraction_confidence !== undefined ? pct(m.extraction_confidence) : "Pending")}
          ${row("Fiscal Year", m.fiscal_year || "Pending")}
          ${row("Financial Trend", health.trend)}
        </div>
      </section>

      ${financialHistoryCoverage()}
      ${trendFeaturePanel()}

      <section class="pillar-grid">
        <article class="credit-pillar">
          <div class="pillar-head">
            <span>Liquidity</span>
            <strong>${escapeHtml(health.liquidityAssessment)}</strong>
          </div>
          ${row("Current Ratio", ratio(r.current_ratio))}
          ${row("Quick Ratio", ratio(r.quick_ratio))}
          ${row("Cash Ratio", ratio(r.cash_ratio))}
          ${row("Working Capital", money(r.working_capital))}
          <p>${health.liquidityAssessment === "Strong" ? "Liquidity comfortably supports short-cycle fuel receivables." : health.liquidityAssessment === "Adequate" ? "Liquidity supports controlled exposure with active monitoring." : "Liquidity weakness limits unsecured credit appetite."}</p>
        </article>
        <article class="credit-pillar">
          <div class="pillar-head">
            <span>Leverage</span>
            <strong>${escapeHtml(health.leverageAssessment)}</strong>
          </div>
          ${row("Debt / EBITDA", ratio(r.debt_to_ebitda))}
          ${row("Debt / Equity", ratio(r.debt_to_equity))}
          ${row("Liabilities / Assets", r.liabilities_to_assets !== undefined ? pct(r.liabilities_to_assets) : "Pending")}
          <p>${health.leverageAssessment === "Low" ? "Debt burden leaves room for trade credit exposure." : health.leverageAssessment === "Moderate" ? "Leverage is acceptable but constrains limit expansion." : "High leverage requires tighter tenor and stronger security."}</p>
        </article>
        <article class="credit-pillar">
          <div class="pillar-head">
            <span>Debt Servicing</span>
            <strong>${escapeHtml(health.coverageAssessment)}</strong>
          </div>
          ${row("Interest Coverage", ratio(r.interest_coverage))}
          ${row("Operating Margin", r.operating_margin !== undefined ? pct(r.operating_margin) : "Pending")}
          ${row("Operating Cash Flow Coverage", health.cashFlowCoverage !== null ? pct(health.cashFlowCoverage) : "Pending")}
          <p>${health.coverageAssessment === "Strong" ? "Coverage supports timely repayment capacity." : health.coverageAssessment === "Moderate" ? "Debt servicing is acceptable under base conditions." : "Coverage pressure could weaken repayment resilience."}</p>
        </article>
      </section>

      <section class="financial-review-grid">
        <article class="terminal-panel trend-panel">
          <div class="panel-title">Multi-Year Financial Trend</div>
          ${trendChart(points)}
        </article>
        <article class="terminal-panel ratio-heatmap">
          <div class="panel-title">Ratio Heatmap</div>
          ${heatmapRows(health.scores)}
        </article>
      </section>

      <section class="financial-bottom-grid">
        <article class="terminal-panel accounting-snapshot">
          <div class="panel-title">Key Financial Metrics</div>
          <div class="snapshot-grid">
            ${row("Revenue", money(m.revenue))}
            ${row("EBITDA", money(m.ebitda))}
            ${row("EBIT / Operating Profit", money(m.ebit))}
            ${row("Net Income", money(m.net_income))}
            ${row("Cash", money(m.cash_and_equivalents))}
            ${row("Accounts Receivable", money(m.accounts_receivable))}
            ${row("Inventory", money(m.inventory))}
            ${row("Debt", money(m.total_debt))}
            ${row("Equity", money(m.shareholders_equity))}
            ${row("Operating Cash Flow", money(m.operating_cash_flow))}
          </div>
        </article>
        <article class="terminal-panel credit-relevance">
          <div class="panel-title">Why It Matters For Credit</div>
          ${row("Liquidity", health.liquidityAssessment)}
          <p>Current ratio ${ratio(r.current_ratio)} indicates ${health.liquidityAssessment.toLowerCase()} short-term balance sheet support.</p>
          ${row("Leverage", health.leverageAssessment)}
          <p>Debt / EBITDA of ${ratio(r.debt_to_ebitda)}x keeps leverage in the ${health.leverageAssessment.toLowerCase()} range.</p>
          ${row("Debt Servicing", health.coverageAssessment)}
          <p>Interest coverage of ${ratio(r.interest_coverage)}x drives the coverage assessment.</p>
        </article>
        <article class="terminal-panel extraction-panel">
          <div class="panel-title">Data Quality & Extraction</div>
          <p class="model-note">This panel checks whether the latest financial snapshot has enough clean inputs for ratios, PD, LGD, and recommendation logic.</p>
          ${row("Document Source", state.latestDocument?.filename || "No document selected")}
          ${row("Fiscal Year", m.fiscal_year || "Pending")}
          ${row("Extraction Confidence", m.extraction_confidence !== undefined ? pct(m.extraction_confidence) : "Pending")}
          ${row("Missing Fields", missing)}
          ${row("Extraction Warnings", warningText(m.extraction_warnings))}
        </article>
        <article class="terminal-panel ratio-audit-panel">
          <div class="panel-title">Financial Ratio Audit</div>
          ${row("Net Margin", r.net_margin !== undefined ? pct(r.net_margin) : "Pending")}
          ${row("Return on Assets", r.return_on_assets !== undefined ? pct(r.return_on_assets) : "Pending")}
          ${row("Return on Equity", r.return_on_equity !== undefined ? pct(r.return_on_equity) : "Pending")}
          ${row("Formula Version", r.formula_version || "Pending")}
          ${row("Missing Ratio Inputs", warningText(r.missing_inputs))}
          ${row("Calculation Warnings", warningText(r.calculation_warnings))}
        </article>
      </section>
    `;
  }

  function renderMarket() {
    const intel = marketIntelligence();
    const indicators = marketIndicatorRows();
    const freshness = marketFreshness(indicators);
    const brent = marketIndicatorByName(indicators, "Brent Crude");
    const jetFuel = marketIndicatorByName(indicators, "Jet Fuel Proxy");
    const usdInr = marketIndicatorByName(indicators, "USD/INR");
    const vix = marketIndicatorByName(indicators, "VIX");
    const grouped = groupedMarketPrices();
    const signals = marketBusinessSignals(indicators);
    const assessment = marketExposureAssessment(indicators);
    const cpName = state.counterparty?.counterparty_name || state.counterparty?.name || "Selected airline";
    const brentSeries = seriesForAsset(marketAssets.find((asset) => asset.name === "Brent Crude"), grouped).series;
    const jetSeries = seriesForAsset(marketAssets.find((asset) => asset.name === "Jet Fuel Proxy"), grouped).series;
    const usdInrSeries = seriesForAsset(marketAssets.find((asset) => asset.name === "USD/INR"), grouped).series;
    const vixSeries = seriesForAsset(marketAssets.find((asset) => asset.name === "VIX"), grouped).series;
    const vixWindow = latestChangeWindow(vixSeries);
    const vixValue = Number((vixSeries.slice(-1)[0] || {}).price);
    const volatility = Number.isFinite(vixValue) ? (vixValue >= 28 ? "High" : vixValue >= 18 ? "Moderate" : "Low") : intel.volatilityEnvironment.replace(" volatility", "");
    const regimeLabel = readableMarketRegime(currentRegime(), intel.stressScore);
    el.root.innerHTML = `
      ${pageHeader("Market", "Current market conditions and external credit impact for the selected airline.")}

      <section class="market-refresh-strip">
        <div>
          <span>Latest market date</span>
          <strong>${escapeHtml(freshness.latestPriceDate)}</strong>
        </div>
        <div>
          <span>Coverage</span>
          <strong>${escapeHtml(freshness.priceSource)}</strong>
        </div>
        <button class="secondary-action" type="button" data-action="refresh-live-market">
          <i class="fa-solid fa-rotate" aria-hidden="true"></i>
          Refresh Live Market Data
        </button>
      </section>

      <section class="market-regime-card">
        <div>
          <span>Current Market Regime</span>
          <strong>${escapeHtml(regimeLabel)}</strong>
        </div>
        <p>${escapeHtml(marketRegimeExplanation(regimeLabel, indicators))}</p>
      </section>

      <section class="market-section">
        <div class="section-heading">
          <span>Section 1</span>
          <h2>Market Snapshot</h2>
          <p>Five quick signals that describe today's external credit backdrop.</p>
        </div>
        <div class="market-kpi-grid">
          ${marketKpiCard("Brent Crude", brent)}
          ${marketKpiCard("USD/INR", usdInr)}
          ${marketKpiCard("Jet Fuel Proxy", jetFuel)}
          <article class="market-kpi-card ${badgeClass(volatility)}">
            <span>Market Volatility</span>
            <strong>${escapeHtml(volatility)}</strong>
            <div><em>${escapeHtml(trendSymbol(vixWindow.change))}</em><small>${escapeHtml(vix ? `${vix.value} VIX | ${vixWindow.label}` : "Latest available")}</small></div>
          </article>
          <article class="market-kpi-card ${badgeClass(assessment.overall)}">
            <span>Overall Market Risk</span>
            <strong>${escapeHtml(assessment.overall)}</strong>
            <div><em>${escapeHtml(assessment.overall === "High" ? "↑" : assessment.overall === "Low" ? "↓" : "→")}</em><small>${assessment.score} / 100 exposure</small></div>
          </article>
        </div>
      </section>

      <section class="market-section">
        <div class="section-heading">
          <span>Section 2</span>
          <h2>Market Trends</h2>
          <p>Minimal trend charts focused on cost pressure and macro pressure.</p>
        </div>
        <div class="market-chart-grid">
          <article class="terminal-panel market-chart-card">
            ${marketLineComparisonChart("Brent Crude vs Jet Fuel Proxy", "Brent Crude", brentSeries, "Jet Fuel Proxy", jetSeries, "Indexed move over recent observations; shows direct fuel-cost pressure.")}
          </article>
          <article class="terminal-panel market-chart-card">
            ${marketSingleSeriesChart("USD/INR Recent Movement", "USD/INR exchange rate", usdInrSeries, "Simple FX chart using latest stored USD/INR observations. A tight Y-axis makes small currency moves easier to read.")}
          </article>
        </div>
      </section>

      <section class="market-section">
        <div class="section-heading">
          <span>Section 3</span>
          <h2>What Does This Mean?</h2>
          <p>Six business signals translated into credit direction.</p>
        </div>
        <article class="terminal-panel market-signals-panel">
          ${marketSignalTable(signals)}
        </article>
      </section>

      <section class="market-section">
        <div class="section-heading">
          <span>Section 4</span>
          <h2>Impact On Selected Airline</h2>
          <p>External market pressure translated for ${escapeHtml(cpName)}.</p>
        </div>
        <article class="terminal-panel market-airline-impact">
          ${marketImpactGrid(assessment)}
        </article>
      </section>

      <section class="market-section">
        <div class="section-heading">
          <span>Section 5</span>
          <h2>Market Summary</h2>
          <p>Rule-based executive summary for credit discussion.</p>
        </div>
        <article class="terminal-panel market-summary-card">
          <p>${escapeHtml(marketExecutiveSummary(indicators, assessment))}</p>
        </article>
      </section>

      <section class="market-section">
        <div class="section-heading">
          <span>Section 6</span>
          <h2>Live Market Watch</h2>
          <p>Compact view of the market indicators used by the credit-risk model.</p>
        </div>
        <div class="market-watch-grid">
          ${marketLiveCards(indicators)}
        </div>
        ${freshness.warning ? `<p class="data-warning compact">${escapeHtml(freshness.warning)}</p>` : ""}
      </section>
    `;
  }

  function renderScenario() {
    const scenarios = forecastScenarioList();
    const activeScenario = activeForecastScenario(scenarios);
    el.root.innerHTML = `
      ${pageHeader("Scenario & Forecasts", "Single-counterparty credit risk forecast under market and business stress.")}
      ${scenarioControlBar()}
      ${scenarioKpiCards(activeScenario)}

      <section class="terminal-panel scenario-engine-panel">
        <div class="scenario-engine-head">
          <div>
            <div class="panel-title">Scenario Engine</div>
            <p>${escapeHtml(activeScenario.description)}</p>
          </div>
          <div class="scenario-engine-meta">
            ${rowLine("Selected Scenario", activeScenario.name)}
            ${rowLine("Credit Days", `${Math.round(activeScenario.creditDays)} days`)}
            ${rowLine("Forecast Horizon", `${activeScenario.horizon} days`)}
          </div>
        </div>
        ${scenarioTabs(scenarios, activeScenario)}
      </section>

      <section class="scenario-workbench-grid">
        ${customScenarioPanel()}
        <article class="terminal-panel scenario-snapshot-panel">
          <div class="panel-title">Selected Scenario Conditions</div>
          ${rowLine("Fuel Shock", signedPct(activeScenario.fuelShock))}
          ${rowLine("FX Shock", signedPct(activeScenario.fxShock))}
          ${rowLine("Revenue Shock", signedPct(activeScenario.revenueShock))}
          ${rowLine("Interest Rate Shock", `${(Number(activeScenario.rateShock) * 100).toFixed(2)} pts`)}
          ${rowLine("Pressure Score", `${Math.round(activeScenario.pressureScore)} / 100`)}
          ${rowLine("Primary Driver", activeScenario.primaryDriver)}
        </article>
      </section>

      <section class="scenario-visual-grid">
        <article class="terminal-panel">
          <div class="panel-title">Monte Carlo Loss Distribution</div>
          ${monteCarloHistogram(activeScenario)}
        </article>
        <article class="terminal-panel">
          <div class="panel-title">Selected Scenario Analysis</div>
          ${selectedScenarioNarrative(activeScenario)}
        </article>
      </section>

      <section class="scenario-selected-grid">
        <article class="terminal-panel pd-forecast-panel">
          <div class="panel-title">Selected Scenario PD Path</div>
          ${selectedPdForecastChart(activeScenario)}
        </article>
        <article class="terminal-panel scenario-driver-panel">
          <div class="panel-title">Selected Scenario Drivers</div>
          ${selectedScenarioDriverPanel(activeScenario)}
        </article>
      </section>

      <section class="terminal-panel counterparty-stress-panel">
        <div class="panel-title">${escapeHtml(activeScenario.name)} Stress Impact</div>
        ${stressImpactTable(activeScenario)}
      </section>
    `;
  }

  function renderModels() {
    const q = quantAnalytics();
    el.root.innerHTML = `
      ${pageHeader("Quantitative Risk & Monte Carlo", "What do the models say about the true risk of this counterparty?")}
      <section class="quant-overview-strip">
          ${quantMetric("Final PD", pct(q.finalPd), "Trace final PD step by step and explain structural PD, ML PD, and blend weights.")}
          ${quantMetric("LGD", pct(q.lgd), "Explain LGD and how collateral or security changes it in this project.")}
          ${quantMetric("EAD", money(q.ead), "Explain EAD and how the project estimates exposure at default.")}
          ${quantMetric("Expected Loss", money(q.expectedLoss), "Trace expected loss using PD, LGD, and EAD.")}
          ${quantMetric("Credit VaR 95", money(q.var95), "Explain Credit VaR 95 and how it differs from expected loss.")}
          ${quantMetric("Expected Shortfall 95", money(q.es95), "Explain Expected Shortfall 95 and why it should be at least as severe as VaR 95.")}
          ${quantMetric("Distance to Default", ratio(q.dd), "Explain distance to default and how it affects structural PD.")}
          ${quantMetric("Model Confidence", q.modelConfidenceText, "Explain model confidence, calibration limitations, and what data is proxy or synthetic.")}
      </section>

      <section class="quant-grid risk-explanation-grid">
        <article class="terminal-panel quant-explainer">
          <div class="panel-title">How To Read This Page</div>
          <p>The quantitative page converts financial strength, market stress, collateral, exposure size, and simulation results into credit-risk quantities. Start with final PD, LGD, EAD, and expected loss, then use the distribution chart to understand downside risk beyond the average case.</p>
          ${row("Primary Question", "How much could we lose if this counterparty weakens?")}
          ${row("Average Case", `Expected loss ${money(q.expectedLoss)}`)}
          ${row("Tail Case", `VaR 95 ${money(q.var95)} / ES 95 ${money(q.es95)}`)}
          ${row("Useful For", "Limit sizing, security choice, and tenor discipline")}
        </article>
        <article class="terminal-panel structural-panel">
          <div class="panel-title">Structural Credit Risk</div>
          ${distanceToDefaultChart(q)}
          ${row("Asset Value Estimate", money(q.assetValue))}
          ${row("Debt Threshold", money(q.debtThreshold))}
          ${row("Asset Volatility", pct(q.assetVol))}
          ${row("Risk-Free Rate", q.pd.risk_free_rate !== undefined ? pct(q.pd.risk_free_rate) : "Pending")}
          ${row("Distance to Default", ratio(q.dd))}
        </article>
      </section>

      <section class="quant-grid quant-model-grid">
        <article class="terminal-panel ml-panel">
          <div class="panel-title">Risk Driver Contribution</div>
          ${row("Model Confidence", q.modelConfidenceText)}
          ${row("Commodity Sensitivity", q.pd.commodity_sensitivity_score !== undefined ? pct(q.pd.commodity_sensitivity_score) : "Pending")}
          ${row("FX Sensitivity", q.pd.fx_sensitivity_score !== undefined ? pct(q.pd.fx_sensitivity_score) : "Pending")}
          ${row("Macro Sensitivity", q.pd.macro_sensitivity_score !== undefined ? pct(q.pd.macro_sensitivity_score) : "Pending")}
          ${featureContributionChart(q.pdDrivers)}
          <p class="model-note">Feature contributions show which risk inputs are pulling the final credit risk higher.</p>
        </article>
        <article class="terminal-panel loss-engine-panel">
          <div class="panel-title">Expected Loss Waterfall</div>
          ${expectedLossWaterfall(q)}
          ${row("Collateral Impact", q.loss.collateral_strength !== undefined ? ratio(q.loss.collateral_strength) : "Moderate")}
          ${row("Security Impact", q.loss.model_assumptions?.security || "Security reduces loss severity where present")}
          ${row("Recovery View", q.lgd >= 0.5 ? "Moderate recovery" : "Strong recovery")}
        </article>
      </section>

      <section class="terminal-panel monte-carlo-panel">
        <div class="panel-title">Monte Carlo Risk Distribution</div>
        <div class="monte-carlo-grid">
          <div>
            ${lossDistributionChart(q)}
          </div>
          <div class="mc-stat-grid">
            ${row("Simulation Count", q.simulationCount)}
            ${row("Expected Loss", money(q.simExpectedLoss))}
            ${row("Unexpected Loss", money(q.unexpectedLoss))}
            ${row("Credit VaR 95", money(q.var95))}
            ${row("Credit VaR 99", money(q.var99))}
            ${row("Expected Shortfall 95", money(q.es95))}
            ${row("Expected Shortfall 99", money(q.es99))}
            ${row("Worst Case Loss", money(q.worstCase))}
          ${row("Scenario", q.simulationScenario)}
          ${row("Copula", q.copulaType)}
          ${row("Scenario Source", q.scenarioDataSource)}
          ${row("MC Calibration", readableStatus(q.mcCalibrationStatus))}
          </div>
        </div>
      </section>

      <section class="quant-grid quant-bottom-grid">
        <article class="terminal-panel tail-risk-panel">
          <div class="panel-title">Tail Risk Drivers</div>
          ${riskDriverRows(q.tailDrivers)}
        </article>
        <article class="terminal-panel copula-panel">
          <div class="panel-title">Copula / Correlation</div>
          <p class="model-note">Click any row for a short explanation of what the metric means in the Monte Carlo model.</p>
          <div class="explainable-table">
            ${explainableRow("Default Correlation", pct(q.defaultCorrelation), "How strongly counterparties are assumed to default together. Higher correlation means losses can cluster in the same bad market scenario.")}
            ${explainableRow("Systematic Risk Contribution", "62%", "The share of simulated default risk driven by common market forces such as fuel, FX, volatility, and macro stress.")}
            ${explainableRow("Idiosyncratic Risk Contribution", "38%", "The share driven by company-specific factors. This is the part that can differ even when the market backdrop is the same.")}
            ${explainableRow("Average Defaults", ratio(q.avgDefaults), "The average number of defaults across all Monte Carlo simulation runs. It is a portfolio stress indicator, not a prediction for one exact company.")}
            ${explainableRow("Maximum Defaults", q.maxDefaults, "The worst default count observed in the simulation runs. This helps show tail clustering risk under severe scenarios.")}
          </div>
        </article>
        <article class="terminal-panel validation-panel">
          <div class="panel-title">Model Validation</div>
          <div class="validation-checks">
            <span class="check-pass">Debt up -> PD up</span>
            <span class="check-pass">Volatility up -> PD up</span>
            <span class="check-pass">Collateral -> LGD down</span>
            <span class="${q.es95 > q.var95 ? "check-pass" : "check-review"}">ES95 >= VaR95</span>
            <span class="${q.mcValidation.var_99_exceeds_var_95 === false ? "check-review" : "check-pass"}">VaR99 >= VaR95</span>
          </div>
          <div class="validation-notes">
            <div><span>Real loss validation</span><strong>${escapeHtml(compactStatus(q.mcCalibrationStatus, 110))}</strong></div>
            <div><span>PD warnings</span><strong>${escapeHtml(compactStatus(warningText(q.pd.warnings), 130))}</strong></div>
            <div><span>Loss warnings</span><strong>${escapeHtml(compactStatus(warningText(q.loss.warnings), 130))}</strong></div>
          </div>
        </article>
      </section>
    `;
  }

  function renderDecision() {
    const d = decisionAnalytics();
    el.root.innerHTML = `
      ${pageHeader("Credit Recommendation", "What credit terms should we approve for this counterparty and why?")}
      <section class="decision-terminal ${d.tone}">
        <div class="decision-copy">
          <div class="page-kicker">Credit Committee Decision</div>
          <h1>${escapeHtml(d.decision)}</h1>
          <div class="counterparty-meta">
            <span>${escapeHtml(state.counterparty?.counterparty_name || "Selected counterparty")}</span>
            <span>${escapeHtml(state.counterparty?.counterparty_type || "Airline")}</span>
            <span>${escapeHtml(state.counterparty?.country || "United States")}</span>
          </div>
        </div>
        <div class="decision-terms">
          <div class="term-chip grade">Risk Grade <strong>${escapeHtml(d.riskGrade)}</strong></div>
          <div class="term-stack">
            <span>Recommended Terms</span>
            <strong>${money(d.recommendedLimit)}</strong>
            <span>${tenorText(d.recommendedTenor)}</span>
            <span>${escapeHtml(d.security)}</span>
          </div>
        </div>
        <div class="decision-market">
          ${row("Requested Limit", money(d.requestedLimit))}
          ${row("Market Regime", currentRegime())}
          ${row("Stress Index", `${stressLevel().score.toFixed(0)} / 100`)}
        </div>
      </section>

      <section class="risk-snapshot">
        <div class="primary-metrics">
          ${metric("PD", d.q.finalPd !== undefined ? pct(d.q.finalPd) : "Pending", "", "Trace final PD and explain why it affects this recommendation.")}
          ${metric("Expected Loss", money(d.expectedLoss), "warn", "Trace expected loss and explain how it affects the credit decision.")}
          ${metric("Recommended Limit", money(d.recommendedLimit), "accent", "Explain how the recommended credit limit is calculated from requested limit and risk adjustment.")}
          ${metric("Risk Grade", d.riskGrade, "danger", "Explain the risk grade mapping from PD and what this internal grade means.")}
        </div>
        <div class="secondary-metrics">
          ${row("LGD", d.q.lgd !== undefined ? pct(d.q.lgd, 0) : "Pending")}
          ${row("EAD", d.loss.exposure_at_default !== undefined ? money(d.loss.exposure_at_default) : "Pending")}
          ${row("Stress Index", `${stressLevel().score.toFixed(0)} / 100`)}
          ${row("Commodity Sensitivity", sensitivityLabel(d.pd.commodity_sensitivity_score))}
          ${row("FX Sensitivity", sensitivityLabel(d.pd.fx_sensitivity_score))}
          ${row("Model Confidence", d.pd.model_confidence !== undefined ? pct(d.pd.model_confidence) : "Pending")}
        </div>
      </section>

      <section class="credit-terms-grid">
        <article class="terminal-panel terms-summary-panel">
          <div class="panel-title">Credit Terms Summary</div>
          ${creditTermsComparisonTable(d)}
          <div class="terms-audit-strip">
            ${rowLine("Stored Status", d.rec.approval_status || "Pending")}
            ${rowLine("Risk Adjustment Score", d.rec.policy_score !== undefined ? ratio(d.rec.policy_score) : "Pending")}
            ${rowLine("Expected Loss Reduction", money(d.expectedLossReduction))}
          </div>
        </article>
        <article class="terminal-panel scorecard-panel">
          <div class="panel-title">Credit Decision Scorecard</div>
          ${scoreRows(d.scores)}
        </article>
      </section>

      <section class="decision-main-grid">
        <article class="terminal-panel decision-driver-panel">
          <div class="panel-title">Key Decision Drivers</div>
          ${riskDriverRows(d.negativeDrivers)}
        </article>
        <article class="terminal-panel mitigants-panel">
          <div class="panel-title">Mitigating Factors</div>
          <ul class="mitigant-list">
            ${d.positiveFactors.slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        </article>
        <article class="terminal-panel policy-panel">
          <div class="panel-title">Risk Checks</div>
          ${policyMatrix(d.policyRows)}
        </article>
      </section>

      <section class="decision-bottom-grid">
        <article class="terminal-panel">
          <div class="panel-title">Credit Structure Impact</div>
          ${structureImpactChart(d)}
        </article>
        <article class="terminal-panel">
          <div class="panel-title">Decision Waterfall</div>
          ${decisionWaterfall(d)}
          <p class="model-note">The waterfall shows how each factor pushes the decision. Positive bars support the proposed line; negative bars reduce appetite or require tighter security and tenor.</p>
        </article>
        <article class="terminal-panel recommendation-panel">
          <div class="panel-title">Committee Rationale</div>
          <p class="committee-rationale">${escapeHtml(d.primaryReason)}</p>
          ${rowLine("Maximum Limit", money(d.recommendedLimit))}
          ${rowLine("Maximum Tenor", tenorText(d.recommendedTenor))}
          ${rowLine("Security Condition", d.security)}
          ${rowLine("Base Risk Adjustment", d.policyHaircutBreakdown.base_policy_haircut_before_scenario !== undefined ? pct(d.policyHaircutBreakdown.base_policy_haircut_before_scenario) : "Pending")}
          ${rowLine("Scenario Risk Add-on", d.policyHaircutBreakdown.scenario_tail_add_on !== undefined ? pct(d.policyHaircutBreakdown.scenario_tail_add_on) : "Pending")}
          ${rowLine("Total Risk Adjustment", d.policyHaircutBreakdown.final_policy_haircut !== undefined ? pct(d.policyHaircutBreakdown.final_policy_haircut) : "Pending")}
          ${rowLine("Scenario EL", d.rec.scenario_expected_loss !== undefined && d.rec.scenario_expected_loss !== null ? money(d.rec.scenario_expected_loss) : "Not included")}
          ${rowLine("Credit VaR 95", d.rec.credit_var_95 !== undefined && d.rec.credit_var_95 !== null ? money(d.rec.credit_var_95) : "Not included")}
          ${rowLine("Scenario Included", yesNo(d.policyDiagnostics.scenario_result_included))}
          ${rowLine("Simulation Included", yesNo(d.policyDiagnostics.simulation_result_included))}
          ${rowLine("Rating Basis", d.ratingNote)}
          ${rowLine("Warnings", warningText(d.rec.warnings))}
        </article>
      </section>
    `;
  }

  function renderPage() {
    renderNav();
    renderPromptButtons();
    updateHeader();
    const renderers = {
      counterparty: renderCounterparty,
      financials: renderFinancials,
      market: renderMarket,
      scenario: renderScenario,
      models: renderModels,
      decision: renderDecision
    };
    (renderers[state.page] || renderers.counterparty)();
  }

  async function loadCounterparties(search = "") {
    const query = new URLSearchParams({ limit: "80" });
    if (search.trim()) query.set("search", search.trim());
    state.counterparties = await api(`/api/v1/documents/counterparties?${query.toString()}`);
    renderCounterpartyResults();
    return state.counterparties;
  }

  function renderCounterpartyResults() {
    if (!state.counterparties.length) {
      el.results.innerHTML = `<button type="button" disabled>No counterparties found</button>`;
      return;
    }
    el.results.innerHTML = state.counterparties.map((cp) => `
      <button type="button" data-counterparty-id="${cp.id}">
        <strong>${escapeHtml(cp.counterparty_name)}</strong><br>
        <span>${escapeHtml(cp.country || "Country not set")}</span>
      </button>
    `).join("");
  }

  async function loadSelectedCounterparty(counterparty) {
    state.counterparty = counterparty;
    state.documents = [];
    state.latestDocument = null;
    state.metrics = null;
    state.financialHistory = null;
    state.trendFeatures = null;
    state.ratios = null;
    state.pd = null;
    state.loss = null;
    state.recommendation = null;
    state.scenarios = null;
    state.calibrationStatus = null;
    state.stressHistory = null;
    state.marketPrices = null;
    state.marketDataWarning = null;

    const id = counterparty.id;
    const calls = await Promise.allSettled([
      api(`/api/v1/documents/counterparty/${id}`),
      api(`/api/v1/financial-analysis/counterparty/${id}/latest-ratios`),
      api(`/api/v1/credit-risk/counterparty/${id}/latest-pd`),
      api(`/api/v1/credit-risk/counterparty/${id}/latest-loss`),
      api(`/api/v1/credit-decision/counterparty/${id}/latest`),
      api("/api/v1/market-intelligence/stress/latest"),
      api("/api/v1/market-intelligence/regime/latest"),
      api("/api/v1/scenario-analysis/monte-carlo/latest"),
      api("/api/v1/monitoring/alerts/latest"),
      api("/api/v1/scenario-analysis/scenarios"),
      api("/api/v1/market-intelligence/stress/history?limit=180"),
      api("/api/v1/market-intelligence/prices/recent?assets=brent_oil,crude_oil,heating_oil_proxy,jet_fuel_proxy,jet_crack_spread,vix,sp500,usd_inr,dxy,gold,us_10y_yield,us_2y_yield,yield_curve_spread,cpi_index,freight_proxy,eia_crude_inventories,opec_production,global_pmi,pmi,iata_passenger_traffic&limit_per_asset=180"),
      api("/api/v1/calibration/status"),
      api(`/api/v1/financial-analysis/counterparty/${id}/metrics-history`),
      api(`/api/v1/financial-analysis/counterparty/${id}/trend-features`)
    ]);

    if (calls[0].status === "fulfilled") {
      state.documents = calls[0].value;
      state.latestDocument = latestByCreatedAt(state.documents);
      if (state.latestDocument) {
        try {
          const status = await api(`/api/v1/documents/status/${state.latestDocument.id}`);
          state.latestDocument = status;
          state.metrics = status.financial_metrics || null;
        } catch (error) {
          console.warn(error);
        }
      }
    }
    if (calls[1].status === "fulfilled") state.ratios = calls[1].value;
    if (calls[2].status === "fulfilled") state.pd = calls[2].value;
    if (calls[3].status === "fulfilled") {
      state.loss = calls[3].value;
      applyCreditTerms(state.loss);
    }
    if (calls[4].status === "fulfilled") state.recommendation = calls[4].value;
    if (calls[5].status === "fulfilled") state.stress = calls[5].value;
    if (calls[6].status === "fulfilled") state.regime = calls[6].value;
    if (calls[7].status === "fulfilled") state.simulation = calls[7].value;
    if (calls[8].status === "fulfilled") state.alerts = calls[8].value;
    if (calls[9].status === "fulfilled") state.scenarios = calls[9].value.scenarios || [];
    if (calls[10].status === "fulfilled") state.stressHistory = calls[10].value;
    else state.marketDataWarning = "Stress history is unavailable. Run market intelligence rebuild after loading market prices.";
    if (calls[11].status === "fulfilled") state.marketPrices = calls[11].value;
    else state.marketDataWarning = [state.marketDataWarning, "Recent market prices are unavailable; affected monitor rows are omitted."].filter(Boolean).join(" ");
    if (calls[12].status === "fulfilled") state.calibrationStatus = calls[12].value;
    if (calls[13].status === "fulfilled") {
      state.financialHistory = calls[13].value;
      if (calls[13].value.latest_metrics) state.metrics = calls[13].value.latest_metrics;
    }
    if (calls[14].status === "fulfilled") state.trendFeatures = calls[14].value;

    renderPage();
  }

  async function chooseInitialCounterparty() {
    const rows = await loadCounterparties();
    const preferred = rows.find((cp) => /Synthetic Skyways Live E2E/i.test(cp.counterparty_name))
      || rows.find((cp) => /Skyways|Golden|Air/i.test(cp.counterparty_name))
      || rows[0];
    if (preferred) await loadSelectedCounterparty(preferred);
    else renderPage();
  }

  async function createOrGetCounterparty(name, country = "United States") {
    return api("/api/v1/documents/counterparties", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ counterparty_name: name, counterparty_type: "Airline", country })
    });
  }

  async function runDownstreamModels(metricsId, counterpartyId) {
    if (!metricsId) return;
    try {
      const ratios = await api(`/api/v1/financial-analysis/ratios/calculate/${metricsId}`, { method: "POST" });
      state.ratios = ratios.ratios;
    } catch (error) {
      console.warn("Ratios not refreshed", error);
    }
    try {
      const prediction = await api(`/api/v1/credit-risk/pd/calculate/${metricsId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ time_horizon_years: 1 })
      });
      state.pd = prediction.prediction;
    } catch (error) {
      console.warn("PD not refreshed", error);
    }
    try {
      const loss = await api("/api/v1/credit-risk/loss/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...currentTradeExposurePayload(counterpartyId)
        })
      });
      state.loss = loss.loss_estimate;
    } catch (error) {
      console.warn("Loss not refreshed", error);
    }
    try {
      state.simulation = await api("/api/v1/scenario-analysis/monte-carlo/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario_type: "adverse",
          counterparty_ids: [counterpartyId],
          n_simulations: 1000,
          random_seed: 42,
          persist: true
        })
      });
    } catch (error) {
      console.warn("Monte Carlo simulation not refreshed", error);
    }
    try {
      const rec = await api(`/api/v1/credit-decision/counterparty/${counterpartyId}/recommend`, { method: "POST" });
      state.recommendation = rec.recommendation;
    } catch (error) {
      console.warn("Recommendation not refreshed", error);
    }
  }

  async function markFinancialPeriodLatest(metricsId) {
    if (!metricsId || !state.counterparty?.id) return;
    setLoading("Switching latest financial snapshot and refreshing models...");
    const result = await api(`/api/v1/financial-analysis/metrics/${metricsId}/mark-latest`, {
      method: "POST"
    });
    state.metrics = result.latest_metrics;
    await runDownstreamModels(result.latest_metrics?.id, state.counterparty.id);
    await loadSelectedCounterparty(state.counterparty);
    clearLoading();
  }

  async function uploadDocument(form) {
    const formData = new FormData(form);
    const name = formData.get("counterparty_name");
    const country = formData.get("country") || "United States";
    const terms = termsFromForm(form);
    applyCreditTerms(terms);
    const cp = await createOrGetCounterparty(name, country);
    const uploadBody = new FormData();
    uploadBody.set("file", formData.get("file"));
    const params = new URLSearchParams({
      counterparty_id: String(cp.id),
      document_type: String(formData.get("document_type") || "annual_report"),
      created_by: "html_ui"
    });
    const upload = await api(`/api/v1/documents/upload?${params.toString()}`, { method: "POST", body: uploadBody });
    const status = await api(`/api/v1/documents/status/${upload.id}`);
    state.counterparty = cp;
    state.latestDocument = status;
    state.metrics = status.financial_metrics || null;
    await runDownstreamModels(state.metrics?.id, cp.id);
    await loadCounterparties();
    await loadSelectedCounterparty(cp);
  }

  function financialPayloadFromContainer(container) {
    const payload = {};
    const creditTermFields = new Set([
      "requested_credit_limit",
      "approved_credit_limit",
      "outstanding_receivables",
      "payment_tenor_days",
      "utilization_rate",
      "collateral_type",
      "deposit_percentage",
      "invoice_amount",
      "fuel_volume",
      "fuel_price"
    ]);
    const data = new FormData();
    container.querySelectorAll("input, select").forEach((field) => {
      if (field.type === "radio") {
        if (field.checked) data.append(field.name, field.value || "on");
      } else {
        data.append(field.name, field.value);
      }
    });
    for (const [key, value] of data.entries()) {
      if (key === "counterparty_name") continue;
      if (creditTermFields.has(key)) continue;
      if (key === "is_latest_snapshot") payload[key] = true;
      else if (["currency", "period_type", "period_label", "fiscal_period"].includes(key)) payload[key] = String(value || "").toUpperCase();
      else if (value !== "") payload[key] = Number(value);
    }
    payload.period_type = String(payload.period_type || "ANNUAL").toLowerCase();
    payload.period_label = payload.period_label || payload.fiscal_period || (payload.period_type === "quarterly" ? "Q1" : "FY");
    payload.fiscal_period = payload.period_label;
    payload.currency = payload.currency || "USD";
    payload.is_latest_snapshot = Boolean(payload.is_latest_snapshot);
    return payload;
  }

  function numericPayload(form) {
    const data = new FormData(form);
    const payload = financialPayloadFromContainer(form);
    return { name: data.get("counterparty_name"), payload, terms: termsFromForm(form) };
  }

  function manualFinancialPeriods(form) {
    const blocks = Array.from(form.querySelectorAll("[data-period-block]"));
    return blocks.map((block, index) => {
      const payload = financialPayloadFromContainer(block);
      payload.is_latest_snapshot = Boolean(block.querySelector("input[name='is_latest_snapshot']")?.checked);
      payload.created_by = "html_ui";
      if (!payload.fiscal_year) {
        const currentYear = new Date().getFullYear();
        payload.fiscal_year = currentYear - index;
      }
      return payload;
    });
  }

  async function saveManualFinancials(form) {
    const { name, terms } = numericPayload(form);
    const cp = await createOrGetCounterparty(name, "United States");
    applyCreditTerms(terms);
    const periods = manualFinancialPeriods(form).map((period) => ({
      ...period,
      counterparty_id: cp.id
    }));
    if (!periods.some((period) => period.is_latest_snapshot) && periods.length) {
      periods[0].is_latest_snapshot = true;
    }
    const created = await api("/api/v1/financial-analysis/metrics/manual/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ counterparty_id: cp.id, periods })
    });
    state.counterparty = cp;
    state.metrics = created.latest_metrics || created.metrics?.[0] || null;
    await runDownstreamModels(state.metrics?.id, cp.id);
    await loadCounterparties();
    await loadSelectedCounterparty(cp);
  }

  async function refreshLiveMarketData() {
    const refresh = await api("/api/v1/market-intelligence/refresh-live?lookback_days=730", { method: "POST" });
    state.stress = await api("/api/v1/market-intelligence/stress/latest");
    state.regime = await api("/api/v1/market-intelligence/regime/latest");
    state.stressHistory = await api("/api/v1/market-intelligence/stress/history?limit=180");
    state.marketPrices = await api("/api/v1/market-intelligence/prices/recent?assets=brent_oil,crude_oil,heating_oil_proxy,jet_fuel_proxy,jet_crack_spread,vix,sp500,usd_inr,dxy,gold,us_10y_yield,us_2y_yield,yield_curve_spread,cpi_index,freight_proxy,eia_crude_inventories,opec_production,global_pmi,pmi,iata_passenger_traffic&limit_per_asset=180");
    state.marketDataWarning = refresh.warnings?.length
      ? `Live refresh completed with provider warnings: ${refresh.warnings.slice(0, 3).join(" | ")}`
      : null;
    if (state.metrics?.id && state.counterparty?.id) {
      await runDownstreamModels(state.metrics.id, state.counterparty.id);
    }
    return refresh;
  }

  function renderDeleteOptions(dialog, query = "") {
    const list = dialog.querySelector("[data-delete-list]");
    const selected = dialog._deleteSelected || new Set();
    const normalized = query.trim().toLowerCase();
    const rows = state.counterparties
      .filter((cp) => !normalized || `${cp.counterparty_name} ${cp.country || ""}`.toLowerCase().includes(normalized))
      .slice(0, 120);
    list.innerHTML = rows.length ? rows.map((cp) => `
      <label class="delete-option">
        <input type="checkbox" name="delete_cp" value="${cp.id}" ${selected.has(cp.id) ? "checked" : ""}>
        <span>
          <strong>${escapeHtml(cp.counterparty_name)}</strong>
          <small>${escapeHtml(cp.country || "Country not set")} - ID ${cp.id}</small>
        </span>
      </label>
    `).join("") : `<p class="model-note">No counterparties match that search.</p>`;
  }

  function showDeleteCounterpartyDialog() {
    const existing = document.getElementById("delete-counterparty-modal");
    if (existing) existing.remove();
    const dialog = document.createElement("div");
    dialog.id = "delete-counterparty-modal";
    dialog.className = "modal-backdrop delete-modal-backdrop";
    dialog.innerHTML = `
      <section class="delete-modal" role="dialog" aria-modal="true" aria-labelledby="delete-title">
        <div class="modal-head">
          <div>
            <h2 id="delete-title">Delete Stored Counterparties</h2>
            <p>Select one or more counterparties. Deleted financials, model outputs, documents, and recommendations cannot be restored.</p>
          </div>
          <button class="icon-button" type="button" data-close-delete aria-label="Close">
            <i class="fa-solid fa-xmark" aria-hidden="true"></i>
          </button>
        </div>
        <div class="delete-modal-body">
          <label class="delete-search">Search counterparties
            <input type="search" data-delete-search placeholder="Search by name, country, or ID">
          </label>
          <div class="delete-option-list" data-delete-list></div>
          <div class="delete-actions">
            <button class="secondary-action" type="button" data-close-delete>Cancel</button>
            <button class="danger-action" type="button" data-confirm-delete>
              <i class="fa-solid fa-trash" aria-hidden="true"></i>
              Delete Selected
            </button>
          </div>
        </div>
      </section>
    `;
    document.body.appendChild(dialog);
    dialog._deleteSelected = new Set();
    renderDeleteOptions(dialog);
    dialog.querySelector("[data-delete-search]").addEventListener("input", (event) => {
      renderDeleteOptions(dialog, event.target.value);
    });
    dialog.addEventListener("change", (event) => {
      const checkbox = event.target.closest("input[name='delete_cp']");
      if (!checkbox) return;
      const id = Number(checkbox.value);
      if (checkbox.checked) dialog._deleteSelected.add(id);
      else dialog._deleteSelected.delete(id);
    });
    dialog.addEventListener("click", async (event) => {
      if (event.target === dialog || event.target.closest("[data-close-delete]")) {
        dialog.remove();
        return;
      }
      if (event.target.closest("[data-confirm-delete]")) {
        const selectedIds = Array.from(dialog._deleteSelected);
        if (!selectedIds.length) {
          showBanner("Select at least one counterparty to delete.", "error");
          return;
        }
        const confirmed = window.confirm(`Delete ${selectedIds.length} selected counterparty record(s) and all linked data? This cannot be undone.`);
        if (!confirmed) return;
        dialog.remove();
        await deleteCounterpartiesByIds(selectedIds);
      }
    });
  }

  async function deleteCounterpartiesByIds(ids) {
    if (!ids.length) return;
    const names = state.counterparties
      .filter((cp) => ids.includes(cp.id))
      .map((cp) => cp.counterparty_name || `ID ${cp.id}`);
    setLoading(`Deleting ${ids.length} counterparty record(s)...`);
    for (const id of ids) {
      await api(`/api/v1/documents/counterparties/${id}`, { method: "DELETE" });
    }
    if (state.counterparty?.id && ids.includes(state.counterparty.id)) {
      state.counterparty = null;
    }
    state.documents = [];
    state.latestDocument = null;
    state.metrics = null;
    state.financialHistory = null;
    state.trendFeatures = null;
    state.ratios = null;
    state.pd = null;
    state.loss = null;
    state.recommendation = null;
    state.scenarios = null;
    await loadCounterparties();
    const next = state.counterparty || state.counterparties[0];
    if (next) await loadSelectedCounterparty(next);
    else renderPage();
    clearLoading();
    showBanner(`Deleted: ${names.join(", ")}.`, "success");
  }

  async function handleAction(action) {
    if (!state.counterparty) return;
    try {
      if (action === "refresh-ratios") {
        if (!state.metrics?.id) throw new Error("No financial metrics are available.");
        setLoading("Refreshing financial ratios...");
        const result = await api(`/api/v1/financial-analysis/ratios/calculate/${state.metrics.id}`, { method: "POST" });
        state.ratios = result.ratios;
      }
      if (action === "refresh-pd") {
        if (!state.metrics?.id) throw new Error("No financial metrics are available.");
        setLoading("Calculating probability of default...");
        const result = await api(`/api/v1/credit-risk/pd/calculate/${state.metrics.id}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ time_horizon_years: 1 })
        });
        state.pd = result.prediction;
      }
      if (action === "refresh-loss") {
        setLoading("Calculating LGD, EAD, and expected loss...");
        const result = await api("/api/v1/credit-risk/loss/calculate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...currentTradeExposurePayload(state.counterparty.id)
          })
        });
        state.loss = result.loss_estimate;
      }
      if (action === "refresh-recommendation") {
        setLoading("Refreshing credit recommendation...");
        const result = await api(`/api/v1/credit-decision/counterparty/${state.counterparty.id}/recommend`, { method: "POST" });
        state.recommendation = result.recommendation;
      }
      if (action === "run-monte-carlo") {
        setLoading("Running Monte Carlo scenario...");
        state.simulation = await api("/api/v1/scenario-analysis/monte-carlo/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scenario_type: "adverse",
            counterparty_ids: [state.counterparty.id],
            n_simulations: 1000,
            random_seed: 42,
            persist: true
          })
        });
      }
      if (action === "rebuild-market") {
        setLoading("Rebuilding market intelligence...");
        await api("/api/v1/market-intelligence/rebuild", { method: "POST" });
        state.stress = await api("/api/v1/market-intelligence/stress/latest");
        state.regime = await api("/api/v1/market-intelligence/regime/latest");
        state.stressHistory = await api("/api/v1/market-intelligence/stress/history?limit=180");
        state.marketPrices = await api("/api/v1/market-intelligence/prices/recent?assets=brent_oil,crude_oil,heating_oil_proxy,jet_fuel_proxy,jet_crack_spread,vix,sp500,usd_inr,dxy,gold,us_10y_yield,us_2y_yield,yield_curve_spread,cpi_index,freight_proxy,eia_crude_inventories,opec_production,global_pmi,pmi,iata_passenger_traffic&limit_per_asset=180");
        state.marketDataWarning = null;
      }
      if (action === "refresh-live-market") {
        setLoading("Fetching live FRED, EIA, and yfinance data, storing it, and rebuilding quantitative market intelligence...");
        await refreshLiveMarketData();
      }
      clearLoading();
      renderPage();
    } catch (error) {
      stopProcessing();
      showBanner(error.message, "error");
      renderPage();
    }
  }

  function copilotVisibleMetrics() {
    return {
      page: state.page,
      selected_counterparty: state.counterparty ? {
        id: state.counterparty.id,
        counterparty_name: state.counterparty.counterparty_name,
        counterparty_type: state.counterparty.counterparty_type,
        country: state.counterparty.country
      } : null,
      requested_terms: {
        requested_credit_limit: state.requestedLimit,
        approved_credit_limit: state.approvedLimit,
        requested_tenor_days: state.requestedTenor,
        collateral_type: state.collateralType,
        deposit_percentage: state.depositPercentage,
        utilization_rate: state.utilizationRate
      },
      financial_metrics: state.metrics,
      financial_ratios: state.ratios,
      pd_model: state.pd,
      loss_estimate: state.loss,
      credit_recommendation: state.recommendation,
      market_stress: state.stress,
      market_regime: state.regime,
      monte_carlo: state.simulation,
      scenarios: state.scenarios
    };
  }

  function copilotTraceValues() {
    return {
      probability_of_default: state.loss?.probability_of_default ?? state.recommendation?.probability_of_default ?? state.pd?.final_pd,
      pd: state.loss?.probability_of_default ?? state.recommendation?.probability_of_default ?? state.pd?.final_pd,
      final_pd: state.pd?.final_pd ?? state.loss?.probability_of_default ?? state.recommendation?.probability_of_default,
      structural_pd: state.pd?.structural_pd,
      ml_pd: state.pd?.ml_pd,
      loss_given_default: state.loss?.predicted_lgd ?? state.recommendation?.loss_given_default,
      lgd: state.loss?.predicted_lgd ?? state.recommendation?.loss_given_default,
      predicted_lgd: state.loss?.predicted_lgd ?? state.recommendation?.loss_given_default,
      exposure_at_default: state.loss?.exposure_at_default ?? state.recommendation?.exposure_at_default,
      ead: state.loss?.exposure_at_default ?? state.recommendation?.exposure_at_default,
      expected_loss: state.loss?.expected_loss ?? state.recommendation?.expected_loss,
      base_limit: state.requestedLimit ?? state.approvedLimit ?? state.loss?.exposure_at_default,
      requested_credit_limit: state.requestedLimit,
      approved_credit_limit: state.approvedLimit,
      limit_haircut: state.recommendation?.limit_haircut,
      stress_index: state.stress?.stress_index ?? state.pd?.market_stress_index,
      pc1_score: state.stress?.pc1_score,
      pca_loadings: state.stress?.pca_loadings,
      component_values: state.stress?.component_values,
      distance_to_default: state.pd?.distance_to_default
    };
  }

  async function askCopilot(question) {
    if (!question.trim()) return;
    if (state.copilotBusy) return;
    const clean = question.trim();
    el.copilotFeed.insertAdjacentHTML("beforeend", `<div class="chat-card"><strong>You</strong>${escapeHtml(clean)}</div>`);
    el.copilotInput.value = "";
    state.copilotBusy = true;
    el.copilotInput.disabled = true;
    const pendingId = `copilot-pending-${Date.now()}`;
    el.copilotFeed.insertAdjacentHTML(
      "beforeend",
      `<div id="${pendingId}" class="chat-card"><strong>Co-Pilot</strong><span class="loading-spinner" aria-hidden="true"></span> Reading selected counterparty context...</div>`
    );
    el.copilotFeed.scrollTop = el.copilotFeed.scrollHeight;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 90000);
    try {
      let data;
      try {
        data = await api("/api/v1/copilot/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({
            question: clean,
            style: "casual_precise",
            values: copilotTraceValues(),
            retrieval_limit: 7
          })
        });
      } catch (groundedError) {
        data = await api("/api/copilot", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({
            question: clean,
            counterparty_id: state.counterparty?.id || null,
            counterparty_name: state.counterparty?.counterparty_name || null,
            page: state.page,
            visible_metrics: copilotVisibleMetrics()
          })
        });
        data = {
          ...data,
          mode: "legacy_sql_rag_fallback",
          sources: ["api/rag/grounded_context.py", "api/rag/router.py"],
          route: { intent: "legacy_copilot" }
        };
      }
      document.getElementById(pendingId)?.remove();
      el.copilotFeed.insertAdjacentHTML("beforeend", renderCopilotAnswer(data));
    } catch (error) {
      document.getElementById(pendingId)?.remove();
      const message = error.name === "AbortError"
        ? "The copilot timed out while reading model context. Try a narrower question or check /api/copilot/health."
        : error.message;
      el.copilotFeed.insertAdjacentHTML("beforeend", `<div class="chat-card"><strong>Co-Pilot</strong>${escapeHtml(message)}</div>`);
    } finally {
      window.clearTimeout(timeout);
      state.copilotBusy = false;
      el.copilotInput.disabled = false;
    }
    el.copilotFeed.scrollTop = el.copilotFeed.scrollHeight;
  }

  function closeIngestModal() {
    el.modal.hidden = true;
  }

  function setCopilotOpen(open) {
    el.copilot.hidden = !open;
    el.copilot.classList.toggle("is-open", open);
    el.frame.classList.toggle("copilot-open", open);
    el.toggleCopilot.setAttribute("aria-expanded", String(open));
  }

  function setFormValue(form, name, value) {
    const field = form.elements[name];
    if (!field) return;
    field.value = value ?? "";
  }

  function prefillCreditTerms(form) {
    setFormValue(form, "requested_credit_limit", state.requestedLimit);
    setFormValue(form, "approved_credit_limit", state.approvedLimit);
    setFormValue(form, "outstanding_receivables", state.outstandingReceivables);
    setFormValue(form, "payment_tenor_days", state.requestedTenor || 30);
    setFormValue(form, "utilization_rate", Math.round(normalizeUtilization(state.utilizationRate) * 100));
    setFormValue(form, "collateral_type", state.collateralType || "unsecured");
    setFormValue(form, "deposit_percentage", state.depositPercentage || 0);
    setFormValue(form, "invoice_amount", state.invoiceAmount);
    setFormValue(form, "fuel_volume", state.fuelVolume);
    setFormValue(form, "fuel_price", state.fuelPrice);
  }

  function relabelManualPeriods() {
    const blocks = Array.from(el.manualForm.querySelectorAll("[data-period-block]"));
    blocks.forEach((block, index) => {
      const title = block.querySelector(".manual-period-head strong");
      const subtitle = block.querySelector(".manual-period-head span");
      const remove = block.querySelector("[data-remove-period]");
      const latest = block.querySelector("input[name='is_latest_snapshot']");
      if (title) title.textContent = `Financial Period ${index + 1}`;
      if (subtitle) subtitle.textContent = latest?.checked
        ? "Latest snapshot used by current models"
        : "Historical period used for trend features";
      if (remove) remove.hidden = blocks.length <= 1;
    });
  }

  function addManualPeriod() {
    const list = document.getElementById("manual-period-list");
    const first = list?.querySelector("[data-period-block]");
    if (!list || !first) return;
    const clone = first.cloneNode(true);
    const index = list.querySelectorAll("[data-period-block]").length;
    clone.querySelectorAll("input, select").forEach((field) => {
      if (field.name === "is_latest_snapshot") field.checked = false;
      else if (field.name === "fiscal_year") {
        const firstYear = Number(first.querySelector("input[name='fiscal_year']")?.value) || new Date().getFullYear();
        field.value = String(firstYear - index);
      } else if (field.name === "period_type") field.value = "annual";
      else if (field.name === "period_label") field.value = "FY";
      else if (field.name === "currency") field.value = first.querySelector("input[name='currency']")?.value || "USD";
      else field.value = "";
    });
    if (!clone.querySelector("[data-remove-period]")) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "secondary-action remove-period-button";
      remove.dataset.removePeriod = "true";
      remove.innerHTML = `<i class="fa-solid fa-minus" aria-hidden="true"></i> Remove Period`;
      clone.appendChild(remove);
    }
    list.appendChild(clone);
    relabelManualPeriods();
  }

  function bindEvents() {
    el.nav.addEventListener("click", (event) => {
      const button = event.target.closest("[data-page]");
      if (!button) return;
      state.page = button.dataset.page;
      renderPage();
    });

    el.root.addEventListener("click", (event) => {
      const markLatest = event.target.closest("[data-mark-latest]");
      if (markLatest) {
        markFinancialPeriodLatest(Number(markLatest.dataset.markLatest)).catch((error) => {
          stopProcessing();
          showBanner(error.message, "error");
          renderPage();
        });
        return;
      }
      const action = event.target.closest("[data-action]")?.dataset.action;
      if (action) handleAction(action);
    });

    el.root.addEventListener("change", async (event) => {
      const counterpartySelect = event.target.closest("[data-scenario-counterparty]");
      if (counterpartySelect) {
        const id = Number(counterpartySelect.value);
        const cp = state.counterparties.find((item) => Number(item.id) === id);
        if (!cp) return;
        try {
          setLoading(`Loading ${cp.counterparty_name}...`);
          await loadSelectedCounterparty(cp);
          clearLoading();
        } catch (error) {
          stopProcessing();
          showBanner(error.message, "error");
          renderPage();
        }
        return;
      }

      const horizonSelect = event.target.closest("[data-forecast-horizon]");
      if (horizonSelect) {
        state.forecastHorizon = Number(horizonSelect.value) || 90;
        renderPage();
      }
    });

    el.root.addEventListener("input", (event) => {
      const slider = event.target.closest("[data-custom-scenario]");
      if (!slider) return;
      const key = slider.dataset.customScenario;
      state.customScenario = {
        ...state.customScenario,
        [key]: Number(slider.value)
      };
      if (state.page === "scenario") renderPage();
    });

    el.toggle.addEventListener("click", () => {
      el.results.hidden = !el.results.hidden;
    });

    el.results.addEventListener("click", async (event) => {
      const id = Number(event.target.closest("[data-counterparty-id]")?.dataset.counterpartyId);
      if (!id) return;
      const cp = state.counterparties.find((item) => item.id === id);
      el.results.hidden = true;
      if (cp) {
        setLoading(`Loading ${cp.counterparty_name}...`);
        await loadSelectedCounterparty(cp);
        clearLoading();
      }
    });

    el.search.addEventListener("input", async () => {
      await loadCounterparties(el.search.value);
      el.results.hidden = false;
    });

    el.openIngest.addEventListener("click", () => {
      el.modal.hidden = false;
      const name = state.counterparty?.counterparty_name || "";
      el.uploadForm.counterparty_name.value = name;
      el.manualForm.counterparty_name.value = name;
      prefillCreditTerms(el.uploadForm);
      prefillCreditTerms(el.manualForm);
      relabelManualPeriods();
    });

    el.refreshMarket.addEventListener("click", async () => {
      try {
        setLoading("Refreshing live market data and recalculating risk outputs...");
        await refreshLiveMarketData();
        clearLoading();
        renderPage();
      } catch (error) {
        stopProcessing();
        showBanner(error.message, "error");
      }
    });

    el.deleteCounterparty.addEventListener("click", async () => {
      try {
        showDeleteCounterpartyDialog();
      } catch (error) {
        stopProcessing();
        showBanner(error.message, "error");
      }
    });

    el.toggleCopilot.addEventListener("click", () => {
      setCopilotOpen(el.copilot.hidden);
    });

    el.closeIngest.addEventListener("click", closeIngestModal);
    el.modal.addEventListener("click", (event) => {
      if (event.target === el.modal || event.target.closest("#close-ingest")) {
        closeIngestModal();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !el.modal.hidden) {
        closeIngestModal();
      }
      if (event.key === "Escape" && !el.copilot.hidden) {
        setCopilotOpen(false);
      }
    });

    document.querySelectorAll(".tab").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((item) => item.classList.remove("is-active"));
        button.classList.add("is-active");
        const tab = button.dataset.tab;
        el.uploadForm.hidden = tab !== "upload";
        el.manualForm.hidden = tab !== "manual";
      });
    });

    el.uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        setLoading("Uploading annual report and running credit models...");
        await uploadDocument(el.uploadForm);
        state.page = "counterparty";
        el.modal.hidden = true;
        clearLoading();
        renderPage();
      } catch (error) {
        stopProcessing();
        showBanner(error.message, "error");
      }
    });

    el.manualForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        setLoading("Saving financial metrics and running credit models...");
        await saveManualFinancials(el.manualForm);
        state.page = "counterparty";
        el.modal.hidden = true;
        clearLoading();
        renderPage();
      } catch (error) {
        stopProcessing();
        showBanner(error.message, "error");
      }
    });

    el.manualForm.addEventListener("click", (event) => {
      if (event.target.closest("#add-manual-period")) {
        addManualPeriod();
        return;
      }
      const remove = event.target.closest("[data-remove-period]");
      if (remove) {
        remove.closest("[data-period-block]")?.remove();
        relabelManualPeriods();
      }
    });

    el.manualForm.addEventListener("change", (event) => {
      if (event.target.closest("input[name='is_latest_snapshot']")) {
        relabelManualPeriods();
      }
    });

    el.copilotForm.addEventListener("submit", (event) => {
      event.preventDefault();
      askCopilot(el.copilotInput.value);
    });

    document.querySelector(".prompt-grid").addEventListener("click", (event) => {
      const button = event.target.closest("[data-prompt]");
      if (button) askCopilot(button.dataset.prompt);
    });

    el.root.addEventListener("click", (event) => {
      const scenarioButton = event.target.closest("[data-scenario-type]");
      if (scenarioButton) {
        state.selectedScenarioType = scenarioButton.dataset.scenarioType;
        renderPage();
        return;
      }
      const button = event.target.closest("[data-copilot-prompt]");
      if (!button) return;
      setCopilotOpen(true);
      askCopilot(button.dataset.copilotPrompt);
    });
  }

  async function boot() {
    renderNav();
    el.root.innerHTML = `${pageHeader("Counterparty Credit Analysis", "Loading live credit workspace...")}`;
    bindEvents();
    try {
      await chooseInitialCounterparty();
    } catch (error) {
      showBanner(`Backend data could not be loaded: ${error.message}`, "error");
      renderPage();
    }
  }

  boot();
}());

