import hashlib
import json
import logging
import os
import sys
from collections import OrderedDict, defaultdict

import redis
from web3 import Web3

import common

logger = logging.getLogger()

redis_db = redis.StrictRedis(host=os.getenv('DB_REDIS_IP'), port=6379, db=0, decode_responses=True)


def flush_database():
    logger.info('Flushing database')
    redis_db.flushdb()


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
    def delete(cls, event_id, pipeline=None):
        key = cls.key(event_id)
        if pipeline is None:
            redis_db.delete(key)
        else:
            pipeline.delete(key)

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_data):
        dict_data = json.loads(json_data)
        return cls(**dict_data)


class EventRegistry:
    LAST_RUN_KEY = 'event_registry_last_run'

    @classmethod
    def set_last_run_timestamp(cls, timestamp):
        redis_db.set(cls.LAST_RUN_KEY, timestamp)

    @classmethod
    def last_run_timestamp(cls):
        return redis_db.get(cls.LAST_RUN_KEY)


class VerityEvent(BaseEvent):
    IDS_KEY = 'event_ids'
    PREFIX = 'event'

    def __init__(self, event_id, owner, token_address, node_addresses, leftovers_recoverable_after,
                 application_start_time, application_end_time, event_start_time, event_end_time,
                 event_name, data_feed_hash, state, is_master_node, min_total_votes,
                 min_consensus_votes, min_consensus_ratio, min_participant_ratio, max_participants,
                 rewards_distribution_function, rewards_validation_round, dispute_amount,
                 dispute_timeout, dispute_multiplier, dispute_round, disputer, staking_amount):
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
        self.dispute_amount = dispute_amount
        self.dispute_timeout = dispute_timeout
        self.dispute_multiplier = dispute_multiplier
        self.dispute_round = dispute_round
        self.disputer = disputer
        self.staking_amount = staking_amount

    @staticmethod
    def consensus_not_reached_job_id(event_id):
        """ Generate a job ID for consensus not reached job """
        return '%s_process_consensus_not_reached' % event_id

    def votes(self, min_votes=None, max_votes=None, filter_by_vote=None, check_uniqueness=True):
        """ Returns votes by users based on filters specified """
        min_votes = min_votes or 2
        max_votes = max_votes or len(self.node_addresses)
        votes_by_users = Vote.group_votes_by_users(self.event_id, self.node_addresses)
        votes_by_users = Vote.filter_votes_by_users(
            self.event_id,
            votes_by_users,
            min_votes=min_votes,
            max_votes=max_votes,
            check_uniqueness=check_uniqueness,
            filter_by_vote=filter_by_vote)
        return votes_by_users

    def votes_consensus(self):
        """ Returns votes by users with predefined filters for consensus """
        return self.votes(
            min_votes=2,
            max_votes=len(self.node_addresses),
            filter_by_vote=None,
            check_uniqueness=True)

    def votes_for_explorer(self):
        """ Returns votes by users with predefined filters for explorer server """
        votes_by_users_all = self.votes(
            min_votes=1, max_votes=sys.maxsize, filter_by_vote=None, check_uniqueness=False)
        votes_by_users_consensus = self.votes_consensus()

        for user_id in votes_by_users_all:
            in_consensus = False
            if user_id in votes_by_users_consensus:
                in_consensus = True
            for i in range(len(votes_by_users_all[user_id])):
                votes_by_users_all[user_id][i].in_consensus = in_consensus
        return self.votes_to_json(votes_by_users_all)

    @staticmethod
    def votes_to_json(votes_by_users):
        return {
            user_id: [vote.to_json() for vote in votes]
            for user_id, votes in votes_by_users.items()
        }

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

    def user_ids_without_vote(self):
        return self.participants().difference(Vote.user_ids_with_vote(self.event_id))

    @classmethod
    def delete_all_event_data(cls, w3, event_id):
        filter_ids = Filters.get_list(event_id)

        pipeline = redis_db.pipeline()
        pipeline.lrem(cls.IDS_KEY, 1, event_id)
        VerityEvent.delete(event_id, pipeline)
        VerityEventMetadata.delete(event_id, pipeline)
        Participants.delete(event_id, pipeline)
        Filters.delete(event_id, pipeline)
        event = VerityEvent.get(event_id)
        if event is not None:
            Vote.delete_all(pipeline, event_id, VerityEvent.get(event_id).node_addresses)
        Rewards.delete(event_id, pipeline)
        pipeline.execute()

        Filters.uninstall(w3, filter_ids)


class VerityEventMetadata(BaseEvent):
    PREFIX = 'metadata'

    def __init__(self, event_id, is_consensus_reached, node_ips, node_websocket_ips,
                 contract_block_number, previous_consensus_answers):
        self.event_id = event_id
        self.is_consensus_reached = is_consensus_reached
        self.node_ips = node_ips
        self.node_websocket_ips = node_websocket_ips
        self.contract_block_number = contract_block_number
        self.previous_consensus_answers = previous_consensus_answers

    def create(self):
        redis_db.set(self.key(self.event_id), self.to_json())

    @staticmethod
    def get_or_create(event_id):
        event_metadata = VerityEventMetadata.get(event_id)
        if event_metadata is None:
            event_metadata = VerityEventMetadata(
                event_id=event_id,
                is_consensus_reached=False,
                node_ips=[],
                node_websocket_ips=[],
                contract_block_number=0,
                previous_consensus_answers=None)
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
    def filter_dict(filter_id, filter_name):
        return {'filter_id': filter_id, 'filter_name': filter_name}

    @classmethod
    def create(cls, event_id, filter_id, filter_name):
        key = cls.key(event_id)
        filter_dict = cls.filter_dict(filter_id, filter_name)
        redis_db.rpush(key, json.dumps(filter_dict))

    @classmethod
    def get_list(cls, event_id):
        key = cls.key(event_id)
        return [json.loads(filter_json) for filter_json in redis_db.lrange(key, 0, -1)]

    @classmethod
    def delete_filter(cls, event_id, filter_id, filter_name):
        key = cls.key(event_id)
        filter_dict = cls.filter_dict(filter_id, filter_name)
        n_deleted = redis_db.lrem(key, 1, json.dumps(filter_dict))
        logger.info('[%s] %d entries for %s filter deleted', event_id, n_deleted, filter_name)
        return n_deleted

    @staticmethod
    def uninstall(w3, filter_ids):
        for filter_id in filter_ids:
            try:
                w3.eth.uninstallFilter(filter_id)
            except Exception as e:
                logger.info(e)


class Rewards(BaseEvent):
    PREFIX = 'rewards'  # stores dictionary with user_id as a key and rewards as values
    PREFIX_REWARDS_USER_IDS = 'rewards_user_ids'  # stores a list of user_ids ordered by rewards
    ETH_KEY = 'eth'
    TOKEN_KEY = 'token'

    @classmethod
    def key_rewards_user_ids(cls, event_id):
        return '%s_%s' % (cls.PREFIX_REWARDS_USER_IDS, event_id)

    @classmethod
    def key_rewards_all_user_ids(cls, event_id):
        return '%s_%s' % (cls.PREFIX_REWARDS_ALL_USER_IDS, event_id)

    @classmethod
    def create(cls, event_id, user_ids_rewards, rewards_dict):
        key = cls.key(event_id)
        rewards_json = json.dumps(rewards_dict)
        redis_db.set(key, rewards_json)

        key_rewards_user_ids = cls.key_rewards_user_ids(event_id)
        for user_id in user_ids_rewards:
            redis_db.rpush(key_rewards_user_ids, user_id)

    @classmethod
    def reward_dict(cls, eth_reward=0, token_reward=0):
        return {cls.ETH_KEY: eth_reward, cls.TOKEN_KEY: token_reward}

    @classmethod
    def transform_dict_to_lists(cls, rewards):
        if rewards is None:
            logger.error('Transform_dict_to_lists called with None')
            return [], [], []
        user_ids = list(rewards.keys())
        eth_rewards, token_rewards = [], []
        for user_id in user_ids:
            eth_rewards.append(rewards[user_id][cls.ETH_KEY])
            token_rewards.append(rewards[user_id][cls.TOKEN_KEY])
        return user_ids, eth_rewards, token_rewards

    @classmethod
    def transform_lists_to_dict(cls, user_ids, eth_rewards, token_rewards):
        return {
            user_id: cls.reward_dict(eth_reward=eth_r, token_reward=token_r)
            for user_id, eth_r, token_r in zip(user_ids, eth_rewards, token_rewards)
        }

    @classmethod
    def get(cls, event_id):
        """ A dictionary with user_id as a key and reward as a value"""
        key = cls.key(event_id)
        rewards_json = redis_db.get(key)
        if rewards_json is None:
            return None
        return json.loads(rewards_json)

    @classmethod
    def get_rewards_user_ids(cls, event_id):
        """ A list of user_ids with rewards"""
        key = cls.key_rewards_user_ids(event_id)
        return redis_db.lrange(key, 0, -1)

    @classmethod
    def get_lists(cls, event_id):
        rewards = cls.get(event_id)
        if rewards is None:
            return [], [], []
        return cls.transform_dict_to_lists(rewards)

    @staticmethod
    def hash(user_ids, eth_rewards, token_rewards):
        value = '%s%s%s' % (user_ids, eth_rewards, token_rewards)
        value = value.encode('utf8')
        return hashlib.sha256(value).hexdigest()


class Vote(BaseEvent):
    PREFIX = 'votes'
    PREFIX_COMMON = 'votes_common'
    PREFIX_EXISTS = 'votes_exists'
    PREFIX_CONSENSUS = 'votes_consensus'
    ANSWERS_SORT_KEY = 'field_name'
    ANSWERS_VALUE_KEY = 'field_value'

    def __init__(self,
                 user_id,
                 event_id,
                 node_id,
                 timestamp,
                 answers,
                 signature,
                 in_consensus=False):  # This property is set on demand for Explorer
        self.user_id = user_id
        self.event_id = event_id
        self.node_id = node_id
        self.timestamp = timestamp
        self.answers = answers
        self.signature = signature
        self.in_consensus = in_consensus

    @classmethod
    def key(cls, event_id, node_id):
        return '%s_%s_%s' % (cls.PREFIX, event_id, node_id)

    @classmethod
    def key_exists(cls, event_id):
        return '%s_%s' % (cls.PREFIX_EXISTS, event_id)

    @classmethod
    def key_common(cls, event_id):
        return '%s_%s' % (cls.PREFIX_COMMON, event_id)

    @staticmethod
    def key_user_node(node_id, user_id):
        return '%s_%s' % (node_id, user_id)

    @classmethod
    def key_consensus(cls, event_id):
        return '%s_%s' % (cls.PREFIX_CONSENSUS, event_id)

    def create(self):
        redis_db.rpush(self.key(self.event_id, self.node_id), self.to_json())  # store vote
        redis_db.sadd(self.key_common(self.event_id), self.user_id)  # for consensus check heuristic
        redis_db.sadd(
            self.key_exists(self.event_id),
            self.key_user_node(self.node_id, self.user_id))  # for vote exists check
        return self

    @classmethod
    def exists(cls, event_id, node_id, user_id):
        key = cls.key_exists(event_id)
        return redis_db.sismember(key, cls.key_user_node(node_id, user_id))

    def set_consensus_vote(self):
        redis_db.set(self.key_consensus(self.event_id), self.to_json())
        return self

    @classmethod
    def get_consensus_vote(cls, event_id):
        key = cls.key_consensus(event_id)
        consensus_vote = redis_db.get(key)
        if consensus_vote is None:
            return None
        return cls.from_json(consensus_vote)

    @classmethod
    def get_consensus_answers(cls, event_id):
        consensus_vote = cls.get_consensus_vote(event_id)
        return cls.answers_from_vote(consensus_vote)

    @classmethod
    def answers_from_vote(cls, vote):
        if vote is None:
            return []
        return [answer[cls.ANSWERS_VALUE_KEY] for answer in vote.ordered_answers()]

    @classmethod
    def delete_all(cls, pipeline, event_id, node_ids):
        for node_id in node_ids:
            pipeline.delete(cls.key(event_id, node_id))
        pipeline.delete(cls.key_common(event_id))
        pipeline.delete(cls.key_consensus(event_id))
        pipeline.delete(cls.key_exists(event_id))

    @classmethod
    def count(cls, event_id):
        return redis_db.scard(cls.key_common(event_id))

    @classmethod
    def user_ids_with_vote(cls, event_id):
        return redis_db.smembers(cls.key_common(event_id))

    @classmethod
    def user_ids_with_incorrect_vote(cls, event_id, user_ids_correct_vote):
        return cls.user_ids_with_vote(event_id).difference(user_ids_correct_vote)

    def ordered_answers(self):
        return sorted(
            [OrderedDict(sorted(answer.items(), key=lambda t: t[0])) for answer in self.answers],
            key=lambda x: x[self.ANSWERS_SORT_KEY])

    @classmethod
    def get_list_json(cls, event_id, node_id):
        key = cls.key(event_id, node_id)
        return redis_db.lrange(key, 0, -1)

    @classmethod
    def get_list(cls, event_id, node_id):
        return [cls.from_json(vote) for vote in cls.get_list_json(event_id, node_id)]

    @classmethod
    def group_votes_by_users(cls, event_id, node_ids):
        votes_by_users = defaultdict(list)
        for node_id in node_ids:
            votes_node = cls.get_list(event_id, node_id)
            for vote in votes_node:
                votes_by_users[vote.user_id].append(vote)
        return votes_by_users

    def answers_representation(self):
        """ Immutable (static) representation of the vote's answers"""
        return self.ordered_answers().__repr__()

    @staticmethod
    def filter_votes_by_users(event_id, votes_by_users, min_votes, max_votes, check_uniqueness,
                              filter_by_vote):
        user_ids = list(votes_by_users.keys())
        for user_id in user_ids:
            n_votes = len(votes_by_users[user_id])
            if n_votes < min_votes or n_votes > max_votes:
                logger.info(
                    '[%s] Vote from %s user has too many or too little entries: %d. Skip it',
                    event_id, user_id, n_votes)
                del votes_by_users[user_id]
            elif check_uniqueness and len(
                {vote.answers_representation()
                 for vote in votes_by_users[user_id]}) != 1:
                # answers from a user from different nodes are not the same
                logger.warning('[%s] User %s voted differently on different nodes', event_id,
                               user_id)
                del votes_by_users[user_id]
            elif filter_by_vote is not None and\
                    votes_by_users[user_id][0].answers_representation() !=\
                    filter_by_vote.answers_representation():
                logger.info('[%s] Vote from %s user is not in consensus. Skip it', event_id,
                            user_id)
                del votes_by_users[user_id]
        return votes_by_users

    @staticmethod
    def group_votes_by_representation(votes_by_users):
        votes_by_repr = defaultdict(list)
        for _, votes in votes_by_users.items():
            if not votes:
                continue
            # each user has multiple votes
            # (although they are the same, so take first one to calculate vote representation
            vote_repr = votes[0].answers_representation()
            votes_by_repr[vote_repr].extend(votes)
        return votes_by_repr


class ContractAddress:
    """ Stores latest addresses of smart contracts """
    @staticmethod
    def key_event_registry():
        return 'event_registry_address'

    @staticmethod
    def key_node_registry():
        return 'node_registry_address'

    @classmethod
    def set_event_registry(cls, contract_address):
        key = cls.key_event_registry()
        redis_db.set(key, contract_address)

    @classmethod
    def set_node_registry(cls, contract_address):
        key = cls.key_node_registry()
        redis_db.set(key, contract_address)

    @classmethod
    def event_registry(cls):
        event_registry_address = os.getenv('EVENT_REGISTRY_ADDRESS')
        if event_registry_address:
            return Web3.toChecksumAddress(event_registry_address)
        key = cls.key_event_registry()
        return redis_db.get(key)

    @classmethod
    def node_registry(cls):
        node_registry_address = os.getenv('NODE_REGISTRY_ADDRESS')
        if node_registry_address:
            return Web3.toChecksumAddress(node_registry_address)
        key = cls.key_node_registry()
        return redis_db.get(key)
