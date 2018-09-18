import logging
import os

from web3 import HTTPProvider, Web3

import common
from database import events as database_events
from database.events import Rewards, VerityEvent

provider = os.getenv('ETH_RPC_PROVIDER')
w3 = Web3(HTTPProvider(provider))

logger = logging.getLogger('flask.app')


def determine_rewards(event_id, consensus_votes):
    event_instance = VerityEvent.instance(w3, event_id)

    w3.eth.defaultAccount = w3.eth.accounts[0]
    [total_eth_balance, total_token_balance] = event_instance.functions.getBalance().call()

    in_consensus_votes_num = len(consensus_votes)

    # eth_reward_single = total_eth_balance / in_consensus_votes_num
    # token_reward_single = total_token_balance / in_consensus_votes_num

    # TODO calculate rewards without floats
    rewards_dict = {
        vote.user_id: database_events.Rewards.reward_dict(1, 2)
        for vote in consensus_votes
    }
    Rewards.create(event_id, rewards_dict)

    return rewards_dict


def set_consensus_rewards(event_id):
    logger.info('Setting rewards for %s started', event_id)
    user_ids, eth_rewards, token_rewards = database_events.Rewards.get_lists(event_id)
    contract_abi = common.verity_event_contract_abi()

    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    contract_instance.functions.setRewards(user_ids, eth_rewards, token_rewards).transact()
    logger.info('Setting rewards for %s done', event_id)

    mark_rewards_set(contract_instance, event_id, user_ids, eth_rewards, token_rewards)


def mark_rewards_set(contract_instance, event_id, user_ids, eth_rewards, token_rewards):
    logger.info('Marking rewards for %s started', event_id)
    rewards_hash = database_events.Rewards.hash(user_ids, eth_rewards, token_rewards)
    contract_instance.functions.markRewardsSet(rewards_hash).transact()
    logger.info('Marking rewards for %s done', event_id)


def validate_rewards(event_id):
    """
    TODO
    Validates rewards set
    Sends 'ok' or 'nok' to conract
    """
    pass
