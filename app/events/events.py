import json
import os
import pickle
import sys

from web3 import HTTPProvider, Web3
provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))

project_root = os.path.dirname(sys.modules['__main__'].__file__)
verity_event_contract_abi = json.loads(open(os.path.join(project_root, 'VerityEvent.json')).read())['abi']


def get_all_events():
    f = open(os.path.join(project_root, 'event_addresses.pkl'), 'rb')
    event_addresses = pickle.load(f)
    return event_addresses


def get_my_events(events):
    """
    TODO
    Checks if node is registered in each of the events

    my_events = []
    for event in events:
        contract_instance = web3.eth.contract(address=event.contract_address,
                                              abi=verity_event_contract_abi)

        if my_address in contract_instance.get_registered_nodes():
            my_events.append(event)
    """
    return events


def vote(data):
    # TODO
    # 1. validate user is registered
    # 2. process vote
    # 3. check if consensus reached

    pass
