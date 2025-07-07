import os
import time
import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime, timedelta

# === Twelve Data API Setup ===
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY", "7251f7fecf024e339e69f9b3acd53253")
BASE_URL = "https://api.twelvedata.com/time_series"

CACHE_DIR = "data"
os.makedirs(CACHE_DIR, exist_ok=True)

# === Download and cache 1y daily OHLCV data ===
def download_data(symbol):
    try:
        cache_file = os.path.join(CACHE_DIR, f"{symbol}.csv")
        today = datetime.utcnow().date()

        # Use cached file if it's up to date
        if os.path.exists(cache_file):
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if not df.empty and df.index[-1].date() >= today - timedelta(days=1):
                return df

        # Request from Twelve Data API
        params = {
            "symbol": symbol,
            "interval": "1day",
            "outputsize": 500,
            "start_date": (today - timedelta(days=365)).strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d"),
            "apikey": TWELVE_API_KEY,
        }

        url = f"{BASE_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())
        print("Requesting:", url)
        resp = requests.get(url)
        data = resp.json()

        if "values" not in data:
            raise ValueError(data.get("message", "No data returned."))

        df = pd.DataFrame(data["values"])
        df = df.rename(columns={"datetime": "timestamp", "close": "close", "open": "open", "high": "high", "low": "low", "volume": "volume"})
        df = df.set_index(pd.to_datetime(df["timestamp"])).sort_index()
        df = df[["open", "high", "low", "close", "volume"]].astype(float)

        df.to_csv(cache_file)
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

        df.ta.rsi(length=14, append=True)
        rsi = df["RSI_14"].dropna()
        if not rsi.empty and rsi.iloc[-1] < rsi_thresh + rsi_buffer:
            print(f"{symbol} RSI: {rsi.iloc[-1]:.2f}")
            return {"symbol": symbol, "rsi": round(rsi.iloc[-1], 2)}
    except Exception as e:
        print(f"RSI error for {symbol}: {e}")
    return None

# === EMA crossover filter ===
def check_ema_crossover(symbol):
    try:
        df = download_data(symbol)
        if df is None or len(df) < 60 or df["close"].iloc[-1] < 5:
            return None

        df["EMA20"] = ta.ema(df["close"], length=20)
        df["EMA50"] = ta.ema(df["close"], length=50)
        df = df.dropna(subset=["EMA20", "EMA50"])

        for i in range(-5, -1):
            if df["EMA20"].iloc[i - 1] < df["EMA50"].iloc[i - 1] and df["EMA20"].iloc[i] > df["EMA50"].iloc[i]:
                return symbol
    except Exception as e:
        print(f"EMA error for {symbol}: {e}")
    return None

# === MACD crossover filter ===
def check_macd_crossover(symbol):
    try:
        df = download_data(symbol)
        if df is None or len(df) < 35 or df["close"].iloc[-1] < 5:
            return None

        macd = ta.macd(df["close"])
        df = pd.concat([df, macd], axis=1).dropna()
        if "MACD_12_26_9" not in df.columns or "MACDs_12_26_9" not in df.columns:
            return None

        for i in range(-5, -1):
            if df["MACD_12_26_9"].iloc[i - 1] < df["MACDs_12_26_9"].iloc[i - 1] and df["MACD_12_26_9"].iloc[i] > df["MACDs_12_26_9"].iloc[i]:
                return symbol
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
            return symbol
    except Exception as e:
        print(f"Volume error for {symbol}: {e}")
    return None
