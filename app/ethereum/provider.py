import logging
import os

from eth_account.account import Account
from web3 import HTTPProvider, Web3

import common

logger = logging.getLogger('flask.app')


class EthProvider:
    def __init__(self):
        self.ETH_RPC_PROVIDER = os.getenv('ETH_RPC_PROVIDER')

    def web3(self):
        w3 = Web3(HTTPProvider(self.ETH_RPC_PROVIDER))
        try:
            # TODO should probably have encrypted private key with passphrase here
            node_address = Account.privateKeyToAccount(os.getenv('NODE_PRIVATE_KEY'))
            w3.eth.defaultAccount = node_address.address
            logger.debug('MY ETH ACCOUNT %s', w3.eth.defaultAccount)
        except Exception as e:
            logger.error(e)
        return w3

    @staticmethod
    def account_dict():
        node_address = Web3.toChecksumAddress(common.node_id())
        node_pvt_key = os.getenv('NODE_PRIVATE_KEY')
        return {'address': node_address, 'pvt_key': node_pvt_key}


NODE_WEB3 = EthProvider().web3()
