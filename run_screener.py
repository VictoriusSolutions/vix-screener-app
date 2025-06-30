# === Import required libraries ===
import yfinance as yf               # To fetch stock price history
import pandas_ta as ta              # To calculate RSI and EMA indicators
import pandas as pd                 # To load CSV and manipulate tabular data
import json                         # To save results as a JSON file
import warnings                     # To suppress any annoying future warnings

# === Suppress FutureWarnings from yfinance about auto_adjust ===
warnings.simplefilter(action='ignore', category=FutureWarning)


# === STEP 1: Function to filter for RSI < 30 ===
def screen_rsi_oversold(tickers):
    results = []  # Initialize an empty list to hold tickers that meet the RSI condition

    for symbol in tickers:
        # Download the last 365 days of daily price data for each ticker
        data = yf.download(symbol, period="365d", interval="1d", progress=False)

        # Skip this ticker if no data was returned
        if data.empty:
            continue

        # Calculate RSI (Relative Strength Index) with a 14-day window
        rsi = ta.rsi(data['Close'], length=14)

        # Only proceed if RSI was successfully calculated and not all NaN
        if rsi is not None and not rsi.isna().all():
            data['RSI'] = rsi  # Add RSI column to the DataFrame

            # Drop rows where RSI is still NaN
            data = data.dropna(subset=['RSI'])

            # If data is still valid, check if latest RSI < 30
            if not data.empty and data['RSI'].iloc[-1] < 30:
                results.append(symbol)  # Add ticker to result list

    return results  # Return tickers with RSI < 30


# === STEP 2: Function to filter for EMA 9 > EMA 21 crossover ===
def screen_bullish_crossover(tickers):
    final = []  # List to store tickers that meet the crossover condition

    for symbol in tickers:
        # Download 365 days of daily price data
        data = yf.download(symbol, period="365d", interval="1d", progress=False)

        # Skip ticker if no data
        if data.empty:
            continue

        # Calculate 9-day and 21-day EMAs
        data['EMA_short'] = ta.ema(data['Close'], length=9)
        data['EMA_long'] = ta.ema(data['Close'], length=21)

        # Drop any rows with missing EMA values
        data = data.dropna(subset=['EMA_short', 'EMA_long'])

        # Proceed only if data is valid and crossover condition is met:
        # - Yesterday, short EMA was below long EMA
        # - Today, short EMA is above long EMA
        if not data.empty and \
           data['EMA_short'].iloc[-2] < data['EMA_long'].iloc[-2] and \
           data['EMA_short'].iloc[-1] > data['EMA_long'].iloc[-1]:
            final.append(symbol)  # Add ticker to the final results

    return final  # Return list of crossover-confirmed tickers


# === STEP 3: Load tickers from a CSV file ===
# Make sure you have 'nasdaq_nyse_tickers.csv' in the same folder with a column named 'symbol'
df = pd.read_csv("all_us_tickers.csv")
all_tickers = df['symbol'].tolist()
#all_tickers = all_tickers[:50]  # ✅ Limit to first 50 tickers for testing



# === STEP 4: Run the RSI and EMA screener ===
rsi_qualified = screen_rsi_oversold(all_tickers)        # Stage 1: RSI filter
bullish_crosses = screen_bullish_crossover(rsi_qualified)  # Stage 2: EMA crossover filter


# === STEP 5: Save results into a JSON file ===
with open("screened_results.json", "w") as f:
    json.dump(bullish_crosses, f)   # Write the final result list to a JSON file

# === STEP 6: Print success message ===
print("✅ Done! Screened results saved to screened_results.json")

import upload_via_ftp  # This will auto-run the FTP upload after screening
