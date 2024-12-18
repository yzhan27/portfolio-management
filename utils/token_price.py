import os
import inspect
import requests
import importlib
from enum import Enum
from loguru import logger
from functools import wraps
from typing import Optional
from datetime import datetime


class PriceSource(Enum):
    BINANCE = "binance"
    OKX = "okx"
    BITGET = "bitget"
    GATE = "gate"


def iter_cex(fn):
    @wraps(fn)
    def run(*args, **kwargs):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cex_dir = os.path.join(current_dir, 'cex')

        for s in PriceSource:
            module_name = s.value
            file_path = os.path.join(cex_dir, f"{module_name}.py")
            if os.path.exists(file_path):
                try:
                    module_path = f'utils.cex.{module_name}'
                    module = importlib.import_module(module_path)
                    kwargs['cex'] = module
                    return fn(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error accessing {module_name}: {fn.__name__} for token '{args[0]}':{e}")
    return run


@iter_cex
def get_token_price(token_name: str, **kwargs):
    cex = kwargs.get('cex')
    if hasattr(cex, "get_current_price") and inspect.isfunction(cex.get_current_price):
        price = cex.get_current_price(token_name)
        logger.info("Return {} price - {}: {}", cex.__name__, token_name, price)
        return float(price)


@iter_cex
def get_token_spot_candlesticks(
        token_name: str,
        interval='1d',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        **kwargs
):
    cex = kwargs.get('cex')
    if hasattr(cex, "get_spot_candlesticks") and inspect.isfunction(cex.get_spot_candlesticks):
        df = cex.get_spot_candlesticks(
            token_name, interval=interval, start_time=start_time, end_time=end_time, limit=limit
        )
        logger.info("Return {} price - {}: {} records", cex.__name__, token_name, len(df))
        return df


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


if __name__ == "__main__":
    p = get_token_price("zrc")
    print(p)

    p = get_token_spot_candlesticks('navx')
    print(p.head(5))

    # p = get_onchain_price('0x2B5D9ADea07B590b638FFc165792b2C610EdA649')
