import os
import pickle
from pathlib import Path

from dotenv import load_dotenv
from web3 import HTTPProvider, Web3
from web3.gas_strategies.time_based import fast_gas_price_strategy

GAS_PRICE_FACTOR = 1
GAS_AMOUNT_FACTOR = 2
STAKING_AMOUNT = 10
DISPUTE_STAKING_AMOUNT = 100

VALIDATION_NODE_KEYS = [('***REMOVED***',
                         '***REMOVED***'),
                        ('***REMOVED***',
                         '***REMOVED***'),
                        ('***REMOVED***',
                         '***REMOVED***')]
VALIDATION_NODE_ACCOUNTS = [{
    'address': node_keys[0],
    'pvt_key': node_keys[1],
    'password': ''
} for node_keys in VALIDATION_NODE_KEYS]


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


def function_transact_with_account(w3, contract_function, account, max_retries=3):
    account['address'] = Web3.toChecksumAddress(account['address'])
    next_nonce = w3.eth.getTransactionCount(account['address'])

    for attempt in range(max_retries):
        try:
            raw_txn = _raw_transaction(w3, contract_function, account, next_nonce + attempt)
            tx_receipt = w3.eth.waitForTransactionReceipt(raw_txn)
            print('Transmitted transaction %s' % Web3.toHex(tx_receipt['transactionHash']))
            return tx_receipt['transactionHash']
        except Exception as e:
            print(e)
            if attempt < max_retries:
                print('Retrying %d with higher nonce' % attempt)
            else:
                print('Final failed to submit transaction')


def deploy_event_contract(w3, constructor, owner_account):
    next_nonce = w3.eth.getTransactionCount(owner_account['address'])
    gas_price = int(w3.eth.generateGasPrice() * GAS_PRICE_FACTOR)

    transaction = {
        'from': owner_account['address'],
        'gasPrice': gas_price,
        'nonce': next_nonce,
    }
    txn = constructor.buildTransaction(transaction)  # Use default gas amount
    signed_txn = w3.eth.account.signTransaction(txn, private_key=owner_account['pvt_key'])
    raw_txn = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    txn_receipt = w3.eth.waitForTransactionReceipt(raw_txn)
    next_nonce += 1
    return txn_receipt['contractAddress'], next_nonce


def send_raw_transaction(w3, from_account, to_address, amount, next_nonce=None):
    sender_address = Web3.toChecksumAddress(from_account['address'])
    sender_private_key = from_account['pvt_key']
    if next_nonce is None:
        next_nonce = w3.eth.getTransactionCount(sender_address)

    try:
        gas_price = int(w3.eth.generateGasPrice() * GAS_PRICE_FACTOR)
    except Exception as e:
        print(e)
        gas_price = w3.toWei(10, 'gwei')

    transaction = {
        'to': Web3.toChecksumAddress(to_address),
        'gasPrice': gas_price,
        'nonce': next_nonce,
        'value': amount
    }

    transaction['gas'] = int(w3.eth.estimateGas(transaction) * GAS_AMOUNT_FACTOR)
    signed_trx = w3.eth.account.signTransaction(transaction, sender_private_key)
    send_raw_trx = w3.eth.sendRawTransaction(signed_trx.rawTransaction)
    next_nonce += 1
    return send_raw_trx, next_nonce


class DevEnvironment:
    def __init__(self):
        env_path = Path('..') / '.env'
        load_dotenv(dotenv_path=env_path)

        eth_rpc_provider = os.getenv('ETH_RPC_PROVIDER', '')
        self.eth_rpc_provider = eth_rpc_provider
        self._init_web3(eth_rpc_provider)

        self.provider_name = self.provider_name_from_env()
        if self.provider_name == 'local':
            print('Using local dev chain')
            self._init_local()
        else:
            print('Using ropsten')
            self._init_ropsten()

    @staticmethod
    def provider_name_from_env():
        provider = os.getenv('ETH_RPC_PROVIDER', '')
        if 'host.docker.internal' in provider or provider == '':
            return 'local'
        else:
            return 'ropsten'

    def _init_web3(self, provider):
        w3 = Web3(HTTPProvider(provider))
        w3.eth.setGasPriceStrategy(fast_gas_price_strategy)
        self.w3 = w3

    def _init_local(self):
        self.owner_account = {
            'address': self.w3.toChecksumAddress('0x00a329c0648769A73afAc7F9381E08FB43dBEA72'),
            'pvt_key': '0x4d5db4107d237df6a3d58ee5f70ae63d73d7658d4026f2eefd2f204c81682cb7'
        }
        self.init_contracts = {}
        self.time_to_join_sec = 20

    def _init_ropsten(self):
        self.owner_account = {
            'address': '0xf670De5a0dE38fF5B48233e310a5ACb5293Bcee5',
            'pvt_key': '0xd32069b398e2ff0739cde4d3184c4f712b770847c2b9e685efd4e37e2b28e0c0'
        }
        self.init_contracts = {
            'VerityToken': Web3.toChecksumAddress('0x4af4114f73d1c1c903ac9e0361b379d1291808a2'),
            'EventRegistry': Web3.toChecksumAddress('0xe15a92dd02ba5b2fcae2cb136bf2f7793f209b80'),
            'NodeRegistry': Web3.toChecksumAddress('0x4bD554f42a57D2345D480e8c1f79fEa661F28813')
        }
        self.time_to_join_sec = 300

    def dump(self):
        print('Dumping DevEnv for %s provider' % self.provider_name)
        self.w3 = None
        with open('data/%s.pkl' % self.provider_name, 'wb') as obj:
            pickle.dump(self, obj)

    @classmethod
    def load(cls, provider):
        print('Loading %s DevEnv' % provider)
        with open('data/%s.pkl' % provider, 'rb') as obj:
            de = pickle.load(obj)
            eth_node = de.eth_rpc_provider
            print('Using %s node' % eth_node)
            de._init_web3(eth_node)
            return de

    @staticmethod
    def accounts():
        accounts = pickle.load(open('data/secrets.pkl', 'rb'))
        return accounts

    @classmethod
    def accounts_with_validation_nodes_accounts(cls):
        accounts = cls.accounts()
        for node_account in VALIDATION_NODE_ACCOUNTS:
            accounts.append(node_account)
        return accounts
