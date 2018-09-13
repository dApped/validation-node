import json

from database.database import redis_db

VOTES_PREFIX = 'votes'

class Vote:
    def __init__(self, user_id, event_id, timestamp, answers):
        self.user_id = user_id
        self.event_id = event_id
        self.timestamp = timestamp
        self.answers = answers

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_data):
        dict_data = json.loads(json_data)
        return cls(**dict_data)

    def push(self):
        redis_db.rpush(compose_vote_key(self.event_id), self.to_json())
        return self

def compose_vote_key(event_id):
    return '%s_%s' % (VOTES_PREFIX, event_id)
