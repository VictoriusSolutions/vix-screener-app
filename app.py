import streamlit as st  # Import the Streamlit library for building the web app
import pandas as pd  # Import pandas for handling data frames
from concurrent.futures import ThreadPoolExecutor, as_completed  # For running tasks in parallel threads
from screener_filters import check_rsi, check_ema_crossover, check_macd_crossover, check_volume_spike  # Import custom filter functions

st.set_page_config(page_title="VIX Screener", layout="wide")  # Set the Streamlit page title and layout to wide
st.title("📈 VIX Screener")  # Display the main app title

# === Load your internal ticker list ===
df = pd.read_csv("all_us_tickers.csv")  # Read ticker symbols from a CSV file
tickers = df['symbol'].dropna().unique().tolist()  # Remove nulls and duplicates from the symbol list
st.success(f"✅ Loaded {len(tickers)} tickers from internal list")  # Show a success message with the number of tickers loaded

# === Screener Controls ===
st.subheader("🔧 Screener Filters")  # Add a subheader for the filter section

col1, col2 = st.columns(2)  # Create two columns for organizing the filter inputs
with col1:
    use_rsi = st.checkbox("RSI Filter", value=True)  # Add checkbox to enable RSI filter
    rsi_thresh = st.slider("RSI Threshold", 10, 70, 50)  # Add slider for setting RSI threshold

    use_ema = st.checkbox("EMA 20/50 Crossover", value=True)  # Add checkbox to enable EMA crossover filter

with col2:
    use_macd = st.checkbox("MACD Crossover", value=True)  # Add checkbox to enable MACD filter

    use_volume = st.checkbox("Volume Spike", value=True)  # Add checkbox to enable Volume Spike filter
    vol_mult = st.slider("Volume Multiplier", 1.0, 5.0, 1.5)  # Add slider to set multiplier for volume spike detection

# === Screener Execution ===
if st.button("🔍 Run Screener"):  # Run the screener when the button is clicked
    st.info("Running filters... This may take a few minutes.")  # Show info message while running
    progress = st.progress(0)  # Initialize a progress bar
    current = tickers  # Start with all loaded tickers

    def threaded_run(filter_fn, **kwargs):  # Function to apply a filter function using threading
        results = []  # List to store passing tickers
        with ThreadPoolExecutor(max_workers=50) as executor:  # Create a thread pool with 20 workers
            futures = {executor.submit(filter_fn, symbol, **kwargs): symbol for symbol in current}  # Submit each ticker to the filter
            for i, future in enumerate(as_completed(futures)):  # As futures complete...
                result = future.result()  # Get the result from the future
                if result:
                    results.append(result)  # Append result if filter passed
                progress.progress((i + 1) / len(current))  # Update progress bar
        return results  # Return all tickers that passed the filter

    if use_rsi:
        current = threaded_run(check_rsi, rsi_thresh=rsi_thresh)  # Apply RSI filter if selected
    if use_ema:
        current = threaded_run(check_ema_crossover)  # Apply EMA crossover filter if selected
    if use_macd:
        current = threaded_run(check_macd_crossover)  # Apply MACD filter if selected
    if use_volume:
        current = threaded_run(check_volume_spike, multiplier=vol_mult)  # Apply Volume Spike filter if selected

    st.success(f"✅ Screener complete. {len(current)} tickers passed all selected filters.")  # Show result count
    result_df = pd.DataFrame(current, columns=["symbol"])  # Convert the results into a DataFrame
    st.dataframe(result_df)  # Display the result DataFrame in the app

    csv = result_df.to_csv(index=False).encode('utf-8')  # Convert the DataFrame to CSV and encode as UTF-8
    st.download_button("📥 Download CSV", csv, "screened_results.csv", "text/csv")  # Add download button for CSV
