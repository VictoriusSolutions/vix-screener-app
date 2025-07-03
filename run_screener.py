# === Import required libraries ===
import yfinance as yf  # For downloading stock price data
import pandas as pd  # For handling dataframes
import pandas_ta as ta  # For calculating technical indicators
import json  # For saving results to JSON file
from concurrent.futures import ThreadPoolExecutor, as_completed  # For running filters in parallel
from tqdm import tqdm  # For showing progress bar in loops

# === Step 1: Load all tickers from CSV ===
df = pd.read_csv("all_us_tickers.csv")  # Load tickers from a CSV file
all_tickers = df["symbol"].dropna().unique().tolist()  # Load all tickers without filtering
echo_count = len(all_tickers)
print(f"✅ Loaded {echo_count} tickers for screening")

# === RSI Filter ===
def check_rsi(symbol):
    try:
        # Download 1 year of daily stock price data
        data = yf.download(symbol, period="365d", interval="1d", progress=False, auto_adjust=True)

        # Handle multi-level column names if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
            data.columns.name = None

        # Skip if no usable data
        if "Close" not in data.columns or data["Close"].isna().all():
            return None

        # Skip if latest price is below $5 or not enough data
        latest_close = data["Close"].dropna().iloc[-1]
        if latest_close < 5 or len(data) < 20:
            return None

        # Calculate RSI and check if it's below 50
        data.ta.rsi(length=14, append=True)
        if "RSI_14" in data.columns and not data["RSI_14"].dropna().empty:
            latest_rsi = data["RSI_14"].dropna().iloc[-1]
            if latest_rsi < 50:
                return symbol
    except:
        return None
    return None

# === EMA Crossover ===
def check_ema_crossover(symbol):
    try:
        data = yf.download(symbol, period="365d", interval="1d", progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
            data.columns.name = None
        if "Close" not in data.columns or data["Close"].isna().all():
            return None
        latest_close = data["Close"].dropna().iloc[-1]
        if latest_close < 5 or len(data) < 25:
            return None

        # Calculate EMA 20 and EMA 50
        data["EMA20"] = ta.ema(data["Close"], length=20)
        data["EMA50"] = ta.ema(data["Close"], length=50)
        data.dropna(subset=["EMA20", "EMA50"], inplace=True)

        # Look for a crossover in the last 5 days
        for i in range(-5, -1):
            if data["EMA20"].iloc[i - 1] < data["EMA50"].iloc[i - 1] and data["EMA20"].iloc[i] > data["EMA50"].iloc[i]:
                return symbol
    except:
        return None
    return None

# === MACD Crossover ===
def check_macd_crossover(symbol):
    try:
        data = yf.download(symbol, period="365d", interval="1d", progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
            data.columns.name = None
        if "Close" not in data.columns or data["Close"].isna().all():
            return None
        latest_close = data["Close"].dropna().iloc[-1]
        if latest_close < 5 or len(data) < 30:
            return None

        # Calculate MACD and check crossover
        macd_df = ta.macd(data["Close"], fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.dropna().empty:
            data = pd.concat([data, macd_df], axis=1)
            for i in range(-5, -1):
                if data["MACD_12_26_9"].iloc[i - 1] < data["MACDs_12_26_9"].iloc[i - 1] and data["MACD_12_26_9"].iloc[i] > data["MACDs_12_26_9"].iloc[i]:
                    return symbol
    except:
        return None
    return None

# === Volume Spike ===
def check_volume_spike(symbol):
    try:
        data = yf.download(symbol, period="365d", interval="1d", progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
            data.columns.name = None
        if "Close" not in data.columns or data["Close"].isna().all():
            return None
        latest_close = data["Close"].dropna().iloc[-1]
        if latest_close < 5 or "Volume" not in data.columns or len(data) < 21:
            return None

        # Calculate average volume and compare
        avg_volume = data["Volume"].iloc[-20:-1].mean()
        if data["Volume"].iloc[-1] > avg_volume * 1.5:
            return symbol
    except:
        return None
    return None

# === Multithreaded Screening Phases ===
print("\n🔄 Running RSI filter...")
rsi_passed = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_rsi, ticker): ticker for ticker in all_tickers}
    for future in tqdm(as_completed(futures), total=len(futures)):
        result = future.result()
        if result:
            rsi_passed.append(result)
print(f"✅ RSI filter passed: {len(rsi_passed)} tickers")

print("\n🔄 Running EMA crossover filter...")
ema_passed = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_ema_crossover, ticker): ticker for ticker in rsi_passed}
    for future in tqdm(as_completed(futures), total=len(futures)):
        result = future.result()
        if result:
            ema_passed.append(result)
print(f"✅ EMA crossover passed: {len(ema_passed)} tickers")

print("\n🔄 Running MACD crossover filter...")
macd_passed = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_macd_crossover, ticker): ticker for ticker in ema_passed}
    for future in tqdm(as_completed(futures), total=len(futures)):
        result = future.result()
        if result:
            macd_passed.append(result)
print(f"✅ MACD crossover passed: {len(macd_passed)} tickers")

print("\n🔄 Running Volume Spike filter...")
volume_spike_passed = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_volume_spike, ticker): ticker for ticker in macd_passed}
    for future in tqdm(as_completed(futures), total=len(futures)):
        result = future.result()
        if result:
            volume_spike_passed.append(result)
print(f"✅ Volume Spike filter passed: {len(volume_spike_passed)} tickers")

# === Save results ===
with open("screened_results.json", "w") as f:
    json.dump(volume_spike_passed, f, indent=2)  # Save final passed tickers to JSON file

pd.DataFrame(volume_spike_passed, columns=["symbol"]).to_csv("screened_results.csv", index=False)  # Save as CSV

print("\n🔖 Screener complete.")
print("📁 Results saved to 'screened_results.json' and 'screened_results.csv'")
