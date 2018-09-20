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
    event_contract_abi = common.verity_event_contract_abi()
    event_contract = w3.eth.contract(address=event_id, abi=event_contract_abi)

    contract_reward_user_ids = event_contract.functions.getRewardsIndex().call()
    # TODO should batch calls to getRewards if a lot of users due to gas limit
    [contract_reward_ether, contract_reward_token] = event_contract.functions.getRewards(
        contract_reward_user_ids).call()

    contract_rewards_dict = Rewards.transform_lists_to_dict(contract_reward_user_ids,
                                                            contract_reward_ether,
                                                            contract_reward_token)
    node_rewards_dict = Rewards.get(event_id)

    rewards_match = do_rewards_match(node_rewards_dict, contract_rewards_dict)
    if rewards_match:
        logger.info('Rewards match for event %s. Approving rewards for round %d', event_id,
                    validation_round)
        event_contract.functions.approveRewards(validation_round).transact()
    else:
        logger.info('Rewards DO NOT match for event %s. Rejecting rewards for round %d', event_id,
                    validation_round)
        event_contract.functions.approveRewards(validation_round).transact()


def do_rewards_match(node_rewards, contract_rewards):
    return node_rewards == contract_rewards
