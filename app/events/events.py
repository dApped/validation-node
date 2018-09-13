import logging
import os
import pickle
import time

from web3 import HTTPProvider, Web3

import common
from database import events as database_events
from ethereum import rewards

provider = os.getenv('ETH_RPC_PROVIDER')
w3 = Web3(HTTPProvider(provider))


logger = logging.getLogger('flask.app')

# Test method
def get_all():
    logger.info('Reading all events from blockchain')
    return w3.eth.accounts


def all_events_addresses():
    # MOCK
    f = open(os.path.join(os.path.join(os.getenv('DATA_DIR'), 'event_addresses.pkl')), 'rb')
    event_addresses = pickle.load(f)

    return event_addresses


def filter_events_addresses(all_events):
    ''' Checks if node is registered in each of the events '''

    node_address = w3.eth.accounts[0]  # TODO Roman: read it from environment
    contract_abi = common.verity_event_contract_abi()

    events = []
    for event_address in all_events:
        contract_instance = w3.eth.contract(address=event_address, abi=contract_abi)
        node_addresses = contract_instance.functions.getEventResolvers().call()
        if node_address in node_addresses:
            events.append(event_address)
    return events


def retrieve_events(filtered_events):
    contract_abi = common.verity_event_contract_abi()

    events = []
    for event_address in filtered_events:
        contract_instance = w3.eth.contract(address=event_address, abi=contract_abi)
        owner = contract_instance.functions.owner().call()
        token_address = contract_instance.functions.tokenAddress().call()
        node_addresses = contract_instance.functions.getEventResolvers().call()
        leftovers_recoverable_after = contract_instance.functions.leftoversRecoverableAfter().call()
        application_start_time = contract_instance.functions.applicationStartTime().call()
        application_end_time = contract_instance.functions.applicationEndTime().call()
        event_start_time = contract_instance.functions.eventStartTime().call()
        event_end_time = contract_instance.functions.eventEndTime().call()
        event_name = contract_instance.functions.eventName().call()
        data_feed_hash = contract_instance.functions.dataFeedHash().call()
        state = contract_instance.functions.getState().call()
        is_master_node = contract_instance.functions.isMasterNode().call()
        consensus_rules = contract_instance.functions.getConsensusRules().call()
        event = database_events.Event(event_address, owner, token_address, node_addresses,
                                      leftovers_recoverable_after, application_start_time,
                                      application_end_time, event_start_time, event_end_time,
                                      event_name, data_feed_hash, state, is_master_node,
                                      *consensus_rules)
        events.append(event)
    return events

#### Maybe move this to some common later?
success_response = {'status': 200}
user_error_response = {'status': 400}
node_error_response = {'status': 500}
####

def _is_vote_valid(timestamp, user_id, event):
    if timestamp < event.event_start_time or timestamp > event.event_end_time:
        return False, user_error_response

    # 2. Check user has registered for event
    user_registered = is_user_registered(event, user_id)
    if not user_registered:
        return False, user_error_response

    return True, success_response


def vote(data):
    current_timestamp = int(time.time())
    event_id = data['event_id']
    user_id = data['user_id']

    event = database_events.get_event(event_id)
    valid_vote, response = _is_vote_valid(current_timestamp, user_id, event)
    if not valid_vote:
        return response


    # 3.1 Get current votes. Data structure to store votes is still TBD
    event_votes = []  #redis_db.get(data['event_id'], [])
    # 3.2 Add vote to other votes
    event_votes.append(data['answers'])

    # 3. check if consensus reached
    if len(event_votes) > event.min_consensus_votes:
        consensus_reached, consensus_votes = check_consensus(event_id)

        if consensus_reached:
            logger.info("Consensus reached")
            event_rewards = rewards.determine_rewards(event_id)  # event.distribution_function)

            if event.is_master_node:
                logger.info("Node is master node. Setting rewards")
                rewards.set_consensus_rewards(event_id, event_rewards)
            else:
                logger.info("Not master node..waiting for rewards to be set")
                # filter for rewards set
                # confirm/not confirm set rewards
    return success_response


def is_user_registered(event, user_id):
    return user_id in database_events.all_participants(event.event_address)


def check_consensus(event_id):
    # mock for now
    votes = [] # get event_id votes from redis
    if len(votes) > 5:
        return True
    return False
