from screener_filters import check_rsi

# Simple manual test for RSI logic
symbol = "AAPL"
rsi_threshold = 70

result = check_rsi(symbol, rsi_thresh=rsi_threshold)
print(result)
