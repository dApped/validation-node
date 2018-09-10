import json
import os
import pickle
import sys
import time

from web3 import HTTPProvider, Web3

from application import redis_db
from ethereum import rewards

provider = os.getenv('ETH_RPC_PROVIDER')
w3 = Web3(HTTPProvider(provider))

project_root = os.path.dirname(sys.modules['__main__'].__file__)
verity_event_contract_abi = json.loads(open(os.path.join(project_root,
                                                         'VerityEvent.json')).read())['abi']


def all_events_addresses():
    f = open(os.path.join(project_root, 'event_addresses.pkl'), 'rb')
    event_addresses = pickle.load(f)
    return event_addresses


def filter_node_events(all_events):
    ''' Checks if node is registered in each of the events '''
    node_address = w3.eth.accounts[0]  # TODO Roman: read it from environment

    events = []
    for event_address in all_events:
        contract_instance = w3.eth.contract(address=event_address, abi=verity_event_contract_abi)
        node_addresses = contract_instance.functions.getEventResolvers().call()
        if node_address in node_addresses:
            events.append(event_address)
    return events


def vote(data):
    current_timestamp = int(time.time())
    event_id = data['event_id']
    event = get_event_instance(event_id)

    #### Maybe move this to some common later?
    success_response = {'status': 200}
    user_error_response = {'status': 400}
    node_error_response = {'status': 500}
    ####

    # 1. Validate users can vote on this event now
    if current_timestamp < event.call().eventStartTime() or current_timestamp > event.call().eventEndTime():
        return user_error_response

    # 2. Check user has registered for event
    user_registered = is_user_registered(event, data['user_id'])
    if not user_registered:
        return user_error_response

    # 3.1 Get current votes. Data structure to store votes is still TBD
    event_votes = redis_db.get(data['event_id'], [])
    # 3.2 Add vote to other votes
    event_votes.append(data['answers'])

    # 3. check if consensus reached
    if len(event_votes) > event.call().minConsensus():
        consensus_reached, consensus_votes = check_consensus(event_votes)

        if consensus_reached:
            event_rewards = rewards.determine_rewards(consensus_votes) #, event.distribution_function)
            rewards.set_consensus_rewards(event_id, event_rewards)

    return success_response


def get_event_instance(event_address):
    event_instance = w3.eth.contract(address=event_address,
                                     abi=verity_event_contract_abi)
    # TODO Create Event Class
    return event_instance


def is_user_registered(event, user_id):

    event_join_filter = event.eventFilter('JoinEvent', {
        'fromBlock': 0,
        'toBlock': 'latest'
    })
    users_joined = event_join_filter.get_all_entries()
    return user_id in users_joined


def check_consensus(votes):
    # all votes in consensus
    return True, votes
