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
    token_name = token_name[:-4] if token_name[-4:] == "USDT" else token_name

    url = f"https://www.okx.com/api/v5/market/ticker?instId={token_name}-USDT"
    response = requests.get(url)
    data = response.json()
    if data.get('code') == '0':
        return data["data"][0]["last"]
    else:
        raise Exception(data['msg'])


def get_spot_candlesticks(
    token_name: str,
    interval='1d',
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: Optional[int] = None
):
    """
    https://www.okx.com/docs-v5/en/?python#public-data-rest-api-get-index-candlesticks-history
    @param token_name: crypto token name, "BTC" "ETH" etc, token-usdt pair by default
    @param interval: default 1m, [1m/3m/5m/15m/30m/1H/2H/4H],HKT：[6H/12H/1D/1W/1M],[/6Hutc/12Hutc/1Dutc/1Wutc/1Mutc]
    @param end_time: Optional, end_time of spot candlesticks
    @param start_time: Optional, start_time of spot candlesticks
    @param limit: default 100, max 100
    @return: dataframe of recent historical price
    """
    symbol = token_name.upper()
    symbol = symbol[:-4] if symbol[-4:] == "USDT" else symbol
    symbol = symbol[:-4] if symbol[-1] in ("-", "_") else symbol

    if interval not in ('1m', '3m', '5m', '15m', '30m'):
        interval = interval.upper()

    url = f'https://www.okx.com/api/v5/market/history-index-candles'
    params = {
        'instId': symbol + '-USDT',
        'bar': interval,
    }
    if start_time is not None and end_time is not None:
        params['before'] = str(1000 * int(start_time.timestamp()))
        params['after'] = str(1000 * int(end_time.timestamp()))
    if limit is not None:
        params['limit'] = 100 if limit > 100 or limit < 0 else limit
    response = requests.get(url, params=params)
    if response.json()['code'] == '0':
        data = response.json()['data']
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'confirmed'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    else:
        logger.error(response.json()['msg'])
        raise Exception(response.json()['msg'])


if __name__ == "__main__":
    print(get_current_price("okb"))
    print(get_spot_candlesticks(
        "okb",
        interval='1D',
        start_time=datetime(2024, 11, 1),
        end_time=datetime(2024, 11, 10)
    ))
