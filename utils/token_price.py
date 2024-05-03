import requests
import pandas as pd
from loguru import logger


def get_binance_price(symbol):
    symbol = symbol.upper()
    symbol = symbol if symbol[-4:] == "USDT" else symbol + "USDT"

    api_url = 'https://api.binance.com/api/v3/ticker/price'
    params = {'symbol': symbol}

    try:
        response = requests.get(api_url, params=params)
        data = response.json()
        return data['price']
    except requests.exceptions.HTTPError as e:
        logger.error(response.content)


def get_okx_price(symbol):
    symbol = symbol.upper()
    symbol = symbol[:-4] if symbol[-4:] == "USDT" else symbol

    url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT"
    try:
        response = requests.get(url)
        data = response.json()
        return data["data"][0]["last"]
    except requests.exceptions.HTTPError as e:
        logger.error(response.content)


def get_gate_price(symbol):
    symbol = symbol.lower()
    symbol = symbol if symbol[-5:] == '_usdt' else symbol + '_usdt'

    url = f'https://data.gateapi.io/api2/1/ticker/{symbol}'
    try:
        response = requests.get(url)
        return response.json()['last']
    except requests.exceptions.HTTPError as e:
        logger.error(response.content)


def get_onchain_price(token):
    url = f'https://api.dexscreener.com/latest/dex/tokens/{token}'
    try:
        res = requests.get(url)
        token_pairs = res.json()['pairs']
        max_liquidity = 0
        for pair in token_pairs:
            dex_label = '&'.join(pair['labels']) if 'labels' in pair.keys() else ''
            base_symbol = pair['baseToken']['symbol']
            quote_symbol = pair['quoteToken']['symbol']
            dex_id = f"{pair['dexId']}_{dex_label}({base_symbol}_{quote_symbol})"
            price_usd = pair['priceUsd']
            liquidity = pair['liquidity']['usd']
            if max_liquidity < liquidity:
                max_liquidity = liquidity
            logger.info(f'{dex_id}-{liquidity}:{price_usd}')
        return price_usd
    except requests.exceptions.HTTPError as e:
        logger.error("Request failed with status code: {status_code}".format(res.status_code))


def get_token_price(symbol):
    exchanges = ['binance', 'okx', 'gate']
    for exchange in exchanges:
        try:
            price_function = globals()[f'get_{exchange}_price']
            price = price_function(symbol)
            logger.info(f"return {exchange} price - {symbol}:{price}")
            return price
        except Exception as e:
            logger.error(f"Error accessing {exchange}: {symbol} {e}")


def get_binance_spot_candlesticks(symbol, interval='1d', limit=200):
    """
    :param symbol: upper token symbol such as "BTC"
    :param interval: [1m/3m/5m/15m/30m/1h/2h/4h]
    :param limit: at most 200
    :return: dataframe of historical price
    """
    symbol = symbol.upper()
    symbol = symbol if symbol[-4:] == "USDT" else symbol + "USDT"

    api_url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }

    try:
        response = requests.get(api_url, params=params)
        data = response.json()

        # 解析响应数据为DataFrame
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                         'quote_asset_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error accessing binance: {e}")


def get_okx_spot_candlesticks(symbol, interval='5m', limit=100):
    """
    :param symbol: upper token symbol such as "BTC"
    :param interval: [1m/3m/5m/15m/30m/1H/2H/4H] HKT：[6H/12H/1D/1W/1M] UTC：[/6Hutc/12Hutc/1Dutc/1Wutc/1Mutc]
    :param limit: at most 100
    :return: dataframe of historical price
    """
    symbol = symbol.upper()
    symbol = symbol[:-4] if symbol[-4:] == "USDT" else symbol
    symbol = symbol[:-4] if symbol[-1] in ("-", "_") else symbol

    if interval in ('1d', '7d', '30d'):
        interval = interval.upper()

    # 发起API请求
    # url = f'api/v5/market/history-index-candles?instId={symbol}&bar={interval}&limit={limit}'
    url = f'https://www.okex.com/api/v5/market/history-index-candles?instId={symbol}-USDT&bar={interval}&limit={limit}'
    logger.info(url)
    try:
        response = requests.get(url)
        data = response.json()['data']
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'confirmed'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error accessing okx: {e}")


def get_gate_spot_candlesticks(symbol, interval='1d', limit=100):
    """
    https://www.gate.io/docs/developers/apiv4/zh_CN/#%E5%B8%82%E5%9C%BA-k-%E7%BA%BF%E5%9B%BE
    :param symbol: simple token symbol such as "BTC"
    :param interval: [1m/5m/15m/30m/1h/4h/8h/1d/7d/30d]
    :param limit: max 1000
    :return: dataframe of token history price
    """
    symbol = symbol.upper()
    symbol = symbol if symbol[-5:] == "USDT" else symbol + '_USDT'

    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = f'https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={symbol}&interval={interval}&limit={limit}'
    logger.info(url)
    try:
        response = requests.request('GET', url, headers=headers)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'quote_volume', 'close', 'high', 'low', 'open', 'base_volume', 'confirmed'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        return df
    except Exception as e:
        logger.error(f"Error accessing gate: {e}")


def get_token_spot_candlesticks(symbol, interval='1d', limit=100):
    exchanges = ['binance', 'okx', 'gate']
    for exchange in exchanges:
        try:
            price_function = globals()[f'get_{exchange}_spot_candlesticks']
            logger.info(price_function)
            df = price_function(symbol, interval=interval, limit=limit)
            print(len(df))
            if len(df) > 0:
                return df
        except Exception as e:
            logger.error(f"Error accessing {exchange}: {e}")


if __name__ == "__main__":
    # p = get_binance_price("BTCUSDT")
    # p = get_okx_price("gpt")
    # p = get_gate_price("cpool")

    # p = get_token_price("cpool")

    # p = get_binance_spot_candlesticks('gpt')
    # p = get_okx_spot_candlesticks('gpt')
    p = get_token_spot_candlesticks('gpt')
    print(p.head(5))

    # p = get_onchain_price('0x2B5D9ADea07B590b638FFc165792b2C610EdA649')
    # p = get_okx_historical_data("BTC", interval='1H')
    # print(p)