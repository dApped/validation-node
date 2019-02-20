import logging
from enum import Enum
from statistics import mean, median

import common
from database import database

logger = logging.getLogger()


class VoteTimestampsMetric(Enum):
    MEAN = 1
    MEDIAN = 2


def should_return_dispute_stake(event_id, disputer_id, disputer_votes_in_consensus,
                                user_ids_without_vote, consensus_answers,
                                previous_consensus_answers):
    if disputer_id == common.default_eth_address():
        logger.info('[%s] No disputer', event_id)
        return False
    if disputer_votes_in_consensus is None and disputer_id not in user_ids_without_vote:
        logger.info('[%s] Disputer %s vote was not in consensus', event_id, disputer_id)
        return False
    if previous_consensus_answers != consensus_answers:
        logger.info('[%s] Current consensus is different from previous consensus', event_id)
        return True
    logger.info('[%s] Current consensus is the same as previous consensus', event_id)
    return False


def user_ids_to_return_join_stakes(event_id, staking_amount, user_ids_consensus,
                                   user_ids_without_vote, return_dispute_stake, disputer_id):
    user_ids = []
    if staking_amount == 0:
        return user_ids

    logger.info('[%s] %d users with at least one correct vote', event_id, len(user_ids_consensus))
    user_ids.extend(user_ids_consensus)

    logger.info('[%s] %d users without a vote', event_id, len(user_ids_without_vote))
    user_ids.extend(user_ids_without_vote)

    if not return_dispute_stake and disputer_id in user_ids:
        logger.info('[%s] Removing %s disputer from join stakes', event_id, disputer_id)
        user_ids.remove(disputer_id)
    return user_ids


def calculate_consensus_rewards(event, consensus_votes_by_users, ether_balance, token_balance):
    """ Calculate join stakes, dispute stakes and rewards when consenus was reached

    Return:
        user_ids ordered by voting time (size of reward),
        dictionary with user_ids as keys and rewards as values.
    """
    event_id = event.event_id
    logger.info('[%s] Calculating consensus rewards', event_id)
    logger.info('[%s] %d users in consensus', event_id, len(consensus_votes_by_users))

    user_ids_without_vote = event.user_ids_without_vote()
    consensus_vote = list(consensus_votes_by_users.values())[0][0]
    consensus_answers = database.Vote.answers_from_vote(consensus_vote)

    # users filtered by correct vote. If a single vote from disputer comes
    # through (instead of required 2 votes) and it is correct then we return him dispute stake
    votes_by_users_filtered = event.votes(min_votes=1, filter_by_vote=consensus_vote)
    user_ids_consensus = list(votes_by_users_filtered.keys())

    # handle dispute
    return_dispute_stake = should_return_dispute_stake(event_id, event.disputer,
                                                       votes_by_users_filtered.get(event.disputer),
                                                       user_ids_without_vote, consensus_answers,
                                                       event.metadata().previous_consensus_answers)
    if return_dispute_stake:
        # disputer voted differently then first consensus and was part of new consensus.
        # we need to return the dispute stake to disputer
        token_balance -= event.dispute_amount
    elif event.disputer in consensus_votes_by_users:
        # disputer voted the same as previous consensus. Don't return dispute stake
        logger.info('[%s] Removing %s disputer from rewards', event_id, event.disputer)
        consensus_votes_by_users.pop(event.disputer)

    # handle join stakes

    user_ids_to_return_staking_amount = user_ids_to_return_join_stakes(
        event_id, event.staking_amount, user_ids_consensus, user_ids_without_vote,
        return_dispute_stake, event.disputer)

    if user_ids_to_return_staking_amount:
        n_users_to_return = len(user_ids_to_return_staking_amount)
        staking_amount_to_return = event.staking_amount * n_users_to_return
        token_balance -= staking_amount_to_return
        logger.info('[%s] %d users to return %d VTY join stake', event_id, n_users_to_return,
                    staking_amount_to_return)

    # handle rewards
    if event.rewards_distribution_function == 0:
        logger.info('[%s] Calculating rewards using linear function', event_id)
        user_ids_rewards, eth_rewards, token_rewards = calculate_linear_rewards(
            ether_balance, token_balance, consensus_votes_by_users)
    elif event.rewards_distribution_function == 1:
        logger.info('[%s] Calculating rewards using exponential function', event_id)
        user_ids_rewards, eth_rewards, token_rewards = calculate_exponential_rewards(
            ether_balance, token_balance, consensus_votes_by_users)
    else:
        logger.error('[%s] Rewards function %d not supported', event_id,
                     event.rewards_distribution_function)
        return

    # compose rewards
    rewards_dict = {
        user_id: database.Rewards.reward_dict(
            eth_reward=eth_rewards[i], token_reward=token_rewards[i])
        for i, user_id in enumerate(user_ids_rewards)
    }
    if not rewards_dict:
        logger.error('[%s] Did not set the rewards because user_ids were empty', event_id)

    if return_dispute_stake:
        logger.info('[%s] Adding dispute staking amount to %s disputer', event_id, event.disputer)
        if event.disputer not in rewards_dict:
            rewards_dict[event.disputer] = database.Rewards.reward_dict()
        rewards_dict[event.disputer][database.Rewards.TOKEN_KEY] += event.dispute_amount

    logger.info('[%s] Returing staking amount to users in consensus or without a vote', event_id)
    for user_id in user_ids_to_return_staking_amount:
        if user_id not in rewards_dict:
            rewards_dict[user_id] = database.Rewards.reward_dict()
        rewards_dict[user_id][database.Rewards.TOKEN_KEY] += event.staking_amount
    return user_ids_rewards, rewards_dict


def calculate_non_consensus_rewards(event):
    """ Return join stakes and dispute stakes becasue consenus was not reached

    Return:
        user_ids ordered by voting time (size of reward),
        dictionary with user_ids as keys and rewards as values.
    """
    event_id = event.event_id
    logger.info('[%s] Calculating non consensus rewards', event_id)
    user_ids = event.participants()

    staking_amount = event.staking_amount
    rewards_dict = {
        user_id: database.Rewards.reward_dict(token_reward=staking_amount)
        for i, user_id in enumerate(user_ids)
    }
    if event.disputer != common.default_eth_address():
        rewards_dict[event.disputer][database.Rewards.TOKEN_KEY] += event.dispute_amount
    return [], rewards_dict


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


def event_data_to_blockchain(w3, event_id):
    user_ids, eth_rewards, token_rewards = database.Rewards.get_lists(event_id)

    contract_abi = common.verity_event_contract_abi()
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)

    set_rewards_on_blockchain(w3, contract_instance, event_id, user_ids, eth_rewards, token_rewards)
    set_result_on_blockchain(w3, contract_instance, event_id)
    mark_rewards_on_blockchain(w3, contract_instance, event_id, user_ids, eth_rewards,
                               token_rewards)


def set_rewards_on_blockchain(w3, contract_instance, event_id, user_ids, eth_rewards,
                              token_rewards):
    logger.info('[%s] Master node started setting rewards', event_id)

    chunks = common.lists_to_chunks(user_ids, eth_rewards, token_rewards)
    for i, (user_ids_chunk, eth_rewards_chunk, token_rewards_chunk) in enumerate(chunks, 1):
        logger.info('[%s] Setting rewards for %d of %d chunks', event_id, i, len(chunks))
        set_rewards_fun = contract_instance.functions.setRewards(user_ids_chunk, eth_rewards_chunk,
                                                                 token_rewards_chunk)
        common.function_transact(w3, set_rewards_fun)
    logger.info('[%s] Master node finished setting rewards', event_id)


def set_result_on_blockchain(w3, contract_instance, event_id):
    logger.info('[%s] Master node started setting result', event_id)
    consensus_answers = database.Vote.get_consensus_answers(event_id)
    if consensus_answers:
        consensus_answers = list(
            map(lambda x: w3.toBytes(hexstr=w3.toHex(text=str(x))), consensus_answers))
    set_consensus_vote_fun = contract_instance.functions.setResults(consensus_answers)
    common.function_transact(w3, set_consensus_vote_fun)
    logger.info('[%s] Master node finished setting result', event_id)


def mark_rewards_on_blockchain(w3, contract_instance, event_id, user_ids, eth_rewards,
                               token_rewards):
    logger.info('[%s] Master node started marking rewards', event_id)
    rewards_hash = database.Rewards.hash(user_ids, eth_rewards, token_rewards)
    mark_rewards_set_fun = contract_instance.functions.markRewardsSet(rewards_hash)
    common.function_transact(w3, mark_rewards_set_fun)
    logger.info('[%s] Master node finished marking rewards', event_id)


def validate_event_data_on_blockchain(w3, event_id, validation_round):
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

    event_consensus_answer = common.consensus_answers_from_contract(event_contract)
    consensus_answer = database.Vote.get_consensus_answers(event_id)

    rewards_match = do_rewards_match(node_rewards_dict, contract_rewards_dict)
    consensus_match = event_consensus_answer == consensus_answer

    logger.info('[%s] Rewards DO%s match', event_id, '' if rewards_match else ' NOT')
    logger.info('[%s] Consensus answers DO%s match. Contract: %s, node: %s', event_id,
                '' if consensus_match else ' NOT', event_consensus_answer, consensus_answer)

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
