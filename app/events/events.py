import logging
import os
import time

from websocket import QUEUE

import scheduler
from database import database
from ethereum import rewards
from ethereum.provider import NODE_WEB3

logger = logging.getLogger('flask.app')

# TODO: Maybe move this to some common later?
success_response = {'status': 200}
user_error_response = {'status': 400}
node_error_response = {'status': 500}


def _is_vote_valid(timestamp, user_id, event):
    # TODO check request data format, maybe use schema validator
    if timestamp < event.event_start_time or timestamp > event.event_end_time:
        logger.info('Voting is not active %s', event.event_id)
        logger.info('Event Start Time %d, Event End Time: %d, Current: %d', event.event_start_time,
                    event.event_end_time, timestamp)
        return False, user_error_response

    # 2. Check user has registered for event
    user_registered = database.Participants.exists(event.event_id, user_id)
    if not user_registered:
        logger.info('User %s is not registered %s', user_id, event.event_id)
        return False, user_error_response
    return True, success_response


def is_vote_payload_valid(data):
    if 'data' not in data:
        return False
    for param in {'user_id', 'event_id', 'answers'}:
        if param not in data['data']:
            return False
    return True


def vote(json_data, ip_address):
    current_timestamp = int(time.time())
    if not is_vote_payload_valid(json_data):
        return user_error_response

    data = json_data['data']
    event_id = data['event_id']
    user_id = data['user_id']
    event = database.VerityEvent.get(event_id)
    if not event:
        logger.info('Event %s not found', event_id)
        return user_error_response

    event_metadata = event.metadata()
    if event_metadata.is_consensus_reached:
        logger.info('Consensus already reached, no more voting')
        return user_error_response
    valid_vote, response = _is_vote_valid(current_timestamp, user_id, event)
    if not valid_vote:
        return response

    logger.info('Valid vote')
    node_id = os.getenv('NODE_ADDRESS')
    vote = database.Vote(user_id, event_id, node_id, current_timestamp, data['answers'])
    vote.create()

    QUEUE.sync_q.put({'node_ips': event_metadata.node_ips, 'vote': vote})
    # QUEUE.sync_q.join() # TODO check if we need to block

    vote_count = database.Vote.count(event.event_id)
    if should_calculate_consensus(event, vote_count):
        scheduler.scheduler.add_job(check_consensus, args=[event, event_metadata])
    return success_response


def should_calculate_consensus(event, vote_count):
    '''Heuristic which checks if there is a potential for consensus (assumes all votes are valid)'''
    participant_ratio = (vote_count / len(event.participants())) * 100
    return vote_count >= event.min_total_votes and participant_ratio >= event.min_participant_ratio




def check_consensus(event, event_metadata):
    event_id = event.event_id
    votes_by_users = event.votes()
    vote_count = len(votes_by_users)

    if not should_calculate_consensus(event, vote_count):
        logger.info('Should not calculate consensus for %s event', event_id)
        return
    consensus_votes_by_users = calculate_consensus(event, votes_by_users)
    if not consensus_votes_by_users:
        logger.info('Consensus not reached for %s event', event_id)
        return
    logger.info('Consensus reached for %s event', event_id)
    event_metadata.is_consensus_reached = True
    event_metadata.update()

    ether_balance, token_balance = event.instance(NODE_WEB3,
                                                  event_id).functions.getBalance().call()
    rewards.determine_rewards(event_id, consensus_votes_by_users, ether_balance, token_balance)
    if event.is_master_node:
        scheduler.scheduler.add_job(rewards.set_consensus_rewards, args=[NODE_WEB3, event_id])
    else:
        logger.info('Not a master node for %s event. Waiting for rewards to be set.', event_id)


def calculate_consensus(event, votes_by_users):
    vote_count = len(votes_by_users)
    if vote_count < event.min_total_votes:
        logger.info(
            'Not enough valid votes to calculate consensus for %s event. votes_by_users=%d, min_total_votes=%d',
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
            'Not enough consensus votes for %s event. votes_by_users=%d, min_total_votes=%d, consensus_ratio=%d, min_consensus_ratio=%d',
            event.event_id, len(votes_by_users), event.min_total_votes, consensus_ratio,
            event.min_consensus_ratio)
        return dict()
    return consensus_votes_by_users
