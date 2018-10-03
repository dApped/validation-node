import hashlib
import json
import logging
import os
from collections import OrderedDict

import redis

import common

logger = logging.getLogger('flask.app')

redis_db = redis.StrictRedis(
    host=os.getenv('REDIS_URL', '127.0.0.1'), port=6379, db=0, decode_responses=True)


def flush_database():
    logger.info('Flushing database')
    redis_db.flushdb()


logger = logging.getLogger('flask.app')


class BaseEvent:
    @classmethod
    def key(cls, event_id):
        return '%s_%s' % (cls.PREFIX, event_id)

    @classmethod
    def get(cls, event_id):
        key = cls.key(event_id)
        event_json = redis_db.get(key)
        if event_json is None:
            return None
        return cls.from_json(event_json)

    @classmethod
    def delete(cls, pipeline, event_id):
        key = cls.key(event_id)
        pipeline.delete(key)

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_data):
        dict_data = json.loads(json_data)
        return cls(**dict_data)


class VerityEvent(BaseEvent):
    IDS_KEY = 'event_ids'
    PREFIX = 'event'

    def __init__(self, event_id, owner, token_address, node_addresses, leftovers_recoverable_after,
                 application_start_time, application_end_time, event_start_time, event_end_time,
                 event_name, data_feed_hash, state, is_master_node, min_total_votes,
                 min_consensus_votes, min_consensus_ratio, min_participant_ratio, max_participants,
                 rewards_distribution_function, rewards_validation_round):
        self.event_id = event_id
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
        self.rewards_distribution_function = rewards_distribution_function
        self.rewards_validation_round = rewards_validation_round

    def votes(self):
        return {node_id: self.votes_from_node_id(node_id) for node_id in self.node_addresses}

    def votes_from_node_id(self, node_id):
        return Vote.get_list(self.event_id, node_id)

    def votes_json(self, node_id):
        return Vote.get_list_json(self.event_id, node_id)

    @staticmethod
    def instance(w3, event_id):
        contract_abi = common.verity_event_contract_abi()
        return w3.eth.contract(address=event_id, abi=contract_abi)

    def update(self):
        ''' Update event in the database'''
        redis_db.set(self.key(self.event_id), self.to_json())

    def create(self):
        ''' Create event in the database and add event_id to event_ids list'''
        pipeline = redis_db.pipeline()
        pipeline.rpush(self.IDS_KEY, self.event_id)
        pipeline.set(self.key(self.event_id), self.to_json())
        pipeline.execute()

    def participants(self):
        return Participants.get_set(self.event_id)

    def metadata(self):
        return VerityEventMetadata.get_or_create(self.event_id)

    @staticmethod
    def get_ids_list():
        return redis_db.lrange(VerityEvent.IDS_KEY, 0, -1)

    @classmethod
    def delete_all_event_data(cls, w3, event_id):
        filter_ids = Filters.get_list(event_id)

        pipeline = redis_db.pipeline()
        pipeline.lrem(cls.IDS_KEY, 1, event_id)
        VerityEvent.delete(pipeline, event_id)
        VerityEventMetadata.delete(pipeline, event_id)
        Participants.delete(pipeline, event_id)
        Filters.delete(pipeline, event_id)
        Rewards.delete(pipeline, event_id)
        pipeline.execute()

        Filters.uninstall(w3, filter_ids)


class VerityEventMetadata(BaseEvent):
    PREFIX = 'metadata'

    def __init__(self, event_id, is_consensus_reached, node_ips):
        self.event_id = event_id
        self.is_consensus_reached = is_consensus_reached
        self.node_ips = node_ips

    def create(self):
        redis_db.set(self.key(self.event_id), self.to_json())

    @staticmethod
    def get_or_create(event_id):
        event_metadata = VerityEventMetadata.get(event_id)
        if event_metadata is None:
            event_metadata = VerityEventMetadata(
                event_id=event_id, is_consensus_reached=False, node_ips=[])
            event_metadata.create()
        return event_metadata

    def update(self):
        self.create()


class Participants(BaseEvent):
    PREFIX = 'join_event'

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


class Filters(BaseEvent):
    PREFIX = 'filters'

    @staticmethod
    def create(event_id, filter_id):
        key = Filters.key(event_id)
        redis_db.rpush(key, filter_id)

    @staticmethod
    def get_list(event_id):
        key = Filters.key(event_id)
        return redis_db.lrange(key, 0, -1)

    @classmethod
    def uninstall(cls, w3, filter_ids):
        for filter_id in filter_ids:
            w3.eth.uninstallFilter(filter_id)


class Rewards(BaseEvent):
    PREFIX = 'rewards'
    ETH_KEY = 'eth'
    TOKEN_KEY = 'token'

    @staticmethod
    def create(event_id, rewards_dict):
        key = Rewards.key(event_id)
        rewards_json = json.dumps(rewards_dict)
        redis_db.set(key, rewards_json)

    @staticmethod
    def reward_dict(eth_reward=0, token_reward=0):
        return {Rewards.ETH_KEY: eth_reward, Rewards.TOKEN_KEY: token_reward}

    @staticmethod
    def transform_dict_to_lists(rewards):
        user_ids = list(rewards.keys())
        eth_rewards, token_rewards = [], []
        for user_id in user_ids:
            eth_rewards.append(rewards[user_id][Rewards.ETH_KEY])
            token_rewards.append(rewards[user_id][Rewards.TOKEN_KEY])
        return user_ids, eth_rewards, token_rewards

    @staticmethod
    def transform_lists_to_dict(user_ids, eth_rewards, token_rewards):
        return {
            user_id: Rewards.reward_dict(eth_reward=eth_r, token_reward=token_r)
            for user_id, eth_r, token_r in zip(user_ids, eth_rewards, token_rewards)
        }

    @staticmethod
    def get(event_id):
        key = Rewards.key(event_id)
        rewards_json = redis_db.get(key)
        if rewards_json is None:
            return None
        return json.loads(rewards_json)

    @staticmethod
    def get_lists(event_id):
        rewards = Rewards.get(event_id)
        if rewards is None:
            return None
        return Rewards.transform_dict_to_lists(rewards)

    @staticmethod
    def hash(user_ids, eth_rewards, token_rewards):
        value = '%s%s%s' % (user_ids, eth_rewards, token_rewards)
        value = value.encode('utf8')
        return hashlib.sha256(value).hexdigest()


class Vote(BaseEvent):
    PREFIX = 'votes'
    PREFIX_COMMON = 'votes_common'  # TODO delete this prefix when deleting event
    ANSWERS_SORT_KEY = 'field_name'

    def __init__(self, user_id, event_id, node_id, timestamp, answers, _ordered_answers=None):
        self.user_id = user_id
        self.event_id = event_id
        self.node_id = node_id
        self.timestamp = timestamp
        self.answers = answers
        self._ordered_answers = _ordered_answers

    @classmethod
    def key(cls, event_id, node_id):
        return '%s_%s_%s' % (cls.PREFIX, event_id, node_id)

    @classmethod
    def key_common(cls, event_id):
        return '%s_%s' % (cls.PREFIX_COMMON, event_id)

    def create(self):
        redis_db.rpush(self.key(self.event_id, self.node_id), self.to_json())
        redis_db.sadd(self.key_common(self.event_id), self.user_id)
        return self

    @classmethod
    def count(cls, event_id):
        return redis_db.scard(cls.key_common(event_id))

    def ordered_answers(self):
        if self._ordered_answers is not None:
            return self._ordered_answers
        # Order each dictionary and sort dictionaries by a key
        self._ordered_answers = sorted(
            [OrderedDict(sorted(answer.items(), key=lambda t: t[0])) for answer in self.answers],
            key=lambda x: x[self.ANSWERS_SORT_KEY])
        return self._ordered_answers

    @classmethod
    def get_list_json(cls, event_id, node_id):
        key = cls.key(event_id, node_id)
        return redis_db.lrange(key, 0, -1)

    @classmethod
    def get_list(cls, event_id, node_id):
        return [cls.from_json(vote) for vote in cls.get_list_json(event_id, node_id)]
