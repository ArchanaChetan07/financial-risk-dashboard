import os
import pandas as pd
import yfinance as yf
import sweetviz as sv

# Create directories if they don't exist
RAW_DATA_DIR = "../data/raw/"
PROCESSED_DATA_DIR = "../data/processed/"
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)


def fetch_yahoo_finance_data(ticker, period="1y"):
    """Fetch historical stock data from Yahoo Finance."""
    try:
        print(f"Fetching data for {ticker} from Yahoo Finance...")
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)
        file_path = os.path.join(RAW_DATA_DIR, f"{ticker}_yahoo.csv")
        data.to_csv(file_path)
        print(f"Data saved to {file_path}")
    except Exception as e:
        print(f"Error fetching Yahoo Finance data for {ticker}: {e}")


def generate_eda_report(file_name):
    """Generate an EDA report using Sweetviz."""
    try:
        file_path = os.path.join(RAW_DATA_DIR, file_name)
        data = pd.read_csv(file_path)
        report = sv.analyze(data)
        report_file = os.path.join(PROCESSED_DATA_DIR, f"{file_name}_eda_report.html")
        report.show_html(report_file)
        print(f"EDA report generated: {report_file}")
    except Exception as e:
        print(f"Error generating EDA report for {file_name}: {e}")


if __name__ == "__main__":
    # Fetch data from Yahoo Finance
    fetch_yahoo_finance_data("AAPL", period="1y")
    fetch_yahoo_finance_data("MSFT", period="1y")
    fetch_yahoo_finance_data("GOOGL", period="1y")
    fetch_yahoo_finance_data("META", period="1y")

    # Generate EDA reports for fetched data
    raw_files = os.listdir(RAW_DATA_DIR)
    for raw_file in raw_files:
        generate_eda_report(raw_file)
