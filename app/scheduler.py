import os
import _thread
import hashlib
from datetime import datetime

import requests
from web3 import Web3, HTTPProvider

import common

from database import events
from events import events as ev

#initiate web3 lib and connect to RPC provider
provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))

def add_event_jobs(scheduler):
    events_data = events.get_events()
    if events_data[0] == "success":
        all_events = events_data[2]
        for event_id, event in all_events.items():

            event_id = event['event_id']
            event_name = event['title']
            event_ttj = event['time_to_join']
            event_end_time = event['end_time']
            event_start_time = event['start_time']
            event_end_flag = event["end_flag"]
            contract_address = event["contract_address"]
            event_ttj_utc_date = datetime.utcfromtimestamp(event_ttj)
            event_end_time_utc_date = datetime.utcfromtimestamp(event_end_time)
            event_start_time_utc_date = datetime.utcfromtimestamp(event_start_time)

            if event_end_flag == 0:

                #join closed jobs
                scheduler.add_job(socket_push, 'date', run_date=event_ttj_utc_date, args=[event_id,"ttj",False,contract_address,scheduler], id=str(event_id)+"_ttj", name=event_name+" ttj passed")

                #start event jobs
                scheduler.add_job(socket_push, 'date', run_date=event_start_time_utc_date, args=[event_id,"start"], id=str(event_id)+"_start", name=event_name+" started")

                #end event jobs
                scheduler.add_job(socket_push, 'date', run_date=event_end_time_utc_date, args=[event_id,"end"], id=str(event_id)+"_end", name=event_name+" ended")

def remove_all_jobs(scheduler):

    jobs = scheduler.get_jobs()
    for job in jobs:
        scheduler.remove_job(job.id)

def socket_push(event_id,event_type,consensus=False,contract=False,scheduler=False):

    event_data = {}

    if event_type == "ttj":
        url_endpoint = "/join_closed/"
        #get event data
        result = ev.get_events_data()
        if result["data"]["code"] == 200:
            for event in result["data"]["events"]:
                if event["event_id"] == event_id:
                    event_data = event

                    make_call_to_socket_server(url_endpoint,event_id,event_type,event_data)
                    contract_address = event_data["contract_address"]
                    start_time = event_data["start_time"]
                    _thread.start_new_thread(common.send_terminal_join_close, (event_id, contract_address, start_time))

        else:
            print("ttj event id: " + str(event_id) + " can not send socket push due to error in getting events data!")
            return

        #end join jobs
        job_id = contract+"_0"
        scheduler.remove_job(job_id)

    elif event_type == "start":
        url_endpoint = "/start_event/"
        #get event data
        result = ev.get_events_data()
        if result["data"]["code"] == 200:
            for event in result["data"]["events"]:
                if event["event_id"] == event_id:
                    event_data = event
                    contract_address = event_data["contract_address"]

                    common.send_terminal_event(event_id, "Event " + contract_address + " started")

                    make_call_to_socket_server(url_endpoint,event_id,event_type,event_data)
        else:
            print("start event id: " + str(event_id) + " can not send socket push due to error in getting events data!")
            return

    elif event_type == "end":
        url_endpoint = "/end_event/"

        if not consensus:
            # TODO change this (some events end prematurely)
            finish_event = events.end_event(event_id, False, None)
            if finish_event[0] != "success":
                print("end event id: " + str(event_id) + " can not send socket push due to DB error when trying to end the event!")
                return

        result = ev.get_events_data(stats=True)
        if result["data"]["code"] == 200:
            for event in result["data"]["events"]:
                if event["event_id"] == event_id:
                    event_data = event
                    event_hash = hashlib.md5(str(event_id)).hexdigest()
                    common.send_terminal_event(event_id, "Event ended for event " + event_hash)
                    make_call_to_socket_server(url_endpoint,event_id,event_type,event_data)
        else:
            print("end event id: " + str(event_id) + " can not send socket push due to error in getting events data!")
            return

    elif event_type == "full":
        url_endpoint = "/event_full/"
        result = ev.get_events_data(stats=True)
        if result["data"]["code"] == 200:
            for event in result["data"]["events"]:
                if event["event_id"] == event_id:
                    event_data = event
                    make_call_to_socket_server(url_endpoint,event_id,event_type,event_data)

        return

def make_call_to_socket_server(url_endpoint,event_id,event_type,event_data):

    data = {
        "api_key": os.getenv('WEBSOCKET_API_KEY'),
        "event": event_data
    }

    url = os.getenv('WEBSOCKET_SERVER_URL') + url_endpoint
    headers = {'content-type': 'application/json'}
    r = requests.post(url, json=data, headers=headers)

    if r.status_code == 200:
        print("Successfully called websocket server for " + event_type + " event: " + str(event_id))
    else:
        print("-- ERROR -- calling websocket server for " + event_type + " event: " + str(event_id))

def listen_for_contract_events(scheduler):

    event_info = events.get_events()
    if event_info[0] == "success":
        all_events = event_info[2]
        for event_id, event in all_events.items():

            contract_address = event["contract_address"]
            end_flag = event['end_flag']
            time_to_join = event['time_to_join']
            start_time = event['start_time']
            end_time = event['end_time']
            reward_claimable = event['reward_claimable']
            claim_topic = event['claim_topic']
            join_topic = event['join_topic']

            state = common.calculate_event_state(end_flag,time_to_join,start_time,end_time,reward_claimable)

            if state == 0 or state == 4:

                if state == 0:
                    topic_hash = join_topic
                elif state == 4:
                    topic_hash = claim_topic

                filter = web3.eth.filter({
                    "fromBlock": "earliest",
                    "toBlock": "latest",
                    "address": contract_address,
                    "topics": [topic_hash]
                })

                log_entries = web3.eth.getFilterLogs(filter.filter_id)

                participants = []

                for log in log_entries:
                    trx_hash = log['transactionHash']
                    trx = web3.eth.getTransaction(trx_hash)
                    participants.append(trx['from'])

                contract_users_from_db = events.get_event_users(contract_address)
                if contract_users_from_db[0] == "success":
                    participants_from_db = contract_users_from_db[2]

                    #find missing participants
                    missing_participants = list(set(participants)-set(participants_from_db))

                    if not missing_participants:
                        print("No new users presented in the contract: ",contract_address)

                    for participant in missing_participants:
                        if events.join_event(participant, contract_address)[0] == "success":
                            print("Added new user from contract ",contract_address," to the DB. User: ", participant)
                            check_event_spots(event_id)
                        #else:
                            #print "ERROR adding new user from contract ",contract_address," to the DB. User: ", participant

                else:
                    print("ERROR getting contract users from DB")

                #add job to listen for new participants in the contract
                scheduler.add_job(check_contract_event, 'interval', seconds=10, args=[filter.filter_id,contract_address,state], id=contract_address+"_"+str(state), name="Events for contract: "+contract_address+" in state: "+str(state))

            else:
                print("Contract ",contract_address," is not available for joining or claiming rewards - not setting new jobs!")

def check_contract_event(filter_id,contract_address,state):

    #TODO: check if filter is still running and if it is not start it again - is this neccessary with manual getFilterChanges poll?
    #print web3.eth.blockNumber
    new_log = web3.eth.getFilterChanges(filter_id)
    if new_log:

        for log in new_log:

            trx_hash = log['transactionHash']
            trx = web3.eth.getTransaction(trx_hash)
            participant = trx['from']

            print("Participant in the log: " + str(participant) + " for state: " + str(state))
            if state == 0:
                user_insert = events.join_event(participant, contract_address)
                if user_insert[0] == "success":
                    user_id = users.get_user(participant, "eth_address")[2]["user_id"]
                    user_hash = hashlib.md5(str(user_id)).hexdigest()
                    event_id = events.get_event_id(contract_address)
                    if event_id[0] == "success":
                        event_id = event_id[2]
                        common.send_terminal_event(event_id, "User " + user_hash + " joined the event")
                        check_event_spots(event_id)

                    print("New user detected for contract: ",contract_address," in state: ",state,"! Successfully added user: ",participant)

                else:
                    print("New user detected for contract: ",contract_address," in state: ",state,"! -- ERROR -- while inserting him to the DB")
            elif state == 4:
                user_claimed = events.set_reward_claimed(contract_address, participant)
                if user_claimed[0] == "success":
                    print("New user detected for contract: ",contract_address," in state: ",state,"! Reward is claimed by: ",participant)
                else:
                    print("New user detected for contract: ",contract_address," in state: ",state,"! -- ERROR -- while inserting him to the DB")
    else:
        pass
        #print "No new users detected in the smart contract: ",contract_address," for state: ",state

def check_event_spots(event_id):
    event_data = events.get_event_data(event_id)
    if event_data[0] == "success":
        event_data = event_data[2]
        max_users = event_data["max_users"]
        user_count = event_data["user_count"]

        if user_count >= max_users:
            socket_push(event_id, "full")

    return
