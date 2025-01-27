import os
import base64
import json
import time
import requests
from cryptography.hazmat.primitives.asymmetric import ed25519
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

BP_BASE_URL = ' https://api.backpack.exchange/'

bpx_api_key = os.getenv("BPX_API_KEY")
bpx_api_secret = os.getenv("BPX_API_SECRET")


class BpxClient:
    url = 'https://api.backpack.exchange/'
    private_key: ed25519.Ed25519PrivateKey

    def __init__(self, api_key, api_secret):
        self.debug = False
        self.proxies = {
            'http': '',
            'https': ''
        }
        self.api_key = api_key
        self.api_secret = api_secret
        self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
            base64.b64decode(api_secret)
        )
        self.debugTs = 0
        self.window = 5000

    # capital
    def balances(self):
        return requests.get(url=f'{self.url}api/v1/capital', proxies=self.proxies,
                            headers=self.sign('balanceQuery', {})).json()
    
    def deposits(self):
        return requests.get(url=f'{self.url}wapi/v1/capital/deposits', proxies=self.proxies,
                            headers=self.sign('depositQueryAll', {})).json()

    def depositAddress(self, chain: str):
        params = {'blockchain': chain}
        return requests.get(url=f'{self.url}wapi/v1/capital/deposit/address', proxies=self.proxies, params=params,
                            headers=self.sign('depositAddressQuery', params)).json()

    def withdrawals(self, limit: int, offset: int):
        params = {'limit': limit, 'offset': offset}
        return requests.get(url=f'{self.url}wapi/v1/capital/withdrawals', proxies=self.proxies, params=params,
                            headers=self.sign('withdrawalQueryAll', params)).json()

    # history

    def orderHistoryQuery(self, symbol: str, limit: int, offset: int):
        params = {'symbol': symbol, 'limit': limit, 'offset': offset}
        return requests.get(url=f'{self.url}wapi/v1/history/orders', proxies=self.proxies, params=params,
                            headers=self.sign('orderHistoryQueryAll', params)).json()

    def fillHistoryQuery(self, symbol: str, limit: int, offset: int):
        params = {'limit': limit, 'offset': offset}
        if len(symbol) > 0:
            params['symbol'] = symbol
        return requests.get(url=f'{self.url}wapi/v1/history/fills', proxies=self.proxies, params=params,
                            headers=self.sign('fillHistoryQueryAll', params)).json()

    # order

    def orderQuery(self, symbol: str, orderId: str, clientId: int = -1):
        params = {'symbol': symbol}
        if len(orderId) > 0:
            params['orderId'] = orderId
        if clientId > -1:
            params['clientId'] = clientId
        return requests.get(url=f'{self.url}api/v1/order', proxies=self.proxies, params=params,
                            headers=self.sign('orderQuery', params)).json()

    def ExeOrder(self, symbol, side, orderType, timeInForce, quantity, price):
        params = {
            'symbol': symbol,
            'side': side,
            'orderType': orderType,
            'quantity': quantity,
            'price': price
        }

        if len(timeInForce) < 1:
            params['postOnly'] = True
        else:
            params['timeInForce'] = timeInForce
        return requests.post(url=f'{self.url}api/v1/order', proxies=self.proxies, data=json.dumps(params),
                             headers=self.sign('orderExecute', params))

    def orderCancel(self, symbol: str, orderId: str, clientId: int = -1):
        params = {'symbol': symbol}
        if len(orderId) > 0:
            params['orderId'] = orderId
        if clientId > -1:
            params['clientId'] = clientId
        return requests.delete(url=f'{self.url}api/v1/order', proxies=self.proxies, data=json.dumps(params),
                               headers=self.sign('orderCancel', params)).json()

    def ordersQuery(self, symbol: str):
        params = {}
        if len(symbol) > 0:
            params['symbol'] = symbol

        return requests.get(url=f'{self.url}api/v1/orders', proxies=self.proxies, params=params,
                            headers=self.sign('orderQueryAll', params)).json()

    def ordersCancel(self, symbol: str):
        params = {'symbol': symbol}
        return requests.delete(url=f'{self.url}api/v1/orders', proxies=self.proxies, data=json.dumps(params),
                               headers=self.sign('orderCancelAll', params)).json()

    def sign(self, instruction: str, params: dict):
        sign_str = f"instruction={instruction}" if instruction else ""
        if 'postOnly' in params:
            params = params.copy()
            params['postOnly'] = str(params['postOnly']).lower()
        sorted_params = "&".join(
            f"{key}={value}" for key, value in sorted(params.items())
        )
        if sorted_params:
            sign_str += "&" + sorted_params
        ts = int(time.time() * 1e3)

        if self.debug and self.debugTs > 0:
            ts = self.debugTs

        sign_str += f"&timestamp={ts}&window={self.window}"
        signature_bytes = self.private_key.sign(sign_str.encode())
        encoded_signature = base64.b64encode(signature_bytes).decode()

        if self.debug:
            print(f'Waiting Sign Str: {sign_str}')
            print(f"Signature: {encoded_signature}")

        headers = {
            "X-API-Key": self.api_key,
            "X-Signature": encoded_signature,
            "X-Timestamp": str(ts),
            "X-Window": str(self.window),
            "Content-Type": "application/json; charset=utf-8",
        }
        return headers


def main():
    my_bpx = BpxClient(bpx_api_key,bpx_api_secret)
    my_balance = my_bpx.balances()
    print(my_balance)
    # order_test = my_bpx.ExeOrder(symbol="SOL_USDC",side="Ask",orderType="Limit",timeInForce="GTC",quantity=0.5,price=111.3)
    # print(order_test)
    # order_test = my_bpx.ExeOrder(symbol="SOL_USDC",side="Bid",orderType="Limit",timeInForce="GTC",quantity=0.5,price=111.2)
    # print(order_test.content)

if __name__ == '__main__':
    main()



