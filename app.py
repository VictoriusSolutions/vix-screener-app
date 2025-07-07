# app.py
import pandas as pd
from screener_filters import filter_intrinio_data

def load_tickers():
    df = pd.read_csv("all_us_tickers.csv")
    return df["symbol"].tolist()

if __name__ == "__main__":
    tickers = load_tickers()
    filtered = filter_intrinio_data(tickers)

    print("✅ Intrinio Filtered Results:")
    for result in filtered:
        print(result)
