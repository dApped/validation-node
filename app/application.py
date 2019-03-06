import os
import time

import websocket
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request

import common
import contract_registry_filter
import logging_conf
import scheduler
from common import AddressType
from database import database
from ethereum.provider import EthProvider
from events import event_registry_filter, events, node_registry
from key_store import node_key_store
from version import __version__


# Flask Setup ------------------------------------------------------------------
def init():
    database.flush_database()

    eth_provider = EthProvider(node_key_store)
    w3 = eth_provider.web3_provider()
    contract_registry_address = common.contract_registry_address()
    contract_registry_filter.init_contract_registry(w3, contract_registry_address)

    event_registry_abi = common.event_registry_contract_abi()
    verity_event_abi = common.verity_event_contract_abi()
    node_registry_abi = common.node_registry_contract_abi()

    node_registry_address = database.ContractAddress.node_registry()
    event_registry_address = database.ContractAddress.event_registry()

    node_ip_port = common.node_ip_port()
    node_websocket_ip_port = common.node_websocket_ip_port()

    node_registry.register_node_ip(w3, node_registry_abi, node_registry_address, node_ip_port,
                                   AddressType.IP)
    node_registry.register_node_ip(w3, node_registry_abi, node_registry_address,
                                   node_websocket_ip_port, AddressType.WEBSOCKET)
    scheduler.init(w3)
    websocket.init()

    event_registry_filter.init_event_registry_filter(scheduler.scheduler, w3, event_registry_abi,
                                                     verity_event_abi, event_registry_address)


def create_app():
    load_dotenv(dotenv_path='.env')

    project_root = os.path.dirname(os.path.realpath(__file__))
    os.environ['CONTRACT_DIR'] = os.path.join(project_root, 'contracts')

    app = Flask(__name__)
    logging_conf.init_logging()
    init()
    return app


application = create_app()
logger = application.logger


@application.before_request
def limit_remote_addr():
    # forbidden for a vietnamese bot
    blacklist = ['14.165.36.165', '104.199.227.129']

    if 'HTTP_X_FORWARDED_FOR' in request.environ and request.environ[
            'HTTP_X_FORWARDED_FOR'] in blacklist:
        logger.warning('Vietnamese bot detected!')
        abort(403)
    if request.environ['REMOTE_ADDR'] in blacklist:
        logger.warning('Vietnamese bot detected!')
        abort(403)


@application.after_request
def apply_headers(response):
    response.headers['Content-Type'] = 'application/json'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers[
        'Access-Control-Allow-Headers'] = 'Content-Type,X-Forwarded-For,HTTP_X_FORWARDED_FOR'
    response.headers['Access-Control-Allow-Methods'] = 'POST,GET'
    return response


# Routes -----------------------------------------------------------------------
@application.route('/health', methods=['GET'])
def health_check():
    w3 = EthProvider(node_key_store).web3_provider()
    response = {
        'version': __version__,
        'NODE_ADDRESS': common.node_id(),
        'CONTRACT_REGISTRY_ADDRESS': os.getenv('CONTRACT_REGISTRY_ADDRESS'),
        'EVENT_REGISTRY_ADDRESS': database.ContractAddress.event_registry(),
        'NODE_REGISTRY_ADDRESS': database.ContractAddress.node_registry(),
        'timestamp': int(time.time()),
        'block_number': w3.eth.blockNumber,
        'event_registry_last_run_timestamp': database.EventRegistry.last_run_timestamp(),
    }
    logger.debug('Health %s', response)
    return jsonify(response), 200


@application.route('/vote', methods=['POST'])
def vote():
    json_data = request.get_json()
    response = events.vote(json_data)
    return jsonify(response), response['status']


if __name__ == '__main__':
    application.run(debug=os.getenv('FLASK_DEBUG'))
