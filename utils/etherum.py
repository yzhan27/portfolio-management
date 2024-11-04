import json
import re
import time
from functools import wraps
from typing import Any, List, Optional, Iterable, NewType

from eth_abi import encode_abi, decode_abi
from eth_abi.exceptions import DecodingError
from eth_utils import event_abi_to_log_topic, encode_hex, function_abi_to_4byte_selector
from eth_utils.abi import collapse_if_tuple
from hexbytes import HexBytes
from loguru import logger
from web3 import Web3
from web3.types import LogReceipt, EventData

from chain import Chain

Address = NewType('Address', str)
ZERO_ADDRESS = Address('0x0000000000000000000000000000000000000000')
ETH_ADDRESS = Address('0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')


def analysis_time_cost(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        start = time.time()
        r = fn(*args, **kwargs)
        logger.debug('{} cost {} seconds', fn.__name__, time.time() - start)
        return r

    return wrap


def byte32_to_address(byte32_hex: str, strict: bool = True) -> Address:
    if strict:
        assert len(byte32_hex) == 66
        assert byte32_hex.startswith('0x000000000000000000000000')
        assert not byte32_hex.endswith('0000000000000000000000000000000000000000')
    return Address(f'0x{byte32_hex[-40:]}')


def __parse_solidity_param(param: str, is_event: bool) -> dict:
    data = param.strip().split(' ')
    result = dict()
    if len(data) > 0:
        result['type'] = data[0]
    if len(data) >= 2:
        result['name'] = data[-1]
    if is_event:
        result['indexed'] = False
        if len(data) == 3:
            result['indexed'] = data[1] == 'indexed'
    return result


def __collapse_if_tuple(abi) -> str:
    typ = abi["type"]
    if not isinstance(typ, str):
        raise TypeError(
            "The 'type' must be a string, but got %r of type %s" % (
                typ, type(typ))
        )
    elif not typ.startswith("tuple"):
        return typ

    delimited = ",".join(__collapse_if_tuple(c) for c in abi["components"])
    # Whatever comes after "tuple" is the array dims.  The ABI spec states that
    # this will have the form "", "[]", or "[k]".
    array_dim = typ[5:]
    collapsed = "({}){}".format(delimited, array_dim)

    return "tuple" + collapsed


def abi_to_solidity(item: dict):
    assert item.get('type', '') == 'function'
    inputs = [
        __collapse_if_tuple(abi_input)
        if abi_input["type"] == "tuple" or abi_input["type"] == "tuple[]"
        else abi_input["type"]
        for abi_input in item["inputs"]
    ]
    res_info = ""
    if (
            item.get("stateMutability", "")
            and item["stateMutability"] != "nonpayable"
    ):
        res_info += item["stateMutability"] + " "
    elif item.get("constant", ""):
        res_info += "view "
    outputs = [
        __collapse_if_tuple(abi_output)
        if abi_output["type"] == "tuple" or abi_output["type"] == "tuple[]"
        else abi_output["type"]
        for abi_output in item["outputs"]
    ]
    gas_info = (
        " @{} ".format(item["gas"]) if item.get("gas", "") else ""
    )
    solidity = "function {}({}) {}{} ({}){}".format(
        item["name"],
        ", ".join(inputs),
        res_info,
        "returns",
        ", ".join(outputs),
        gas_info,
    )
    return solidity


def __parse_solidity_params(solidity: str, start: int, result: list, is_event: bool) -> int:
    cur = start
    x = ''
    item = {}
    while cur < len(solidity):
        while x.startswith(' '):
            x = x[1:]
        s = solidity[cur]
        if s == '(':
            sub = []
            cur = __parse_solidity_params(solidity, cur + 1, sub, is_event)
            item['components'] = sub
        elif s == ')':
            break
        elif s == ',':
            if x:
                item.update(__parse_solidity_param(x, is_event))
                result.append(item)
            x = ''
            item = {}
        else:
            x += s
        cur += 1
    if x:
        item.update(__parse_solidity_param(x, is_event))
        result.append(item)
    return cur


def solidity_to_abi(solidity: str) -> dict:
    result = dict()
    c = re.compile(r"(?P<type>\w*) (?P<name>\w*)\((?P<inputs>.*?)\)")
    result.update(c.search(solidity).groupdict())
    result['inputs'] = []
    is_event = result['type'] == 'event'
    __parse_solidity_params(solidity, solidity.index('(') + 1, result['inputs'], is_event)
    if 'returns (' in solidity:
        result['outputs'] = []
        __parse_solidity_params(solidity, solidity.index('returns (') + 9, result['outputs'], False)
    if is_event:
        result['anonymous'] = False
    else:
        result['stateMutability'] = 'view'
    return result


def solidity_to_selector(solidity: str) -> str:
    abi = solidity_to_abi(solidity)
    abi_type = abi.get('type', '')
    if abi_type == 'function':
        return encode_hex(function_abi_to_4byte_selector(abi))
    elif abi_type == 'event':
        return encode_hex(event_abi_to_log_topic(abi))
    return ''


def decode_by_solidity(data: bytes, solidity: str) -> tuple:
    abi = solidity_to_abi(solidity)
    output_types = [collapse_if_tuple(arg) for arg in abi['outputs']]
    return decode_abi(output_types, data)


def encode_by_solidity(params: list, solidity: str) -> str:
    if not params:
        return solidity_to_selector(solidity)
    abi = solidity_to_abi(solidity)
    input_types = [collapse_if_tuple(arg) for arg in abi['inputs']]
    return encode_hex(function_abi_to_4byte_selector(abi) + encode_abi(input_types, params))


class Call:
    """
    used for multicall,
    if not allow_failure, the whole multicall will fail
    """
    __slots__ = ["address", "solidity", "params", "allow_failure"]

    def __init__(self, address: Address, solidity: str, *params, allow_failure: bool = False):
        self.address = address
        self.solidity = solidity
        self.params = params
        self.allow_failure = allow_failure

    def __str__(self):
        return f"{self.address}, {self.solidity}, {self.params}"


class OutOfGasException(ValueError):
    pass


class Client:
    @staticmethod
    def from_chain(chain: Chain = Chain.ETH, **kwargs):
        return Client(chain.url, chain=chain, **kwargs)

    def __init__(self, url: str, multicall_address: Address = '0xca11bde05977b3631167028862be2a173976ca11',
                 event_from_doris: bool = True, chain: Optional[Chain] = None):
        logger.info('new eth client: {}', url)
        self.w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': (60, 60)}))
        self.multicall_address = multicall_address
        self.event_from_doris = event_from_doris
        self.chain = chain

    def __call_contract_function(self, address: Address, abi_str: str, function_name: str, *params) -> Any:
        contract_address = self.w3.toChecksumAddress(address)
        contract = self.w3.eth.contract(address=contract_address, abi=abi_str)
        final_e = Exception()
        for i in range(10):
            try:
                contract_function = getattr(contract.functions, function_name)
                contract_function = contract_function(*params)
                result = contract_function.call()  # {'gas': 2 ** 64 - 1}
                logger.debug('called rpc address: {}, function_name: {}',
                             address, function_name)
                return result
            except (ConnectionError, IOError) as e:
                logger.warning("retry call rpc: {}", e)
                final_e = e
                continue
            except ValueError as e:
                # ValueError: {'code': -32000, 'message': 'execution aborted (timeout = 5s)'}
                if e.args[0] == {'code': -32000, 'message': 'execution aborted (timeout = 5s)'}:
                    logger.warning("retry call rpc: {}", e)
                    continue
                if e.args[0] == {'code': -32000, 'message': 'out of gas'}:
                    raise OutOfGasException(e)
                raise e
        logger.warning('call rpc failed, params: {}', params)
        raise final_e

    @analysis_time_cost
    def call_contract_function_by_abi(self, address: Address, abi_str: str, function_name: str, *params) -> Any:
        """ call contract by abi

        call contract function, easier than using web3.Web3 directly

        :param address: target address ( case insensitive )
        :param abi_str: abi list json str, such as: '[{"name":...,"type":...},{"name":...}]'
        :param function_name: function name to call
        :param params: function params to call
        :return: Any type from node-rpc, same result as web3.eth.contract.function.call()
        """
        logger.debug('calling contract function address: {}, function_name: {}', address, function_name)
        return self.__call_contract_function(address, abi_str, function_name, *params)

    @analysis_time_cost
    def call_contract_function(self, address: Address, solidity: str, *params) -> Any:
        """ call contract by solidity

        call contract function, easier than using web3.Web3 directly,
        you can use abi_to_solidity to check if solidity is right,
        example solidity: "function getPoolTokens(bytes32 poolId) view returns (address[], uint256[], uint256)"

        :param address: target address ( case insensitive )
        :param solidity: function solidity
        :param params: function params to call
        :return: Any type from node-rpc, same result as web3.eth.contract.function.call()
        """
        logger.debug('calling contract function address: {}, solidity: {}', address, solidity)
        abi = solidity_to_abi(solidity)
        assert abi.get('type', '') == 'function'
        function_name = abi.get('name')
        abi_str = json.dumps([abi])
        return self.__call_contract_function(address, abi_str, function_name, *params)

    @analysis_time_cost
    def get_storage_at(self, address: Address, position: int) -> str:
        """ web3.eth.get_storage_at

        :param address: target address
        :param position: position
        :return: hex string at the position of storage
        """
        logger.debug('getting storage at address: {}, position: {}', address, position)
        contract_address = self.w3.toChecksumAddress(address)
        r = self.w3.eth.get_storage_at(contract_address, position)
        return r.hex()

    def __chain_get_contract_logs(self, address: Address, solidity: str,
                                  from_block: int | str = 'latest',
                                  to_block: int | str = 'latest') -> Iterable[EventData]:
        logger.debug('getting contract events from chain at address: {}, solidity: {}, from: {}, to: {}',
                     address, solidity, from_block, to_block)
        abi = solidity_to_abi(solidity)
        assert abi.get('type', '') == 'event'
        event_name = abi.get('name')
        topic = encode_hex(event_abi_to_log_topic(abi))
        contract_address = self.w3.toChecksumAddress(address)
        abi_str = json.dumps([abi])
        r = self.w3.eth.get_logs({"fromBlock": from_block,
                                  "toBlock": to_block,
                                  "address": contract_address, "topics": [topic]})
        contract = self.w3.eth.contract(address=contract_address, abi=abi_str)
        contract_event = getattr(contract.events, event_name)
        contract_event.abi = abi
        return map(lambda x: contract_event.processLog(x), r)

    def iterate_contract_logs(self, address: Address, solidity: str,
                              from_block: int | str = 'latest',
                              to_block: int | str = 'latest') -> Iterable[EventData]:
        """ query contract events use solidity, use iterator to save memory

        query contract events, default from doris which can be set when initializing Client,
        this will also help decode log data,
        example solidity:
            "event PoolRegistered(bytes32 indexed poolId, address indexed poolAddress, uint8 specialization)"

        :param address: target address
        :param solidity: event solidity
        :param from_block: from block number
        :param to_block: to block number, default latest
        :return: iterator of web3.types.EventData
        """
        if self.event_from_doris:
            return self.__doris_get_contract_logs(address, solidity, from_block, to_block)
        else:
            return self.__chain_get_contract_logs(address, solidity, from_block, to_block)

    def get_contract_logs(self, address: Address, solidity: str,
                          from_block: int | str = 'latest',
                          to_block: int | str = 'latest') -> List[EventData]:
        """ query contract events use solidity

        query contract events, default from doris which can be set when initializing Client,
        this will also help decode log data,
        example solidity:
            "event PoolRegistered(bytes32 indexed poolId, address indexed poolAddress, uint8 specialization)"

        :param address: target address
        :param solidity: event solidity
        :param from_block: from block number
        :param to_block: to block number, default latest
        :return: list of web3.types.EventData
        """
        return list(self.iterate_contract_logs(address, solidity, from_block, to_block))

    def __call_and_check_out_of_gas(self, abi_str: str, function_name: str, calls: List[dict]) -> List[Any]:
        if len(calls) == 0:
            return []
        try:
            result = self.__call_contract_function(self.multicall_address, abi_str, function_name, calls)
            return result
        except OutOfGasException as e:
            if len(calls) == 1:
                logger.error(calls[0])
                raise e
            mid = len(calls) // 2
            result0 = self.__call_and_check_out_of_gas(abi_str, function_name, calls[:mid])
            result1 = self.__call_and_check_out_of_gas(abi_str, function_name, calls[mid:])
            return result0 + result1

    def __multicall_by_batch(self, calls: List[Call]) -> Iterable[Any]:
        logger.debug('multicall calls[0]: {} {} {}', calls[0].address, calls[0].solidity, calls[0].params)
        solidity = 'function aggregate3(tuple(address target,bool allowFailure,bytes callData)[]) ' \
                   'payable returns (tuple(bool success,bytes returnDate)[])'
        abi = solidity_to_abi(solidity)
        assert abi.get('type', '') == 'function'
        function_name = abi.get('name')
        abi_str = json.dumps([abi])
        for i, x_call in enumerate(calls):
            try:
                self.w3.toChecksumAddress(x_call.address)
            except Exception as e:
                logger.error(e)
                calls[i].address = '0x0000000000000000000000000000000000000000'
        result = self.__call_and_check_out_of_gas(abi_str, function_name,
                                                  list(map(lambda x_call: {
                                                      'target': self.w3.toChecksumAddress(x_call.address),
                                                      'allowFailure': x_call.allow_failure,
                                                      'callData': encode_by_solidity(x_call.params, x_call.solidity)},
                                                           calls))
                                                  )
        for i, call in enumerate(calls):
            try:
                x = decode_by_solidity(result[i][1], call.solidity)
                if isinstance(x, tuple) and len(x) == 1:
                    x = x[0]
                result[i] = x
            except (OverflowError, DecodingError) as e:
                logger.warning("error: {}, i in batch: {}, call: {}", e, i, call)
                result[i] = None
            except Exception as e:
                logger.error(json.dumps(solidity_to_abi(call.solidity)))
                logger.error(i)
                logger.error(call.params)
                logger.error(result[i][1])
                raise e
        return result

    def iterate_multicall(self, calls: List[Call], batch_size: int = 100) -> Iterable[Any]:
        for start in range(0, len(calls), batch_size):
            yield from self.__multicall_by_batch(calls[start:start + batch_size])

    @analysis_time_cost
    def multicall(self, calls: List[Call], batch_size: int = 100) -> List[Any]:
        """ easy multicall

        easy multicall using default multicall3 address: 0xca11bde05977b3631167028862be2a173976ca11,
        which can be set when initializing Client

        :param calls: class with attributes: address: str, solidity: str, params: list, allow_failure: bool = True
        :param batch_size: default 1000. if batch size is too big, node will return "out of gas"
        :return: a result list, each of which is same as web3.eth.contract.function.call()
        """
        logger.debug('multicall len(calls): {}', len(calls))
        return list(self.iterate_multicall(calls, batch_size))
