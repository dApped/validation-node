import logging
from enum import Enum
from statistics import mean, median

import common
from database import database

logger = logging.getLogger()


class VoteTimestampsMetric(Enum):
    MEAN = 1
    MEDIAN = 2


def determine_rewards(event, consensus_votes_by_users, ether_balance, token_balance):
    event_id = event.event_id
    if event.disputer in consensus_votes_by_users:
        logger.info('[%s] Disputer %s in consensus', event_id, event.disputer)
        token_balance -= event.dispute_amount

    if event.staking_amount > 0:
        token_balance -= event.staking_amount * len(consensus_votes_by_users)

    if event.rewards_distribution_function == 0:
        logger.info('[%s] Calculating rewards using linear function', event_id)
        user_ids, eth_rewards, token_rewards = calculate_linear_rewards(
            ether_balance, token_balance, consensus_votes_by_users)
    elif event.rewards_distribution_function == 1:
        logger.info('[%s] Calculating rewards using exponential function', event_id)
        user_ids, eth_rewards, token_rewards = calculate_exponential_rewards(
            ether_balance, token_balance, consensus_votes_by_users)
    else:
        logger.error('[%s] Rewards function %d not supported', event_id,
                     event.rewards_distribution_function)
        return

    rewards_dict = {}
    for i, user_id in enumerate(user_ids):
        rewards_dict[user_id] = database.Rewards.reward_dict(
            eth_reward=eth_rewards[i], token_reward=token_rewards[i])
    if not user_ids:
        logger.warning('[%s] Did not set the rewards because user_ids were empty', event_id)

    if event.disputer in consensus_votes_by_users:
        rewards_dict[event.disputer][database.Rewards.TOKEN_KEY] += event.dispute_amount

    logger.warning('[%s] Adding staking amount to users that were in consensus', event_id)
    for user_id in consensus_votes_by_users:
        rewards_dict[user_id][database.Rewards.TOKEN_KEY] += event.staking_amount
    database.Rewards.create(event.event_id, rewards_dict)


def calculate_linear_rewards(ether_balance, token_balance, consensus_votes_by_users):
    user_ids = list(consensus_votes_by_users.keys())
    votes_count = len(consensus_votes_by_users)

    eth_reward = int(ether_balance / votes_count)
    token_reward = int(token_balance / votes_count)

    eth_rewards = [eth_reward for _ in range(votes_count)]
    token_rewards = [token_reward for _ in range(votes_count)]
    return user_ids, eth_rewards, token_rewards


def _exponential_factor(min_reward, factor, i):
    return min_reward + 1 / (factor * i + 1)


def _determine_params(rewards_list):
    last = rewards_list[-1]
    first = rewards_list[0] - last
    multi = 29 / first
    return last, multi


def _rescale(reward, last, multi):
    return (reward - last) * multi + 1


def order_users_by_vote_timestamps(consensus_votes_by_users,
                                   timestamps_metric=VoteTimestampsMetric.MEAN):
    scores = []
    for user_id, votes in consensus_votes_by_users.items():
        timestamps = [vote.timestamp for vote in votes]
        if not timestamps:
            logging.warning('Users %s vote timestamps are empty', user_id)
            continue
        if timestamps_metric == VoteTimestampsMetric.MEAN:
            score = mean(timestamps)
        elif timestamps_metric == VoteTimestampsMetric.MEDIAN:
            score = median(timestamps)
        else:
            raise Exception('Given TimestampsMetric is not supported: ' + str(timestamps_metric))
        scores.append((user_id, score))
    scores = sorted(scores, key=lambda x: x[1])
    return [user_id for user_id, _ in scores]


def calculate_exponential_rewards(ether_balance, token_balance, consensus_votes_by_users):
    user_ids = order_users_by_vote_timestamps(consensus_votes_by_users)
    if not user_ids:
        logger.info('User ids are empty. Cannot calculate exponential rewards')
        return [], [], []
    num_users = len(consensus_votes_by_users)
    min_reward = 1.0
    factor = 8 / num_users
    exponential_factors = [_exponential_factor(min_reward, factor, i) for i in range(num_users)]
    last, multi = _determine_params(exponential_factors)
    exponential_factors = [_rescale(reward, last, multi) for reward in exponential_factors]
    rewards_sum = sum(exponential_factors)

    eth_rewards, token_rewards = [], []
    for reward in exponential_factors:
        part = reward / rewards_sum
        eth_rewards.append(int(part * ether_balance))
        token_rewards.append(int(part * token_balance))
    return user_ids, eth_rewards, token_rewards


def set_consensus_rewards(w3, event_id):
    logger.info('[%s] Master node started setting rewards', event_id)
    user_ids, eth_rewards, token_rewards = database.Rewards.get_lists(event_id)
    contract_abi = common.verity_event_contract_abi()
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)

    chunks = common.lists_to_chunks(user_ids, eth_rewards, token_rewards)
    for i, (user_ids_chunk, eth_rewards_chunk, token_rewards_chunk) in enumerate(chunks, 1):
        logger.info('[%s] Setting rewards for %d of %d chunks', event_id, i, len(chunks))
        set_rewards_fun = contract_instance.functions.setRewards(user_ids_chunk, eth_rewards_chunk,
                                                                 token_rewards_chunk)
        common.function_transact(w3, set_rewards_fun)
    logger.info('[%s] Master node started setting consensus answer', event_id)
    consensus_answer = database.Vote.get_consensus_vote(event_id)
    answer_list = [
        answer[database.Vote.ANSWERS_VALUE_KEY] for answer in consensus_answer.ordered_answers()
    ]
    answer_list = list(map(lambda x: w3.toBytes(hexstr=w3.toHex(text=str(x))), answer_list))
    set_consensus_vote_fun = contract_instance.functions.setResults(answer_list)
    common.function_transact(w3, set_consensus_vote_fun)
    logger.info('[%s] Master node finished setting consensus answer', event_id)

    logger.info('[%s] Master node finished setting rewards', event_id)
    mark_rewards_set(w3, contract_instance, event_id, user_ids, eth_rewards, token_rewards)


def mark_rewards_set(w3, contract_instance, event_id, user_ids, eth_rewards, token_rewards):
    logger.info('[%s] Master node started marking rewards', event_id)
    rewards_hash = database.Rewards.hash(user_ids, eth_rewards, token_rewards)
    mark_rewards_set_fun = contract_instance.functions.markRewardsSet(rewards_hash)
    common.function_transact(w3, mark_rewards_set_fun)
    logger.info('[%s] Master node finished marking rewards', event_id)


def validate_rewards(w3, event_id, validation_round):
    logger.info('[%s] Validating rewards for round %d', event_id, validation_round)
    event_contract_abi = common.verity_event_contract_abi()
    event_contract = w3.eth.contract(address=event_id, abi=event_contract_abi)
    contract_reward_user_ids = event_contract.functions.getRewardsIndex().call()

    contract_reward_ether, contract_reward_token = [], []
    contract_reward_user_ids_chunks = common.list_to_chunks(contract_reward_user_ids)
    for i, contract_reward_user_ids_chunk in enumerate(contract_reward_user_ids_chunks, 1):
        logger.info('[%s] Requesting contract reward user ids for %d of %d chunks', event_id, i,
                    len(contract_reward_user_ids_chunks))
        (contract_reward_ether_chunk, contract_reward_token_chunk
         ) = event_contract.functions.getRewards(contract_reward_user_ids_chunk).call()
        contract_reward_ether.extend(contract_reward_ether_chunk)
        contract_reward_token.extend(contract_reward_token_chunk)

    contract_rewards_dict = database.Rewards.transform_lists_to_dict(
        contract_reward_user_ids, contract_reward_ether, contract_reward_token)
    node_rewards_dict = database.Rewards.get(event_id)

    event_consensus_vote = event_contract.functions.getResults().call()
    # TODO Find a better way of removing trailing 0 bytes
    event_consensus_vote = [x.decode('utf8').replace('\x00', '') for x in event_consensus_vote]
    consensus_vote = database.Vote.get_consensus_vote(event_id)
    consensus_vote = [
        answer[database.Vote.ANSWERS_VALUE_KEY] for answer in consensus_vote.ordered_answers()
    ]

    rewards_match = do_rewards_match(node_rewards_dict, contract_rewards_dict)
    consensus_match = event_consensus_vote == consensus_vote

    logger.info('[%s] Rewards DO%s match', event_id, '' if rewards_match else ' NOT')
    logger.info('[%s] Consensus votes DO%s match', event_id, '' if consensus_match else ' NOT')

    if rewards_match and consensus_match:
        logger.info('[%s] Approving rewards for round %d', event_id, validation_round)
        approve_fun = event_contract.functions.approveRewards(validation_round)
        common.function_transact(w3, approve_fun)
    else:
        logger.info('[%s] Rejecting rewards for round %d', event_id, validation_round)
        (user_ids, eth_rewards,
         token_rewards) = database.Rewards.transform_dict_to_lists(node_rewards_dict)
        alt_hash = database.Rewards.hash(user_ids, eth_rewards, token_rewards)
        reject_fun = event_contract.functions.rejectRewards(validation_round, alt_hash)
        common.function_transact(w3, reject_fun)


def do_rewards_match(node_rewards, contract_rewards):
    return node_rewards == contract_rewards
