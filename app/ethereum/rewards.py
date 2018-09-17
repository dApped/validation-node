# -*- coding: utf-8 -*-
import os

from web3 import Web3, HTTPProvider

provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))


def determine_rewards(consensus_votes, distribution_function='linear'):
    #addresses = [vote.user_id for vote in consensus_votes]
    #token_rewards = [10 for vote in consensus_votes]
    #eth_rewards = [0.1 for vote in consensus_votes]

    rewards = []
    for vote in consensus_votes:
        r = {vote.user_id : {'token': t, 'eth': e}}

        rewards.append(r)



    # TODO store in REDIS
    rewards = [{'address': a, 'token': t, 'eth': e} for a, t, e in
               zip(addresses, token_rewards, eth_rewards)]




    return addresses, token_rewards, eth_rewards


def set_consensus_rewards(event_id, rewards):
    # TODO read determine_rewards from redis

    # TODO write to blockchain, scheduler

    return True


def validate_rewards(event_id):
    """
    TODO
    Validates rewards set
    Sends 'ok' or 'nok' to conract
    """
    pass
