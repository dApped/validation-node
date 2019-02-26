import getpass
import os

import web3
from eth_account.account import Account


class NodeKeyStore:
    def __init__(self, address, private_key):
        self.address = address
        self.private_key = private_key

    @classmethod
    def init_node_key_store(cls):
        node_address, private_key = cls._node_address_and_key()
        return NodeKeyStore(node_address, private_key)

    def account_dict(self):
        return {'address': self.address, 'pvt_key': self.private_key}

    @staticmethod
    def _read_key_file(key_filename):
        encrypted_key = None
        with open(key_filename) as keyfile:
            encrypted_key = keyfile.read()
        return encrypted_key

    @classmethod
    def _node_address_and_key(cls):
        node_address = os.getenv('NODE_ADDRESS')
        private_key = os.getenv('NODE_PRIVATE_KEY')
        key_filename = os.getenv('KEY_FILENAME')
        if key_filename is not None:
            encrypted_key = cls._read_key_file(key_filename)
            password = getpass.getpass('Input password to decrypt the node key: ')
            private_key = web3.eth.Account.decrypt(encrypted_key, password)
            node_address = Account.privateKeyToAccount(private_key).address
        return node_address, private_key


node_key_store = NodeKeyStore.init_node_key_store()
