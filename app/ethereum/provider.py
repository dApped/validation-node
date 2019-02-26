import logging
import os

import web3

logger = logging.getLogger()


class EthProvider:
    def __init__(self, node_key_store):
        self.ETH_RPC_PROVIDER = os.getenv('ETH_RPC_PROVIDER')
        self.node_key_store = node_key_store

    def web3_provider(self):
        w3 = web3.Web3(web3.HTTPProvider(self.ETH_RPC_PROVIDER))
        try:
            w3.eth.defaultAccount = self.node_key_store.address
        except Exception as e:
            logger.exception(e)
        return w3
