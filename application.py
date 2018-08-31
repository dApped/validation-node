import os
import sys
import json

import requests
import threading
from threading import Thread
import _thread, time
from _thread import start_new_thread
from datetime import datetime, timedelta

from flask import Flask,request,redirect,send_from_directory,render_template, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.util import get_ipaddr

from apscheduler.schedulers.background import BackgroundScheduler
import scheduler as sch

from pytz import utc

from config import *
from users import account
from events import events
from bounties import bounties
from kyc import kyc
import common

import logging
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
application.config["RATELIMIT_STORAGE_URL"] = '' # "redis://eventum-redis.muydls.0001.euc1.cache.amazonaws.com"


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
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Accept,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "POST,GET,OPTIONS,PUT,DELETE"
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
    return "Nothing to see here", 200

@application.route('/users', methods=['POST'])
#@limiter.limit("10/minute")
def users():
    json_data = request.get_json()

    #insert/signup new user
    result = account.signup(json_data)

    if "data" in result:

        if "HTTP_X_FORWARDED_FOR" in request.environ and request.environ["HTTP_X_FORWARDED_FOR"]:
            print("Account created from ip:", request.environ["HTTP_X_FORWARDED_FOR"])

        return json.dumps(result), result["data"]["code"]
    else:
        return json.dumps(result), result["error"]["code"]

@application.route('/reset', methods=['POST'])
def reset():
    json_data = request.get_json()

    result = account.recover_password(json_data)

    if "data" in result:
        return json.dumps(result), result["data"]["code"]
    else:
        return json.dumps(result), result["error"]["code"]

@application.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    json_data = request.get_json()
    headers = request.headers
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        #update existing user
        result = account.update_user(json_data,auth_token,user_id)
        if "data" in result:

            if "HTTP_X_FORWARDED_FOR" in request.environ and request.environ["HTTP_X_FORWARDED_FOR"]:
                print("Account updated from ip:", request.environ["HTTP_X_FORWARDED_FOR"])

            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
        return json.dumps(result), result["error"]["code"]

@application.route('/users/<int:user_id>', methods=['GET'])
def get_user_data(user_id):
    json_data = request.get_json()
    headers = request.headers

    include_bounties = False
    include_kyc = False
    include = request.args.get('include')
    if include == "bounties":
        include_bounties = True
    if include == "kyc":
        include_kyc = True

    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]
        result = account.get_user_data(json_data,auth_token,user_id, include_bounties=include_bounties, include_kyc=include_kyc)

        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource"+str(auth_header))
        return json.dumps(result), result["error"]["code"]

@application.route('/confirm_otk', methods=['POST'])
def confirm_otk():
    json_data = request.get_json()
    #headers = request.headers

    #confirm otk
    result = account.confirm_otk(json_data)
    if "data" in result:
        return json.dumps(result), result["data"]["code"]
    else:
        return json.dumps(result), result["error"]["code"]

@application.route('/login', methods=['POST'])
#@limiter.limit("50/minute")
def login_user():
    json_data = request.get_json()

    #login existing user
    result = account.login(json_data)
    if "data" in result:
        return json.dumps(result), result["data"]["code"]
    else:
        return json.dumps(result), result["error"]["code"]

@application.route('/events', methods=['GET'])
def get_events():
    include = request.args.get('include')
    statistics = False
    if include == "statistics":
        statistics = True
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
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        # check if json is right format and add ip addres to the json
        if "data" in json_data and "HTTP_X_FORWARDED_FOR" in request.environ:
            json_data["data"]["ip_address"] = request.environ["HTTP_X_FORWARDED_FOR"]

        result = events.vote(json_data, auth_token, scheduler)

        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
        return json.dumps(result), result["error"]["code"]

# ------------------------------------------------------------------------------
# bounties endpoints -----------------------------------------------------------

@application.route('/set_ref', methods=['POST'])
def set_ref():
    json_data = request.get_json()
    headers = request.headers
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        result = account.generate_ref(json_data, auth_token)
        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
        return json.dumps(result), result["error"]["code"]

@application.route('/join_bounty', methods=['POST'])
def join_bounty():
    json_data = request.get_json()
    headers = request.headers
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        result = bounties.join_bounty(json_data, auth_token)
        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
        return json.dumps(result), result["error"]["code"]

@application.route('/edit_bounty', methods=['POST'])
def edit_bounty():
    json_data = request.get_json()
    headers = request.headers
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        result = bounties.edit_bounty_username(json_data, auth_token)
        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
        return json.dumps(result), result["error"]["code"]

@application.route('/verify_bounty', methods=['POST'])
def verify_bounty():
    json_data = request.get_json()
    headers = request.headers
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        result = bounties.verify_bounty(json_data, auth_token)
        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
        return json.dumps(result), result["error"]["code"]

@application.route('/submit_bounty', methods=['POST'])
def submit_bounty():
    json_data = request.get_json()
    headers = request.headers
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        result = bounties.submit_bounty(json_data, auth_token)
        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
        return json.dumps(result), result["error"]["code"]

# ------------------------------------------------------------------------------
# kyc endpoints ----------------------------------------------------------------

@application.route('/join_kyc', methods=['POST'])
def join_kyc():
    json_data = request.get_json()
    headers = request.headers
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        result = kyc.join_kyc(json_data, auth_token)
        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
        return json.dumps(result), result["error"]["code"]

@application.route('/submit_kyc', methods=['POST'])
def submit_kyc():
    json_data = request.get_json()
    headers = request.headers
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        data = request.form.to_dict()

        if "id_type" in data:
            files = {
                "id_front": request.files["id_front"],
                "selfie": request.files["selfie"],
                "utility": request.files["utility"]
            }
            if data["id_type"] == "id":
                files["id_back"] = request.files["id_back"]


        for file_t in files:
            file = files[file_t]
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)

            if size > 10485760:
                result = common.error_resp(400,"file_too_big","Uploaded files are too big")
                return json.dumps(result), result["error"]["code"]
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                result = common.error_resp(400,"file_wrong_format", "Uploaded files are wrong format")
                return json.dumps(result), result["error"]["code"]

        result = kyc.submit_kyc(data, files, auth_token)
        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]

    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
        return json.dumps(result), result["error"]["code"]

@application.route('/request_kyc_window', methods=['POST'])
def request_kyc_window():

    json_data = request.get_json()
    headers = request.headers
    auth_header = headers.get("Authorization") or None
    if auth_header is not None:

        auth_token = auth_header.split()[1]

        result = kyc.request_kyc_window(json_data, auth_token)

        if "data" in result:
            return json.dumps(result), result["data"]["code"]
        else:
            return json.dumps(result), result["error"]["code"]
    else:
        result = common.error_resp(401,"Unauthorized","You need a valid authorization token to access this resource")
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

# ------------------------------------------------------------------------------
# private sale endpoints -------------------------------------------------------

@application.route('/private', methods=['GET'])
def private():

    code = request.args.get('code')
    result = account.get_private_sale_address(code)

    return json.dumps(result)

@application.route('/kyc_timer', methods=['GET'])
def kyc_timer():

    kyc_start = KYC_START - int(time.time())

    result = {
        "code": 200,
        "id": "kyc_start",
        "message": "KYC start successfuly retrieved",
        "kyc_start": kyc_start
    }

    return json.dumps(result)

@application.route('/ico_timer', methods=['GET'])
def ico_timer():

    ico_start = ICO_START - int(time.time())

    result = {
        "code": 200,
        "id": "ico_start",
        "message": "ICO start successfuly retrieved",
        "ico_start": ico_start
    }

    return json.dumps(result)

@application.route('/timers', methods=['GET'])
def timers():

    ico_start = ICO_START - int(time.time())
    kyc_start = KYC_START - int(time.time())
    kyc_form_start = KYC_FORM_START - int(time.time())


    result = {
        "code": 200,
        "id": "ico_start",
        "message": "ICO and KYC start successfuly retrieved",
        "ico_start": ico_start,
        "kyc_start": kyc_start,
        "kyc_form_start": kyc_form_start
    }

    return json.dumps(result)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# run the app.
if __name__ == "__main__":
    # TODO Roman: Change debug and reload argument
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    application.run(debug=True, use_reloader=True)
    #application.run()
