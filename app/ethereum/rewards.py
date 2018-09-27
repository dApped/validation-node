import logging

import common
from database import database
from ethereum.provider import NODE_WEB3

logger = logging.getLogger('flask.app')


def determine_rewards(event_id, consensus_votes):
    event_instance = database.VerityEvent.instance(NODE_WEB3, event_id)
    [total_ether_balance, total_token_balance] = event_instance.functions.getBalance().call()

    in_consensus_votes_num = len(consensus_votes)

    user_ether_reward_in_wei = int(
        NODE_WEB3.toWei(total_ether_balance, 'ether') / in_consensus_votes_num)
    user_token_reward_in_wei = int(
        NODE_WEB3.toWei(total_token_balance, 'ether') / in_consensus_votes_num)

    rewards_dict = {
        vote.user_id: database.Rewards.reward_dict(
            eth_reward=user_ether_reward_in_wei, token_reward=user_token_reward_in_wei)
        for vote in consensus_votes
    }
    database.Rewards.create(event_id, rewards_dict)


def set_consensus_rewards(w3, event_id):
    logger.info('Started setting rewards for %s', event_id)
    user_ids, eth_rewards, token_rewards = database.Rewards.get_lists(event_id)
    contract_abi = common.verity_event_contract_abi()

    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    contract_instance.functions.setRewards(user_ids, eth_rewards, token_rewards).transact()
    logger.info('Finished setting rewards for %s', event_id)

    mark_rewards_set(contract_instance, event_id, user_ids, eth_rewards, token_rewards)


def mark_rewards_set(contract_instance, event_id, user_ids, eth_rewards, token_rewards):
    logger.info('Started marking rewards for %s', event_id)
    rewards_hash = database.Rewards.hash(user_ids, eth_rewards, token_rewards)
    contract_instance.functions.markRewardsSet(rewards_hash).transact()
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
        event_contract.functions.approveRewards(validation_round).transact()
    else:
        logger.info('Rewards DO NOT match for event %s. Rejecting rewards for round %d', event_id,
                    validation_round)
        alt_hash = database.Rewards.hash(
            database.Rewards.transform_dict_to_lists(node_rewards_dict))
        event_contract.functions.rejectRewards(validation_round, alt_hash).transact()


def do_rewards_match(node_rewards, contract_rewards):
    return node_rewards == contract_rewards
