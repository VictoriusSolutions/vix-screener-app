import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from pandas_ta import rsi, ema, macd

# === Polygon.io API Setup ===
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "LzVEztPbgAekcs6mC5CBQ2Joa0_KNYAs")
BASE_URL = "https://api.polygon.io/v2/aggs/ticker"

CACHE_DIR = "data"
os.makedirs(CACHE_DIR, exist_ok=True)

# === Download and cache 1y daily OHLCV data from Polygon.io ===
def download_data(symbol):
    try:
        cache_file = os.path.join(CACHE_DIR, f"{symbol}.csv")
        today = datetime.utcnow().date()
        one_year_ago = today - timedelta(days=365)

        # Use cached file if it's up to date
        if os.path.exists(cache_file):
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if not df.empty and df.index[-1].date() >= today - timedelta(days=1):
                return df

        url = f"{BASE_URL}/{symbol}/range/1/day/{one_year_ago}/{today}?adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_API_KEY}"
        print("Requesting:", url)

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
        time.sleep(0.2)  # Throttle slightly
        return df

    except Exception as e:
        print(f"Download error for {symbol}: {e}")
        return None

# === RSI filter ===
def check_rsi(symbol, rsi_thresh=50, min_price=5, rsi_buffer=0):
    try:
        df = download_data(symbol)
        if df is None or len(df) < 20 or df["close"].iloc[-1] < min_price:
            return None

        df["RSI"] = rsi(df["close"], length=14)
        if pd.notna(df["RSI"].iloc[-1]) and df["RSI"].iloc[-1] < rsi_thresh + rsi_buffer:
            print(f"{symbol} RSI: {df['RSI'].iloc[-1]:.2f}")
            return {"symbol": symbol, "rsi": round(df["RSI"].iloc[-1], 2)}
    except Exception as e:
        print(f"RSI error for {symbol}: {e}")
    return None

# === EMA crossover filter ===
def check_ema_crossover(symbol):
    try:
        df = download_data(symbol)
        if df is None or len(df) < 60 or df["close"].iloc[-1] < 5:
            return None

        df["EMA20"] = ema(df["close"], length=20)
        df["EMA50"] = ema(df["close"], length=50)
        df = df.dropna(subset=["EMA20", "EMA50"])

        for i in range(-5, -1):
            if df["EMA20"].iloc[i - 1] < df["EMA50"].iloc[i - 1] and df["EMA20"].iloc[i] > df["EMA50"].iloc[i]:
                return {"symbol": symbol}
    except Exception as e:
        print(f"EMA error for {symbol}: {e}")
    return None

# === MACD crossover filter ===
def check_macd_crossover(symbol):
    try:
        df = download_data(symbol)
        if df is None or len(df) < 35 or df["close"].iloc[-1] < 5:
            return None

        macd_df = macd(df["close"])
        df = pd.concat([df, macd_df], axis=1).dropna()
        if "MACD_12_26_9" not in df.columns or "MACDs_12_26_9" not in df.columns:
            return None

        for i in range(-5, -1):
            if df["MACD_12_26_9"].iloc[i - 1] < df["MACDs_12_26_9"].iloc[i - 1] and df["MACD_12_26_9"].iloc[i] > df["MACDs_12_26_9"].iloc[i]:
                return {"symbol": symbol}
    except Exception as e:
        print(f"MACD error for {symbol}: {e}")
    return None

# === Volume spike filter ===
def check_volume_spike(symbol, multiplier=1.5):
    try:
        df = download_data(symbol)
        if df is None or len(df) < 21 or df["close"].iloc[-1] < 5:
            return None

        avg_volume = df["volume"].iloc[-20:-1].mean()
        if df["volume"].iloc[-1] > avg_volume * multiplier:
            return {"symbol": symbol}
    except Exception as e:
        print(f"Volume error for {symbol}: {e}")
    return None
