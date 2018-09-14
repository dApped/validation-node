import json
from collections import OrderedDict

from database.database import redis_db


class Vote:
    PREFIX = 'votes'
    ANSWERS_SORT_KEY = 'field_name'

    def __init__(self, user_id, event_id, timestamp, answers, _ordered_answers=None):
        self.user_id = user_id
        self.event_id = event_id
        self.timestamp = timestamp
        self.answers = answers
        self._ordered_answers = _ordered_answers

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

    def ordered_answers(self):
        if self._ordered_answers is not None:
            return self._ordered_answers
        # Order each dictionary and sort dictionaries by a key
        self._ordered_answers = sorted([OrderedDict(sorted(answer.items(), key=lambda t: t[0]))
                       for answer in self.answers], key=lambda x: x[self.ANSWERS_SORT_KEY])
        return self._ordered_answers

    @staticmethod
    def get_list(event_id):
        key = Vote.key(event_id)
        event_votes = redis_db.lrange(key, 0, -1)
        return [Vote.from_json(vote) for vote in event_votes]
