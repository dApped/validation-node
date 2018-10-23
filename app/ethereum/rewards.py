import logging

import common
from database import database
from ethereum.provider import NODE_WEB3

logger = logging.getLogger('flask.app')


def determine_rewards(event_id, consensus_votes_by_users, ether_balance, token_balance):

    event = database.VerityEvent.get(event_id)
    if event.disputer in consensus_votes_by_users:
        logger.info('Disputer %s in consensus', event.disputer)
        token_balance -= event.dispute_amount

    # TODO support non linear reward distribution
    votes_count = len(consensus_votes_by_users)
    user_ether_reward_in_wei = int(NODE_WEB3.toWei(ether_balance, 'ether') / votes_count)
    user_token_reward_in_wei = int(NODE_WEB3.toWei(token_balance, 'ether') / votes_count)

    rewards_dict = {
        user_id: database.Rewards.reward_dict(
            eth_reward=user_ether_reward_in_wei, token_reward=user_token_reward_in_wei)
        for user_id in consensus_votes_by_users
    }
    if event.disputer in consensus_votes_by_users:
        rewards_dict[event.disputer] = rewards_dict[event.disputer] + event.dispute_amount
    database.Rewards.create(event_id, rewards_dict)


def set_consensus_rewards(w3, event_id):
    logger.info('Started setting rewards for %s', event_id)
    user_ids, eth_rewards, token_rewards = database.Rewards.get_lists(event_id)
    contract_abi = common.verity_event_contract_abi()
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    # TODO should batch transacts to setRewards if a lot of users due to gas limit
    set_rewards_fun = contract_instance.functions.setRewards(user_ids, eth_rewards, token_rewards)
    common.function_transact(w3, set_rewards_fun)
    logger.info('Finished setting rewards for %s', event_id)
    mark_rewards_set(w3, contract_instance, event_id, user_ids, eth_rewards, token_rewards)


def mark_rewards_set(w3, contract_instance, event_id, user_ids, eth_rewards, token_rewards):
    logger.info('Started marking rewards for %s', event_id)
    rewards_hash = database.Rewards.hash(user_ids, eth_rewards, token_rewards)
    mark_rewards_set_fun = contract_instance.functions.markRewardsSet(rewards_hash)
    common.function_transact(w3, mark_rewards_set_fun)
    logger.info('Finished marking rewards for %s', event_id)


def validate_rewards(w3, event_id, validation_round):
    event_contract_abi = common.verity_event_contract_abi()
    event_contract = w3.eth.contract(address=event_id, abi=event_contract_abi)
    contract_reward_user_ids = event_contract.functions.getRewardsIndex().call()
    # TODO should batch calls to getRewards if a lot of users due to gas limit
    (contract_reward_ether,
     contract_reward_token) = event_contract.functions.getRewards(contract_reward_user_ids).call()

    contract_rewards_dict = database.Rewards.transform_lists_to_dict(
        contract_reward_user_ids, contract_reward_ether, contract_reward_token)
    node_rewards_dict = database.Rewards.get(event_id)
    rewards_match = do_rewards_match(node_rewards_dict, contract_rewards_dict)
    if rewards_match:
        logger.info('Rewards match for event %s. Approving rewards for round %d', event_id,
                    validation_round)
        approve_fun = event_contract.functions.approveRewards(validation_round)
        common.function_transact(w3, approve_fun)
    else:
        logger.info('Rewards DO NOT match for event %s. Rejecting rewards for round %d', event_id,
                    validation_round)
        (user_ids, eth_rewards,
         token_rewards) = database.Rewards.transform_dict_to_lists(node_rewards_dict)
        alt_hash = database.Rewards.hash(user_ids, eth_rewards, token_rewards)
        reject_fun = event_contract.functions.rejectRewards(validation_round, alt_hash)
        common.function_transact(w3, reject_fun)


def do_rewards_match(node_rewards, contract_rewards):
    return node_rewards == contract_rewards
