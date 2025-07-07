import streamlit as st
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from screener_filters import check_rsi, check_ema_crossover, check_macd_crossover, check_volume_spike, load_grouped_data

st.set_page_config(page_title="VIXTradingHub Stock Screener", layout="wide")
st.title("\U0001F4C8 VIXTradingHub Screener")

st.markdown("""
### \U0001F9E0 Strategy Context
This VIXTradingHub Screener helps filter stocks for **In-the-Money (ITM) LEAPS Options** with expirations **6 to 18 months out**, with the goal of exiting for profit **within a few weeks**.

We use this as part of the **Daily Stock Picks** series on [VIXTradingHub.com](https://vixtradinghub.com), where we handpick potential LEAPS plays using a combination of technical indicators.
""")

# Load ticker symbols
df = pd.read_csv("all_us_tickers.csv")
tickers = df['symbol'].dropna().unique().tolist()
st.success(f"✅ Loaded {len(tickers)} tickers from internal list")

st.subheader("\U0001F527 Technical Stock Screener")

col1, col2 = st.columns(2)

with col1:
    use_rsi = st.checkbox("RSI Filter", value=True)
    rsi_thresh = st.slider("RSI Threshold", 10, 70, 50)
    st.caption("\U0001F4CA RSI (Relative Strength Index) detects overbought or oversold conditions. Values below the threshold suggest better entry opportunities.")

    use_ema = st.checkbox("EMA 20/50 Crossover", value=True)
    st.caption("\U0001F4C8 EMA crossover helps identify short-term momentum. A bullish crossover may indicate upward movement.")

with col2:
    use_macd = st.checkbox("MACD Crossover", value=True)
    st.caption("\U0001F501 MACD (Moving Average Convergence Divergence) is used to spot trend reversals via signal line crossovers.")

    use_volume = st.checkbox("Volume Spike", value=True)
    vol_mult = st.slider("Volume Multiplier", 1.0, 5.0, 1.5)
    st.caption("\U0001F4E3 Volume spikes indicate unusual trading activity, possibly signaling news or institutional interest.")

progress_placeholder = st.empty()
results_placeholder = st.empty()

if st.button("\U0001F50D Run Screener"):
    st.markdown("""
        <style>
        .stProgress > div > div > div > div {
            background-color: #22c55e !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("⚙️ Stock screening is in progress... this may take a few minutes. Please wait.")
    progress = progress_placeholder.progress(0)

    grouped_data = load_grouped_data()
    total = len(tickers)
    passed = set(tickers)

    if use_rsi:
        results = []
        for i, symbol in enumerate(tickers):
            if symbol not in grouped_data:
                continue
            if check_rsi(symbol, rsi_thresh=rsi_thresh, grouped_data=grouped_data):
                results.append(symbol)
            progress.progress((i + 1) / total)
        passed &= set(results)

    if use_ema:
        results = []
        for i, symbol in enumerate(tickers):
            if symbol not in grouped_data or symbol not in passed:
                continue
            if check_ema_crossover(symbol, grouped_data=grouped_data):
                results.append(symbol)
            progress.progress((i + 1) / total)
        passed &= set(results)

    if use_macd:
        results = []
        for i, symbol in enumerate(tickers):
            if symbol not in grouped_data or symbol not in passed:
                continue
            if check_macd_crossover(symbol, grouped_data=grouped_data):
                results.append(symbol)
            progress.progress((i + 1) / total)
        passed &= set(results)

    if use_volume:
        results = []
        for i, symbol in enumerate(tickers):
            if symbol not in grouped_data or symbol not in passed:
                continue
            if check_volume_spike(symbol, multiplier=vol_mult, grouped_data=grouped_data):
                results.append(symbol)
            progress.progress((i + 1) / total)
        passed &= set(results)

    final_results = [{"symbol": s} for s in sorted(passed)]
    st.success(f"✅ Screener complete. {len(final_results)} tickers passed all selected filters.")
    result_df = pd.DataFrame(final_results)

    results_placeholder.dataframe(result_df, use_container_width=True)

    csv = result_df.to_csv(index=False).encode('utf-8')
    st.download_button("\U0001F4E5 Download CSV", csv, "screened_results.csv", "text/csv")
