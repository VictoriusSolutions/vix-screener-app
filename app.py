import streamlit as st
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from screener_filters import check_rsi, check_ema_crossover, check_macd_crossover, check_volume_spike

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
    current = tickers[:]

    def threaded_run(filter_fn, **kwargs):
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(filter_fn, symbol, **kwargs): symbol for symbol in current}
            for i, future in enumerate(as_completed(futures)):
                try:
                    result = future.result()
                    if result:
                        if isinstance(result, dict):
                            results.append(result)
                        else:
                            results.append({"symbol": result})
                except Exception as e:
                    print(f"Error processing {futures[future]}: {e}")
                progress.progress((i + 1) / len(current))
        return results

    if use_rsi:
        filtered = threaded_run(check_rsi, rsi_thresh=rsi_thresh)
        current = [item["symbol"] for item in filtered]
    if use_ema:
        current = [r["symbol"] for r in threaded_run(check_ema_crossover) if r["symbol"] in current]
    if use_macd:
        current = [r["symbol"] for r in threaded_run(check_macd_crossover) if r["symbol"] in current]
    if use_volume:
        current = [r["symbol"] for r in threaded_run(check_volume_spike, multiplier=vol_mult) if r["symbol"] in current]

    final_results = [{"symbol": sym} for sym in current]
    st.success(f"✅ Screener complete. {len(final_results)} tickers passed all selected filters.")
    result_df = pd.DataFrame(final_results)

    if "rsi" in result_df.columns:
        result_df.sort_values(by="rsi", inplace=True)

    results_placeholder.dataframe(result_df, use_container_width=True)

    csv = result_df.to_csv(index=False).encode('utf-8')
    st.download_button("\U0001F4E5 Download CSV", csv, "screened_results.csv", "text/csv")
