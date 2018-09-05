import os

from web3 import HTTPProvider, Web3

provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))

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
    """
    return events

def vote(data):

    # TODO
    # 1. validate user is registered
    # 2. process vote
    # 3. check if consensus reached

    pass


