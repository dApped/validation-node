import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request

import common
import scheduler
from database import database
from ethereum.provider import NODE_WEB3
from events import event_registry_filter, events, node_registry

# ------------------------------------------------------------------------------
# Flask Setup ------------------------------------------------------------------


def init():
    database.flush_database()
    event_registry_abi = common.event_registry_contract_abi()
    verity_event_abi = common.verity_event_contract_abi()
    node_registry_abi = common.node_registry_contract_abi()

    node_address = common.node_registry_address()
    event_registry_address = common.event_registry_address()

    node_ip = common.public_ip()

    node_registry.register_node_ip(node_registry_abi, node_address, node_ip)
    event_registry_filter.init_event_registry_filter(NODE_WEB3, event_registry_abi,
                                                     verity_event_abi, event_registry_address)
    scheduler.init()


def create_app():
    load_dotenv(dotenv_path='.env')

    project_root = os.path.dirname(os.path.realpath(__file__))
    os.environ['DATA_DIR'] = os.path.join(project_root, 'data')

    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)

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
        logger.debug('Vietnamese bot detected!')
        abort(403)
    if request.environ['REMOTE_ADDR'] in blacklist:
        logger.debug('Vietnamese bot detected!')
        abort(403)


@application.after_request
def apply_headers(response):
    response.headers['Content-Type'] = 'application/json'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Accept,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'POST,GET,OPTIONS,PUT,DELETE'
    return response


# TODO check why this is here
def ip_whitelist():
    return request.remote_addr == os.getenv('IP_WHITELIST')


# ------------------------------------------------------------------------------
# Routes -----------------------------------------------------------------------


@application.route('/', methods=['GET'])
def hello():
    application.logger.debug('Root resource requested' + str(datetime.utcnow()))
    return "Nothing to see here, verity dev", 200


@application.route('/vote', methods=['POST'])
def vote():
    json_data = request.get_json()
    headers = request.headers
    ip_address = request.environ.get('HTTP_X_FORWARDED_FOR')
    response = events.vote(json_data, ip_address)
    return jsonify(response), response['status']


@application.route('/receive_vote', methods=['POST'])
def receive_vote():
    # TODO replace this with websocket
    json_data = request.get_json()
    headers = request.headers

    if 'vote' not in json_data:
        return "Invalid request message", 400
    vote_json = json_data['vote']
    response = events.receive_vote(vote_json)
    return jsonify(response), 200


if __name__ == '__main__':
    application.run(debug=os.getenv('FLASK_DEBUG'))
