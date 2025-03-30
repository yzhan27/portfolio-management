from web3 import Web3
from loguru import logger
from decimal import Decimal
from typing import Optional

from utils.chain import Chain


def get_uniswap_v2_price(pair_address: str, chain: Chain = Chain.ETH) -> Optional[float]:
    """获取Uniswap V2协议池子的价格
    Args:
        pair_address: 池子合约地址
        chain: 链信息
    Returns:
        token1/token0的价格，如果出错返回None
    """
    try:
        w3 = Web3(Web3.HTTPProvider(chain.url))
        if not w3.is_connected():
            logger.error(f"Failed to connect to {chain.value} network")
            return None

        pair_abi = '[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"}]'
        pair_contract = w3.eth.contract(address=pair_address, abi=pair_abi)
        
        reserves = pair_contract.functions.getReserves().call()
        reserve0 = Decimal(reserves[0])
        reserve1 = Decimal(reserves[1])
        
        if reserve0 == 0:
            logger.warning(f"Zero reserve0 in pool {pair_address}")
            return None
            
        price = reserve1 / reserve0
        return float(price)
        
    except Exception as e:
        logger.error(f"Error getting price from Uniswap V2 pool {pair_address}: {str(e)}")
        return None


def get_uniswap_v3_price(pool_address: str, chain: Chain = Chain.ETH) -> Optional[float]:
    """获取Uniswap V3协议池子的价格
    Args:
        pool_address: 池子合约地址
        chain: 链信息
    Returns:
        token1/token0的价格，如果出错返回None
    """
    try:
        w3 = Web3(Web3.HTTPProvider(chain.url))
        if not w3.is_connected():
            logger.error(f"Failed to connect to {chain.value} network")
            return None

        pool_abi = '[{"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"}]'
        pool_contract = w3.eth.contract(address=pool_address, abi=pool_abi)
        
        slot0 = pool_contract.functions.slot0().call()
        sqrt_price_x96 = Decimal(slot0[0])
        
        # Calculate price from sqrtPriceX96
        price = (sqrt_price_x96 * sqrt_price_x96 * Decimal(10**18)) / (Decimal(2**192))
        return float(price)
        
    except Exception as e:
        logger.error(f"Error getting price from Uniswap V3 pool {pool_address}: {str(e)}")
        return None


def main():
    # Test Uniswap V2 pool price
    v2_pair_address = '0x5de4EF4879F4C7Eff28B504A2f442bfCB086E2c4'
    v2_price = get_uniswap_v2_price(v2_pair_address)
    logger.info(f"Uniswap V2 pool price: {v2_price}")
    
    # Test Uniswap V3 pool price
    v3_pool_address = '0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8'
    v3_price = get_uniswap_v3_price(v3_pool_address)
    logger.info(f"Uniswap V3 pool price: {v3_price}")


if __name__ == "__main__":
    main()
