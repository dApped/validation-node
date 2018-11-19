import logging

import scheduler
from database import database
from ethereum import rewards
from ethereum.provider import NODE_WEB3

logger = logging.getLogger('flask.app')


def should_calculate_consensus(event, vote_count):
    '''Heuristic which checks if there is a potential for consensus (assumes all votes are valid)'''
    event_id = event.event_id
    participant_ratio = (vote_count / len(event.participants())) * 100
    if vote_count < event.min_total_votes:
        logger.info('[%s] Should not calculate consensus: vote_count<min_total_votes: %d<%d',
                    event_id, vote_count, event.min_total_votes)
        return False
    if participant_ratio < event.min_participant_ratio:
        logger.info(
            '[%s] Should not calculate consensus: participant_ratio<min_participant_ratio: %d<%d',
            event_id, vote_count, event.min_total_votes)
        return False
    logger.info('[%s] Should calculate consensus', event_id)
    return True


def check_consensus(event, event_metadata):
    event_id = event.event_id
    votes_by_users = event.votes()
    vote_count = len(votes_by_users)

    if not should_calculate_consensus(event, vote_count):
        return
    consensus_votes_by_users = calculate_consensus(event, votes_by_users)
    if not consensus_votes_by_users:
        logger.info('[%s] Consensus not reached', event_id)
        return
    logger.info('[%s] Consensus reached', event_id)
    if event.metadata().is_consensus_reached:
        logger.info('[%s] Consensus already set', event_id)
        return
    event_metadata.is_consensus_reached = True
    event_metadata.update()

    ether_balance, token_balance = event.instance(NODE_WEB3, event_id).functions.getBalance().call()
    rewards.determine_rewards(event, consensus_votes_by_users, ether_balance, token_balance)
    if event.is_master_node:
        scheduler.scheduler.add_job(rewards.set_consensus_rewards, args=[NODE_WEB3, event_id])
    else:
        logger.info('[%s] Not a master node. Waiting for rewards to be set.', event_id)


def calculate_consensus(event, votes_by_users):
    vote_count = len(votes_by_users)
    if vote_count < event.min_total_votes:
        logger.info(
            '[%s] Not enough valid votes to calculate consensus. votes_by_users=%d, min_total_votes=%d',
            event.event_id, len(votes_by_users), event.min_total_votes)
        return dict()

    votes_by_repr = database.Vote.group_votes_by_representation(votes_by_users)
    vote_repr = max(votes_by_repr, key=lambda x: len(votes_by_repr[x]))
    consensus_user_ids = {vote.user_id for vote in votes_by_repr[vote_repr]}
    consensus_votes_by_users = {
        user_id: votes
        for user_id, votes in votes_by_users.items() if user_id in consensus_user_ids
    }

    consensus_votes_count = len(consensus_votes_by_users)
    consensus_ratio = consensus_votes_count / len(votes_by_users)
    if (consensus_votes_count < event.min_consensus_votes
            or consensus_ratio * 100 < event.min_consensus_ratio):
        logger.info(
            '[%s] Not enough consensus votes. votes_by_users=%d, min_total_votes=%d, consensus_ratio=%d, min_consensus_ratio=%d',
            event.event_id, len(votes_by_users), event.min_total_votes, consensus_ratio,
            event.min_consensus_ratio)
        return dict()
    return consensus_votes_by_users
