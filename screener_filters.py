import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from pandas_ta import rsi, ema, macd  # Use pandas_ta explicitly

# === Twelve Data API Setup ===
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY", "7251f7fecf024e339e69f9b3acd53253")
BASE_URL = "https://api.twelvedata.com/indicator"

CACHE_DIR = "data"
os.makedirs(CACHE_DIR, exist_ok=True)

# === Download and cache indicators from Twelve Data API ===
def download_indicators(symbol):
    today = datetime.utcnow().date()
    cache_file = os.path.join(CACHE_DIR, f"{symbol}_indicators_{today}.json")

    if os.path.exists(cache_file):
        return pd.read_json(cache_file)

    try:
        params = {
            "symbol": symbol,
            "interval": "1day",
            "indicators": "rsi,macd,ema",
            "outputsize": 30,
            "apikey": TWELVE_API_KEY,
        }

        url = f"{BASE_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())
        print("Requesting:", url)
        resp = requests.get(url)
        data = resp.json()

        if "values" not in data:
            raise ValueError(data.get("message", "No indicator data returned."))

        df = pd.DataFrame(data["values"])
        df = df.set_index(pd.to_datetime(df["datetime"])).sort_index()
        df = df.apply(pd.to_numeric, errors="coerce")
        df.to_json(cache_file)
        return df

    except Exception as e:
        print(f"Download error for {symbol}: {e}")
        return None

# === RSI filter ===
def check_rsi(symbol, rsi_thresh=50, min_price=5, rsi_buffer=0):
    try:
        df = download_indicators(symbol)
        if df is None or "rsi" not in df.columns or df.iloc[-1]["close"] < min_price:
            return None

        rsi_val = df["rsi"].dropna().iloc[-1]
        if rsi_val < rsi_thresh + rsi_buffer:
            print(f"{symbol} RSI: {rsi_val:.2f}")
            return {"symbol": symbol, "rsi": round(rsi_val, 2)}
    except Exception as e:
        print(f"RSI error for {symbol}: {e}")
    return None

# === EMA crossover filter ===
def check_ema_crossover(symbol):
    try:
        df = download_indicators(symbol)
        if df is None or "ema20" not in df.columns or "ema50" not in df.columns:
            return None

        df["EMA20"] = df["ema20"]
        df["EMA50"] = df["ema50"]

        for i in range(-5, -1):
            if df["EMA20"].iloc[i - 1] < df["EMA50"].iloc[i - 1] and df["EMA20"].iloc[i] > df["EMA50"].iloc[i]:
                return {"symbol": symbol}
    except Exception as e:
        print(f"EMA error for {symbol}: {e}")
    return None

# === MACD crossover filter ===
def check_macd_crossover(symbol):
    try:
        df = download_indicators(symbol)
        if df is None or "macd" not in df.columns or "macd_signal" not in df.columns:
            return None

        for i in range(-5, -1):
            if df["macd"].iloc[i - 1] < df["macd_signal"].iloc[i - 1] and df["macd"].iloc[i] > df["macd_signal"].iloc[i]:
                return {"symbol": symbol}
    except Exception as e:
        print(f"MACD error for {symbol}: {e}")
    return None

# === Volume spike filter ===
def check_volume_spike(symbol, multiplier=1.5):
    try:
        df = download_indicators(symbol)
        if df is None or "volume" not in df.columns:
            return None

        if len(df) < 21 or df["close"].iloc[-1] < 5:
            return None

        avg_volume = df["volume"].iloc[-20:-1].mean()
        if df["volume"].iloc[-1] > avg_volume * multiplier:
            return {"symbol": symbol}
    except Exception as e:
        print(f"Volume error for {symbol}: {e}")
    return None
