import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

# === Configure Twelve Data API ===
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY") or "7251f7fecf024e339e69f9b3acd53253"  # Replace with your key
BASE_URL = "https://api.twelvedata.com"

# === Caching setup ===
CACHE_DIR = "data"
os.makedirs(CACHE_DIR, exist_ok=True)

# === Download and cache 1y daily OHLCV data from Twelve Data ===
def download_data(symbol):
    try:
        cache_file = os.path.join(CACHE_DIR, f"{symbol}.csv")
        today = datetime.utcnow().date()

        # Load cache if fresh
        if os.path.exists(cache_file):
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if df.index[-1].date() >= today - timedelta(days=1):
                return df

        # Manually build URL to ensure apikey is passed correctly
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        url = (
            f"{BASE_URL}/time_series?symbol={symbol}&interval=1day&outputsize=500"
            f"&start_date={start_date}&end_date={end_date}&apikey={TWELVE_API_KEY}"
        )

        print(f"Requesting: {url}")
        response = requests.get(url)
        data = response.json()

        if "values" not in data:
            print(f"Download error for {symbol}: {data.get('message', 'Unknown error')}")
            return None

        df = pd.DataFrame(data["values"])
        df.set_index("datetime", inplace=True)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        df = df.rename(columns={
            "close": "close",
            "open": "open",
            "high": "high",
            "low": "low",
            "volume": "volume"
        })

        df[["close", "open", "high", "low", "volume"]] = df[["close", "open", "high", "low", "volume"]].astype(float)

        df.to_csv(cache_file)
        return df

    except Exception as e:
        print(f"Download error for {symbol}: {e}")
        return None

# === Manual RSI calculation ===
def manual_rsi(close_prices, period=14):
    delta = close_prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# === RSI filter ===
def check_rsi(symbol, rsi_thresh=50, min_price=5, rsi_buffer=0):
    try:
        df = download_data(symbol)
        if df is None or len(df) < 20 or df["close"].iloc[-1] < min_price:
            return None

        rsi_series = manual_rsi(df["close"])
        latest_rsi = rsi_series.iloc[-1]

        if not pd.isna(latest_rsi):
            print(f"{symbol} RSI: {latest_rsi:.2f}")
            if float(latest_rsi) < float(rsi_thresh + rsi_buffer):
                return {"symbol": symbol, "rsi": round(float(latest_rsi), 2)}
    except Exception as e:
        print(f"RSI error for {symbol}: {e}")
    return None

# === Run test if executed directly ===
if __name__ == "__main__":
    result = check_rsi("AAPL", rsi_thresh=55)
    print(result)