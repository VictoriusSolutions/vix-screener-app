import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta

# === Polygon.io API Setup ===
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "oJKYVH4FZFzK4U2zi6jNb9ZT0SZRK53P")
BASE_URL = "https://api.polygon.io/v2/aggs/ticker"

CACHE_DIR = "data"
os.makedirs(CACHE_DIR, exist_ok=True)

# === Download and cache 1y daily OHLCV data from Polygon.io ===
def download_data(symbol):
    try:
        cache_file = os.path.join(CACHE_DIR, f"{symbol}.csv")
        today = datetime.utcnow().date()
        one_year_ago = today - timedelta(days=365)

        if os.path.exists(cache_file):
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if not df.empty and df.index[-1].date() >= today - timedelta(days=1):
                return df

        url = f"{BASE_URL}/{symbol}/range/1/day/{one_year_ago}/{today}?adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_API_KEY}"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if "results" not in data:
            raise ValueError(data.get("message", "No data returned."))

        records = []
        for item in data["results"]:
            ts = datetime.utcfromtimestamp(item["t"] / 1000)
            records.append({
                "timestamp": ts,
                "open": item["o"],
                "high": item["h"],
                "low": item["l"],
                "close": item["c"],
                "volume": item["v"]
            })

        df = pd.DataFrame(records)
        df = df.set_index("timestamp").sort_index()
        df.to_csv(cache_file)
        time.sleep(0.2)
        return df

    except Exception as e:
        print(f"Download error for {symbol}: {e}")
        return None

# === Compute RSI ===
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# === Compute EMA ===
def compute_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

# === Compute MACD ===
def compute_macd(series):
    ema12 = compute_ema(series, 12)
    ema26 = compute_ema(series, 26)
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line

# === RSI filter ===
def check_rsi(symbol, rsi_thresh=50, min_price=5, rsi_buffer=0, cached_df=None):
    try:
        df = cached_df if cached_df is not None else download_data(symbol)
        if df is None or len(df) < 20 or df["close"].iloc[-1] < min_price:
            return None

        df["RSI"] = compute_rsi(df["close"], period=14)
        if pd.notna(df["RSI"].iloc[-1]) and df["RSI"].iloc[-1] < rsi_thresh + rsi_buffer:
            return {"symbol": symbol, "rsi": round(df["RSI"].iloc[-1], 2)}
    except Exception as e:
        print(f"RSI error for {symbol}: {e}")
    return None

# === EMA crossover filter ===
def check_ema_crossover(symbol, cached_df=None):
    try:
        df = cached_df if cached_df is not None else download_data(symbol)
        if df is None or len(df) < 60 or df["close"].iloc[-1] < 5:
            return None

        df["EMA20"] = compute_ema(df["close"], 20)
        df["EMA50"] = compute_ema(df["close"], 50)
        df = df.dropna(subset=["EMA20", "EMA50"])

        for i in range(-5, -1):
            if df["EMA20"].iloc[i - 1] < df["EMA50"].iloc[i - 1] and df["EMA20"].iloc[i] > df["EMA50"].iloc[i]:
                return {"symbol": symbol}
    except Exception as e:
        print(f"EMA error for {symbol}: {e}")
    return None

# === MACD crossover filter ===
def check_macd_crossover(symbol, cached_df=None):
    try:
        df = cached_df if cached_df is not None else download_data(symbol)
        if df is None or len(df) < 35 or df["close"].iloc[-1] < 5:
            return None

        macd_line, signal_line = compute_macd(df["close"])
        df["MACD"] = macd_line
        df["Signal"] = signal_line
        df = df.dropna(subset=["MACD", "Signal"])

        for i in range(-5, -1):
            if df["MACD"].iloc[i - 1] < df["Signal"].iloc[i - 1] and df["MACD"].iloc[i] > df["Signal"].iloc[i]:
                return {"symbol": symbol}
    except Exception as e:
        print(f"MACD error for {symbol}: {e}")
    return None

# === Volume spike filter ===
def check_volume_spike(symbol, multiplier=1.5, cached_df=None):
    try:
        df = cached_df if cached_df is not None else download_data(symbol)
        if df is None or len(df) < 21 or df["close"].iloc[-1] < 5:
            return None

        avg_volume = df["volume"].iloc[-20:-1].mean()
        if df["volume"].iloc[-1] > avg_volume * multiplier:
            return {"symbol": symbol}
    except Exception as e:
        print(f"Volume error for {symbol}: {e}")
    return None
