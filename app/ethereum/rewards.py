# -*- coding: utf-8 -*-
import os

from web3 import Web3, HTTPProvider

provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))

def determine_rewards(consensus_votes):
    token_rewards = []
    eth_rewards = []

    return token_rewards, eth_rewards


def set_consensus_rewards(event_id, rewards):
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
    pass