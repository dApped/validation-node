import logging
import os
import pickle
import time
from collections import defaultdict

import scheduler
from database import events as database_events
from database import votes as database_votes
from ethereum import rewards
from ethereum.provider import EthProvider
from events import filters

provider = os.getenv('ETH_RPC_PROVIDER')

logger = logging.getLogger('flask.app')


def call_event_contract_for_event_ids():
    # TODO: Fetch events from event registry
    logger.info('Reading all events from blockchain')
    f = open(os.path.join(os.path.join(os.getenv('DATA_DIR'), 'event_addresses.pkl')), 'rb')
    event_addresses = pickle.load(f)
    return event_addresses


def read_node_id():
    ''' Returns the node address'''
    # TODO read Node Id from somewhere
    w3 = EthProvider().web3()
    return w3.eth.defaultAccount


def is_node_registered_on_event(contract_abi, node_id, event_id):
    w3 = EthProvider().web3()
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    node_ids = contract_instance.functions.getEventResolvers().call()
    node_ids = set(node_ids)
    return node_id in node_ids


def call_event_contract_for_metadata(contract_abi, event_id):
    w3 = EthProvider().web3()
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)

    state = contract_instance.functions.getState().call()
    if state > 2:  # TODO: Change this to 1
        logger.info('Skipping event %s with state: %d. It is not in waiting or application state',
                    event_id, state)
        return None

    owner = contract_instance.functions.owner().call()
    token_address = contract_instance.functions.tokenAddress().call()
    node_addresses = contract_instance.functions.getEventResolvers().call()
    (application_start_time, application_end_time, event_start_time, event_end_time,
     leftovers_recoverable_after) = contract_instance.functions.getEventTimes().call()
    event_name = contract_instance.functions.eventName().call()
    data_feed_hash = contract_instance.functions.dataFeedHash().call()
    is_master_node = contract_instance.functions.isMasterNode().call()
    consensus_rules = contract_instance.functions.getConsensusRules().call()
    (min_total_votes, min_consensus_votes, min_consensus_ratio, min_participant_ratio,
     max_participants, rewards_distribution_function) = consensus_rules
    validation_round = contract_instance.functions.rewardsValidationRound().call()
    event = database_events.VerityEvent(
        event_id, owner, token_address, node_addresses, leftovers_recoverable_after,
        application_start_time, application_end_time, event_start_time, event_end_time, event_name,
        data_feed_hash, state, is_master_node, min_total_votes, min_consensus_votes,
        min_consensus_ratio, min_participant_ratio, max_participants, rewards_distribution_function,
        validation_round)
    return event


def init_event(contract_abi, node_id, event_id):
    w3 = EthProvider().web3()
    if not is_node_registered_on_event(contract_abi, node_id, event_id):
        logger.info('Node %s is not included in %s event', node_id, event_id)
        return
    logger.info('Initializing %s event', event_id)
    event = call_event_contract_for_metadata(contract_abi, event_id)
    if not event:
        return
    event.create()
    filters.init_event_filters(w3, contract_abi, event.event_id)
    logger.info('%s event initialized', event_id)


# TODO: Maybe move this to some common later?
success_response = {'status': 200}
user_error_response = {'status': 400}
node_error_response = {'status': 500}


def _is_vote_valid(timestamp, user_id, event):
    # TODO check request data format, maybe use schema validator

    if timestamp < event.event_start_time or timestamp > event.event_end_time:
        logger.info("Voting is not active %s", event.event_id)
        return False, user_error_response

    # 2. Check user has registered for event
    user_registered = database_events.Participants.exists(event.event_id, user_id)
    if not user_registered:
        logger.info("User %s is not registered %s", user_id, event.event_id)
        return False, user_error_response
    return True, success_response


def is_vote_payload_valid(data):
    if 'data' not in data:
        return False
    for param in {'user_id', 'event_id', 'answers'}:
        if param not in data['data']:
            return False
    return True


def vote(json_data, ip_address):
    current_timestamp = int(time.time())
    if not is_vote_payload_valid(json_data):
        return user_error_response

    data = json_data['data']
    event_id = data['event_id']
    user_id = data['user_id']
    event = database_events.VerityEvent.get(event_id)
    event_metadata = event.metadata()

    # consensus already reached, no more voting possible
    if event_metadata.is_consensus_reached:
        logger.info("Consensus already reached, no more voting")
        return user_error_response
    valid_vote, response = _is_vote_valid(current_timestamp, user_id, event)
    if not valid_vote:
        logger.info("VOTE NOT VALID BUT CONTINUE ANYWAY")
        return response

    logger.info("Valid vote")
    database_votes.Vote(user_id, event_id, current_timestamp, data['answers']).create()
    event_votes = event.votes()
    # check if consensus reached
    vote_count = len(event_votes)
    participant_ratio = (vote_count / len(event.participants())) * 100
    if vote_count >= event.min_total_votes and participant_ratio >= event.min_participant_ratio:
        consensus_reached, consensus_votes = check_consensus(event, event_votes)
        if consensus_reached:
            logger.info("Consensus reached")
            event_metadata.is_consensus_reached = consensus_reached
            event_metadata.update()

            rewards.determine_rewards(event_id, consensus_votes)
            if event.is_master_node:
                scheduler.scheduler.add_job(rewards.set_consensus_rewards, args=[event_id])
            else:
                logger.info("Not master node..waiting for rewards to be set")
    return success_response


def check_consensus(event, votes):
    answers_combinations = defaultdict(list)
    for vote in votes:
        vote_answers = vote.ordered_answers().__repr__()
        # store in vote for when adding to consensus_votes
        answers_combinations[vote_answers].append(vote)

    consensus_candidate = max(answers_combinations, key=lambda x: len(answers_combinations[x]))
    cons_vote_count = len(answers_combinations[consensus_candidate])
    consensus_ratio = cons_vote_count / len(votes)
    if cons_vote_count < event.min_consensus_votes or consensus_ratio * 100 < event.min_consensus_ratio:
        logger.info('Not enough consensus votes!')
        return False, []

    consensus_votes = sorted(answers_combinations[consensus_candidate], key=lambda v: v.timestamp)
    return True, consensus_votes
