from web3 import Web3
from loguru import logger

from utils.chain import Chain


class Transaction(object):
    def __init__(self, transaction_hash: str, chain: Chain = Chain('eth')):
        self.transaction_hash = transaction_hash
        self.chain = chain
        self.web3 = Web3(Web3.HTTPProvider(chain.url))
    
    def get_receipt(self):
        if not self.web3.is_connected():
            raise ConnectionError("Unable to connect to the Web3 provider.")
        try:
            # Fetch transaction receipt to get gasUsed and logs
            receipt: dict = self.web3.eth.get_transaction_receipt(self.transaction_hash)
            return receipt
        except Exception as e:
            print(f"Error fetching transaction data: {e}")
            return None
        

    @property
    def eth_gas_fee(self):
        """
        Calculate gas fee in wei (gasUsed * effectiveGasPrice)
        """
        receipt = self.get_receipt()
        gas_used = receipt['gasUsed']
        gas_price = receipt.get('effectiveGasPrice', receipt.get('gasPrice'))
        gas_fee_wei = gas_used * gas_price
        
        # Convert gas fee to Ether for easier reading
        if self.chain.value == "eth":
            gas_fee_eth = self.web3.from_wei(gas_fee_wei, 'ether')
            return gas_fee_eth
        else:
            return gas_fee_wei
    

    @property
    def logs(self):
        """
        Return: All logs of the transactions
        """
        receipt = self.get_receipt()
        logs = receipt.get('logs',[])
        return logs


if __name__ == "__main__":
    txn_hash = '0x07a582bdfca3c12da00572252e86b4b343201f37b3c9741d9ac99f195e8d3d1d'
    txn = Transaction(txn_hash)
    print(txn.eth_gas_fee)
    print(txn.logs)
