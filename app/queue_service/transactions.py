import logging
import time

import requests
import web3
from web3.gas_strategies.time_based import fast_gas_price_strategy

from key_store import node_key_store
from queue_service.queue_service import QUEUE_IN, QUEUE_OUT

logger = logging.getLogger()

GAS_PRICE_FACTOR = 1.2
GAS_LIMIT_FACTOR = 2
WAIT_FOR_TRANSACTION_RECEIPT_TIMEOUT = 60 * 15  # 15 minutes


def _raw_transaction(w3, contract_function, account, gas_price, nonce):
    transaction = {
        'from': account['address'],
        'nonce': nonce,
    }
    gas = _estimate_gas_limit(contract_function)
    transaction['gasPrice'] = gas_price
    transaction['gas'] = gas
    signed_txn = w3.eth.account.signTransaction(
        contract_function.buildTransaction(transaction), private_key=account['pvt_key'])
    raw_txn = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    logger.info('Raw transaction nonce: %d, gas_price: %d, gas: %d', nonce, gas_price, gas)
    return raw_txn


def _estimate_gas_limit(contract_function):
    return int(GAS_LIMIT_FACTOR * contract_function.estimateGas())


def _estimate_gas_price(w3, wei_addition=0):
    w3.eth.setGasPriceStrategy(fast_gas_price_strategy)
    return int(GAS_PRICE_FACTOR * w3.eth.generateGasPrice() + wei_addition)


def _next_nonce(w3, address, max_retries=3):
    for attempt in range(max_retries):
        try:
            return w3.eth.getTransactionCount(address)
        except Exception as e:
            logger.info('Get nonce %s exception. Retry %d/%d', e, attempt + 1, max_retries)
            time.sleep(60 * 1)
    logger.exception('Could not get nonce')
    return None


def _function_transact(w3, contract_function, max_retries=3):
    account = node_key_store.account_dict()

    for retry in range(max_retries):
        next_nonce = _next_nonce(w3, account['address'])
        if next_nonce is None:
            return None
        gas_price_addition = web3.Web3.toWei(retry, 'gwei')
        try:
            gas_price = _estimate_gas_price(w3, wei_addition=gas_price_addition)
            tx_raw = _raw_transaction(w3, contract_function, account, gas_price, next_nonce)
            tx_receipt = w3.eth.waitForTransactionReceipt(
                tx_raw, timeout=WAIT_FOR_TRANSACTION_RECEIPT_TIMEOUT)
            logger.info('Transmitted transaction %s',
                        web3.Web3.toHex(tx_receipt['transactionHash']))
            return tx_receipt
        except web3.utils.threads.Timeout as e:
            logger.info('Replacing transaction with increased gas price. Retry %d/%d: %s',
                        retry + 1, max_retries, e)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            logger.info('Transaction %s exception. Sleeping 1 minute then retry it',
                        e.__class__.__name__)
            time.sleep(60 * 1)
        except Exception:
            logger.exception('New transaction with new nonce. Retry: %d/%d', retry + 1, max_retries)
    return None


def queue_transaction(w3, contract_function, event_id='default'):
    QUEUE_IN.put((_function_transact, w3, contract_function))
    QUEUE_IN.join()
    while True:
        result = QUEUE_OUT.get(block=False)
        logger.info('Task completed %s', result)
        return result
