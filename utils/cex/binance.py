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
    symbol = token_name if token_name[-4:] == "USDT" else token_name + "USDT"

    api_url = 'https://api.binance.com/api/v3/ticker/price'
    params = {'symbol': symbol}

    try:
        response = requests.get(api_url, params=params)
        data = response.json()
        return data['price']
    except requests.exceptions.HTTPError as e:
        logger.error(response.content)


def get_spot_candlesticks(
        symbol: str,
        interval='1d',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
) -> pd.DataFrame:
    """
    @param symbol: crypto token name, "BTC" "ETH" etc
    @param interval: [1s/1m/3m/5m/15m/30m/1h/2h/4h/6h/8h/12h/1d/3d/1w/1M]
    @param start_time: Optional, UTC timezone
    @param end_time: Optional, UTC timezone
    @param limit:Optional, Default 500; max 1000
    @return: dataframe of recent historical price
    """
    symbol = symbol.upper()
    symbol = symbol if symbol[-4:] == "USDT" else symbol + "USDT"

    api_url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
    }
    if start_time is not None and end_time is not None:
        params['startTime'] = 1000 * int(start_time.timestamp())
        params['endTime'] = 1000 * int(end_time.timestamp())
    if limit is not None:
        params['limit'] = 1000 if limit > 1000 or limit < 0 else limit

    try:
        logger.info(params)
        response = requests.get(api_url, params=params)
        data = response.json()

        # 解析响应数据为DataFrame
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                         'quote_asset_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error accessing binance: {e}")


if __name__ == "__main__":
    print(get_current_price("BTCUSDT"))
    print(get_spot_candlesticks(
        "BTCUSDT",
        start_time=datetime(2022, 11, 1),
        end_time=datetime(2022, 11, 10)
    ))
