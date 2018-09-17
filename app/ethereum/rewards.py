# -*- coding: utf-8 -*-
import os

from web3 import Web3, HTTPProvider

from database.events import Event, Rewards

provider = os.getenv('ETH_RPC_PROVIDER')
w3 = Web3(HTTPProvider(provider))


def determine_rewards(event_id, consensus_votes):
    # addresses = [vote.user_id for vote in consensus_votes]
    # token_rewards = [10 for vote in consensus_votes]
    # eth_rewards = [0.1 for vote in consensus_votes]

    event_instance = Event.instance(event_id)

    [total_eth_balance, total_token_balance] = event_instance.functions.getBalance().call()

    # TODO support multiple distribution functions, for now assume linear
    in_consensus_votes_num = len(consensus_votes)

    eth_reward_gwei = Web3.toWei(total_eth_balance / in_consensus_votes_num)
    token_reward_gwei = Web3.toWei(total_token_balance / in_consensus_votes_num)

    rewards_dict = {
        vote.user_id: {'eth': eth_reward_gwei, 'token': token_reward_gwei}
        for vote in consensus_votes
    }
    Rewards.create(event_id, rewards_dict)

    return rewards_dict


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
