import json

from database.database import redis_db


class Vote:
    PREFIX = 'votes'

    def __init__(self, user_id, event_id, timestamp, answers):
        self.user_id = user_id
        self.event_id = event_id
        self.timestamp = timestamp
        self.answers = answers

    @staticmethod
    def key(event_id):
        return '%s_%s' % (Vote.PREFIX, event_id)

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_data):
        dict_data = json.loads(json_data)
        return cls(**dict_data)

    def create(self):
        redis_db.rpush(self.key(self.event_id), self.to_json())
        return self

    @staticmethod
    def get_list(event_id):
        key = Vote.key(event_id)
        event_votes = redis_db.lrange(key, 0, -1)
        return [Vote.from_json(vote) for vote in event_votes]
