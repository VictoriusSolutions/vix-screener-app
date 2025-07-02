import yfinance as yf
import pandas_ta as ta
import pandas as pd

def download_data(symbol):
    try:
        data = yf.download(symbol, period="365d", interval="1d", progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
        return data if "Close" in data.columns else None
    except:
        return None

def check_rsi(symbol, rsi_thresh=50, min_price=5):
    data = download_data(symbol)
    if (
        data is None
        or "Close" not in data.columns
        or data["Close"].dropna().empty
        or len(data) < 20
    ):
        return None
    latest_close = data["Close"].dropna().iloc[-1]
    if latest_close < min_price:
        return None
    data.ta.rsi(length=14, append=True)
    if "RSI_14" in data.columns and not data["RSI_14"].dropna().empty:
        latest_rsi = data["RSI_14"].dropna().iloc[-1]
        if latest_rsi < rsi_thresh:
            return symbol
    return None

def check_ema_crossover(symbol):
    data = download_data(symbol)
    if (
        data is None
        or "Close" not in data.columns
        or data["Close"].dropna().empty
        or len(data) < 50
    ):
        return None
    latest_close = data["Close"].dropna().iloc[-1]
    if latest_close < 5:
        return None
    data["EMA20"] = ta.ema(data["Close"], length=20)
    data["EMA50"] = ta.ema(data["Close"], length=50)
    data = data.dropna(subset=["EMA20", "EMA50"])
    for i in range(-5, -1):
        if i < 1 or len(data) < abs(i) + 1:
            continue
        if data["EMA20"].iloc[i - 1] < data["EMA50"].iloc[i - 1] and data["EMA20"].iloc[i] > data["EMA50"].iloc[i]:
            return symbol
    return None

def check_macd_crossover(symbol):
    data = download_data(symbol)
    if (
        data is None
        or "Close" not in data.columns
        or data["Close"].dropna().empty
        or len(data) < 30
    ):
        return None
    latest_close = data["Close"].dropna().iloc[-1]
    if latest_close < 5:
        return None
    macd = ta.macd(data["Close"], fast=12, slow=26, signal=9)
    if macd is not None:
        data = pd.concat([data, macd], axis=1)
        if "MACD_12_26_9" not in data.columns or "MACDs_12_26_9" not in data.columns:
            return None
        data = data.dropna(subset=["MACD_12_26_9", "MACDs_12_26_9"])
        for i in range(-5, -1):
            if i < 1 or len(data) < abs(i) + 1:
                continue
            if data["MACD_12_26_9"].iloc[i - 1] < data["MACDs_12_26_9"].iloc[i - 1] and data["MACD_12_26_9"].iloc[i] > data["MACDs_12_26_9"].iloc[i]:
                return symbol
    return None

def check_volume_spike(symbol, multiplier=1.5):
    data = download_data(symbol)
    if (
        data is None
        or "Volume" not in data.columns
        or "Close" not in data.columns
        or data["Close"].dropna().empty
        or len(data) < 21
    ):
        return None
    latest_close = data["Close"].dropna().iloc[-1]
    if latest_close < 5:
        return None
    avg_volume = data["Volume"].iloc[-20:-1].mean()
    if data["Volume"].iloc[-1] > avg_volume * multiplier:
        return symbol
    return None
 