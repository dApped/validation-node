import logging

import common
from database import database
from ethereum.provider import NODE_WEB3

logger = logging.getLogger()


def register_node_ip(node_registry_abi, node_registry_address, node_ip, address_type):
    node_addresses = [common.node_id()]
    node_ips = get_node_ips(node_registry_abi, node_registry_address, node_addresses, address_type)

    if not node_ips or node_ip != node_ips[0]:
        contract_instance = NODE_WEB3.eth.contract(
            address=node_registry_address, abi=node_registry_abi)
        if common.AddressType.IP == address_type:
            logger.info('Registering node IP: %s', node_ip)
            register_node_ip_fun = contract_instance.functions.registerNodeIp(node_ip)
        elif common.AddressType.WEBSOCKET == address_type:
            logger.info('Registering node Websocket IP: %s', node_ip)
            register_node_ip_fun = contract_instance.functions.registerNodeWs(node_ip)
        else:
            raise Exception('Unsupported address type ' + str(address_type))
        common.function_transact(NODE_WEB3, register_node_ip_fun)
    logger.info('Node %s: %s', str(address_type), node_ip)


def get_node_ips(node_registry_abi, node_registry_address, node_ids, address_type):
    contract_instance = NODE_WEB3.eth.contract(address=node_registry_address, abi=node_registry_abi)
    node_ips = []
    for node_id in node_ids:
        if common.AddressType.IP == address_type:
            node_ip = contract_instance.functions.nodeIp(node_id).call()
        elif common.AddressType.WEBSOCKET == address_type:
            node_ip = contract_instance.functions.nodeWs(node_id).call()
        else:
            raise Exception('Unsupported address type ' + str(address_type))
        if not node_ip:
            continue
        node_ips.append(node_ip)
    return node_ips


def update_node_ips(node_registry_abi, node_registry_address):
    event_ids = database.VerityEvent.get_ids_list()
    for event_id in event_ids:
        event = database.VerityEvent.get(event_id)
        if event is None:
            logger.info('[%s] Event is not in the database', event_id)
            continue
        metadata = event.metadata()
        for address_type in [common.AddressType.IP, common.AddressType.WEBSOCKET]:
            node_ips = get_node_ips(node_registry_abi, node_registry_address, event.node_addresses,
                                    address_type)
            if common.AddressType.IP == address_type:
                if set(node_ips) == set(metadata.node_ips):
                    continue
                logger.info('[%s] Updating node IPs', event.event_id)
                metadata.node_ips = node_ips
            elif common.AddressType.WEBSOCKET == address_type:
                if set(node_ips) == set(metadata.node_websocket_ips):
                    continue
                logger.info('[%s] Updating node Websocket IPs', event.event_id)
                metadata.node_websocket_ips = node_ips
            else:
                raise Exception('Unsupported address type ' + str(address_type))
        metadata.update()
