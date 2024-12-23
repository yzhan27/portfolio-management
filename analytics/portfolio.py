import pandas as pd
from loguru import logger

from utils.token_price import get_token_price


def parce_df_address_group(address: str):
    if address.split('-')[0] == 'onchain':
        return address.split('-')[0] + '-' + address.split('-')[1]
    else:
        return address


def parce_df_token_price(df: pd.DataFrame):
    for index, row in df.iterrows():
        token_price = get_token_price(row['token']) if row['token'].lower() != 'usd' else 1
        df.at[index, 'price'] = float(token_price)
        df.at[index, 'value'] = float(token_price) * float(row['amount'])
    return df


def portfolio_token_analysis(balance):
    df = pd.DataFrame(balance, columns=['token', 'address', 'amount'])
    df = df.groupby('token')['amount'].sum().reset_index()
    df = parce_df_token_price(df)
    total_value = df['value'].sum()
    logger.info(f'total_value is {total_value}')
    df['pct'] = df['value'] / total_value
    df = df.sort_values('pct', ascending=False)
    return df.reset_index().drop('index', axis=1)


def portfolio_address_analysis(balance):
    df = pd.DataFrame(balance, columns=['token', 'address', 'amount'])
    df = get_token_price(df)
    df['address_group'] = df['address'].apply(lambda x: parce_df_address_group(x))
    df = df.groupby('address_group')['value'].sum().reset_index()
    total_value = df['value'].sum()
    logger.info(f'total_value is {total_value}')
    df['pct'] = df['value'] / total_value
    df = df.sort_values('pct', ascending=False)
    return df
