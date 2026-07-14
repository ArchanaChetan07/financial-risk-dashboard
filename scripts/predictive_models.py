"""Leakage-safe model comparison for equity next-day return prediction.

Root cause (pre-fix): features included ``Daily Return`` while the target was
``ROI``. In ``data_processing.py`` those two columns are algebraically identical
(``pct_change`` vs ``(Close / Close.shift(1)) - 1``), so Linear Regression
achieved R² ≈ 1.0 by reading the answer.

This script:
  * predicts **next-day** return (shifted target)
  * uses only **lagged** features (no same-day return / risk metrics)
  * splits **chronologically** (no random shuffle of time series)
  * fits the scaler on the training fold only
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA_DIR = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "models"
GRAPHS_DIR = ROOT / "graphs"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "Close_lag1",
    "Volume_lag1",
    "Return_lag1",
    "Volatility_lag1",
    "Sharpe_lag1",
    "ticker",
]
TARGET_COL = "Next_Day_Return"


def build_leakage_safe_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Build lagged features and a forward return target per ticker."""
    df = data.copy()
    df["Date"] = pd.to_datetime(df["Date"], utc=True, errors="coerce")
    df = df.dropna(subset=["Date", "Close", "Daily Return"]).sort_values(
        ["ticker", "Date"]
    )

    parts = []
    for _, group in df.groupby("ticker", sort=False):
        g = group.copy()
        # Lag every same-day feature by 1 so the row cannot see today's return.
        g["Close_lag1"] = g["Close"].shift(1)
        g["Volume_lag1"] = g["Volume"].shift(1)
        g["Return_lag1"] = g["Daily Return"].shift(1)
        # Rolling windows already include the current row in raw data — shift
        # them as well so they only summarize the past.
        g["Volatility_lag1"] = g["Volatility"].shift(1)
        g["Sharpe_lag1"] = g["Sharpe Ratio"].shift(1)
        # Predict tomorrow's return from today's lagged feature row.
        g[TARGET_COL] = g["Daily Return"].shift(-1)
        parts.append(g)

    out = pd.concat(parts, ignore_index=True)
    out = out.dropna(subset=FEATURE_COLS + [TARGET_COL]).reset_index(drop=True)
    return out


def chronological_split(df: pd.DataFrame, test_size: float = 0.2):
    """Hold out the most recent fraction of dates (global chronological cut)."""
    dates = np.sort(df["Date"].unique())
    cut = int(len(dates) * (1 - test_size))
    cut = max(1, min(cut, len(dates) - 1))
    cutoff = dates[cut]
    train = df[df["Date"] < cutoff].copy()
    test = df[df["Date"] >= cutoff].copy()
    if train.empty or test.empty:
        raise RuntimeError("Chronological split produced an empty fold")
    return train, test, cutoff


def evaluate_models(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    encoder = LabelEncoder()
    train = train.copy()
    test = test.copy()
    train["ticker"] = encoder.fit_transform(train["ticker"])
    # Unseen tickers on test should not occur (same universe), but be safe.
    test["ticker"] = test["ticker"].map(
        lambda t: encoder.transform([t])[0] if t in encoder.classes_ else -1
    )

    num_cols = [c for c in FEATURE_COLS if c != "ticker"]
    scaler = StandardScaler()
    X_train = train[FEATURE_COLS].copy()
    X_test = test[FEATURE_COLS].copy()
    X_train[num_cols] = scaler.fit_transform(X_train[num_cols])
    X_test[num_cols] = scaler.transform(X_test[num_cols])
    y_train = train[TARGET_COL].values
    y_test = test[TARGET_COL].values

    models = {
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(alpha=1.0),
        "Gradient Boosting Regressor": GradientBoostingRegressor(random_state=42),
    }

    rows = []
    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        rows.append(
            {
                "Model": name,
                "R-Squared": float(r2_score(y_test, pred)),
                "RMSE": float(np.sqrt(mean_squared_error(y_test, pred))),
                "MAE": float(mean_absolute_error(y_test, pred)),
                "n_train": len(train),
                "n_test": len(test),
            }
        )
    return pd.DataFrame(rows).sort_values(by="R-Squared", ascending=False)


def max_abs_feature_target_corr(df: pd.DataFrame) -> float:
    """Largest |corr| between any non-ticker feature and the target."""
    cols = [c for c in FEATURE_COLS if c != "ticker"]
    corrs = [abs(df[c].corr(df[TARGET_COL])) for c in cols]
    return float(max(corrs)) if corrs else 0.0


def main() -> None:
    file_path = PROCESSED_DATA_DIR / "combined_stock_metrics.csv"
    raw = pd.read_csv(file_path)
    data = build_leakage_safe_frame(raw)
    train, test, cutoff = chronological_split(data, test_size=0.2)

    print(f"Rows after lag/target alignment: {len(data)}")
    print(f"Chronological cutoff (UTC): {cutoff}")
    print(f"Train={len(train)}  Test={len(test)}")
    print(
        f"Max |corr(feature, target)| on full aligned frame: "
        f"{max_abs_feature_target_corr(data):.4f}"
    )

    performance_df = evaluate_models(train, test)
    performance_file = MODEL_DIR / "model_performance.csv"
    performance_df.to_csv(performance_file, index=False)
    print(f"Model performance metrics saved to {performance_file}")
    print(performance_df.to_string(index=False))

    plt.figure(figsize=(10, 5))
    plt.barh(
        performance_df["Model"],
        performance_df["R-Squared"],
        color="#FF8F46",
        edgecolor="#0F3166",
    )
    plt.xlabel("R-Squared (chronological holdout)")
    plt.title("Leakage-safe model comparison — next-day return")
    plt.axvline(0.0, color="#0F3166", linewidth=0.8, linestyle="--")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    graph_path = GRAPHS_DIR / "model_comparison_r2.png"
    plt.savefig(graph_path, dpi=300)
    plt.close()
    print(f"Model comparison graph saved to {graph_path}")

    best = performance_df.iloc[0]
    print(
        f"Best (least-bad) model: {best['Model']} "
        f"R²={best['R-Squared']:.4f} RMSE={best['RMSE']:.6f} MAE={best['MAE']:.6f}"
    )


if __name__ == "__main__":
    main()
