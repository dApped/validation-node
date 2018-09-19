import logging

import common
from database import events as database_events
from database.events import Rewards, VerityEvent
from ethereum.provider import EthProvider

logger = logging.getLogger('flask.app')


def determine_rewards(event_id, consensus_votes):
    w3 = EthProvider().web3()

    event_instance = VerityEvent.instance(w3, event_id)
    w3.eth.defaultAccount = w3.eth.accounts[0]
    [total_ether_balance, total_token_balance] = event_instance.functions.getBalance().call()

    in_consensus_votes_num = len(consensus_votes)

    user_ether_reward_in_wei = int(w3.toWei(total_ether_balance, 'ether') / in_consensus_votes_num)
    user_token_reward_in_wei = int(w3.toWei(total_token_balance, 'ether') / in_consensus_votes_num)

    # TODO calculate rewards without floats
    rewards_dict = {
        vote.user_id: database_events.Rewards.reward_dict(eth_reward=user_ether_reward_in_wei,
                                                          token_reward=user_token_reward_in_wei)
        for vote in consensus_votes
    }
    Rewards.create(event_id, rewards_dict)


def set_consensus_rewards(event_id):
    w3 = EthProvider().web3()
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


def validate_rewards(event_id, validation_round):
    w3 = EthProvider().web3()
    contract_abi = common.verity_event_contract_abi()
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)

    # TODO read from redis if rewards have been set
    # read rewards from BC, compare with others
    rewards_match = True
    if rewards_match:
        logger.info('Rewards match. Approving rewards for round %d', validation_round)
        contract_instance.functions.approveRewards(validation_round).transact()
    else:
        logger.info('Rewards DO NOT match. Rejecting rewards for round %d', validation_round)
        contract_instance.functions.approveRewards(validation_round).transact()
