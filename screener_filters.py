import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta

# === Polygon.io API Setup ===
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "UEU7Nv69DiEpeGGeDrTLb575P4e7QTSe")
GROUPED_CACHE_FILE = os.path.join("data", "grouped_ohlcv.csv")
os.makedirs("data", exist_ok=True)

# === Load grouped OHLCV data for all stocks (1 API call) ===
def load_grouped_data(date=None):
    try:
        date = date or datetime.utcnow().date() - timedelta(days=1)
        date_str = date.strftime("%Y-%m-%d")

        if os.path.exists(GROUPED_CACHE_FILE):
            df = pd.read_csv(GROUPED_CACHE_FILE, parse_dates=["timestamp"])
            if not df.empty and df["timestamp"].max().date() >= date:
                return df.set_index("symbol")

        url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date_str}?adjusted=true&apiKey={POLYGON_API_KEY}"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if "results" not in data:
            raise ValueError(data.get("message", "No grouped data returned."))

        records = []
        for item in data["results"]:
            ts = datetime.utcfromtimestamp(item["t"] / 1000)
            records.append({
                "symbol": item["T"],
                "timestamp": ts,
                "open": item["o"],
                "high": item["h"],
                "low": item["l"],
                "close": item["c"],
                "volume": item["v"]
            })

        df = pd.DataFrame(records)
        df.to_csv(GROUPED_CACHE_FILE, index=False)
        return df.set_index("symbol")

    except Exception as e:
        print(f"Grouped data error: {e}")
        return pd.DataFrame()

# === Build mini dataframe for a single symbol from grouped cache ===
def download_data(symbol):
    try:
        grouped_df = load_grouped_data()
        if symbol not in grouped_df.index:
            raise ValueError("Symbol not in grouped data.")
        row = grouped_df.loc[symbol]
        df = pd.DataFrame([row])
        df.index = [row["timestamp"]]
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
        if df is None or df.empty or df["close"].iloc[-1] < min_price:
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
        if df is None or df.empty or df["close"].iloc[-1] < 5:
            return None

        df["EMA20"] = compute_ema(df["close"], 20)
        df["EMA50"] = compute_ema(df["close"], 50)
        df = df.dropna(subset=["EMA20", "EMA50"])

        if len(df) >= 2 and df["EMA20"].iloc[-2] < df["EMA50"].iloc[-2] and df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]:
            return {"symbol": symbol}
    except Exception as e:
        print(f"EMA error for {symbol}: {e}")
    return None

# === MACD crossover filter ===
def check_macd_crossover(symbol, cached_df=None):
    try:
        df = cached_df if cached_df is not None else download_data(symbol)
        if df is None or df.empty or df["close"].iloc[-1] < 5:
            return None

        macd_line, signal_line = compute_macd(df["close"])
        df["MACD"] = macd_line
        df["Signal"] = signal_line
        df = df.dropna(subset=["MACD", "Signal"])

        if len(df) >= 2 and df["MACD"].iloc[-2] < df["Signal"].iloc[-2] and df["MACD"].iloc[-1] > df["Signal"].iloc[-1]:
            return {"symbol": symbol}
    except Exception as e:
        print(f"MACD error for {symbol}: {e}")
    return None

# === Volume spike filter ===
def check_volume_spike(symbol, multiplier=1.5, cached_df=None):
    try:
        df = cached_df if cached_df is not None else download_data(symbol)
        if df is None or df.empty or df["close"].iloc[-1] < 5:
            return None

        return {"symbol": symbol} if df["volume"].iloc[-1] > multiplier * df["volume"].mean() else None
    except Exception as e:
        print(f"Volume error for {symbol}: {e}")
    return None
