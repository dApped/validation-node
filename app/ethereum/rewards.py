import os

from web3 import HTTPProvider, Web3

import common
from database import events as database_events
from database.events import Event, Rewards

provider = os.getenv('ETH_RPC_PROVIDER')
w3 = Web3(HTTPProvider(provider))


def determine_rewards(event_id, consensus_votes):
    event_instance = Event.instance(w3, event_id)

    [total_eth_balance, total_token_balance] = event_instance.functions.getBalance().call()

    in_consensus_votes_num = len(consensus_votes)
    eth_reward_gwei = Web3.toWei(total_eth_balance / in_consensus_votes_num)
    token_reward_gwei = Web3.toWei(total_token_balance / in_consensus_votes_num)

    rewards_dict = {
        vote.user_id: {
            'eth': eth_reward_gwei,
            'token': token_reward_gwei
        }
        for vote in consensus_votes
    }
    Rewards.create(event_id, rewards_dict)

    return rewards_dict


def set_consensus_rewards(event_id):
    user_ids, eth_rewards, token_rewards = database_events.Rewards.get_lists(event_id)
    contract_abi = common.verity_event_contract_abi()

    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    contract_instance.functions.setRewards(user_ids, eth_rewards, token_rewards).transact()


def validate_rewards(event_id):
    """
    TODO
    Validates rewards set
    Sends 'ok' or 'nok' to conract
    """
    pass
