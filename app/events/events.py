import json
import os
import pickle
import sys

from web3 import HTTPProvider, Web3

provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))

project_root = os.path.dirname(sys.modules['__main__'].__file__)
verity_event_contract_abi = json.loads(open(os.path.join(project_root,
                                                         'VerityEvent.json')).read())['abi']


def all_events_addresses():
    f = open(os.path.join(project_root, 'event_addresses.pkl'), 'rb')
    event_addresses = pickle.load(f)
    return event_addresses


def filter_node_events(all_events):
    ''' Checks if node is registered in each of the events '''
    node_address = web3.eth.accounts[0]  # TODO Roman: read it from environment

    events = []
    for event_address in all_events:
        contract_instance = web3.eth.contract(address=event_address, abi=verity_event_contract_abi)
        node_addresses = contract_instance.functions.getEventResolvers().call()
        if node_address in node_addresses:
            events.append(event_address)
    return events


def vote(data):
    # TODO
    # 1. validate user is registered
    # 2. process vote
    # 3. check if consensus reached

    pass
