# screener_filters.py
from intrinio_api import get_bulk_technicals

def filter_intrinio_data(ticker_list, rsi_thresh=35, macd_positive=True):
    results = []
    batch_size = 100

    for i in range(0, len(ticker_list), batch_size):
        batch = ticker_list[i:i+batch_size]
        data = get_bulk_technicals(batch)

        for symbol, indicators in data.items():
            rsi = indicators.get("RSI")
            macd = indicators.get("MACD")
            ema = indicators.get("EMA")

            if rsi is None or macd is None or ema is None:
                continue

            if rsi < rsi_thresh and (macd > 0 if macd_positive else True):
                results.append({
                    "symbol": symbol,
                    "RSI": round(rsi, 2),
                    "MACD": round(macd, 2),
                    "EMA": round(ema, 2)
                })

    return results
