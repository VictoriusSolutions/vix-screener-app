import os
import time
import pandas as pd
import pandas_ta as ta
import finnhub
from datetime import datetime, timedelta

# Setup: Finnhub client
FINNHUB_API_KEY = "d1lg2s1r01qt4thfvtk0d1lg2s1r01qt4thfvtkg"  # Replace with your actual key
client = finnhub.Client(api_key=FINNHUB_API_KEY)

# Directory for caching
CACHE_DIR = "data"
os.makedirs(CACHE_DIR, exist_ok=True)

# === Helper: Convert date to UNIX timestamp
def to_unix(dt):
    return int(time.mktime(dt.timetuple()))

# === Download and cache 1y daily OHLCV data ===
def download_data(symbol):
    try:
        cache_file = os.path.join(CACHE_DIR, f"{symbol}.csv")
        today = datetime.utcnow().date()

        # Check cache
        if os.path.exists(cache_file):
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if df.index[-1].date() >= today - timedelta(days=1):
                return df  # Use cached version

        # Otherwise fetch from API
        to_ts = int(time.time())
        from_ts = to_unix(datetime.utcnow() - timedelta(days=365))

        candles = client.stock_candles(symbol, "D", from_ts, to_ts)
        if candles.get("s") != "ok":
            return None

        df = pd.DataFrame({
            "close": candles["c"],
            "open": candles["o"],
            "high": candles["h"],
            "low": candles["l"],
            "volume": candles["v"],
            "timestamp": pd.to_datetime(candles["t"], unit="s")
        }).set_index("timestamp")

        df.to_csv(cache_file)  # Save to cache
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
