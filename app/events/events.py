import logging
import time

from websocket import QUEUE

import common
import scheduler
from database import database
from events import consensus

logger = logging.getLogger()


def _response(message, status):
    return {'message': message, 'status': status}


def vote(json_data):
    current_timestamp = int(time.time())
    if not common.is_vote_payload_valid(json_data):
        message = 'Invalid vote payload'
        logger.warning('%s: %s', message, json_data)
        return _response(message, 400)

    event_id, user_id, data, signature = common.parse_fields_from_json_data(json_data)
    event = database.VerityEvent.get(event_id)
    if not event:
        message = 'Event not found'
        logger.warning('[%s] %s', event_id, message)
        return _response(message, 404)

    event_metadata = event.metadata()
    if event_metadata.is_consensus_reached:
        message = 'Consensus already reached, no more voting'
        logger.info('[%s] %s', event_id, message)
        return _response(message, 403)

    is_voting_active = common.is_voting_active(current_timestamp, event.event_start_time,
                                               event.event_end_time)
    if not is_voting_active:
        message = '[%s] Voting is not active. Event Start Time %d, Event End Time: %d'
        message = message % (event.event_id, event.event_start_time, event.event_end_time)
        logger.info(message)
        return _response(message, 422)

    is_user_registered = common.is_user_registered(user_id, event.event_id)
    if not is_user_registered:
        message = '[%s] User %s is not registered' % (event.event_id, user_id)
        logger.info(message)
        return _response(message, 403)

    is_vote_signed_correctly, signer = common.is_vote_signed(json_data)
    if not is_vote_signed_correctly:
        message = 'Vote not signed correctly'
        logger.warning('[%s] %s from %s user. Message signed by %s', event_id, message, user_id,
                       signer)
        return _response(message, 400)

    node_id = common.node_id()
    if database.Vote.exists(event_id, node_id, user_id):
        message = 'Already received vote from %s user' % user_id
        logger.warning('[%s] %s', event_id, message)
        return _response(message, 406)

    vote = database.Vote(user_id, event_id, node_id, current_timestamp, data['answers'], signature)
    vote.create()
    logger.info('[%s] Accepted vote from %s user: %s', event_id, user_id, data['answers'])

    QUEUE.sync_q.put({
        'event_id': event_id,
        'node_id': node_id,
        'current_timestamp': current_timestamp,
        'json_data': json_data
    })
    if consensus.should_calculate_consensus(event):
        scheduler.scheduler.add_job(consensus.check_consensus, args=[event, event_metadata])
    return _response('Vote accepted', 200)
