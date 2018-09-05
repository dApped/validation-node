# -*- coding: utf-8 -*-
import os

from web3 import Web3, HTTPProvider

provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))

def set_consensus_rewards(rewards):
    """
    TODO
    Setting rewards and write to blockchain
    """

    return True


def validate_rewards(event_id):
    """
    TODO
    Validates rewards set
    Sends 'ok' or 'nok' to conract
    """