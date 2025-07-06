import yfinance as yf
import pandas_ta as ta
import pandas as pd

# === Function to download historical stock data ===
def download_data(symbol):
    try:
        # Use unadjusted prices and apply Adjusted Close manually
        data = yf.download(symbol, period="365d", interval="1d", progress=False, auto_adjust=False)

        # Flatten columns if multi-indexed
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]

        # Overwrite Close with Adjusted Close to calculate RSI consistently
        if "Adj Close" in data.columns:
            data["Close"] = data["Adj Close"]

        return data
    except:
        return None

# === RSI filter function (improved for debugging and accuracy) ===
def check_rsi(symbol, rsi_thresh=50, min_price=5, rsi_buffer=0):
    try:
        data = download_data(symbol)

        if (
            data is None or
            not isinstance(data, pd.DataFrame) or
            "Close" not in data.columns or
            len(data) < 20
        ):
            return None

        close = data["Close"].dropna()
        if close.empty or close.iloc[-1] < min_price:
            return None

        data.ta.rsi(length=14, append=True)
        rsi = data["RSI_14"].dropna()

        if not rsi.empty:
            latest_rsi = rsi.iloc[-1]
            print(f"{symbol}: RSI = {latest_rsi:.2f}, Threshold = {rsi_thresh}")
            if latest_rsi < rsi_thresh + rsi_buffer:
                return {"symbol": symbol, "rsi": round(latest_rsi, 2)}
    except Exception as e:
        print(f"Error checking RSI for {symbol}: {e}")
        return None

    return None

# === EMA crossover filter ===
def check_ema_crossover(symbol):
    try:
        data = download_data(symbol)
        if (
            data is None or
            not isinstance(data, pd.DataFrame) or
            "Close" not in data.columns or
            len(data) < 50
        ):
            return None

        close = data["Close"].dropna()
        if close.empty or close.iloc[-1] < 5:
            return None

        data["EMA20"] = ta.ema(close, length=20)
        data["EMA50"] = ta.ema(close, length=50)
        data = data.dropna(subset=["EMA20", "EMA50"])

        if len(data) < 6:
            return None

        for i in range(-5, -1):
            if data["EMA20"].iloc[i - 1] < data["EMA50"].iloc[i - 1] and data["EMA20"].iloc[i] > data["EMA50"].iloc[i]:
                return symbol
    except:
        return None
    return None

# === MACD crossover filter ===
def check_macd_crossover(symbol):
    try:
        data = download_data(symbol)
        if (
            data is None or
            not isinstance(data, pd.DataFrame) or
            "Close" not in data.columns or
            len(data) < 30
        ):
            return None

        close = data["Close"].dropna()
        if close.empty or close.iloc[-1] < 5:
            return None

        macd = ta.macd(close, fast=12, slow=26, signal=9)
        if macd is not None:
            data = pd.concat([data, macd], axis=1)
            if "MACD_12_26_9" not in data.columns or "MACDs_12_26_9" not in data.columns:
                return None

            data = data.dropna(subset=["MACD_12_26_9", "MACDs_12_26_9"])
            if len(data) < 6:
                return None

            for i in range(-5, -1):
                if data["MACD_12_26_9"].iloc[i - 1] < data["MACDs_12_26_9"].iloc[i - 1] and data["MACD_12_26_9"].iloc[i] > data["MACDs_12_26_9"].iloc[i]:
                    return symbol
    except:
        return None
    return None

# === Volume spike filter ===
def check_volume_spike(symbol, multiplier=1.5):
    try:
        data = download_data(symbol)
        if (
            data is None or
            not isinstance(data, pd.DataFrame) or
            "Close" not in data.columns or
            "Volume" not in data.columns or
            len(data) < 21
        ):
            return None

        close = data["Close"].dropna()
        if close.empty or close.iloc[-1] < 5:
            return None

        avg_volume = data["Volume"].iloc[-20:-1].mean()
        if pd.notna(avg_volume) and data["Volume"].iloc[-1] > avg_volume * multiplier:
            return symbol
    except:
        return None
    return None
