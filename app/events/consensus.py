import logging
import time

import requests

import common
import scheduler
from database import database
from ethereum import provider, rewards
from key_store import node_key_store

logger = logging.getLogger()


def should_calculate_consensus(event):
    '''Heuristic which checks if there is a potential for consensus (assumes all votes are valid)'''
    event_id = event.event_id
    vote_count = database.Vote.count(event_id)
    n_participants = len(event.participants())
    if n_participants == 0:
        logger.info('[%s] Should not calculate consensus: %d participants', event_id,
                    n_participants)
        return False
    participant_ratio = (vote_count / n_participants) * 100
    if vote_count < event.min_total_votes:
        logger.info('[%s] Should not calculate consensus: %d vote_count < %d min_total_votes',
                    event_id, vote_count, event.min_total_votes)
        return False
    if participant_ratio < event.min_participant_ratio:
        logger.info(
            '[%s] Should not calculate consensus: %.4f participant_ratio < %.4f min_participant_ratio',
            event_id, participant_ratio, event.min_participant_ratio)
        return False
    logger.info('[%s] Should try to calculate consensus', event_id)
    return True


def check_consensus(event, event_metadata):
    event_id = event.event_id
    votes_by_users = event.votes_consensus()

    if not should_calculate_consensus(event):
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

    remove_consensus_not_reached_job(event_id)

    n_seconds_wait = 5
    logger.info('[%s] Waiting %d seconds for websockets to exchange votes', event_id,
                n_seconds_wait)
    time.sleep(n_seconds_wait)
    schedule_event_data_to_blockchain_job(event, consensus_votes_by_users)


def schedule_event_data_to_blockchain_job(event, consensus_votes_by_users):
    event_id = event.event_id

    event_metadata = event.metadata()
    event_metadata.processing_end_time = int(time.time())
    event_metadata.update()

    w3 = provider.EthProvider(node_key_store).web3_provider()
    # developer might initialize event and set rewards later. We fetch them just in time
    ether_balance, token_balance = event.instance(w3, event_id).functions.getBalance().call()
    logger.info('[%s] Contract balance: %d WEI, %d VTY', event_id, ether_balance, token_balance)

    if not consensus_votes_by_users:
        user_ids_rewards, rewards_dict = rewards.calculate_non_consensus_rewards(event)
    else:
        user_ids_rewards, rewards_dict = rewards.calculate_consensus_rewards(
            event, consensus_votes_by_users, ether_balance, token_balance)
    database.Rewards.create(event_id, user_ids_rewards, rewards_dict)
    send_data_to_explorer(event_id)
    if event.is_master_node:
        scheduler.scheduler.add_job(rewards.event_data_to_blockchain, args=[w3, event_id])
    else:
        logger.info('[%s] Not a master node. Waiting for event data to be set.', event_id)


def calculate_consensus(event, votes_by_users):
    event_id = event.event_id
    vote_count = len(votes_by_users)
    if vote_count < event.min_total_votes:
        logger.info(
            '[%s] Not enough valid votes to calculate consensus: %d vote_count < %d event.min_total_votes',
            event_id, vote_count, event.min_total_votes)
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
    if consensus_votes_count < event.min_consensus_votes:
        logger.info(
            '[%s] Not enough consensus votes: %d consensus_votes_count < %d event.min_consensus_votes',
            event_id, consensus_votes_count, event.min_consensus_votes)
        return dict()
    if consensus_ratio * 100 < event.min_consensus_ratio:
        logger.info(
            '[%s] Not enough consensus votes: %d consensus_ratio < %d event.min_consensus_ratio',
            event_id, consensus_ratio * 100, event.min_consensus_ratio)
        return dict()
    consensus_vote = votes_by_users[next(iter(consensus_user_ids))][0]
    consensus_vote.set_consensus_vote()
    return consensus_votes_by_users


def remove_consensus_not_reached_job(event_id):
    logger.info('[%s] Removing consensus_not_reached_job', event_id)
    consensus_not_reached_job_id = database.VerityEvent.consensus_not_reached_job_id(event_id)
    scheduler.remove_job(consensus_not_reached_job_id)


def process_consensus_not_reached(event_id):
    logger.info('[%s] Running process_consensus_not_reached_job', event_id)
    event = database.VerityEvent.get(event_id)
    if event is None:
        logger.info('[%s] Event does not exists', event_id)
        return
    event_metadata = event.metadata()
    if event_metadata.is_consensus_reached:
        logger.info('[%s] Consensus already reached', event_id)
        return
    schedule_event_data_to_blockchain_job(event, {})


def send_data_to_explorer(event_id, max_retries=2):
    logger.info('[%s] Sending event data to explorer', event_id)
    event = database.VerityEvent.get(event_id)
    payload = compose_event_payload(event)
    target = "%s/event_data" % common.explorer_ip_port()

    for retry in range(1, max_retries + 1):
        try:
            response = requests.post(target, json=payload)
            if response.status_code == 200:
                logger.info('[%s] Event data successfully sent to explorer', event_id)
                return
            logger.info('Cannot send data to explorer. Status %d, %d/%d retry',
                        response.status_code, retry, max_retries)
        except requests.exceptions.ConnectionError as e:
            logger.info('[%s] Cannot reach explorer %d/%d retry: %s', event_id, retry, max_retries,
                        e)
        except Exception:
            logger.exception('Cannot send data to explorer')
        time.sleep(60)


def compose_event_payload(event):
    event_id = event.event_id
    event_metadata = event.metadata()

    correct_vote_user_ids = event.consensus_vote_user_ids()
    incorrect_vote_user_ids = list(
        database.Vote.user_ids_with_incorrect_vote(event_id, correct_vote_user_ids))
    user_ids_without_vote = list(event.user_ids_without_vote())

    payload = {
        'data': {
            'event_id': event_id,
            'node_id': common.node_id(),
            'processing_end_time': event_metadata.processing_end_time,
            'voting_round': event.dispute_round,
            'votes_by_users': event.votes_for_explorer(),
            'rewards_dict': database.Rewards.get(event_id),
            'vote_position_user_ids': database.Rewards.get_rewards_user_ids(event_id),
            # can differ from rewards_dict because there can be a single correct vote for a
            # user and consensus required two votes
            'correct_vote_user_ids': correct_vote_user_ids,
            'incorrect_vote_user_ids': incorrect_vote_user_ids,
            'without_vote_user_ids': user_ids_without_vote,
        }
    }
    payload['signature'] = common.sign_data(payload)
    return payload
