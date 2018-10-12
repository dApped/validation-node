import logging
import os
import time

from websocket import QUEUE

import scheduler
from database import database
from events import consensus

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
    if consensus.should_calculate_consensus(event, vote_count):
        scheduler.scheduler.add_job(consensus.check_consensus, args=[event, event_metadata])
    return success_response
