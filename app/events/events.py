import os

from web3 import HTTPProvider, Web3

import common

provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))

verity_event_contract_abi = common.get_content("http://api.verity.network/contract/abi")


def get_all_events():
    """
    TODO
    Gets all registered events in a contract from ethereum
    """
    print("Getting events from blockchain...")
    return []


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
