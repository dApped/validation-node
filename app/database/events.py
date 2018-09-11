import json

from database.database import redis_db

EVENTS_KEY = 'events'


class Event:
    def __init__(self, event_address, owner, token_address, node_addresses,
                 leftovers_recoverable_after, application_start_time, application_end_time,
                 event_start_time, event_end_time, event_name, data_feed_hash):
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

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_data):
        dict_data = json.loads(json_data)
        return cls(**dict_data)


def store_events(events):
    for event in events:
        event_json = event.to_json()
        redis_db.rpush(EVENTS_KEY, event_json)


def all_events():
    events = []
    for i in range(redis_db.llen(EVENTS_KEY)):
        event_json = redis_db.lindex(EVENTS_KEY, i)
        event = Event.from_json(event_json)
        events.append(event)
    return events
