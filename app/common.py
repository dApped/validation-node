import json
import logging
import os
import pickle

from web3 import Web3

from ethereum.provider import EthProvider

logger = logging.getLogger('flask.app')


def verity_event_contract_abi():
    return json.loads(open(os.path.join(os.getenv('DATA_DIR'), 'VerityEvent.json')).read())['abi']


def event_registry_contract_abi():
    return json.loads(open(os.path.join(os.getenv('DATA_DIR'), 'EventRegistry.json')).read())['abi']


def event_registry_address():
    f = open(os.path.join(os.path.join(os.getenv('DATA_DIR'), 'contract_addresses.pkl')), 'rb')
    contract_addresses = pickle.load(f)
    # TODO read from environment, this is ropsten
    return Web3.toChecksumAddress('0x9718274d370b8bc15f08d7cf675df21a02848692')


def function_transact(w3, contract_function):
    account = EthProvider.account_dict()

    address = Web3.toChecksumAddress(account['address'])
    next_nonce = w3.eth.getTransactionCount(address)

    gas_estimate = 5000000
    gas_price = Web3.toWei(10, 'gwei')
    transaction = {
        'from': address,
        'gas': gas_estimate,
        'gasPrice': gas_price,
        'nonce': next_nonce,
    }
    signed_txn = w3.eth.account.signTransaction(contract_function.buildTransaction(transaction),
                                                private_key=account['pvt_key'])
    raw_txn = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(raw_txn)
    logger.info('Transmitted transaction %s', Web3.toHex(tx_receipt['transactionHash']))
    return tx_receipt['transactionHash']
