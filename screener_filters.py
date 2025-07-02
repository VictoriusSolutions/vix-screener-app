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
    if data is None or data["Close"].dropna().iloc[-1] < min_price or len(data) < 20:
        return None
    data.ta.rsi(length=14, append=True)
    if "RSI_14" in data.columns:
        latest_rsi = data["RSI_14"].dropna().iloc[-1]
        if latest_rsi < rsi_thresh:
            return symbol
    return None

def check_ema_crossover(symbol):
    data = download_data(symbol)
    if data is None or data["Close"].dropna().iloc[-1] < 5 or len(data) < 50:
        return None
    data["EMA20"] = ta.ema(data["Close"], length=20)
    data["EMA50"] = ta.ema(data["Close"], length=50)
    for i in range(-5, -1):
        if data["EMA20"].iloc[i - 1] < data["EMA50"].iloc[i - 1] and data["EMA20"].iloc[i] > data["EMA50"].iloc[i]:
            return symbol
    return None

def check_macd_crossover(symbol):
    data = download_data(symbol) 
    if data is None or data["Close"].dropna().iloc[-1] < 5 or len(data) < 30:
        return None
    macd = ta.macd(data["Close"], fast=12, slow=26, signal=9)
    if macd is not None:
        data = pd.concat([data, macd], axis=1)
        for i in range(-5, -1):
            if data["MACD_12_26_9"].iloc[i - 1] < data["MACDs_12_26_9"].iloc[i - 1] and data["MACD_12_26_9"].iloc[i] > data["MACDs_12_26_9"].iloc[i]:
                return symbol
    return None

def check_volume_spike(symbol, multiplier=1.5):
    data = download_data(symbol)
    if data is None or "Volume" not in data.columns or len(data) < 21:
        return None
    avg_volume = data["Volume"].iloc[-20:-1].mean()
    if data["Volume"].iloc[-1] > avg_volume * multiplier:
        return symbol
    return None
