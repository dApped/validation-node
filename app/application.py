import functools
import os
from datetime import datetime

from flask import Flask, abort, jsonify, request

import common
import scheduler
from database import database
from events import events

project_root = os.path.dirname(os.path.realpath(__file__))
os.environ['DATA_DIR'] = os.path.join(project_root, 'data')

# ------------------------------------------------------------------------------
# Flask Setup ------------------------------------------------------------------

# EB looks for an 'application' callable by default.
application = Flask(__name__)
logger = application.logger


def init():
    logger.info('Validation Node Init started')

    database.flush_database()
    scheduler.init()

    event_ids = events.call_event_contract_for_event_ids()
    logger.info('Event ids %s', event_ids)

    node_id = events.read_node_id()
    contract_abi = common.verity_event_contract_abi()
    for event_id in event_ids:
        events.init_event(contract_abi, node_id, event_id)

    logger.info('Validation Node Init done')


def return_json(resp):
    @functools.wraps(resp)
    def wrapped_resp(**values):
        return jsonify(resp(**values))

    return wrapped_resp


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


# @limiter.request_filter
# TODO check why this is here
def ip_whitelist():
    return request.remote_addr == os.getenv('IP_WHITELIST')


# ------------------------------------------------------------------------------
# Routes -----------------------------------------------------------------------


@application.route('/', methods=['GET'])
# @limiter.limit('10/minute')
def hello():
    application.logger.debug('Root resource requested' + str(datetime.utcnow()))
    return "Nothing to see here, verity dev", 200


@application.route('/events', methods=['GET'])
@return_json
def get_events():
    logger.info('GET /events')
    return events.get_all()


@application.route('/vote', methods=['POST'])
@return_json
def vote():
    json_data = request.get_json()
    headers = request.headers

    # check if json is right format and add ip addres to the json
    if 'data' in json_data and 'HTTP_X_FORWARDED_FOR' in request.environ:
        json_data['data']['ip_address'] = request.environ['HTTP_X_FORWARDED_FOR']
    result = events.vote(json_data['data'])
    return result


# run the app.
# if init in main it does not get executed by gunicorn
init()
if __name__ == '__main__':
    application.run(debug=os.getenv('FLASK_DEBUG'))
