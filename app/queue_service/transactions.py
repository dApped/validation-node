import logging
import time
from datetime import datetime, timedelta

import requests
import web3
from web3.gas_strategies.time_based import fast_gas_price_strategy

from database import database
from key_store import node_key_store
from queue_service.queue_service import QUEUE_IN, RESULTS_DICT, Job

logger = logging.getLogger()

GAS_PRICE_FACTOR = 1.2
GAS_LIMIT_FACTOR = 1.2
WAIT_FOR_TRANSACTION_RECEIPT_TIMEOUT = 60 * 15  # 15 minutes


def _raw_transaction(w3, contract_function, account, gas_price, nonce, event_id):
    transaction = {
        'from': account['address'],
        'nonce': nonce,
        'gas': 4000000,  # this will be overriden by estimateGas
    }
    gas = _estimate_gas_limit(contract_function)
    transaction['gasPrice'] = gas_price
    transaction['gas'] = gas
    signed_txn = w3.eth.account.signTransaction(
        contract_function.buildTransaction(transaction), private_key=account['pvt_key'])
    raw_txn = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    logger.info('[%s] Raw transaction nonce: %d, gas_price: %d, gas: %d', event_id, nonce,
                gas_price, gas)
    return raw_txn


def _estimate_gas_limit(contract_function):
    return 4000000


def _estimate_gas_price(w3, wei_addition=0):
    w3.eth.setGasPriceStrategy(fast_gas_price_strategy)
    return int(GAS_PRICE_FACTOR * w3.eth.generateGasPrice() + wei_addition)


def _next_nonce(w3, account_address, event_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            return w3.eth.getTransactionCount(account_address)
        except Exception as e:
            logger.info('[%s] Get nonce %s exception. Retry %d/%d', event_id, e, attempt + 1,
                        max_retries)
            time.sleep(60 * 1)
    logger.exception('Could not get nonce')
    return None


def _should_execute_transaction(w3, contract_function, event_id):
    function_name = contract_function.fn_name
    if function_name in {'approveRewards', 'rejectRewards'}:
        # avoid sending last approve or reject transaction that always fails
        event_instance = database.VerityEvent.instance(w3, event_id)
        if event_instance.functions.validationState().call() != 1:
            logger.info('[%s] Event is not in validating state. Skipping %s', event_id,
                        function_name)
            return False
    return True


def _execute_transaction(w3, contract_function, event_id, max_retries=3):
    if not _should_execute_transaction(w3, contract_function, event_id):
        return None

    account = node_key_store.account_dict()
    for retry in range(max_retries):
        next_nonce = _next_nonce(w3, account['address'], event_id, max_retries=max_retries)
        if next_nonce is None:
            return None
        gas_price_addition = web3.Web3.toWei(retry, 'gwei')
        try:
            gas_price = _estimate_gas_price(w3, wei_addition=gas_price_addition)
            tx_raw = _raw_transaction(w3, contract_function, account, gas_price, next_nonce,
                                      event_id)
            tx_receipt = w3.eth.waitForTransactionReceipt(
                tx_raw, timeout=WAIT_FOR_TRANSACTION_RECEIPT_TIMEOUT)
            logger.info('[%s] Transmitted transaction %s', event_id,
                        web3.Web3.toHex(tx_receipt['transactionHash']))
            return tx_receipt
        except web3.utils.threads.Timeout as e:
            logger.info('[%s] Replacing transaction with increased gas price. Retry %d/%d: %s',
                        event_id, retry + 1, max_retries, e)
            time.sleep(60 * 1)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            logger.info('[%s] Transaction %s exception. Sleeping 1 minute then retry it', event_id,
                        e.__class__.__name__)
            time.sleep(60 * 1)
        except Exception:
            logger.exception('New transaction with new nonce. Retry: %d/%d', retry + 1, max_retries)
            time.sleep(60 * 1)
    return None


def queue_transaction(w3, contract_function, event_id='default'):
    contract_function_name = contract_function.fn_name
    job = Job(event_id, contract_function_name, _execute_transaction, w3, contract_function,
              event_id)
    QUEUE_IN.put(job)

    datetime_last_message = datetime.now()
    while job.id_ not in RESULTS_DICT:
        time.sleep(1)
        current_datetime = datetime.now()
        if datetime_last_message + timedelta(minutes=1) < current_datetime:
            datetime_last_message = current_datetime
            logger.info('[%s][%s] Waiting %s to complete. Queue size %d', event_id, job.id_,
                        contract_function_name, QUEUE_IN.qsize())

    logger.info('[%s][%s] %s completed. Queue size %d', event_id, job.id_, contract_function_name,
                QUEUE_IN.qsize())
    job_result = RESULTS_DICT.pop(job.id_)
    result = job_result.result
    if result is None:
        logger.info('[%s][%s] %s empty result', event_id, job.id_, contract_function_name)
        return None
    tx_hash = web3.Web3.toHex(result['transactionHash'])
    logger.info('[%s][%s] %s, tx_hash: %s', event_id, job.id_, contract_function_name, tx_hash)
    return tx_hash
