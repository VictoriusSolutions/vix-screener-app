# intrinio_api.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("INTRINIO_API_KEY") or "PASTE_YOUR_KEY_HERE"
print(f"🔐 [HARDCODED] API key starts with: {API_KEY[:5]}")


BASE_URL = "https://api-v2.intrinio.com"

def get_bulk_technicals(tickers, indicators=["rsi", "macd", "ema"]):
    joined = ",".join(tickers[:100])  # Intrinio allows up to 100 tickers per batch
    url = f"{BASE_URL}/securities/prices/technicals/bulk"

    params = {
        "identifiers": joined,
        "technicals": ",".join(indicators),
        "output_size": 1  # Just want most recent
    }

    response = requests.get(url, params=params, auth=(API_KEY, ""))
    if response.status_code != 200:
        print("❌ API error:", response.status_code, response.json())
        return {}

    data = response.json()
    results = {}
    for result in data.get("technicals", []):
        symbol = result.get("identifier")
        results[symbol] = {
            "RSI": result.get("rsi", {}).get("value"),
            "MACD": result.get("macd", {}).get("value"),
            "EMA": result.get("ema", {}).get("value")
        }

    return results
