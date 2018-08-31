# -*- coding: utf-8 -*-
from database import events, users
import time
import os
import common
import hashlib
import json
import requests
import _thread
from ethereum import contract_deploy
import datetime

import sys
import warnings

CEND      = '\33[0m'
CBOLD     = '\33[1m'
CITALIC   = '\33[3m'
CURL      = '\33[4m'
CBLINK    = '\33[5m'
CBLINK2   = '\33[6m'
CSELECTED = '\33[7m'

CBLACK  = '\33[30m'
CRED    = '\33[31m'
CGREEN  = '\33[32m'
CYELLOW = '\33[33m'
CBLUE   = '\33[34m'
CVIOLET = '\33[35m'
CBEIGE  = '\33[36m'
CWHITE  = '\33[37m'


if not sys.warnoptions:
    warnings.simplefilter("ignore")

def specific_contract_constructor_abi(ttj_start, ttj_end):

    abi_encoded = common.pad_hex(hex(ttj_start),32) + common.pad_hex(hex(ttj_end),32)

    return abi_encoded, ttj_start, ttj_end

def create_event(event_data):

    event_id = event_data["event_id"]
    image = event_data["image"]
    name = event_data["name"]
    subject = event_data["subject"]
    description = event_data["description"]
    category_id = event_data["category_id"]
    resource = event_data["resource"]
    resource_type = event_data["resource_type"]
    contract_address = event_data["contract_address"]
    max_users = event_data["max_users"]
    min_consensus = event_data["min_consensus"]

    join_start = event_data["join_start"]
    time_to_join = event_data["time_to_join"]
    start_time = event_data["start_time"]
    end_time = event_data["end_time"]
    reward_ETH = event_data["reward_ETH"]
    reward_EVT = event_data["reward_EVT"]

    fields = event_data["fields"]

    avg_event = event_data["avg_event"]

    reward_distribution = event_data["reward_distribution"]

    field_ids = []

    event = events.create_event(event_id, image, name, subject, description, category_id, resource, resource_type, contract_address, max_users, min_consensus, join_start, time_to_join, start_time, end_time, reward_ETH, reward_EVT, avg_event, reward_distribution)
    if event[0] == "success":
        event_id = event[2]

        field = "field 1"
        validation_required = None
        val_max = None
        val_min = None
        validation_type = None

        for field in fields:
            field_name = field["name"]
            field_type = field["type"]
            answers = field["answers"]
            validation_type = field["validation_type"]
            validation_required = field["validation_required"]

            fld = events.create_event_field(event_id, field_name, field_type, validation_required, val_max, val_min, validation_type)
            field_id = fld[2]
            field_ids.append(field_id)

            for answer in answers:
                ans = events.create_field_answer(event_id, field_id, answer, answer)

        return (event_id, field_ids)

def create_event_contract(event_data):

    event_id = event_data["event_id"]
    chk = events.get_event_data(event_id)[2]["id"]
    if chk != None:
        print("ERROR: Event %s already exists" % event_id)
        return (None, None)

    ttj_start = event_data["join_start"]
    ttj_end = event_data["time_to_join"]

    abi, ttj_start, ttj_end = specific_contract_constructor_abi(ttj_start, ttj_end)
    event_id, field_ids = create_event(event_data)

    if event_id:
        print("------------------------------------------")
        print("Event successfuly created")
        event_bytecode_data = open("ethereum/event_bytecode.json", "r").read()
        bytecode = json.loads(event_bytecode_data)["object"]
        data = bytecode + abi
        contract_address = contract_deploy.deploy_event_contract(data)
        events.add_contract_address_to_event(event_id, contract_address)
        contract_funds_txid = contract_deploy.send_eth(contract_address, event_data["reward_ETH"])

    print("------------------------------------------")
    print("EVENT AND CONTRACT CREATION SUCCESSFUL")
    print("Reward funds sent to contract")
    print("https://ropsten.etherscan.io/tx/%s" % contract_funds_txid)

    return (event_id, field_ids)

def check_fields(event_id):
    all_events = events.get_events()
    if all_events[0] == "success":
        all_events = all_events[2]
        if event_id not in all_events:
            return "Error getting event", str(event_id)
    else:
        return "Error getting events"

    fields = all_events[event_id]["fields"]
    input_methods = all_events[event_id]["input_methods"]

    for field in fields:
        field_id = field["field_id"]
        print(field["label"])
        #print field["type"]
        for input_method in input_methods:
            if input_method["field_id"] == field_id:
                print(input_method["type"])
                if "values" in input_method:
                    for value in input_method["values"]:
                        print(" - ", value)

def check_event(event_id):

    event_data = events.get_event_data(event_id)
    event_score_data = events.get_score_event_data(event_id)
    event_fields = events.get_event_data

    if event_data[0] == "success" and event_score_data[0] == "success":
        event_data = event_data[2]
        event_score_data = event_score_data[2]
    else:
        return "Event %s - ERROR: Event could not be loaded" % event_id

    join_start = event_data["join_start"]
    time_to_join = event_data["time_to_join"]
    start_time = event_data["start_time"]
    end_time = event_data["end_time"]

    if join_start >= time_to_join or time_to_join >= start_time or start_time >= end_time:
        return "Event %s - ERROR: Event times are overlaping" % event_id

    contract_address = event_data["contract_address"]
    if contract_address == "":
        return "Event %s - ERROR: Event has no contract address" % event_id

    application_times = contract_deploy.get_contract_application_times(contract_address)

    if application_times["applicationStartTime"] != join_start:
        return "Event %s - ERROR: Join start time not equal to contract applicationStartTime" % event_id

    if application_times["applicationEndTime"] != time_to_join:
        return "Event %s - ERROR: Join end time not equal to contract applicationEndTime" % event_id

    if event_data["end_flag"] == 0:
        balance = contract_deploy.get_contract_balance(contract_address)
        if int(balance) < int(event_data["reward_ETH"]):
            return "Event %s - ERROR: contract balance too low: %s" % (event_id, contract_address)

    score_event = False
    if event_score_data != {}:
        event_fields = events.get_event_fields(event_id)
        if event_fields[0] != "success":
            return "Event %s - ERROR: Couln't load event fields" % event_id
        event_fields = event_fields[2]

        score_event = True

        team_1_score_field_id = str(event_score_data["team_1_score_field_id"])
        team_2_score_field_id = str(event_score_data["team_2_score_field_id"])

        team_1_name = event_score_data["team_1_name"]
        team_2_name = event_score_data["team_2_name"]

        if team_1_name != event_fields[int(team_1_score_field_id)]["field"] or team_2_name != event_fields[int(team_2_score_field_id)]["field"]:
            return "Event %s - ERROR: Event fields names do not match score_event field names" % event_id

        score_fields = "%s (field %s) VS %s (field %s)" % (team_1_name, team_1_score_field_id, team_2_name, team_2_score_field_id)

    if score_event:
        return "Event " + str(event_id) + " ✓ \n    " + str(score_fields)
    return "Event " + str(event_id) + " ✓"

def check_all_events(only_upcoming=True, participants=False):

    print("CHECKING EVENTS")

    all_events = events.get_events()
    if all_events[0] == "success":
        all_events = all_events[2]
    else:
        print("ERROR: could not load events")

    if only_upcoming:
        event_ids = []
        for event_id in all_events:
            if all_events[event_id]["end_flag"] == 0:
                event_ids.append(event_id)
    else:
        event_ids = list(all_events.keys())

    event_ids.sort()
    for event_id in event_ids:
        print(check_event(event_id))

        if participants:
            missing = check_participants(event_id)
            if len(missing) > 0:
                print("ERROR: participants missing")
                print(missing)

def check_participants(event_id):
    event_data = events.get_event_data(event_id)

    if event_data[0] == "success":
        event_data = event_data[2]
    else:
        return "Event %s - ERROR: Event could not be loaded" % event_id

    url = "http://api-ropsten.etherscan.io/api?module=account&action=txlist&address=%s&startblock=0&endblock=99999999&sort=asc&apikey=YourApiKeyToken" % event_data["contract_address"]

    r = requests.get(url)
    content = json.loads(r.content)
    joined_users_addresses = []
    for trx in content["result"]:
        if trx["input"] == "0xf9010d19": # TODO Roman what is this?
            joined_users_addresses.append(trx["from"])

    not_in_db = []
    for joined_user_address in joined_users_addresses:
        user = users.get_user(joined_user_address, "eth_address")
        #print joined_user_address
        if user[0] == "success":
            user = user[2]
            user_id = user["user_id"]
            user_joined = events.user_joined(user_id, event_id)
            if user_joined[0] == "success":
                user_joined = user_joined[2]
                if not user_joined:
                    not_in_db.append(user)
    if len(not_in_db) == 0:
        print("Participants check out")
    return not_in_db

def check_user_input(inpt):
    try:
        inpt = int(inpt)
        return inpt
    except:
        return None

def reload_jobs():
    print("Reloading jobs")

    url = "http://api.eventum.network/reload_jobs"
    payload = "{\n\t\"data\":{\n\t\t\"key\": \"***REMOVED***\"\n\t}\n}"
    headers = {
        'content-type': "application/json",
        'cache-control': "no-cache",
        }
    response = requests.request("POST", url, data=payload, headers=headers)
    print(response.text)

def select_option():
    print("1) Check upcoming events")
    print("2) Check participants")
    print("3) Create a new event (from new_event.json)")
    print("4) Reload scheduler")

    inpt = input("Select and option to perform: ")
    inpt = check_user_input(inpt)
    if inpt == None:
        print("ERROR: Not an integer")
        return ""

    if inpt not in [1,2,3,4]:
        print("ERROR: Not an integer")
        return ""
    else:
        if inpt == 1:
            check_all_events()
            return ""

        elif inpt == 2:
            event_id = input("Type in the event's id: ")
            event_id = check_user_input(event_id)
            if event_id == None:
                print("ERROR: Not an integer")
                return ""
            check_participants(event_id)

        elif inpt == 3:
            event_data = open("new_event.json", "r").read()
            event_data = json.loads(event_data)
            create_event_contract(event_data)

        elif inpt == 4:
            reload_jobs()

print(CBLUE + "___________                    __                  ________                ___________           .__          ")
print("\\_   _____/__  __ ____   _____/  |_ __ __  _____   \\______ \\   _______  __ \\__    ___/___   ____ |  |   ______")
print(" |    __)_\\  \\/ // __ \\ /    \\   __\\  |  \\/     \\   |    |  \\_/ __ \\  \\/ /   |    | /  _ \\ /  _ \\|  |  /  ___/")
print(" |        \\\\   /\\  ___/|   |  \\  | |  |  /  Y Y  \\  |    `   \\  ___/\\   /    |    |(  <_> |  <_> )  |__\\___ \\ ")
print("/_______  / \\_/  \\___  >___|  /__| |____/|__|_|  / /_______  /\\___  >\\_/     |____| \\____/ \\____/|____/____  >")
print("        \\/           \\/     \\/                 \\/          \\/     \\/                                       \\/ " + CEND)
print("")
print(CBEIGE + "By Luka Perović -----------------------------------------------------------------------------------------------" + CEND)
print("")

select_option()
