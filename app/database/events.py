import json
import logging

from database.database import redis_db

EVENTS_KEY = 'events'
JOIN_EVENT_KEY = 'join_event'

logger = logging.getLogger('app.sub')


class Event:
    def __init__(self, event_address, owner, token_address, node_addresses,
                 leftovers_recoverable_after, application_start_time, application_end_time,
                 event_start_time, event_end_time, event_name, data_feed_hash, state):
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

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_data):
        dict_data = json.loads(json_data)
        return cls(**dict_data)


def get_event(event_address):
    events = all_events()
    for event in events:
        if event.event_address == event_address:
            return event
    return None


def store_events(events):
    redis_db.rpush(EVENTS_KEY, *[event.to_json() for event in events])


def all_events():
    events_json = redis_db.lrange(EVENTS_KEY, 0, -1)
    return [Event.from_json(event) for event in events_json]


def compose_participants_key(event_address):
    return '%s_%s' % (event_address, JOIN_EVENT_KEY)


def store_participants(event_address, participants_list):
    key = compose_participants_key(event_address)
    redis_db.sadd(key, *participants_list)


def all_participants(event_address):
    key = compose_participants_key(event_address)
    return redis_db.smembers(key)
