import os
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = str(ROOT / "data" / "raw") + os.sep
PROCESSED_DATA_DIR = str(ROOT / "data" / "processed") + os.sep
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# Load environment variables
load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}


def execute_query(cursor, query, params=None, fetch_result=False):
    """Helper function to execute a query and optionally fetch results."""
    try:
        cursor.execute(query, params or ())
        if fetch_result:
            return cursor.fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return None


def save_to_database(data, stock_symbol):
    """Save processed data to MySQL database and locally."""
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Ensure the company exists in the companies table
        company_details = {
            "AAPL": ("Apple Inc.", "Technology", "Consumer electronics."),
            "MSFT": ("Microsoft Corp.", "Technology", "Enterprise software."),
            "GOOGL": ("Alphabet Inc.", "Technology", "Search and advertising."),
            "META": ("Meta Platforms", "Technology", "Social media and VR."),
        }
        if stock_symbol in company_details:
            name, sector, description = company_details[stock_symbol]
            execute_query(
                cursor,
                """
                INSERT INTO companies (ticker, name, sector, description)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                sector = VALUES(sector),
                description = VALUES(description)
            """,
                (stock_symbol, name, sector, description),
            )
            connection.commit()

            # Link the company to a category
            category_id = execute_query(
                cursor,
                "SELECT category_id FROM categories WHERE name = %s",
                (sector,),
                fetch_result=True,
            )
            if not category_id:
                execute_query(
                    cursor,
                    """
                    INSERT INTO categories (name)
                    VALUES (%s)
                    ON DUPLICATE KEY UPDATE name = VALUES(name)
                """,
                    (sector,),
                )
                connection.commit()
                category_id = execute_query(
                    cursor,
                    "SELECT category_id FROM categories WHERE name = %s",
                    (sector,),
                    fetch_result=True,
                )

            if category_id:
                category_id = category_id[0][0]
                execute_query(
                    cursor,
                    """
                    INSERT INTO stock_categories (ticker, category_id)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE category_id = VALUES(category_id)
                """,
                    (stock_symbol, category_id),
                )
                connection.commit()

        # Process and save data into stock_metrics
        data = data.dropna(subset=["Date"])
        for _, row in data.iterrows():
            if not isinstance(row["Date"], pd.Timestamp):
                continue
            date_value = row["Date"].strftime("%Y-%m-%d")
            execute_query(
                cursor,
                """
                INSERT INTO stock_metrics (ticker, date, close_price, daily_return, roi, volatility, sharpe_ratio)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                close_price = VALUES(close_price),
                daily_return = VALUES(daily_return),
                roi = VALUES(roi),
                volatility = VALUES(volatility),
                sharpe_ratio = VALUES(sharpe_ratio)
            """,
                (
                    stock_symbol,
                    date_value,
                    row["Close"],
                    row["Daily Return"],
                    row["ROI"],
                    row["Volatility"],
                    row["Sharpe Ratio"],
                ),
            )
        connection.commit()

        # Save processed data to the 'data/processed' folder for visualization
        processed_file_path = os.path.join(
            PROCESSED_DATA_DIR, f"processed_stock_metrics_{stock_symbol}.csv"
        )
        data.to_csv(processed_file_path, index=False)
        print(
            f"Processed stock metrics for {stock_symbol} saved to {processed_file_path}."
        )

    except Exception as e:
        print(f"Error saving data for {stock_symbol} to database: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def process_stock_data(file_name):
    """Process raw stock data and calculate financial metrics."""
    try:
        file_path = os.path.join(RAW_DATA_DIR, file_name)
        print(f"Processing {file_path}...")
        data = pd.read_csv(file_path, index_col="Date", parse_dates=True)

        # Ensure required columns exist
        if "Close" not in data.columns:
            raise ValueError("Missing required column: Close")

        # Drop rows with missing data in the 'Close' column
        data = data.dropna(subset=["Close"])

        # Add the ticker column based on the file name
        stock_symbol = file_name.split("_")[0]  # Extract stock symbol from file name
        data["ticker"] = stock_symbol

        # Calculate financial metrics
        # NOTE: Daily Return and ROI are algebraically identical (pct_change ≡
        # (Close/Close.shift(1))-1). Both are kept for dashboard/Tableau
        # compatibility, but must NEVER both appear as (feature, target) in ML.
        data["Daily Return"] = data["Close"].pct_change()
        data["ROI"] = (data["Close"] / data["Close"].shift(1)) - 1
        # min_periods=20 avoids one-observation "volatility"; analytical charts
        # may still use same-day rolling values — ML lagging lives in
        # predictive_models.build_leakage_safe_frame.
        data["Volatility"] = (
            data["Daily Return"].rolling(window=20, min_periods=20).std()
        )
        rolling_mean = data["Daily Return"].rolling(window=20, min_periods=20).mean()
        rolling_std = data["Daily Return"].rolling(window=20, min_periods=20).std()
        data["Sharpe Ratio"] = rolling_mean / rolling_std

        data = data.bfill().ffill()

        # Persist CSV always; MySQL is optional (skip if env vars missing).
        processed_file_path = os.path.join(
            PROCESSED_DATA_DIR, f"processed_stock_metrics_{stock_symbol}.csv"
        )
        data.reset_index().to_csv(processed_file_path, index=False)
        print(
            f"Processed stock metrics for {stock_symbol} saved to {processed_file_path}."
        )
        if all(DB_CONFIG.get(k) for k in ("host", "user", "password", "database")):
            save_to_database(data.reset_index(), stock_symbol)
        else:
            print(f"DB env not set — skipping MySQL write for {stock_symbol}.")
        return data.reset_index()
    except Exception as e:
        print(f"Error processing {file_name}: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    combined_data = []
    raw_files = os.listdir(RAW_DATA_DIR)
    for raw_file in raw_files:
        stock_data = process_stock_data(raw_file)
        if not stock_data.empty:
            combined_data.append(stock_data)

    # Combine all processed stock data into a single DataFrame
    if combined_data:
        combined_data_df = pd.concat(combined_data, ignore_index=True)
        combined_file_path = os.path.join(
            PROCESSED_DATA_DIR, "combined_stock_metrics.csv"
        )
        combined_data_df.to_csv(combined_file_path, index=False)
        print(f"Combined stock metrics saved to {combined_file_path}.")
