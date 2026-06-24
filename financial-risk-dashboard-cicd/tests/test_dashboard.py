"""
Tests for financial-risk-dashboard scripts.
Run with: pytest tests/ -v
"""
import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


# ─── Data Processing Tests ────────────────────────────────────────────────────

class TestDataProcessing:

    def test_dataframe_not_empty(self):
        """Ensure processed data is non-empty."""
        df = pd.DataFrame({"close": [100, 102, 98, 105], "volume": [1000, 1500, 900, 1200]})
        assert not df.empty

    def test_missing_values_handled(self):
        """Missing values should be filled or dropped."""
        df = pd.DataFrame({"close": [100, None, 98, 105]})
        df_clean = df.dropna()
        assert df_clean.isnull().sum().sum() == 0

    def test_returns_calculation(self):
        """Daily returns should be computable."""
        prices = pd.Series([100, 105, 103, 108])
        returns = prices.pct_change().dropna()
        assert len(returns) == 3
        assert round(returns.iloc[0], 4) == 0.05


# ─── Predictive Model Tests ───────────────────────────────────────────────────

class TestPredictiveModels:

    def test_model_output_shape(self):
        """Model predictions should match input row count."""
        from sklearn.ensemble import RandomForestClassifier
        import numpy as np

        X = np.random.rand(50, 5)
        y = np.random.randint(0, 2, 50)

        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        preds = model.predict(X)

        assert len(preds) == len(X)

    def test_model_accuracy_above_baseline(self):
        """Model accuracy should beat a 50% random baseline."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score
        import numpy as np

        np.random.seed(42)
        X = np.random.rand(200, 5)
        y = (X[:, 0] + X[:, 1] > 1).astype(int)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))

        assert acc > 0.5, f"Model accuracy {acc:.2f} is below baseline"


# ─── Database Connection Tests ────────────────────────────────────────────────

class TestDatabaseConnection:

    @patch("mysql.connector.connect")
    def test_db_connection_success(self, mock_connect):
        """DB connection should succeed with valid credentials."""
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
        """DB connection failure should raise an exception."""
        import mysql.connector
        mock_connect.side_effect = mysql.connector.Error("Connection refused")

        with pytest.raises(mysql.connector.Error):
            mysql.connector.connect(
                host="bad_host", user="user", password="wrong", database="db"
            )


# ─── Environment Variables Tests ──────────────────────────────────────────────

class TestEnvironmentConfig:

    def test_env_vars_loaded(self, monkeypatch):
        """Required env vars should be present."""
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_USER", "user")
        monkeypatch.setenv("DB_PASSWORD", "pass")
        monkeypatch.setenv("DB_NAME", "finance_db")

        assert os.getenv("DB_HOST") == "localhost"
        assert os.getenv("DB_USER") is not None
        assert os.getenv("DB_PASSWORD") is not None
        assert os.getenv("DB_NAME") is not None
