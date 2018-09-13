import json
import logging

from database import votes
from database.database import redis_db

EVENTS_ADDRESSES_KEY = 'events_addreses'
EVENT_PREFIX = 'event'
JOIN_EVENT_PREFIX = 'join_event'

logger = logging.getLogger('flask.app')


class Event:
    def __init__(self, event_address, owner, token_address, node_addresses,
                 leftovers_recoverable_after, application_start_time, application_end_time,
                 event_start_time, event_end_time, event_name, data_feed_hash, state,
                 is_master_node, min_votes, min_consensus_votes, consensus_ratio, max_users):
        self.event_address = event_address
        self.owner = owner
        self.token_address = token_address
        self.node_addresses = node_addresses
        self.leftovers_recoverable_after = leftovers_recoverable_after
        self.application_start_time = application_start_time
        self.application_end_time = application_end_time
        self.event_start_time = event_start_time
        self.event_end_time = event_end_time
        self.event_name = event_name
        self.data_feed_hash = data_feed_hash
        self.state = state
        self.is_master_node = is_master_node
        self.min_votes = min_votes
        self.min_consensus_votes = min_consensus_votes
        self.consensus_ratio = consensus_ratio
        self.max_users = max_users

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_data):
        dict_data = json.loads(json_data)
        return cls(**dict_data)

    def get_votes(self):
        event_votes = redis_db.lrange(votes.compose_vote_key(self.event_address), 0, -1)
        return [votes.Vote.from_json(vote) for vote in event_votes]

    def is_consensus_reached(self):
        # TODO figure out how state behaves, for now it is always 4
        return self.state != 4

    def set(self):
        redis_db.set(compose_event_key(self.event_address), self.to_json())


# Events
def compose_event_key(event_address):
    return '%s_%s' % (EVENT_PREFIX, event_address)


def get_event(event_address):
    key = compose_event_key(event_address)
    event = redis_db.get(key)
    if event:
        return Event.from_json(event)
    return None


def get_all_events():
    addresses = event_addresses()
    events = [get_event(event_address) for event_address in addresses]
    return [event for event in events if event]


def store_events(events):
    # TODO Roman: Add transaction
    for event in events:
        key = compose_event_key(event.event_address)
        redis_db.set(key, event.to_json())
    redis_db.rpush(EVENTS_ADDRESSES_KEY, *[event.event_address for event in events])


def event_addresses():
    return redis_db.lrange(EVENTS_ADDRESSES_KEY, 0, -1)


# Participants
def compose_participants_key(event_address):
    return '%s_%s' % (JOIN_EVENT_PREFIX, event_address)


def store_participants(event_address, participants_list):
    key = compose_participants_key(event_address)
    redis_db.sadd(key, *participants_list)


def all_participants(event_address):
    key = compose_participants_key(event_address)
    # TODO this always returnes an empty set!!
    return redis_db.smembers(key)


def is_participant(event_address, address):
    key = compose_participants_key(event_address)
    return redis_db.sismember(key, address)
