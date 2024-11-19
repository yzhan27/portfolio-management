import math
import numpy as np
import pandas as pd
from loguru import logger

from utils.token_price import get_token_price
from utils.token_price import get_token_spot_candlesticks


class Pair(object):
    def __init__(self, base_token: str, quote_token: str = 'BTC'):
        self.base_token = base_token.upper()
        self.quote_token = quote_token.upper()

    @property
    def scale_k(self):
        logger.info("test")
        relative_price = get_token_price(self.base_token) / get_token_price(self.quote_token)
        return -1 * math.floor(math.log10(relative_price))

    def candlesticks(self, interval: str = '1d', limit: int = 200) -> pd.DataFrame:
        """
            :param interval: [1m/3m/5m/15m/30m/1h/2h/4h]
            :param limit: at most 200
            :return: dataframe of historical pair price
        """
        limit = 200 if limit > 200 or limit <= 0 else limit
        scale_k = self.scale_k
        base_df = get_token_spot_candlesticks(self.base_token, interval=interval, limit=limit)
        quote_df = get_token_spot_candlesticks(self.quote_token, interval=interval, limit=limit)

        for col in ['open', 'high', 'low', 'close']:
            base_df[col] = base_df[col].astype(float)
            quote_df[col] = quote_df[col].astype(float)

        pair_df = pd.merge(base_df, quote_df, on='timestamp', how='inner')
        for col in ['open', 'high', 'low', 'close']:
            pair_df[col] = pair_df[col + '_x'] / pair_df[col + '_y'] * pow(10, scale_k)
        pair_df.set_index('timestamp', inplace=True)
        pair_df = pair_df.loc[:, ['open', 'high', 'low', 'close']]
        return pair_df


if __name__ == "__main__":
    df = Pair('ETH', 'BTC').candlesticks(interval='1d')
    print(df)
