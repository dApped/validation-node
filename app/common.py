import json
import os
import pickle

from web3 import Web3

def verity_event_contract_abi():
    return json.loads(open(os.path.join(os.getenv('DATA_DIR'), 'VerityEvent.json')).read())['abi']


def event_registry_contract_abi():
    return json.loads(open(os.path.join(os.getenv('DATA_DIR'), 'EventRegistry.json')).read())['abi']


def event_registry_address():
    f = open(os.path.join(os.path.join(os.getenv('DATA_DIR'), 'contract_addresses.pkl')), 'rb')
    contract_addresses = pickle.load(f)
    return Web3.toChecksumAddress('0x9718274d370b8bc15f08d7cf675df21a02848692')
