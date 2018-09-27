import logging
import os
import time

from database import database
from ethereum.provider import NODE_WEB3

logger = logging.getLogger('flask.app')

BEFORE_EVENT_START = 60 * 10  # 10 minutes


def register_node_ip(node_registry_abi, node_registry_address, node_ip):
    node_addresses = [os.getenv('NODE_ADDRESS')]
    node_ips = get_node_ips(node_registry_abi, node_registry_address, node_addresses)

    if not node_ips or node_ip != node_ips[0]:
        logger.info('Registering Node IP: %s', node_ip)
        contract_instance = NODE_WEB3.eth.contract(
            address=node_registry_address, abi=node_registry_abi)
        trx = contract_instance.functions.registerNodeIp(node_ip).transact()
        NODE_WEB3.eth.waitForTransactionReceipt(trx)
    logger.info('Node IP: %s', node_ip)


def get_node_ips(node_registry_abi, node_registry_address, node_addresses):
    contract_instance = NODE_WEB3.eth.contract(address=node_registry_address, abi=node_registry_abi)
    node_ips = []
    for node_address in node_addresses:
        node_ip = contract_instance.functions.nodeIp(node_address).call()
        if not node_ip:
            continue
        node_ips.append(node_ip)
    return node_ips


def update_node_ips(node_registry_abi, node_registry_address):
    event_ids = database.VerityEvent.get_ids_list()
    current_timestamp = int(time.time())
    for event_id in event_ids:
        event = database.VerityEvent.get(event_id)
        metadata = event.metadata()
        before_event_start_time = event.event_start_time - BEFORE_EVENT_START
        if (before_event_start_time <= current_timestamp < event.event_start_time
                and not metadata.node_ips):
            metadata.node_ips = get_node_ips(node_registry_abi, node_registry_address,
                                             event.node_addresses)
            metadata.update()
            logger.info('%d node ip addresses set for %s', len(metadata.node_ips), event.event_id)
