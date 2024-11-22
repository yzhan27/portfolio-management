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
    token_name = token_name.lower()
    symbol = token_name if token_name[-5:] == '_usdt' else token_name + '_usdt'

    url = f'https://data.gateapi.io/api2/1/ticker/{symbol}'
    try:
        logger.info(url)
        response = requests.get(url)
        return response.json()['last']
    except requests.exceptions.HTTPError as e:
        logger.error(e)


def get_spot_candlesticks(
    token_name: str,
    interval='1D',
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: Optional[int] = None
):
    """
    https://www.gate.io/docs/developers/apiv4/zh_CN/#%E5%B8%82%E5%9C%BA-k-%E7%BA%BF%E5%9B%BE
    @param token_name: crypto token name, "BTC" "ETH" etc, token-usdt pair by default
    @param interval: default 1m, [1m/3m/5m/15m/30m/1H/2H/4H],HKT：[6H/12H/1D/1W/1M],[/6Hutc/12Hutc/1Dutc/1Wutc/1Mutc]
    @param end_time: Optional, end_time of spot candlesticks
    @param start_time: Optional, default end_time - 100 * intervals
    @param limit: max 1000
    @return:
    """
    token_name = token_name.upper()
    symbol = token_name if token_name[-5:] == "USDT" else token_name + '_USDT'

    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = f'https://api.gateio.ws/api/v4/spot/candlesticks'
    params = {
        'currency_pair': symbol,
        'interval': interval,
    }
    if start_time is not None and end_time is not None:
        params['from'] = int(start_time.timestamp())
        params['to'] = int(end_time.timestamp())
    if limit is not None:
        params['limit'] = 1000 if limit > 1000 or limit < 0 else limit

    try:
        response = requests.request('GET', url, headers=headers, params=params)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'quote_volume', 'close', 'high', 'low', 'open', 'base_volume', 'confirmed'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        return df
    except Exception as e:
        logger.error(f"Error accessing gate: {e}")


if __name__ == "__main__":
    print(get_current_price("BTC"))
    print(get_spot_candlesticks(
        "BTC",
        interval='1d',
        start_time=datetime(2024, 11, 1),
        end_time=datetime(2024, 11, 10)
    ))
