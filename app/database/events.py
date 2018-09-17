import json
import logging
import os

from web3 import HTTPProvider, Web3

import common
from database import votes
from database.database import redis_db

logger = logging.getLogger('flask.app')
provider = os.getenv('ETH_RPC_PROVIDER')
w3 = Web3(HTTPProvider(provider))


class Event:
    IDS_KEY = 'event_ids'
    PREFIX = 'event'

    def __init__(self, event_id, owner, token_address, node_addresses, leftovers_recoverable_after,
                 application_start_time, application_end_time, event_start_time, event_end_time,
                 event_name, data_feed_hash, state, is_master_node, min_total_votes,
                 min_consensus_votes, min_consensus_ratio, min_participant_ratio, max_participants):
        self.event_id = event_id  # TODO Roman: make event_id immutable
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
        self.min_total_votes = min_total_votes
        self.min_consensus_votes = min_consensus_votes
        self.min_consensus_ratio = min_consensus_ratio
        self.min_participant_ratio = min_participant_ratio
        self.max_participants = max_participants

    @staticmethod
    def key(event_id):
        return '%s_%s' % (Event.PREFIX, event_id)

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_data):
        dict_data = json.loads(json_data)
        return cls(**dict_data)

    def votes(self):
        return votes.Vote.get_list(self.event_id)

    def is_consensus_reached(self):
        # TODO figure out how state behaves, for now it is always 4
        return self.state > 1

    @staticmethod
    def get(event_id):
        ''' Get event from the database'''
        event_json = redis_db.get(Event.key(event_id))
        if event_json:
            return Event.from_json(event_json)
        return None

    @staticmethod
    def instance(event_id):
        contract_abi = common.verity_event_contract_abi()
        return w3.eth.contract(address=event_id, abi=contract_abi)

    def update(self):
        ''' Update event in the database'''
        # TODO Roman: This should in transaction
        redis_db.set(self.key(self.event_id), self.to_json())

    def create(self):
        ''' Create event in the database and add event_id to event_ids list'''
        pipeline = redis_db.pipeline()
        pipeline.rpush(self.IDS_KEY, self.event_id)
        pipeline.set(self.key(self.event_id), self.to_json())
        pipeline.execute()

    def participants(self):
        return Participants.get_set(self.event_id)

    @staticmethod
    def get_ids_list():
        return redis_db.lrange(Event.IDS_KEY, 0, -1)


class Participants:
    PREFIX = 'join_event'

    @staticmethod
    def key(event_id):
        return '%s_%s' % (Participants.PREFIX, event_id)

    @staticmethod
    def create(event_id, user_ids):
        key = Participants.key(event_id)
        redis_db.sadd(key, *user_ids)

    @staticmethod
    def get_set(event_id):
        key = Participants.key(event_id)
        return redis_db.smembers(key)

    @staticmethod
    def exists(event_id, user_id):
        key = Participants.key(event_id)
        return redis_db.sismember(key, user_id)


class Filters:
    PREFIX = 'filters'

    @staticmethod
    def key(event_id):
        return '%s_%s' % (Filters.PREFIX, event_id)

    @staticmethod
    def create(event_id, filter_id):
        key = Filters.key(event_id)
        redis_db.rpush(key, filter_id)

    @staticmethod
    def get_list(event_id):
        key = Filters.key(event_id)
        return redis_db.lrange(key, 0, -1)
