import json
import logging
import os
import time
from enum import Enum

from eth_account.messages import defunct_hash_message
from web3 import Web3
from web3.auto import w3 as web3_auto

from database import database
from ethereum.provider import EthProvider

logger = logging.getLogger()

CHUNK_SIZE = 20


class AddressType(Enum):
    IP = 1
    WEBSOCKET = 2


def verity_event_contract_abi():
    return json.loads(open(os.path.join(os.getenv('CONTRACT_DIR'),
                                        'VerityEvent.json')).read())['abi']


def event_registry_contract_abi():
    return json.loads(open(os.path.join(os.getenv('CONTRACT_DIR'),
                                        'EventRegistry.json')).read())['abi']


def node_registry_contract_abi():
    return json.loads(open(os.path.join(os.getenv('CONTRACT_DIR'),
                                        'NodeRegistry.json')).read())['abi']


def event_registry_address():
    return Web3.toChecksumAddress(os.getenv('EVENT_REGISTRY_ADDRESS'))


def node_registry_address():
    return Web3.toChecksumAddress(os.getenv('NODE_REGISTRY_ADDRESS'))


def node_id():
    return os.getenv('NODE_ADDRESS')


def node_ip():
    return os.getenv('NODE_IP')


def node_port():
    return os.getenv('HTTP_PORT')


def node_ip_port():
    return '%s:%s' % (node_ip(), node_port())


def node_websocket_port():
    return os.getenv("WEBSOCKET_PORT")


def node_websocket_ip_port():
    return '%s:%s' % (node_ip(), node_websocket_port())


def function_transact(w3, contract_function, max_retries=3):
    account = EthProvider.account_dict()

    account['address'] = Web3.toChecksumAddress(account['address'])
    next_nonce = w3.eth.getTransactionCount(account['address'])

    for attempt in range(max_retries):
        try:
            raw_txn = _raw_transaction(w3, contract_function, account, next_nonce + attempt)
            tx_receipt = w3.eth.waitForTransactionReceipt(raw_txn)
            logger.info('Transmitted transaction %s', Web3.toHex(tx_receipt['transactionHash']))
            return tx_receipt['transactionHash']
        except Exception as e:
            logger.error(e)
            if attempt < max_retries:
                logger.info('Retrying %d with higher nonce', attempt)
            else:
                logger.error('Final failed to submit transaction')
            time.sleep(1)


def _raw_transaction(w3, contract_function, account, nonce):
    gas_price = Web3.toWei(10, 'gwei')
    gas_estimate = 4000000

    transaction = {
        'from': account['address'],
        'gasPrice': gas_price,
        'gas': gas_estimate,
        'nonce': nonce,
    }
    signed_txn = w3.eth.account.signTransaction(
        contract_function.buildTransaction(transaction), private_key=account['pvt_key'])
    raw_txn = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    return raw_txn


def list_to_chunks(list_, chunk_size=CHUNK_SIZE):
    """ Converts a list to chunks with chunk_size entries """
    return list(list_[i:i + chunk_size] for i in range(0, len(list_), chunk_size))


def lists_to_chunks(*lists, batch_size=CHUNK_SIZE):
    """ Converts multiple lists to chunks with chunk_size entries """
    assert len({len(list_) for list_ in lists}) == 1, "Lists have different lengths"

    chunks = list(list_to_chunks(list_, batch_size) for list_ in lists)
    return list(map(list, zip(*chunks)))  # transpose lists


def is_vote_payload_valid(data):
    if data is None:
        return False
    for field in ['data', 'signedData']:
        if field not in data or data[field] is None:
            return False
    for param in {'user_id', 'event_id', 'answers'}:
        if param not in data['data'] or data['data'][param] is None:
            return False
    for answer in data['data']['answers']:
        for key in [database.Vote.ANSWERS_VALUE_KEY, database.Vote.ANSWERS_SORT_KEY]:
            if key not in answer:
                return False
    return True


def parse_fields_from_json_data(json_data):
    data = json_data['data']
    event_id = data['event_id']
    user_id = data['user_id']
    signature = json_data['signedData']
    return event_id, user_id, data, signature


def is_vote_valid(timestamp, user_id, event):
    if timestamp < event.event_start_time or timestamp > event.event_end_time:
        message = '[%s] Voting is not active. Event Start Time %d, Event End Time: %d'
        message = message % (event.event_id, event.event_start_time, event.event_end_time)
        logger.info(message)
        return False, message

    user_registered = database.Participants.exists(event.event_id, user_id)
    if not user_registered:
        message = '[%s] User %s is not registered' % (event.event_id, user_id)
        logger.info(message)
        return False, message
    return True, ''


def is_vote_signed(vote_json):
    vote_data = vote_json['data']
    data_msg = defunct_hash_message(text=str(vote_data))
    signer = web3_auto.eth.account.recoverHash(data_msg, signature=vote_json['signedData'])
    return vote_data['user_id'] == signer