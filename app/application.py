import logging
import os
from datetime import datetime

from flask import Flask, abort, jsonify, request

import common
import scheduler
from database import database
from ethereum.provider import NODE_WEB3
from events import event_registry_filter, events

project_root = os.path.dirname(os.path.realpath(__file__))
os.environ['DATA_DIR'] = os.path.join(project_root, 'data')

# ------------------------------------------------------------------------------
# Flask Setup ------------------------------------------------------------------

# EB looks for an 'application' callable by default.
application = Flask(__name__)
logger = application.logger
logging.getLogger().setLevel(logging.INFO)


def init():
    logger.info('Validation Node Init started')
    database.flush_database()
    event_registry_abi = common.event_registry_contract_abi()
    verity_event_abi = common.verity_event_contract_abi()
    event_registry_address = common.event_registry_address()
    event_registry_filter.init_event_registry_filter(NODE_WEB3, event_registry_abi,
                                                     verity_event_abi, event_registry_address)
    scheduler.init()
    logger.info('Validation Node Init done')


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


init()  # if init in main it does not get executed by gunicorn
if __name__ == '__main__':
    application.run(debug=os.getenv('FLASK_DEBUG'))
