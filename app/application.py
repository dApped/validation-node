import json
import logging
import os
from datetime import datetime

from flask import Flask, abort, request

from events import events

logger = logging.getLogger('spam_application')
logger.setLevel(logging.DEBUG)

# ------------------------------------------------------------------------------
# Flask Setup ------------------------------------------------------------------

# EB looks for an 'application' callable by default.
application = Flask(__name__)

def startup():
    """
    At startup
    """
    print("Validation Node Starting...")
    all_events = events.get_all_events()
    my_events = events.get_my_events(all_events)
    print("Setting up finished")

startup()


@application.before_request
def limit_remote_addr():
    # forbidden for a vietnamese bot
    blacklist = ['14.165.36.165', '104.199.227.129']

    if "HTTP_X_FORWARDED_FOR" in request.environ and request.environ["HTTP_X_FORWARDED_FOR"] in blacklist:
        print("Vietnamese bot detected!")
        abort(403)
    if request.environ['REMOTE_ADDR'] in blacklist:
        print("Vietnamese bot detected!")
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
    print("Now: ", datetime.utcnow())
    return "Nothing to see here, verity dev", 200


@application.route('/events', methods=['GET'])
def get_events():
    my_events = ['abcde']
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
