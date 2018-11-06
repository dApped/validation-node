import logging

import common
from database import database

logger = logging.getLogger('flask.app')


def determine_rewards(event, consensus_votes_by_users, ether_balance, token_balance):
    if event.disputer in consensus_votes_by_users:
        logger.info('Disputer %s in consensus', event.disputer)
        token_balance -= event.dispute_amount

    if event.staking_amount > 0:
        token_balance -= event.staking_amount * len(consensus_votes_by_users)

    if event.rewards_distribution_function == 0:
        eth_rewards, token_rewards = calculate_linear_rewards(ether_balance, token_balance,
                                                              consensus_votes_by_users)
    elif event.rewards_distribution_function == 1:
        eth_rewards, token_rewards = calculate_exponential_rewards(ether_balance, token_balance,
                                                                   consensus_votes_by_users)
    else:
        logger.error('Rewards function %d not supported', event.rewards_distribution_function)
        return

    rewards_dict = {
        user_id: database.Rewards.reward_dict(
            eth_reward=eth_rewards[i], token_reward=token_rewards[i])
        for i, user_id in enumerate(consensus_votes_by_users)
    }

    if event.disputer in consensus_votes_by_users:
        logger.info('Disputer %s added event dispute', event.disputer)
        rewards_dict[event.disputer][database.Rewards.TOKEN_KEY] += event.dispute_amount

    if event.staking_amount > 0:
        for user_id in consensus_votes_by_users:
            rewards_dict[user_id][database.Rewards.TOKEN_KEY] += event.staking_amount
    database.Rewards.create(event.event_id, rewards_dict)


def calculate_linear_rewards(ether_balance, token_balance, consensus_votes_by_users):
    votes_count = len(consensus_votes_by_users)

    eth_reward = int(ether_balance / votes_count)
    token_reward = int(token_balance / votes_count)

    eth_rewards = [eth_reward for _ in range(votes_count)]
    token_rewards = [token_reward for _ in range(votes_count)]
    return eth_rewards, token_rewards


def _exponential_factor(min_reward, factor, i):
    return min_reward + 1 / (factor * i + 1)


def _determine_params(rewards_list):
    last = rewards_list[-1]
    first = rewards_list[0] - last
    multi = 29 / first
    return last, multi


def _rescale(reward, last, multi):
    return (reward - last) * multi + 1


def calculate_exponential_rewards(ether_balance, token_balance, consensus_votes_by_users):
    num_users = len(consensus_votes_by_users)
    min_reward = 1.0
    factor = 8 / num_users
    rewards_list = [_exponential_factor(min_reward, factor, i) for i in range(num_users)]
    last, multi = _determine_params(rewards_list)
    rewards_list = [_rescale(reward, last, multi) for reward in rewards_list]
    rewards_sum = sum(rewards_list)

    eth_rewards, token_rewards = [], []
    for reward in rewards_list:
        part = reward / rewards_sum
        eth_rewards.append(int(part * ether_balance))
        token_rewards.append(int(part * token_balance))
    return eth_rewards, token_rewards


def set_consensus_rewards(w3, event_id):
    logger.info('Master node started setting rewards for %s', event_id)
    user_ids, eth_rewards, token_rewards = database.Rewards.get_lists(event_id)
    contract_abi = common.verity_event_contract_abi()
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    # TODO should batch transacts to setRewards if a lot of users due to gas limit
    set_rewards_fun = contract_instance.functions.setRewards(user_ids, eth_rewards, token_rewards)
    common.function_transact(w3, set_rewards_fun)
    logger.info('Master node finished setting rewards for %s', event_id)
    mark_rewards_set(w3, contract_instance, event_id, user_ids, eth_rewards, token_rewards)


def mark_rewards_set(w3, contract_instance, event_id, user_ids, eth_rewards, token_rewards):
    logger.info('Master node started marking rewards for %s', event_id)
    rewards_hash = database.Rewards.hash(user_ids, eth_rewards, token_rewards)
    mark_rewards_set_fun = contract_instance.functions.markRewardsSet(rewards_hash)
    common.function_transact(w3, mark_rewards_set_fun)
    logger.info('Master node finished marking rewards for %s', event_id)


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
