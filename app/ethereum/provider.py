import logging
import os

from web3 import HTTPProvider, Web3

logger = logging.getLogger('flask.app')


class EthProvider:

    def __init__(self):
        self.ETH_RPC_PROVIDER = os.getenv('ETH_RPC_PROVIDER')
        # TODO while nodes don't get their own wallet or they 'outside' wallet
        # This fails in debug mode as flask starts 2 times
        try:
            node_id = int(os.getenv('DEV_NODE_ACCOUNT_IDX'))
        except Exception as e:
            logger.error(e)
            node_id = 1
        self.NODE_ACCOUNT_IDX = node_id

    def web3(self):
        w3 = Web3(HTTPProvider(self.ETH_RPC_PROVIDER))
        w3.eth.defaultAccount = w3.eth.accounts[self.NODE_ACCOUNT_IDX]
        logger.debug('MY ETH ACCOUNT %s' % w3.eth.defaultAccount)
        return w3
