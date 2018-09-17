# -*- coding: utf-8 -*-
import os

from web3 import Web3, HTTPProvider, utils

from database.events import Event
provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))


def determine_rewards(event_id, consensus_votes):
    #addresses = [vote.user_id for vote in consensus_votes]
    #token_rewards = [10 for vote in consensus_votes]
    #eth_rewards = [0.1 for vote in consensus_votes]

    event_instance = Event.instance(event_id)

    [total_eth_balance, total_token_balance] = event_instance.functions.getBalance().call()

    # TODO support multiple distribution functions, for now assume linear
    in_consensus_votes_num = len(consensus_votes)

    eth_reward_gwei = utils.toWei(total_eth_balance/in_consensus_votes_num)
    token_reward_gwei = utils.toWei(total_token_balance / in_consensus_votes_num)


    rewards = []
    for vote in consensus_votes:
        r = {vote.user_id : {'eth': eth_reward_gwei, 'token': token_reward_gwei}}
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
