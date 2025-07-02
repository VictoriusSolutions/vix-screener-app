import streamlit as st
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from screener_filters import check_rsi, check_ema_crossover, check_macd_crossover, check_volume_spike

st.set_page_config(page_title="VIX Screener", layout="wide")
st.title("📈 VIX Screener")

# === Load your internal ticker list ===
df = pd.read_csv("all_us_tickers.csv")
tickers = df['symbol'].dropna().unique().tolist()
st.success(f"✅ Loaded {len(tickers)} tickers from internal list")

# === Screener Controls ===
st.subheader("🔧 Screener Filters")

col1, col2 = st.columns(2)
with col1:
    use_rsi = st.checkbox("RSI Filter", value=True)
    rsi_thresh = st.slider("RSI Threshold", 10, 70, 50)

    use_ema = st.checkbox("EMA 20/50 Crossover", value=True)

with col2:
    use_macd = st.checkbox("MACD Crossover", value=True)

    use_volume = st.checkbox("Volume Spike", value=True)
    vol_mult = st.slider("Volume Multiplier", 1.0, 5.0, 1.5)

# === Screener Execution ===
if st.button("🔍 Run Screener"):
    st.info("Running filters... This may take a few minutes.")
    progress = st.progress(0)
    current = tickers

    def threaded_run(filter_fn, **kwargs):
        results = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(filter_fn, symbol, **kwargs): symbol for symbol in current}
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if result:
                    results.append(result)
                progress.progress((i + 1) / len(current))
        return results

    if use_rsi:
        current = threaded_run(check_rsi, rsi_thresh=rsi_thresh)
    if use_ema:
        current = threaded_run(check_ema_crossover)
    if use_macd:
        current = threaded_run(check_macd_crossover)
    if use_volume:
        current = threaded_run(check_volume_spike, multiplier=vol_mult)

    st.success(f"✅ Screener complete. {len(current)} tickers passed all selected filters.")
    result_df = pd.DataFrame(current, columns=["symbol"])
    st.dataframe(result_df)

    csv = result_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", csv, "screened_results.csv", "text/csv")
