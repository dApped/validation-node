# -*- coding: utf-8 -*-
import sys
import json
import requests
import hashlib
import hmac
import time
import string
import random

import config

def random_string(size=11, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in list(range(size)))

def error_resp(code,id,message):
    result = {
        "error": {
            "code": code,
            "id": id,
            "message": message
        }
    }
    return result

def success_resp(code,id,message):
    result = {
        "data": {
            "code": code,
            "id": id,
            "message": message
        }
    }
    return result

def calculate_event_state(end_flag,time_to_join,start_time,end_time,reward_claimable):

    current_timestamp = int(time.time())

    if end_flag:
        state = 3
        if reward_claimable:
            state = 4
    else:
        if current_timestamp < start_time and current_timestamp < time_to_join:
            state = 0 # upcoming joinable
        elif current_timestamp < start_time and current_timestamp >= time_to_join:
            state = 1 # upcoming unjoinable
        elif current_timestamp >= start_time and current_timestamp < end_time:
            state = 2 # live
        else:
            state = 3 # done
            if reward_claimable:
                state = 4

    return state

def pad_hex(string,num_of_bytes,prefix=False):
    if prefix:
        return '0x' + string[2:].zfill(num_of_bytes*2)
    else:
        return string[2:].zfill(num_of_bytes*2)

def pad_hex_right(string, num_of_bytes, prefix=False):
    if prefix:
        return '0x' + string[2:].ljust(num_of_bytes*2, '0')
    else:
        return string[2:].ljust(num_of_bytes*2, '0')

def send_terminal_event(event_id, text):

    headers = {
        "Content-Type": "application/json",
    }

    # TODO Nejc: move this api key to env
    data = {
        "api_key": "***REMOVED***",
        "event": {
            "event_id": event_id,
            "text": text
        }
    }

    r = requests.post("https://socket.eventum.network/status", headers = headers, json = data)

def send_terminal_join_close(event_id, contract_address, start_time):
    print("SEND TERMINAL EVENT CALLED")

    message = "Time to join ended for event " + contract_address
    send_terminal_event(event_id, message)

    message = "Selecting nodes..."
    send_terminal_event(event_id, message)

    time.sleep(1)

    message = "Nodes selected: [5da6b2, 069b85, 317c77]"
    send_terminal_event(event_id, message)

    time.sleep(1)

    message = "Nodes synced and ready"
    send_terminal_event(event_id, message)

    message = "Waiting for event " + contract_address + " to start @ " + str(start_time)
    send_terminal_event(event_id, message)
