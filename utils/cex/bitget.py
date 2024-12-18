import requests
import pandas as pd
from loguru import logger
from typing import Optional
from datetime import datetime


def get_current_price(token_name: str):
    """
    @param token_name: crypto token name, "BTC" "ETH" etc
    @return: current price of input token
    """
    token_name = token_name.upper()
    symbol = token_name + 'USDT' if token_name[-4:] != 'USDT' else token_name

    url = "https://api.bitget.com/api/v2/spot/market/tickers"
    params = {"symbol": symbol}
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("code") == "00000":
        ticker_data = data.get("data", [])[0]
        price = ticker_data.get("lastPr")
        return float(price)
    else:
        return f"Error: {data.get('msg', 'Unknown error')}"


if __name__ == "__main__":
    print(get_current_price("btc"))

