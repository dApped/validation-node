import os

from web3 import HTTPProvider, Web3

import common
from database import events as database_events

provider = os.getenv('ETH_RPC_PROVIDER')
w3 = Web3(HTTPProvider(provider))

#def determine_rewards(consensus_votes, distribution_function='linear'):
#    #addresses = [vote.user_id for vote in consensus_votes]
#    #token_rewards = [10 for vote in consensus_votes]
#    #eth_rewards = [0.1 for vote in consensus_votes]

#    rewards = []
#    for vote in consensus_votes:
#        r = {vote.user_id: {'token': t, 'eth': e}}

#        rewards.append(r)

#    # TODO store in REDIS
#    rewards = [{
#        'address': a,
#        'token': t,
#        'eth': e
#    } for a, t, e in zip(addresses, token_rewards, eth_rewards)]

#    return addresses, token_rewards, eth_rewards


def set_consensus_rewards(event_id):
    user_ids, eth_rewards, token_rewards = database_events.Rewards.get_lists(event_id)
    contract_abi = common.verity_event_contract_abi()

    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    contract_instance.functions.setRewards(user_ids, eth_rewards, token_rewards).transact()


def validate_rewards(event_id):
    """
    TODO
    Validates rewards set
    Sends 'ok' or 'nok' to conract
    """
    pass
