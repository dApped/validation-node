import logging

import common
from database import database

logger = logging.getLogger()


def read_contract_addresses(w3, contract_registry_address):
    contract_abi = common.contract_registry_contract_abi()
    contract_instance = w3.eth.contract(address=contract_registry_address, abi=contract_abi)
    node_registry_address = contract_instance.functions.nodeRegistry().call()
    event_registry_address = contract_instance.functions.eventRegistry().call()
    logger.info('[%s] Node registry', node_registry_address)
    logger.info('[%s] Event registry', event_registry_address)
    return node_registry_address, event_registry_address


def store_addresses(node_registry_address, event_registry_address):
    database.ContractAddress.set_node_registry(node_registry_address)
    database.ContractAddress.set_event_registry(event_registry_address)


def init_contract_registry(w3, contract_registry_address):
    logger.info('[%s] Init contract registry', contract_registry_address)
    node_registry_address, event_registry_address = read_contract_addresses(
        w3, contract_registry_address)
    store_addresses(node_registry_address, event_registry_address)
