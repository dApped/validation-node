import logging

import requests

import common
from database import database
from queue_service import transactions

logger = logging.getLogger()


def register_node_ip(w3, node_registry_abi, node_registry_address, node_ip, address_type):
    node_addresses = [common.node_id()]
    node_ips = get_node_ips(w3, node_registry_abi, node_registry_address, node_addresses,
                            address_type)

    if not node_ips or node_ip != node_ips[0]:
        contract_instance = w3.eth.contract(address=node_registry_address, abi=node_registry_abi)
        if common.AddressType.IP == address_type:
            logger.info('Registering node IP: %s', node_ip)
            register_node_ip_fun = contract_instance.functions.registerNodeIp(node_ip)
        elif common.AddressType.WEBSOCKET == address_type:
            logger.info('Registering node Websocket IP: %s', node_ip)
            register_node_ip_fun = contract_instance.functions.registerNodeWs(node_ip)
        else:
            raise Exception('Unsupported address type ' + str(address_type))
        trx_hash = transactions.queue_transaction(w3, register_node_ip_fun)
        if trx_hash is None:
            raise Exception(
                'Make sure you have registered your validation node address in Node Registry')
    logger.info('Node %s: %s', str(address_type), node_ip)


def get_node_ips(w3, node_registry_abi, node_registry_address, node_ids, address_type):
    contract_instance = w3.eth.contract(address=node_registry_address, abi=node_registry_abi)
    node_ips = []
    for node_id in node_ids:
        try:
            if common.AddressType.IP == address_type:
                node_ip = contract_instance.functions.nodeIp(node_id).call()
            elif common.AddressType.WEBSOCKET == address_type:
                node_ip = contract_instance.functions.nodeWs(node_id).call()
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            logger.info('Get_node_ips %s exception', e.__class__.__name__)
            continue
        if not node_ip:
            continue
        node_ips.append(node_ip)
    return node_ips


def update_node_ips(w3, node_registry_abi, node_registry_address):
    event_ids = database.VerityEvent.get_ids_list()
    for event_id in event_ids:
        event = database.VerityEvent.get(event_id)
        if event is None:
            logger.info('[%s] Event is not in the database', event_id)
            continue

        was_updated = False
        metadata = event.metadata()
        for address_type in [common.AddressType.IP, common.AddressType.WEBSOCKET]:
            node_ips = get_node_ips(w3, node_registry_abi, node_registry_address,
                                    event.node_addresses, address_type)
            if common.AddressType.IP == address_type:
                if set(node_ips) == set(metadata.node_ips):
                    continue
                logger.info('[%s] Updating node IPs', event.event_id)
                metadata.node_ips = node_ips
                was_updated = True
            elif common.AddressType.WEBSOCKET == address_type:
                if set(node_ips) == set(metadata.node_websocket_ips):
                    continue
                logger.info('[%s] Updating node Websocket IPs', event.event_id)
                metadata.node_websocket_ips = node_ips
                was_updated = True
            else:
                raise Exception('Unsupported address type ' + str(address_type))
        if was_updated:
            metadata.update()
