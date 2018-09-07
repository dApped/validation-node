import json
import logging
import os
from datetime import datetime

import redis
from flask import Flask, abort, request

from events import events

# ------------------------------------------------------------------------------
# Flask Setup ------------------------------------------------------------------

# EB looks for an 'application' callable by default.
application = Flask(__name__)

gunicorn_error_logger = logging.getLogger('gunicorn.error')
application.logger.handlers.extend(gunicorn_error_logger.handlers)
application.logger.setLevel(logging.DEBUG)
logger = application.logger

#r = redis.StrictRedis(host='redis', port=6379, db=0)
r = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)


def init():
    logger.info('Validation Node Init started')

    r.set('foo', 'bar')

    all_events = events.all_events_addresses()
    logger.info('All event addresses %s', all_events)

    node_events = events.filter_node_events(all_events)
    logger.info('Node event addresses %s', node_events)

    logger.info('Validation Node Init done')


@application.before_request
def limit_remote_addr():
    # forbidden for a vietnamese bot
    blacklist = ['14.165.36.165', '104.199.227.129']

    if 'HTTP_X_FORWARDED_FOR' in request.environ and request.environ['HTTP_X_FORWARDED_FOR'] in blacklist:
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
    logger.info(r.get('foo'))
    return "Nothing to see here, verity dev", 200


@application.route('/events', methods=['GET'])
def get_events():
    my_events = ['0xee19f1d6dbc27cf4e68952e41873b4f84ce0ca58']
    return json.dumps(my_events), 200


@application.route('/vote', methods=['POST'])
def vote():
    json_data = request.get_json()
    headers = request.headers

    # check if json is right format and add ip addres to the json
    if 'data' in json_data and 'HTTP_X_FORWARDED_FOR' in request.environ:
        json_data['data']['ip_address'] = request.environ['HTTP_X_FORWARDED_FOR']

    result = events.vote(json_data)

    if 'data' in result:
        return json.dumps(result), result['data']['code']
    return json.dumps(result), result['error']['code']


# run the app.
if __name__ == '__main__':
    init()
    application.run(debug=os.getenv('FLASK_DEBUG'))
