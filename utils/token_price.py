import requests
from loguru import logger


def get_binance_price(symbol):
    symbol = symbol.upper()
    symbol = symbol if symbol[-4:] == "USDT" else symbol+"USDT"

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
        price = data["data"][0]["last"]
        return price
    except requests.exceptions.HTTPError as e:
        logger.error(response.content)


def get_okx_price(symbol):
    symbol = symbol.upper()

    url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT"
    try:
        response = requests.get(url)
        data = response.json()
        price = data["data"][0]["last"]
        return price
    except requests.exceptions.HTTPError as e:
        logger.error(response.content)
    

def get_token_price(symbol):
    try:
        price = get_binance_price(symbol)
        if price is not None:
            logger.info(f"return binance price - {symbol}:{price}")
            return price
    except Exception as e:
        pass

    try:
        price = get_okx_price(symbol)
        if price is not None:
            logger.info(f"return okx price - {symbol}:{price}")
            return price
    except Exception as e:
        pass




if __name__ == "__main__":
    # price = get_binance_price("BTCUSDT")
    # print(price)

    # price = get_okx_price("gpt")
    # print(price)

    price = get_token_price("btc")
    print(price)
