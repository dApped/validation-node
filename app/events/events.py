import logging
import time

from websocket import QUEUE

import common
import scheduler
from database import database
from events import consensus

logger = logging.getLogger('flask.app')


def _is_vote_valid(timestamp, user_id, event):
    if timestamp < event.event_start_time or timestamp > event.event_end_time:
        message = '[%s] Voting is not active. Event Start Time %d, Event End Time: %d'
        message = message % (event.event_id, event.event_start_time, event.event_end_time)
        logger.info(message)
        return False, message

    user_registered = database.Participants.exists(event.event_id, user_id)
    if not user_registered:
        message = '[%s] User %s is not registered' % (event.event_id, user_id)
        logger.info(message)
        return False, message
    return True, ''


def _is_vote_payload_valid(data):
    if 'data' not in data:
        return False
    for param in {'user_id', 'event_id', 'answers'}:
        if param not in data['data']:
            return False
    return True


def _response(message, status):
    return {'message': message, 'status': status}


def vote(json_data):
    current_timestamp = int(time.time())
    if not _is_vote_payload_valid(json_data):
        message = 'Invalid vote payload'
        logger.info(message)
        return _response(message, 400)

    data = json_data['data']
    event_id = data['event_id']
    user_id = data['user_id']
    event = database.VerityEvent.get(event_id)
    if not event:
        message = '[%s] Event not found' % event_id
        logger.info(message)
        return _response(message, 400)

    event_metadata = event.metadata()
    if event_metadata.is_consensus_reached:
        message = '[%s] Consensus already reached, no more voting' % event_id
        logger.info(message)
        return _response(message, 200)

    valid_vote, message = _is_vote_valid(current_timestamp, user_id, event)
    if not valid_vote:
        return _response(message, 400)

    node_id = common.node_id()
    vote = database.Vote(user_id, event_id, node_id, current_timestamp, data['answers'])
    vote.create()
    logger.info('[%s] Received vote %s from user: %s', event_id, user_id, data['answers'])

    QUEUE.sync_q.put({'node_ips': event_metadata.node_ips, 'vote': vote})

    vote_count = database.Vote.count(event.event_id)
    if consensus.should_calculate_consensus(event, vote_count):
        scheduler.scheduler.add_job(consensus.check_consensus, args=[event, event_metadata])
    return _response('Vote accepted', 200)
