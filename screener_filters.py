# === Import necessary libraries ===
import yfinance as yf  # For downloading stock price data from Yahoo Finance
import pandas_ta as ta  # For technical indicators like RSI, EMA, MACD
import pandas as pd  # For working with tabular data using DataFrames

# === Function to download historical stock data ===
def download_data(symbol):
    try:
        # Download 1 year of daily price data for the given symbol with adjusted prices
        data = yf.download(symbol, period="365d", interval="1d", progress=False, auto_adjust=True)

        # If columns are in MultiIndex format, flatten them
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]  # Keep only the first level of column names

        return data  # Return the DataFrame of downloaded data
    except:
        return None  # Return None if download fails

# === RSI filter function ===
# === RSI filter function (Updated for transparency and debugging) ===
def check_rsi(symbol, rsi_thresh=50, min_price=5, rsi_buffer=0):
    try:
        data = download_data(symbol)  # Get historical stock data for the symbol

        # Validate data structure and price availability
        if (
            data is None or
            not isinstance(data, pd.DataFrame) or
            "Close" not in data.columns or
            len(data) < 20
        ):
            return None

        close = data["Close"].dropna()  # Use adjusted closing prices
        if close.empty or close.iloc[-1] < min_price:
            return None

        # Calculate RSI(14) using pandas_ta
        data.ta.rsi(length=14, append=True)
        rsi = data["RSI_14"].dropna()

        if not rsi.empty:
            latest_rsi = rsi.iloc[-1]

            # DEBUG: Print the symbol and RSI used (for CLI or log visibility)
            print(f"{symbol}: RSI = {latest_rsi:.2f}, Threshold = {rsi_thresh}")

            # Return both symbol and RSI if below threshold (plus optional buffer)
            if latest_rsi < rsi_thresh + rsi_buffer:
                return {"symbol": symbol, "rsi": round(latest_rsi, 2)}  # Rounded for display/debugging
    except Exception as e:
        print(f"Error checking RSI for {symbol}: {e}")
        return None

    return None  # Default if conditions not met


# === EMA crossover filter ===
def check_ema_crossover(symbol):
    try:
        data = download_data(symbol)  # Download data for the given stock symbol

        # Check if data is valid, has 'Close', and is long enough
        if (
            data is None or
            not isinstance(data, pd.DataFrame) or
            "Close" not in data.columns or
            len(data) < 50
        ):
            return None

        close = data["Close"].dropna()  # Clean up closing prices
        if close.empty or close.iloc[-1] < 5:  # Skip if price is too low
            return None

        # Compute Exponential Moving Averages (EMAs)
        data["EMA20"] = ta.ema(close, length=20)
        data["EMA50"] = ta.ema(close, length=50)
        data = data.dropna(subset=["EMA20", "EMA50"])  # Remove rows with missing EMAs

        if len(data) < 6:  # Need at least 6 rows for crossover comparison
            return None

        # Check for EMA20 crossing above EMA50 within the last 5 days
        for i in range(-5, -1):
            if data["EMA20"].iloc[i - 1] < data["EMA50"].iloc[i - 1] and data["EMA20"].iloc[i] > data["EMA50"].iloc[i]:
                return symbol  # Return symbol if crossover condition is met
    except:
        return None  # Handle error silently
    return None  # Default return

# === MACD crossover filter ===
def check_macd_crossover(symbol):
    try:
        data = download_data(symbol)  # Download stock data

        # Validate structure and size
        if (
            data is None or
            not isinstance(data, pd.DataFrame) or
            "Close" not in data.columns or
            len(data) < 30
        ):
            return None

        close = data["Close"].dropna()  # Get cleaned close prices
        if close.empty or close.iloc[-1] < 5:  # Skip if price is too low
            return None

        # Calculate MACD indicators
        macd = ta.macd(close, fast=12, slow=26, signal=9)
        if macd is not None:
            data = pd.concat([data, macd], axis=1)  # Combine with original data

            # Ensure both MACD and Signal lines exist
            if "MACD_12_26_9" not in data.columns or "MACDs_12_26_9" not in data.columns:
                return None

            data = data.dropna(subset=["MACD_12_26_9", "MACDs_12_26_9"])  # Clean NaNs
            if len(data) < 6:
                return None

            # Look for MACD crossover in recent 5 days
            for i in range(-5, -1):
                if data["MACD_12_26_9"].iloc[i - 1] < data["MACDs_12_26_9"].iloc[i - 1] and data["MACD_12_26_9"].iloc[i] > data["MACDs_12_26_9"].iloc[i]:
                    return symbol  # Return symbol if crossover happened
    except:
        return None
    return None

# === Volume spike filter ===
def check_volume_spike(symbol, multiplier=1.5):
    try:
        data = download_data(symbol)  # Download price and volume data

        # Validate volume and close columns and size
        if (
            data is None or
            not isinstance(data, pd.DataFrame) or
            "Close" not in data.columns or
            "Volume" not in data.columns or
            len(data) < 21
        ):
            return None

        close = data["Close"].dropna()  # Get cleaned close prices
        if close.empty or close.iloc[-1] < 5:
            return None  # Ignore penny stocks

        # Calculate average volume for the last 20 days (excluding today)
        avg_volume = data["Volume"].iloc[-20:-1].mean()

        # Check if today's volume is at least 1.5x the recent average
        if pd.notna(avg_volume) and data["Volume"].iloc[-1] > avg_volume * multiplier:
            return symbol  # Return symbol if spike detected
    except:
        return None
    return None
