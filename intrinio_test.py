import requests

# 🔐 Paste your actual API key here temporarily
API_KEY = "de84de1c2889062ba161b6948922c8da"

url = "https://api-v2.intrinio.com/securities/AAPL/prices/technicals/rsi"

params = {
    "period": 14,
    "price_key": "close",
    "output_size": 1,
}

print(f"🔍 Making request to Intrinio...")

response = requests.get(url, params=params, auth=(API_KEY, ""))
print(f"Status Code: {response.status_code}")
print(f"Response JSON:\n{response.json()}")
