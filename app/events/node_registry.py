import logging
import os

import common
from database import database
from ethereum.provider import NODE_WEB3

logger = logging.getLogger('flask.app')


def register_node_ip(node_registry_abi, node_registry_address, node_ip):
    node_addresses = [os.getenv('NODE_ADDRESS')]
    node_ips = get_node_ips(node_registry_abi, node_registry_address, node_addresses)

    if not node_ips or node_ip != node_ips[0]:
        logger.info('Registering Node IP: %s', node_ip)
        contract_instance = NODE_WEB3.eth.contract(
            address=node_registry_address, abi=node_registry_abi)
        register_node_ip_fun = contract_instance.functions.registerNodeIp(node_ip)
        trx = common.function_transact(NODE_WEB3, register_node_ip_fun)
        NODE_WEB3.eth.waitForTransactionReceipt(trx)
    logger.info('Node IP: %s', node_ip)


def get_node_ips(node_registry_abi, node_registry_address, node_ids):
    contract_instance = NODE_WEB3.eth.contract(address=node_registry_address, abi=node_registry_abi)
    node_ips = []
    for node_id in node_ids:
        node_ip = contract_instance.functions.nodeIp(node_id).call()
        if not node_ip:
            continue
        node_ips.append(node_ip)
    return node_ips


def update_node_ips(node_registry_abi, node_registry_address):
    event_ids = database.VerityEvent.get_ids_list()
    for event_id in event_ids:
        event = database.VerityEvent.get(event_id)
        metadata = event.metadata()
        node_ips = get_node_ips(node_registry_abi, node_registry_address, event.node_addresses)
        if set(node_ips) == set(metadata.node_ips):
            continue
        logger.info('Updating node ips for %s event', event.event_id)
        metadata.node_ips = node_ips
        metadata.update()
