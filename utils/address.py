import pandas as pd
from loguru import logger
from eth_account import Account


def generate_eth_address(numbers):
    # 生成地址和私钥
    data = []
    for _ in range(10):
        account = Account.create()
        privateKey = account._key_obj
        publicKey = privateKey.public_key
        address = publicKey.to_checksum_address()
        logger.debug("address:{},private_key:{}",str(address),str(privateKey))
        data.append({
            'Address': address,
            'Private Key': privateKey
        })
    
    # 存入本地excel
    df = pd.DataFrame(data)
    return df

def batch_eth_address(numbers,filename="eth_address.xlsx"):
    df = generate_eth_address(numbers)
    try:
        origin_df = pd.read_excel("eth_address.xlsx")
        logger.info("origin_df:{},df:{}",len(origin_df),len(df))
        res_df = pd.concat([origin_df,df])
        logger.info("res_df:{}",len(res_df))
        assert len(res_df) == len(df)+len(origin_df),"df concat error"
        res_df.to_excel(filename,sheet_name="eth")
    except FileNotFoundError:
        df.to_excel(filename,sheet_name="eth")


if __name__ == "__main__":
    batch_eth_address(10)
