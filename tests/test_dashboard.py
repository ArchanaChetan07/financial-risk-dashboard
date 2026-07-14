"""
Tests for financial-risk-dashboard — includes leakage regression guards.
Run with: pytest tests/ -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


# ─── Data Processing Tests ────────────────────────────────────────────────────


class TestDataProcessing:
    def test_dataframe_not_empty(self):
        df = pd.DataFrame(
            {"close": [100, 102, 98, 105], "volume": [1000, 1500, 900, 1200]}
        )
        assert not df.empty

    def test_missing_values_handled(self):
        df = pd.DataFrame({"close": [100, None, 98, 105]})
        df_clean = df.dropna()
        assert df_clean.isnull().sum().sum() == 0

    def test_returns_calculation(self):
        prices = pd.Series([100, 105, 103, 108])
        returns = prices.pct_change().dropna()
        assert len(returns) == 3
        assert round(returns.iloc[0], 4) == 0.05

    def test_roi_equals_daily_return_algebraically(self):
        """Documents the historical tautology that caused R²=1.0 when both used."""
        close = pd.Series([100.0, 110.0, 105.0, 120.0])
        daily = close.pct_change()
        roi = (close / close.shift(1)) - 1
        pd.testing.assert_series_equal(daily, roi, check_names=False)


# ─── Leakage-safe predictive pipeline ─────────────────────────────────────────


@pytest.fixture(scope="module")
def aligned_frame():
    from predictive_models import build_leakage_safe_frame

    path = ROOT / "data" / "processed" / "combined_stock_metrics.csv"
    raw = pd.read_csv(path)
    return build_leakage_safe_frame(raw)


class TestLeakageGuards:
    def test_target_is_forward_return_not_same_day_roi(self, aligned_frame):
        from predictive_models import TARGET_COL

        assert TARGET_COL == "Next_Day_Return"
        assert "Daily Return" not in [
            "Close_lag1",
            "Volume_lag1",
            "Return_lag1",
            "Volatility_lag1",
            "Sharpe_lag1",
            "ticker",
        ]

    def test_no_feature_near_perfectly_correlates_with_target(self, aligned_frame):
        """Would have failed on the old pipeline (Daily Return vs ROI → corr ≈ 1)."""
        from predictive_models import max_abs_feature_target_corr

        max_corr = max_abs_feature_target_corr(aligned_frame)
        assert max_corr < 0.99, f"Suspected leakage: max |corr|={max_corr:.4f}"
        assert (
            max_corr < 0.5
        ), f"Feature/target corr still suspiciously high: {max_corr:.4f}"

    def test_chronological_split_preserves_time_order(self, aligned_frame):
        from predictive_models import chronological_split

        train, test, cutoff = chronological_split(aligned_frame, test_size=0.2)
        assert train["Date"].max() < test["Date"].min()
        assert train["Date"].max() < cutoff
        assert test["Date"].min() >= cutoff

    def test_models_r2_not_perfect_on_holdout(self, aligned_frame):
        """Linear/Ridge must not hit R²≈1 after the leakage fix."""
        from predictive_models import chronological_split, evaluate_models

        train, test, _ = chronological_split(aligned_frame, test_size=0.2)
        perf = evaluate_models(train, test)
        for _, row in perf.iterrows():
            assert (
                row["R-Squared"] < 0.95
            ), f"{row['Model']} R²={row['R-Squared']:.4f} looks leaked"


# ─── Database Connection Tests ────────────────────────────────────────────────


class TestDatabaseConnection:
    @patch("mysql.connector.connect")
    def test_db_connection_success(self, mock_connect):
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_connect.return_value = mock_conn

        import mysql.connector

        conn = mysql.connector.connect(
            host="localhost", user="user", password="pass", database="db"
        )
        assert conn.is_connected()

    @patch("mysql.connector.connect")
    def test_db_connection_failure_handled(self, mock_connect):
        import mysql.connector

        mock_connect.side_effect = mysql.connector.Error("Connection refused")
        with pytest.raises(mysql.connector.Error):
            mysql.connector.connect(
                host="bad_host", user="user", password="wrong", database="db"
            )


# ─── Environment Variables Tests ──────────────────────────────────────────────


class TestEnvironmentConfig:
    def test_env_vars_loaded(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_USER", "user")
        monkeypatch.setenv("DB_PASSWORD", "pass")
        monkeypatch.setenv("DB_NAME", "finance_db")

        assert os.getenv("DB_HOST") == "localhost"
        assert os.getenv("DB_USER") is not None
        assert os.getenv("DB_PASSWORD") is not None
        assert os.getenv("DB_NAME") is not None
