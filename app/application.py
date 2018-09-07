import json
import logging
import os
import redis
from datetime import datetime

from flask import Flask, abort, request
from web3 import HTTPProvider, Web3

from events import events

# ------------------------------------------------------------------------------
# Flask Setup ------------------------------------------------------------------

# EB looks for an 'application' callable by default.
application = Flask(__name__)

gunicorn_error_logger = logging.getLogger('gunicorn.error')
application.logger.handlers.extend(gunicorn_error_logger.handlers)
application.logger.setLevel(logging.DEBUG)
logger = application.logger

provider = os.getenv('ETH_RPC_PROVIDER')
logger.info(provider)
web3 = Web3(HTTPProvider(provider))

#r = redis.StrictRedis(host='redis', port=6379, db=0)
r = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)


def startup():
    """
    At startup
    """
    # Mock this nodes account
    #my_account = web3.eth.accounts[1]
    r.set('foo', 'bar')
    logger.debug("Validation Node Starting...")
    all_events = events.get_all_events()
    my_events = events.get_my_events(all_events)
    logger.debug("Setting up finished")


startup()


@application.before_request
def limit_remote_addr():
    # forbidden for a vietnamese bot
    blacklist = ['14.165.36.165', '104.199.227.129']

    if "HTTP_X_FORWARDED_FOR" in request.environ and request.environ["HTTP_X_FORWARDED_FOR"] in blacklist:
        logger.debug("Vietnamese bot detected!")
        abort(403)
    if request.environ['REMOTE_ADDR'] in blacklist:
        logger.debug("Vietnamese bot detected!")
        abort(403)


@application.after_request
def apply_headers(response):
    response.headers["Content-Type"] = "application/json"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers[
        "Access-Control-Allow-Headers"] = "Content-Type,Accept,Authorization"
    response.headers[
        "Access-Control-Allow-Methods"] = "POST,GET,OPTIONS,PUT,DELETE"
    return response

# @limiter.request_filter
# TODO check why this is here
def ip_whitelist():
    return request.remote_addr == os.getenv('IP_WHITELIST')


# ------------------------------------------------------------------------------
# Routes -----------------------------------------------------------------------


@application.route('/', methods=['GET'])
# @limiter.limit("10/minute")
def hello():
    application.logger.debug("Root resource requested" +str(datetime.utcnow()))
    logger.debug('Logger is up')
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
    if "data" in json_data and "HTTP_X_FORWARDED_FOR" in request.environ:
        json_data["data"]["ip_address"] = request.environ["HTTP_X_FORWARDED_FOR"]

    result = events.vote(json_data)

    if "data" in result:
        return json.dumps(result), result["data"]["code"]
    return json.dumps(result), result["error"]["code"]


# run the app.
if __name__ == "__main__":
    application.run(debug=os.getenv('FLASK_DEBUG'))
