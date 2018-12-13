import os
import time

import websocket
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request

import common
import logging_conf
import scheduler
from common import AddressType
from database import database
from ethereum.provider import NODE_WEB3
from events import event_registry_filter, events, node_registry
from version import __version__


# Flask Setup ------------------------------------------------------------------
def init():
    database.flush_database()
    event_registry_abi = common.event_registry_contract_abi()
    verity_event_abi = common.verity_event_contract_abi()
    node_registry_abi = common.node_registry_contract_abi()

    node_address = common.node_registry_address()
    event_registry_address = common.event_registry_address()

    node_ip_port = common.node_ip_port()
    node_websocket_ip_port = common.node_websocket_ip_port()

    node_registry.register_node_ip(node_registry_abi, node_address, node_ip_port, AddressType.IP)
    node_registry.register_node_ip(node_registry_abi, node_address, node_websocket_ip_port,
                                   AddressType.WEBSOCKET)
    event_registry_filter.init_event_registry_filter(NODE_WEB3, event_registry_abi,
                                                     verity_event_abi, event_registry_address)
    scheduler.init()
    websocket.init()


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
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST,GET,OPTIONS,PUT,DELETE'
    return response


# Routes -----------------------------------------------------------------------
@application.route('/health', methods=['GET'])
def health_check():
    response = {
        'version': __version__,
        'NODE_ADDRESS': os.getenv('NODE_ADDRESS'),
        'EVENT_REGISTRY_ADDRESS': os.getenv('EVENT_REGISTRY_ADDRESS'),
        'NODE_REGISTRY_ADDRESS': os.getenv('NODE_REGISTRY_ADDRESS'),
        'timestamp': int(time.time()),
        'block_number': NODE_WEB3.eth.blockNumber,
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
