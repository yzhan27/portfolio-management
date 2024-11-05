import os
from enum import Enum

from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class Chain(Enum):
    ETH = "eth"
    BSC = "bsc"
    ARB = "arb"
    OP = "op"
    POL = "polygon"
    AVAX = "avax"
    MANTLE = "mnt"
    SOL = "sol"
    SCROLL = "scroll"
    UNKNOWN = "unknown"

    def __hash__(self):
        return hash(self.value)

    @classmethod
    def from_string(cls, c):
        if c is None:
            logger.warning("Invalid Chain!!")
            return cls.UNKNOWN
        for chain in cls:
            if chain == cls.UNKNOWN:
                continue
            if c == chain.value:
                return chain
        logger.warning(f"unknown chain: [{c}]")
        return cls.UNKNOWN
    
    @classmethod
    def from_env(cls):
        return cls.from_string(os.getenv("CHAIN"))
    
    @property
    def url(self) -> str:
        env_name = '{}_CHAIN_URL'.format(self.value.upper())
        chain_url = os.getenv(env_name, '')
        if not chain_url:
            logger.warning('chain {} url not found in environment', self.value)
        return chain_url

    @property
    def valid(self) -> bool:
        valid_chain = os.getenv("VALID_CHAIN").split(',')
        return self.value in valid_chain


ChainIDs = [
    (Chain.ETH, '1'),
    (Chain.BSC, '56'),
    (Chain.POL, '137'),
    (Chain.AVAX, '43114'),
    (Chain.ARB, '42161'),
    (Chain.OP, '10'),
]


def chain_from_id(chain_id: str) -> Chain:
    for c, i in ChainIDs:
        if i == chain_id:
            return c
    raise KeyError('chain id not found')


def chain_to_id(chain: Chain) -> str:
    for c, i in ChainIDs:
        if c.value == chain.value:
            return i
    raise KeyError('unknown chain')


if __name__ == "__main__":
    c = Chain.from_string('eth')
    print(chain_to_id(c))
    print(c.url)
