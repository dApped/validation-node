import json
import logging
import os
import time
from collections import defaultdict

import requests

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

    scheduler.scheduler.add_job(send_vote, args=[event_id, node_id, vote])
    if should_calculate_consensus(event, event_metadata):
        scheduler.scheduler.add_job(check_consensus, args=[event, event_metadata])
    return success_response


def should_calculate_consensus(event, event_metadata):
    vote_count = database.Vote.count(event.event_id)
    participant_ratio = (vote_count / len(event.participants())) * 100
    if vote_count >= event.min_total_votes and participant_ratio >= event.min_participant_ratio:
        return True
    return False


def send_vote(event_id, node_id, vote):
    # TODO replace this with websocket
    event = database.VerityEvent.get(event_id)
    metadata = event.metadata()

    user_id = vote.user_id
    vote_json = vote.to_json()
    json_payload = {'vote': vote_json}

    for node_ip in metadata.node_ips:
        # TODO don't send votes to yourself
        logger.info('Sending vote from %s user to %s node for %s event', user_id, node_ip, event_id)
        url = 'http://%s:%d/%s' % (node_ip, 5000, 'receive_vote')
        # TODO watch for timeouts
        requests.post(url, json=json_payload)


def receive_vote(vote_json):
    # TODO replace this with websocket
    try:
        vote = database.Vote.from_json(vote_json)
    except Exception as e:
        logger.exception(e)
        return 'Vote has improper formatting'

    event = database.VerityEvent.get(vote.event_id)
    if event is None:
        return user_error_response

    event_metadata = event.metadata()
    if event_metadata.is_consensus_reached:
        logger.info('Consensus already reached, no more voting')
        return user_error_response

    vote.create()
    logger.info('Stored vote from %s user for %s event from %s node', vote.user_id, vote.event_id,
                vote.node_id)
    if should_calculate_consensus(event, event_metadata):
        scheduler.scheduler.add_job(check_consensus, args=[event, event_metadata])
    return success_response


def check_consensus(event, event_metadata):
    event_id = event.event_id
    consensus_reached, consensus_votes = calculate_consensus(event)
    if consensus_reached:
        logger.info('Consensus reached for %s event', event_id)
        event_metadata.is_consensus_reached = consensus_reached
        event_metadata.update()

        rewards.determine_rewards(event_id, consensus_votes)
        if event.is_master_node:
            scheduler.scheduler.add_job(rewards.set_consensus_rewards, args=[NODE_WEB3, event_id])
        else:
            logger.info('Not master node..waiting for rewards to be set')


def calculate_consensus(event):
    votes = list(event.votes().values())[0]  # TODO we need to combine votes from all nodes
    answers_combinations = defaultdict(list)
    for vote in votes:
        vote_answers = vote.ordered_answers().__repr__()
        # store in vote for when adding to consensus_votes
        answers_combinations[vote_answers].append(vote)

    consensus_candidate = max(answers_combinations, key=lambda x: len(answers_combinations[x]))
    cons_vote_count = len(answers_combinations[consensus_candidate])
    consensus_ratio = cons_vote_count / len(votes)
    if (cons_vote_count < event.min_consensus_votes
            or consensus_ratio * 100 < event.min_consensus_ratio):
        logger.info('Not enough consensus votes!')
        return False, []

    consensus_votes = sorted(answers_combinations[consensus_candidate], key=lambda v: v.timestamp)
    return True, consensus_votes
