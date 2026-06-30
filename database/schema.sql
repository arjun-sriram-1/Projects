-- PHASE 1: MARKET DATA

CREATE TABLE IF NOT EXISTS market_prices (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP,
    price DOUBLE PRECISION,
    asset TEXT,
    ticker TEXT,
    source_id TEXT,
    asset_name TEXT,
    data_source TEXT,
    frequency TEXT,
    units TEXT,
    return DOUBLE PRECISION,
    rolling_volatility DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_features (
    id SERIAL PRIMARY KEY,
    asset TEXT,
    ticker TEXT,
    source_id TEXT,
    data_source TEXT,
    mu DOUBLE PRECISION,
    sigma DOUBLE PRECISION,
    latest_price DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS macro_indicators (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP,
    indicator TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    source_id TEXT,
    data_source TEXT,
    frequency TEXT,
    units TEXT,
    return DOUBLE PRECISION,
    rolling_volatility DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- PORTFOLIO & SIMULATION

CREATE TABLE IF NOT EXISTS simulation_results (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) UNIQUE,
    scenario TEXT,
    scenario_result_id INT,
    model_name VARCHAR(150),
    model_version VARCHAR(50),
    expected_loss DOUBLE PRECISION,
    var_95 DOUBLE PRECISION,
    var_99 DOUBLE PRECISION,
    expected_shortfall_95 DOUBLE PRECISION,
    expected_shortfall_99 DOUBLE PRECISION,
    expected_shortfall DOUBLE PRECISION,
    unexpected_loss DOUBLE PRECISION,
    avg_defaults DOUBLE PRECISION,
    max_defaults INTEGER,
    number_of_simulations INTEGER,
    random_seed INTEGER,
    loss_distribution_summary JSONB,
    marginal_risk_contribution JSONB,
    default_correlation DOUBLE PRECISION,
    input_data_reference JSONB,
    assumptions_reference JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scenario_results (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) UNIQUE,
    scenario_name TEXT,
    scenario_type VARCHAR(50),
    model_name VARCHAR(150),
    model_version VARCHAR(50),
    expected_loss DOUBLE PRECISION,
    var_95 DOUBLE PRECISION,
    var_99 DOUBLE PRECISION,
    expected_shortfall_95 DOUBLE PRECISION,
    expected_shortfall_99 DOUBLE PRECISION,
    expected_shortfall DOUBLE PRECISION,
    unexpected_loss DOUBLE PRECISION,
    max_loss DOUBLE PRECISION,
    scenario_inputs JSONB,
    scenario_impacts JSONB,
    input_data_reference JSONB,
    assumptions_reference JSONB,
    number_of_counterparties INTEGER,
    number_of_simulations INTEGER,
    random_seed INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS monte_carlo_runs (
    run_id SERIAL PRIMARY KEY,
    avg_loss DOUBLE PRECISION,
    max_loss DOUBLE PRECISION,
    min_loss DOUBLE PRECISION,
    avg_defaults DOUBLE PRECISION,
    max_defaults INTEGER,
    anomaly_flags_triggered INTEGER,
    n_simulations INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- PHASE 2: MASTER TABLES (NO DEPENDENCIES)

CREATE TABLE IF NOT EXISTS counterparties_master (
    id SERIAL PRIMARY KEY,
    counterparty_name VARCHAR(255) NOT NULL,
    counterparty_type VARCHAR(50),
    country VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(counterparty_name)
);

-- PHASE 2: DOCUMENT & FINANCIAL DATA (DEPENDS ON counterparties_master)

CREATE TABLE IF NOT EXISTS uploaded_documents (
    id SERIAL PRIMARY KEY,
    counterparty_id INT REFERENCES counterparties_master(id),
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    document_type VARCHAR(50),
    file_size_bytes BIGINT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    extraction_status VARCHAR(50),
    extraction_error TEXT,
    created_by VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(counterparty_id, filename)
);

CREATE TABLE IF NOT EXISTS financial_metrics_extracted (
    id SERIAL PRIMARY KEY,
    uploaded_document_id INT REFERENCES uploaded_documents(id),
    counterparty_id INT REFERENCES counterparties_master(id),
    fiscal_year INT,
    fiscal_period VARCHAR(10),
    
    -- Income Statement
    revenue DECIMAL(20, 2),
    cost_of_goods_sold DECIMAL(20, 2),
    operating_expenses DECIMAL(20, 2),
    ebitda DECIMAL(20, 2),
    ebit DECIMAL(20, 2),
    interest_expense DECIMAL(20, 2),
    net_income DECIMAL(20, 2),
    
    -- Balance Sheet Assets
    cash_and_equivalents DECIMAL(20, 2),
    short_term_investments DECIMAL(20, 2),
    accounts_receivable DECIMAL(20, 2),
    inventory DECIMAL(20, 2),
    other_current_assets DECIMAL(20, 2),
    current_assets DECIMAL(20, 2),
    ppe_gross DECIMAL(20, 2),
    accumulated_depreciation DECIMAL(20, 2),
    ppe_net DECIMAL(20, 2),
    intangible_assets DECIMAL(20, 2),
    goodwill DECIMAL(20, 2),
    total_assets DECIMAL(20, 2),
    
    -- Balance Sheet Liabilities & Equity
    accounts_payable DECIMAL(20, 2),
    short_term_debt DECIMAL(20, 2),
    current_portion_long_term_debt DECIMAL(20, 2),
    other_current_liabilities DECIMAL(20, 2),
    current_liabilities DECIMAL(20, 2),
    long_term_debt DECIMAL(20, 2),
    total_debt DECIMAL(20, 2),
    other_long_term_liabilities DECIMAL(20, 2),
    total_liabilities DECIMAL(20, 2),
    shareholders_equity DECIMAL(20, 2),
    retained_earnings DECIMAL(20, 2),
    
    -- Cash Flow
    operating_cash_flow DECIMAL(20, 2),
    investing_cash_flow DECIMAL(20, 2),
    financing_cash_flow DECIMAL(20, 2),
    free_cash_flow DECIMAL(20, 2),
    
    -- Meta
    currency VARCHAR(3),
    extraction_confidence DECIMAL(3, 2),
    missing_critical_fields JSONB,
    original_text_references JSONB,
    extraction_warnings JSONB,
    source_document_id INT REFERENCES uploaded_documents(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(uploaded_document_id, fiscal_year)
);

-- INDEXES FOR PERFORMANCE

CREATE INDEX IF NOT EXISTS idx_financial_metrics_counterparty ON financial_metrics_extracted(counterparty_id);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_doc ON financial_metrics_extracted(uploaded_document_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_counterparty ON uploaded_documents(counterparty_id);

-- PHASE 3: FINANCIAL RATIO ENGINE

CREATE TABLE IF NOT EXISTS financial_ratios (
    id SERIAL PRIMARY KEY,
    counterparty_id INT NOT NULL REFERENCES counterparties_master(id),
    uploaded_document_id INT REFERENCES uploaded_documents(id),
    financial_metrics_id INT NOT NULL UNIQUE REFERENCES financial_metrics_extracted(id),
    fiscal_year INT,
    fiscal_period VARCHAR(10),
    currency VARCHAR(3),

    -- Liquidity
    current_ratio DECIMAL(18, 6),
    quick_ratio DECIMAL(18, 6),
    cash_ratio DECIMAL(18, 6),
    working_capital DECIMAL(20, 2),

    -- Leverage
    debt_to_equity DECIMAL(18, 6),
    debt_to_ebitda DECIMAL(18, 6),
    liabilities_to_assets DECIMAL(18, 6),

    -- Coverage
    interest_coverage DECIMAL(18, 6),

    -- Profitability
    operating_margin DECIMAL(18, 6),
    net_margin DECIMAL(18, 6),
    return_on_assets DECIMAL(18, 6),
    return_on_equity DECIMAL(18, 6),

    -- Auditability
    formula_version VARCHAR(50) NOT NULL,
    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_data_reference TEXT,
    missing_inputs JSONB,
    calculation_warnings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_financial_ratios_counterparty ON financial_ratios(counterparty_id);
CREATE INDEX IF NOT EXISTS idx_financial_ratios_financial_metrics ON financial_ratios(financial_metrics_id);

-- PHASE 4: MARKET STRESS INDEX & REGIME DETECTION

CREATE TABLE IF NOT EXISTS stress_index_history (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    stress_index DECIMAL(5, 2) NOT NULL,
    stress_level VARCHAR(20) NOT NULL,
    pc1_score DOUBLE PRECISION,
    explained_variance_ratio DOUBLE PRECISION,
    pca_loadings JSONB,
    top_positive_drivers JSONB,
    top_negative_drivers JSONB,
    component_values JSONB,
    available_components JSONB,
    missing_components JSONB,
    model_version VARCHAR(50),
    data_source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_regime_history (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    regime_id INT NOT NULL,
    regime_label VARCHAR(50) NOT NULL,
    regime_probability DECIMAL(8, 6),
    regime_characteristics JSONB,
    feature_values JSONB,
    model_version VARCHAR(50),
    data_source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stress_date ON stress_index_history(date);
CREATE INDEX IF NOT EXISTS idx_regime_date ON market_regime_history(date);

-- PHASE 5: PROBABILITY OF DEFAULT MODELS

CREATE TABLE IF NOT EXISTS pd_model_predictions (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL UNIQUE,
    counterparty_id INT NOT NULL REFERENCES counterparties_master(id),
    financial_metrics_id INT REFERENCES financial_metrics_extracted(id),
    financial_ratios_id INT REFERENCES financial_ratios(id),
    model_name VARCHAR(150) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    structural_pd DECIMAL(12, 8) NOT NULL,
    ml_pd DECIMAL(12, 8) NOT NULL,
    final_pd DECIMAL(12, 8) NOT NULL,
    classification_label VARCHAR(20) NOT NULL,
    model_confidence DECIMAL(12, 8),
    model_disagreement BOOLEAN DEFAULT FALSE,
    pd_divergence DECIMAL(12, 8),
    distance_to_default DECIMAL(18, 8),
    asset_value_proxy DECIMAL(20, 2),
    debt_threshold DECIMAL(20, 2),
    asset_volatility DECIMAL(12, 8),
    risk_free_rate DECIMAL(12, 8),
    time_horizon_years DECIMAL(10, 4),
    commodity_sensitivity_score DECIMAL(12, 8),
    fx_sensitivity_score DECIMAL(12, 8),
    macro_sensitivity_score DECIMAL(12, 8),
    market_stress_index DECIMAL(5, 2),
    market_regime VARCHAR(50),
    feature_contributions JSONB,
    model_assumptions JSONB,
    input_data_reference JSONB,
    warnings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pd_predictions_counterparty ON pd_model_predictions(counterparty_id);
CREATE INDEX IF NOT EXISTS idx_pd_predictions_financial_metrics ON pd_model_predictions(financial_metrics_id);

-- PHASE 6: LGD, EAD & EXPECTED LOSS

CREATE TABLE IF NOT EXISTS trade_exposures (
    id SERIAL PRIMARY KEY,
    counterparty_id INT NOT NULL REFERENCES counterparties_master(id),
    invoice_amount DECIMAL(20, 2),
    fuel_volume DECIMAL(20, 4),
    fuel_price DECIMAL(20, 6),
    approved_credit_limit DECIMAL(20, 2),
    requested_credit_limit DECIMAL(20, 2),
    outstanding_receivables DECIMAL(20, 2) DEFAULT 0,
    payment_tenor_days INT DEFAULT 30,
    utilization_rate DECIMAL(8, 6) DEFAULT 0.50,
    collateral_type VARCHAR(50) DEFAULT 'unsecured',
    letter_of_credit_flag BOOLEAN DEFAULT FALSE,
    guarantee_flag BOOLEAN DEFAULT FALSE,
    deposit_percentage DECIMAL(8, 4) DEFAULT 0,
    counterparty_type VARCHAR(50),
    country_risk_score DECIMAL(8, 4),
    seniority_score DECIMAL(8, 4),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS loss_estimates (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL UNIQUE,
    counterparty_id INT NOT NULL REFERENCES counterparties_master(id),
    pd_prediction_id INT REFERENCES pd_model_predictions(id),
    trade_exposure_id INT REFERENCES trade_exposures(id),
    model_name VARCHAR(150) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    probability_of_default DECIMAL(12, 8) NOT NULL,
    predicted_lgd DECIMAL(12, 8) NOT NULL,
    exposure_at_default DECIMAL(20, 2) NOT NULL,
    expected_loss DOUBLE PRECISION NOT NULL,
    collateral_strength DECIMAL(12, 8),
    liquidity_score DECIMAL(12, 8),
    ead_cap_applied BOOLEAN DEFAULT FALSE,
    expected_drawdown DECIMAL(20, 2),
    invoice_exposure DECIMAL(20, 2),
    model_assumptions JSONB,
    input_data_reference JSONB,
    warnings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trade_exposures_counterparty ON trade_exposures(counterparty_id);
CREATE INDEX IF NOT EXISTS idx_loss_estimates_counterparty ON loss_estimates(counterparty_id);
CREATE INDEX IF NOT EXISTS idx_loss_estimates_pd_prediction ON loss_estimates(pd_prediction_id);

-- PHASE 8: CREDIT DECISION ENGINE & GROUNDED MEMOS

CREATE TABLE IF NOT EXISTS credit_recommendations (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL UNIQUE,
    counterparty_id INT NOT NULL REFERENCES counterparties_master(id),
    model_name VARCHAR(150) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    probability_of_default DECIMAL(12, 8) NOT NULL,
    loss_given_default DECIMAL(12, 8) NOT NULL,
    exposure_at_default DECIMAL(20, 2) NOT NULL,
    expected_loss DECIMAL(20, 2) NOT NULL,
    scenario_expected_loss DECIMAL(20, 2),
    credit_var_95 DECIMAL(20, 2),
    expected_shortfall_95 DECIMAL(20, 2),
    recommended_credit_limit DECIMAL(20, 2) NOT NULL,
    recommended_tenor_days INT NOT NULL,
    recommended_security TEXT NOT NULL,
    risk_grade VARCHAR(20) NOT NULL,
    approval_status VARCHAR(50) NOT NULL,
    policy_score DECIMAL(12, 6) NOT NULL,
    limit_haircut DECIMAL(12, 6) NOT NULL,
    key_risk_drivers JSONB,
    mitigating_factors JSONB,
    model_assumptions JSONB,
    input_data_reference JSONB,
    warnings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_credit_memos (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL,
    counterparty_id INT NOT NULL REFERENCES counterparties_master(id),
    credit_recommendation_id INT REFERENCES credit_recommendations(id),
    model_name VARCHAR(150) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    memo_text TEXT NOT NULL,
    input_data_reference JSONB,
    assumptions_reference JSONB,
    warnings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_credit_recommendations_counterparty ON credit_recommendations(counterparty_id);
CREATE INDEX IF NOT EXISTS idx_ai_credit_memos_counterparty ON ai_credit_memos(counterparty_id);

-- MODEL TRAINING, VALIDATION & GOVERNANCE

CREATE TABLE IF NOT EXISTS historical_training_dataset (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    counterparty_id INT REFERENCES counterparties_master(id),
    counterparty_name TEXT,
    fiscal_year INT,
    counterparty_type VARCHAR(100),
    country VARCHAR(100),
    data_source TEXT NOT NULL,
    current_ratio DOUBLE PRECISION,
    quick_ratio DOUBLE PRECISION,
    cash_ratio DOUBLE PRECISION,
    working_capital DOUBLE PRECISION,
    debt_to_equity DOUBLE PRECISION,
    debt_to_ebitda DOUBLE PRECISION,
    liabilities_to_assets DOUBLE PRECISION,
    interest_coverage DOUBLE PRECISION,
    operating_margin DOUBLE PRECISION,
    net_margin DOUBLE PRECISION,
    return_on_assets DOUBLE PRECISION,
    return_on_equity DOUBLE PRECISION,
    market_stress_index DOUBLE PRECISION,
    market_regime VARCHAR(100),
    oil_volatility DOUBLE PRECISION,
    fuel_return DOUBLE PRECISION,
    dxy_return DOUBLE PRECISION,
    vix_level DOUBLE PRECISION,
    sp500_return DOUBLE PRECISION,
    country_risk_score DOUBLE PRECISION,
    payment_tenor_days INT,
    collateral_type VARCHAR(100),
    letter_of_credit_flag BOOLEAN DEFAULT FALSE,
    guarantee_flag BOOLEAN DEFAULT FALSE,
    deposit_percentage DOUBLE PRECISION,
    exposure_size DOUBLE PRECISION,
    proxy_default_risk_score DOUBLE PRECISION,
    proxy_default_label INT,
    proxy_lgd_label DOUBLE PRECISION,
    feature_payload JSONB,
    label_logic JSONB,
    input_data_reference JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_training_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL UNIQUE,
    model_name VARCHAR(150) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    algorithm VARCHAR(150) NOT NULL,
    training_rows INT NOT NULL,
    train_rows INT,
    test_rows INT,
    target_column VARCHAR(100) NOT NULL,
    feature_columns JSONB,
    artifact_path TEXT,
    feature_importance JSONB,
    input_data_reference JSONB,
    assumptions_reference JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_validation_results (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    model_training_run_id INT REFERENCES model_training_runs(id),
    model_name VARCHAR(150) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    validation_type VARCHAR(100) NOT NULL,
    metrics JSONB,
    sanity_checks JSONB,
    train_start_year INT,
    train_end_year INT,
    test_start_year INT,
    test_end_year INT,
    assumptions_reference JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_dataset_run_id ON historical_training_dataset(run_id);
CREATE INDEX IF NOT EXISTS idx_training_dataset_counterparty ON historical_training_dataset(counterparty_id);
CREATE INDEX IF NOT EXISTS idx_training_runs_type ON model_training_runs(model_type);
CREATE INDEX IF NOT EXISTS idx_validation_results_run_id ON model_validation_results(run_id);
