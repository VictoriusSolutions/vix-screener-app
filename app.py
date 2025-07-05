import streamlit as st  # Streamlit for building the web app UI
import pandas as pd  # Pandas for handling dataframes
from concurrent.futures import ThreadPoolExecutor, as_completed  # For running filter functions concurrently
from screener_filters import check_rsi, check_ema_crossover, check_macd_crossover, check_volume_spike  # Importing screening filter functions

# === Set up Streamlit app layout ===
st.set_page_config(page_title="VIXTradingHub Stock Screener", layout="wide")  # Set the page title and layout format
st.title("📈 VIXTradingHub Screener")  # Title displayed on the app

# === Screener Overview and Strategy Context ===
st.markdown("""
### 🧠 Strategy Context
This VIXTradingHub Screener helps filter stocks for **In-the-Money (ITM) LEAPS Options** with expirations **6 to 18 months out**, with the goal of exiting for profit **within a few weeks**.

We use this as part of the **Daily Stock Picks** series on [VIXTradingHub.com](https://vixtradinghub.com), where we handpick potential LEAPS plays using a combination of technical indicators.
""")  # Explanation and purpose of the screener

# === Load your internal ticker list ===
df = pd.read_csv("all_us_tickers.csv")  # Read the list of tickers from CSV file
tickers = df['symbol'].dropna().unique().tolist()  # Drop NaNs and extract unique ticker symbols
st.success(f"✅ Loaded {len(tickers)} tickers from internal list")  # Show success message with ticker count

# === Screener Controls ===
st.subheader("🔧 Technical Stock Screener")  # Subheader for filter section

col1, col2 = st.columns(2)  # Split filter controls into two columns

with col1:
    use_rsi = st.checkbox("RSI Filter", value=True)  # Toggle to enable RSI filter
    rsi_thresh = st.slider("RSI Threshold", 10, 70, 50)  # Slider to set RSI threshold
    st.caption("📊 RSI (Relative Strength Index) detects overbought or oversold conditions. Values below the threshold suggest better entry opportunities.")

    use_ema = st.checkbox("EMA 20/50 Crossover", value=True)  # Toggle to enable EMA crossover filter
    st.caption("📈 EMA crossover helps identify short-term momentum. A bullish crossover may indicate upward movement.")

with col2:
    use_macd = st.checkbox("MACD Crossover", value=True)  # Toggle to enable MACD crossover filter
    st.caption("🔁 MACD (Moving Average Convergence Divergence) is used to spot trend reversals via signal line crossovers.")

    use_volume = st.checkbox("Volume Spike", value=True)  # Toggle to enable volume spike filter
    vol_mult = st.slider("Volume Multiplier", 1.0, 5.0, 1.5)  # Slider to set multiplier threshold for volume spike
    st.caption("📣 Volume spikes indicate unusual trading activity, possibly signaling news or institutional interest.")

# === Screener Execution ===
if st.button("🔍 Run Screener"):  # Run button initiates the screening process
    st.info("Running filters... This may take a few minutes.")  # Inform the user the screener is running
    progress = st.progress(0)  # Display a progress bar
    current = tickers  # Start with full list of tickers

    def threaded_run(filter_fn, **kwargs):  # Function to run filters using multithreading
        results = []  # Initialize list to store results
        with ThreadPoolExecutor(max_workers=20) as executor:  # Use thread pool for concurrency
            futures = {executor.submit(filter_fn, symbol, **kwargs): symbol for symbol in current}  # Submit tasks
            for i, future in enumerate(as_completed(futures)):  # As tasks complete...
                result = future.result()  # Get result
                if result:
                    results.append(result)  # Add if passed
                progress.progress((i + 1) / len(current))  # Update progress bar
        return results  # Return tickers that passed

    if use_rsi:
        current = threaded_run(check_rsi, rsi_thresh=rsi_thresh)  # Apply RSI filter if enabled
    if use_ema:
        current = threaded_run(check_ema_crossover)  # Apply EMA crossover filter if enabled
    if use_macd:
        current = threaded_run(check_macd_crossover)  # Apply MACD crossover filter if enabled
    if use_volume:
        current = threaded_run(check_volume_spike, multiplier=vol_mult)  # Apply Volume Spike filter if enabled

    st.success(f"✅ Screener complete. {len(current)} tickers passed all selected filters.")  # Display number of passing tickers
    result_df = pd.DataFrame(current, columns=["symbol"])  # Create DataFrame of results
    st.dataframe(result_df)  # Show results table

    csv = result_df.to_csv(index=False).encode('utf-8')  # Convert results to CSV bytes
    st.download_button("📥 Download CSV", csv, "screened_results.csv", "text/csv")  # Download button for CSV
