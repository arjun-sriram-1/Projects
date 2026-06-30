"""Central paths for free-source calibration data and artifacts."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
FREE_SOURCE_ROOT = DATA_ROOT / "external" / "free_sources"
PROCESSED_ROOT = DATA_ROOT / "processed" / "calibration"
MODEL_ROOT = DATA_ROOT / "models"
REPORT_ROOT = DATA_ROOT / "reports" / "calibration"

SEC_FINANCIALS_DIR = FREE_SOURCE_ROOT / "sec_financials"
MARKET_DIR = FREE_SOURCE_ROOT / "market"
DEFAULT_LABELS_DIR = FREE_SOURCE_ROOT / "default_labels"
RECOVERY_PROXY_DIR = FREE_SOURCE_ROOT / "recovery_proxy"
TRADE_EXPOSURE_DIR = FREE_SOURCE_ROOT / "trade_exposure_history"

COMPANY_FINANCIALS_CSV = SEC_FINANCIALS_DIR / "company_financials.csv"
MARKET_CONTEXT_CSV = MARKET_DIR / "market_context.csv"
DEFAULT_LABELS_CSV = DEFAULT_LABELS_DIR / "default_labels.csv"
RECOVERY_PROXY_CSV = RECOVERY_PROXY_DIR / "recovery_proxy.csv"
TRADE_EXPOSURE_HISTORY_CSV = TRADE_EXPOSURE_DIR / "trade_exposure_history.csv"
SYNTHETIC_TRADE_HISTORY_REPORT_JSON = REPORT_ROOT / "synthetic_trade_history_summary.json"

PD_TRAINING_CSV = PROCESSED_ROOT / "pd_training_dataset.csv"
LGD_TRAINING_CSV = PROCESSED_ROOT / "lgd_training_dataset.csv"
EAD_TRAINING_CSV = PROCESSED_ROOT / "ead_training_dataset.csv"

HISTORICAL_PD_MODEL = MODEL_ROOT / "historical_pd_model.pkl"
HISTORICAL_LGD_MODEL = MODEL_ROOT / "historical_lgd_model.pkl"
EAD_MODEL = MODEL_ROOT / "calibrated_ead_model.pkl"
PD_BLEND_CONFIG = MODEL_ROOT / "pd_blend_config.json"
COLLATERAL_STRENGTH_CONFIG = MODEL_ROOT / "collateral_strength_config.json"
SCENARIO_MULTIPLIER_CONFIG = MODEL_ROOT / "scenario_multiplier_config.json"
DEFAULT_CORRELATION_CONFIG = MODEL_ROOT / "default_correlation_config.json"
VALIDATION_REPORT_JSON = REPORT_ROOT / "validation_report.json"
ARTIFACT_MANIFEST_JSON = REPORT_ROOT / "artifact_manifest.json"


def ensure_calibration_dirs() -> None:
    """Create all calibration directories if missing."""
    for path in [
        SEC_FINANCIALS_DIR,
        MARKET_DIR,
        DEFAULT_LABELS_DIR,
        RECOVERY_PROXY_DIR,
        TRADE_EXPOSURE_DIR,
        PROCESSED_ROOT,
        MODEL_ROOT,
        REPORT_ROOT,
    ]:
        path.mkdir(parents=True, exist_ok=True)
