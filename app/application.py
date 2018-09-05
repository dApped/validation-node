import json
import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, abort, request
from pytz import utc

import scheduler as sch
from events import events

logging.basicConfig()

# ------------------------------------------------------------------------------
# apscheduler ------------------------------------------------------------------

scheduler = BackgroundScheduler(timezone=utc)
try:
    scheduler.start()
    sch.add_event_jobs(scheduler)
    sch.listen_for_contract_events(scheduler)
except:
    print("Scheduler error")

# ------------------------------------------------------------------------------
# flask setup ------------------------------------------------------------------

# EB looks for an 'application' callable by default.
application = Flask(__name__)


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


# ------------------------------------------------------------------------------
# flask limiter ----------------------------------------------------------------

#limiter = Limiter(
#    application,
#    key_func=get_ipaddr,
#    default_limits=["200/hour", "60/minute"]
#)


#@limiter.request_filter
def ip_whitelist():
    #pass
    return request.remote_addr == "89.212.5.47"


# ------------------------------------------------------------------------------
# routes -----------------------------------------------------------------------


@application.route('/', methods=['GET'])
#@limiter.limit("10/minute")
def hello():
    scheduler.print_jobs()
    print("Now: ", datetime.utcnow())
    return "Nothing to see here, verity dev", 200


@application.route('/events', methods=['GET'])
def get_events():
    include = request.args.get('include')
    statistics = include == "statistics"

    result = events.get_events_data(stats=statistics)

    if "data" in result:
        return json.dumps(result), result["data"]["code"]
    else:
        return json.dumps(result), result["error"]["code"]


@application.route('/events/<int:event_id>', methods=['GET'])
def get_event_outcome(event_id):
    result = events.get_event_outcome(event_id)

    if "data" in result:
        return json.dumps(result), result["data"]["code"]
    else:
        return json.dumps(result), result["error"]["code"]


@application.route('/vote', methods=['POST'])
def vote():
    json_data = request.get_json()
    headers = request.headers

    # check if json is right format and add ip addres to the json
    if "data" in json_data and "HTTP_X_FORWARDED_FOR" in request.environ:
        json_data["data"]["ip_address"] = request.environ["HTTP_X_FORWARDED_FOR"]

    result = events.vote(json_data, None, scheduler)

    if "data" in result:
        return json.dumps(result), result["data"]["code"]
    return json.dumps(result), result["error"]["code"]


# ------------------------------------------------------------------------------
# DEV endpoints ----------------------------------------------------------------
@application.route('/kill_event', methods=['POST'])
def kill_event():
    json_data = request.get_json()
    headers = request.headers

    result = events.kill_event(json_data, scheduler)

    if "data" in result:
        return json.dumps(result), result["data"]["code"]
    else:
        return json.dumps(result), result["error"]["code"]


@application.route('/reload_jobs', methods=['POST'])
def reload_jobs():
    json_data = request.get_json()
    headers = request.headers

    result = events.reload_jobs(json_data, scheduler)

    if "data" in result:
        return json.dumps(result), result["data"]["code"]
    else:
        return json.dumps(result), result["error"]["code"]


# run the app.
if __name__ == "__main__":
    application.run(debug=os.getenv('FLASK_DEBUG'))
