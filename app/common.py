import json
import os
import pickle

import requests


def verity_event_contract_abi():
    return json.loads(open(os.path.join(os.getenv('DATA_DIR'), 'VerityEvent.json')).read())['abi']


def event_registry_contract_abi():
    return json.loads(open(os.path.join(os.getenv('DATA_DIR'), 'EventRegistry.json')).read())['abi']


def node_registry_contract_abi():
    return json.loads(open(os.path.join(os.getenv('DATA_DIR'), 'NodeRegistry.json')).read())['abi']


def event_registry_address():
    f = open(os.path.join(os.path.join(os.getenv('DATA_DIR'), 'contract_addresses.pkl')), 'rb')
    contract_addresses = pickle.load(f)
    return contract_addresses['EventRegistry']


def node_registry_address():
    f = open(os.path.join(os.path.join(os.getenv('DATA_DIR'), 'contract_addresses.pkl')), 'rb')
    contract_addresses = pickle.load(f)
    return contract_addresses['NodeRegistry']


def public_ip():
    return requests.get('https://ip.42.pl/raw').text
