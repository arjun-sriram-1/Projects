"""Market Regime Detection with KMeans, GMM, and HMM-style smoothing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler


REGIME_MODEL_VERSION = "market_regime_v2_kmeans_gmm_hmm"


@dataclass
class RegimeDetectionResult:
    history: pd.DataFrame
    interpretation: Dict[int, dict]
    feature_columns: List[str]
    model_version: str = REGIME_MODEL_VERSION


class RegimeDetector:
    """Detect learned market regimes from stress components."""

    def __init__(self, n_regimes: int = 4, random_state: int = 42, model_type: str = "kmeans"):
        self.n_regimes = n_regimes
        self.random_state = random_state
        self.model_type = (model_type or "kmeans").lower()
        self.scaler = StandardScaler()
        self.model = None

    def fit_predict(self, features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if features.empty:
            raise ValueError("Regime features are empty")
        n_clusters = max(1, min(self.n_regimes, len(features)))
        scaled = self.scaler.fit_transform(features)
        if self.model_type == "kmeans":
            self.model = KMeans(n_clusters=n_clusters, random_state=self.random_state, n_init=10)
            regimes = self.model.fit_predict(scaled)
            distances = self.model.transform(scaled)
            confidence = 1 / (1 + distances.min(axis=1))
            return regimes.astype(int), confidence.astype(float)
        if self.model_type in {"gmm", "hmm"}:
            self.model = GaussianMixture(n_components=n_clusters, random_state=self.random_state, covariance_type="full")
            regimes = self.model.fit_predict(scaled).astype(int)
            probabilities = self.model.predict_proba(scaled)
            confidence = probabilities.max(axis=1)
            if self.model_type == "hmm":
                regimes = self._markov_smooth(regimes, probabilities)
                confidence = np.maximum(confidence, probabilities[np.arange(len(regimes)), regimes])
            return regimes.astype(int), confidence.astype(float)
        raise ValueError("model_type must be one of: kmeans, gmm, hmm")

    @staticmethod
    def _markov_smooth(regimes: np.ndarray, probabilities: np.ndarray) -> np.ndarray:
        """Apply lightweight Markov persistence smoothing to GMM state labels."""
        if len(regimes) < 3:
            return regimes
        smoothed = regimes.copy()
        transition_counts = np.ones((probabilities.shape[1], probabilities.shape[1]))
        for prev, curr in zip(regimes[:-1], regimes[1:]):
            transition_counts[int(prev), int(curr)] += 1
        transition = transition_counts / transition_counts.sum(axis=1, keepdims=True)
        for idx in range(1, len(smoothed)):
            prev_state = int(smoothed[idx - 1])
            scores = probabilities[idx] * transition[prev_state]
            smoothed[idx] = int(np.argmax(scores))
        return smoothed

    @staticmethod
    def _label_cluster(row: pd.Series, stress_rank: int, max_rank: int) -> str:
        oil_pressure = max(row.get("oil_volatility_zscore", 0), row.get("brent_return_zscore", 0), row.get("heating_oil_return_zscore", 0))
        usd_pressure = max(row.get("dxy_return_zscore", 0), row.get("usd_inr_return_zscore", 0))
        risk_off = max(row.get("vix_zscore", 0), row.get("sp500_loss_zscore", 0), row.get("gold_return_zscore", 0))
        if stress_rank == max_rank:
            return "Crisis" if risk_off >= oil_pressure else "Commodity Stress"
        if oil_pressure >= usd_pressure and oil_pressure >= risk_off and oil_pressure > 0:
            return "Commodity Stress"
        if usd_pressure >= risk_off and usd_pressure > 0:
            return "USD Stress"
        if risk_off > 0:
            return "Risk-Off"
        if stress_rank == 0:
            return "Stable Market"
        return "Normal Volatility"

    def interpret_regimes(self, features: pd.DataFrame, regimes: np.ndarray, stress_history: pd.DataFrame) -> Dict[int, dict]:
        working = features.copy()
        working["regime_id"] = regimes
        stress_by_date = stress_history.set_index(pd.to_datetime(stress_history["date"]).dt.date)
        working["stress_index"] = [
            float(stress_by_date.loc[idx, "stress_index"]) if idx in stress_by_date.index else 0.0
            for idx in working.index
        ]
        cluster_means = working.groupby("regime_id").mean(numeric_only=True)
        stress_order = cluster_means["stress_index"].rank(method="dense").astype(int) - 1
        max_rank = int(stress_order.max()) if not stress_order.empty else 0
        interpretation: Dict[int, dict] = {}
        used_labels: set[str] = set()
        for regime_id, row in cluster_means.iterrows():
            label = self._label_cluster(row, int(stress_order.loc[regime_id]), max_rank)
            if label in used_labels:
                label = f"{label} {int(regime_id)}"
            used_labels.add(label)
            interpretation[int(regime_id)] = {
                "label": label,
                "feature_means": {k: float(v) for k, v in row.items()},
                "frequency": int((regimes == regime_id).sum()),
                "model_type": self.model_type,
            }
        return interpretation


def detect_market_regimes(
    component_matrix: pd.DataFrame,
    stress_history: pd.DataFrame,
    n_regimes: int = 4,
    model_type: str = "kmeans",
) -> RegimeDetectionResult:
    """Detect daily learned market regimes from stress components and score history."""
    if component_matrix.empty:
        raise ValueError("Component matrix is empty")
    features = component_matrix.copy()
    features.index = pd.to_datetime(features.index).date
    detector = RegimeDetector(n_regimes=n_regimes, model_type=model_type)
    regimes, confidence = detector.fit_predict(features)
    interpretation = detector.interpret_regimes(features, regimes, stress_history)
    history = pd.DataFrame({
        "date": pd.to_datetime(features.index),
        "regime_id": regimes.astype(int),
        "regime_label": [interpretation[int(regime)]["label"] for regime in regimes],
        "regime_probability": confidence.astype(float),
        "regime_characteristics": [interpretation[int(regime)] for regime in regimes],
        "feature_values": features.to_dict(orient="records"),
        "model_version": REGIME_MODEL_VERSION,
        "data_source": "stress_index_components",
    })
    return RegimeDetectionResult(history=history, interpretation=interpretation, feature_columns=list(features.columns))
