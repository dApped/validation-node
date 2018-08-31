import sys
import json
import requests
import hashlib
import hmac
import time
import string
import random
import statistics

import config
import common
from database import events
import scheduler as sch
from ethereum import rewards, contract_deploy
from web3 import Web3, HTTPProvider, IPCProvider

provider = config.ETH_RPC_PROVIDER
web3 = Web3(HTTPProvider(provider))

# ------------------------------------------------------------------------------
# event data -------------------------------------------------------------------


def get_events_data(stats=False):
    '''
        Function that return ALL data of ALL events

        Parameters
        ------------
        stats : 'bool'
            If stats == True, event statistics will be added to the returning 'dict' (for events that are already ended)


        Returns
        ------------
        'dict'
            A dictionary structure of ALL events data
    '''

    events_data = events.get_events()

    current_timestamp = int(time.time())

    if events_data[0] == "success":

        all_events = events_data[2]

        for event_id in all_events:
            event = all_events[event_id]
            if event["end_flag"]:
                state = 3
                if event["reward_claimable"]:
                    state = 4
            else:
                if current_timestamp <= event["join_start"]:
                    state = -1  # upcoming unjoinable
                elif current_timestamp < event["start_time"] and current_timestamp < event["time_to_join"]:
                    state = 0  # upcoming joinable
                elif current_timestamp < event["start_time"] and current_timestamp >= event["time_to_join"]:
                    state = 1  # upcoming unjoinable
                elif current_timestamp >= event["start_time"] and current_timestamp < event["end_time"]:
                    state = 2  # live
                else:
                    state = 3  # done
                    if event["reward_claimable"]:
                        state = 4
            event["state"] = state

            if state >= 2:
                for input_method in event["input_methods"]:
                    input_method["validation"] = []
                    if input_method["required"]:
                        input_method["validation"].append("required")
                    if input_method["val_min"] != None:
                        input_method["validation"].append("min:" + str(input_method["val_min"]))
                    if input_method["val_max"] != None:
                        input_method["validation"].append("max:" + str(input_method["val_max"]))
                    if input_method["input_type"] != None:
                        input_method["validation"].append(input_method["input_type"])
                    input_method.pop("val_max", None)
                    input_method.pop("val_min", None)
                    input_method.pop("input_type", None)
                    input_method.pop("required", None)

            else:
                event.pop("input_methods", None)
                event.pop("resource", None)
                event.pop("fields", None)

        all_events = list(all_events.values())

        avg_event_ids = []
        for event in all_events:
            if event["avg_event"] == 1:
                avg_event_ids.append(event["event_id"])

        if stats:
            all_stats = events.get_saved_all_events_stats()
            answers = events.get_consensus_answers()
            avg_answers = events.get_avg_consensus_answers(avg_event_ids)

            if all_stats[0] == "success" and answers[0] == "success" and avg_answers[0] == "success":
                all_stats = all_stats[2]
                answers = answers[2]
                avg_answers = avg_answers[2]
            else:
                return common.error_resp(500, "db_error", "Unknown DB error")

            for event in all_events:
                event_id = event["event_id"]
                if event["state"] >= 3:
                    if event_id in all_stats:
                        event["graph_data"] = all_stats[event_id]
                        event["graph_data"]["majority"] = sum(event["graph_data"]["vote_data"])
                        event["graph_data"]["minority"] = sum(
                            event["graph_data"]["wrong_vote_data"])
                        event["graph_data"]["providers"] = sum(
                            event["graph_data"]["vote_data"]) + sum(event["graph_data"]["wrong_vote_data"])

                        if event_id not in answers:
                            answers[event_id] = ["None"]

                        if event["avg_event"]:
                            event_answers = list(map(float, avg_answers[event_id]))
                            event["graph_data"]["answer"] = [statistics.mean(event_answers)]
                        else:
                            event["graph_data"]["answer"] = answers[event_id]

                        event["graph_data"]["consensus_reached_in"] = event["graph_data"]["labels"][-1] - \
                            event["graph_data"]["labels"][0]
                    else:
                        event["graph_data"] = {}

        result = {
            "data": {
                "code": 200,
                "id": "events_info",
                "message": "Events info successfuly retrieved",
                "server_timestamp": int(time.time()),
                "events": all_events
            }
        }
        return result

    else:

        return common.error_resp(500, "db_error", "Unknown DB error")


def get_user_events_data(user_id):
    '''
        Function that returns a specific user's event data for all events (user's votes, positions, rewards)

        Parameters
        ------------
        user_id : 'int'
            User's id

        Returns
        ------------
        'dict'
            A dictionary with all user's events and user's votes, positions and rewards for those events
    '''

    all_user_events = events.get_user_events(user_id)
    participated_events = []
    if all_user_events[0] == "success":
        for event in all_user_events[2]:

            if "end_flag" in event and event["end_flag"] == False:
                event["user_in_consensus"] = None

            if "user_reward_ETH" in event or event["user_voted"]:
                participated_events.append(event["event_id"])

    if len(participated_events) > 0:
        votes = events.get_events_votes(participated_events)
        if votes[0] == "success":
            votes = votes[2]
            for event in all_user_events[2]:
                event_id = event["event_id"]
                if event["user_voted"]:
                    event["vote_position"] = votes[event_id].index(user_id) + 1
        else:
            return common.error_resp(500, "db_error", "Unknown DB error")

    return all_user_events

# ------------------------------------------------------------------------------
# voting & consensus -----------------------------------------------------------


def vote(data, auth_token, scheduler):
    '''
        Function that processes and stores user's vote for a specific event

        Parameters
        ------------
        data : 'dict'
            a dictionary containing user_id, event_id, answers and ip_address keys and coresponding values

        auth_token : 'str'
            user's auth token

        scheduler : 'scheduler'
            scheduler object

        Returns
        ------------
        'dict'
            A dictionary containing code 201, 400, or 500, coresponding message and user's submitted vote answers
    '''

    if "user_id" in data["data"]:
        user_id = data["data"]["user_id"]
    else:
        return common.error_resp(400, "json_error", "Could not find user_id field in the JSON")

    if "event_id" in data["data"]:
        event_id = data["data"]["event_id"]
    else:
        return common.error_resp(400, "json_error", "Could not find event_id field in the JSON")

    if "answers" in data["data"]:
        answer_ids = data["data"]["answers"]
    else:
        return common.error_resp(400, "json_error", "Could not find answer_ids field in the JSON")

    if "ip_address" in data["data"]:
        ip_address = data["data"]["ip_address"]
    else:
        ip_address = "None"

    user_joined = events.user_joined(user_id, event_id)
    if user_joined[0] != "success":
        return common.error_resp(500, "db_error", "Unknown DB error")
    elif user_joined[2] == False:
        return common.error_resp(400, "not_joined_error", "User is not joined on this event")

    all_data = events.get_event_data(event_id)
    if all_data[0] != "success":
        return common.error_resp(500, "db_error", "Unknown DB error")
    event_data = all_data[2]

    # if event is avg_event, all "field_value" values should be floats
    if event_data["avg_event"]:
        for answer in answer_ids:
            try:
                answer["field_value"] = float(answer["field_value"])
            except:
                print("Can't convert answer to float")
                return common.error_resp(400, "answer_not_float", "Please provide a numerical value!")

    min_consensus = event_data["min_consensus"]
    min_consensus_ratio = event_data["min_consensus_ratio"]
    min_consensus_percentage = event_data["min_consensus_percentage"]
    end_flag = event_data["end_flag"]
    start_time = event_data["start_time"]
    end_time = event_data["end_time"]
    current_timestamp = int(time.time())

    if min_consensus_ratio <= 0.5:
        return common.error_resp(500, "event_error", "Event parameters error")
    if end_time < current_timestamp:
        return common.error_resp(400, "event_end_error", "Event already ended")
    if end_flag:
        return common.success_resp(201, "vote_cast", "Vote cast, consensus reached beforehand, confirmation saved")
        if vote[0] == "duplicate":
            return common.error_resp(400, "already_voted_error", "User already voted on this event")
        elif vote[0] != "success":
            return common.error_resp(500, "db_error", "Unknown DB error")
        else:
            return common.success_resp(201, "vote_cast", "Vote cast, consensus reached beforehand, confirmation saved")
    if start_time > current_timestamp:
        return common.error_resp(400, "event_start_error", "Event not started")

    vote = events.vote_event(user_id, event_id, False, answer_ids, ip_address)
    user_hash = hashlib.md5(str(user_id)).hexdigest()
    if vote[0] == "duplicate":
        return common.error_resp(400, "already_voted_error", "User already voted on this event")
    elif vote[0] != "success":
        return common.error_resp(500, "db_error", "Unknown DB error")

    if event_data["avg_event"]:
        cons = check_avg_consensus(event_id, event_data, scheduler)
    else:
        cons = check_consensus(event_id, event_data, scheduler)

    if "vote_number" in cons:
        common.send_terminal_event(event_id, "Vote #" + str(
            cons["vote_number"]) + " ***REMOVED*** " + str(user_hash) + " @ " + str(current_timestamp) + ")")

    if cons["consensus_reached"]:
        message = "Vote cast, consensus reached"
        event_hash = hashlib.md5(str(event_id)).hexdigest()
        try:
            scheduler.remove_job(str(event_id) + "_end")
        except:
            print("scheduler error")
    else:
        message = "Vote cast, consensus not yet reached"

    result = {
        "data": {
            "code": 201,
            "id": "vote_cast",
            "message": message,
            "answers": answer_ids,
        }
    }
    return result


def check_consensus(event_id, event_data, scheduler):
    '''
        Function checks if the consensus is reached (or if it even can be)

        Parameters
        ------------
        event_id : 'int'
            event's id

        event_data: 'dict'
            dictionary containing all event's data

        scheduler : 'scheduler'
            scheduler object

        Returns
        ------------
        'dict'
            A dictionary containing key 'consensus_reached' key and coresponding value (depending on the consensus), key 'vote_number' representing number of votes (all together)
    '''

    # Check if there are enough votes to form a consensus

    vote_count = events.get_event_votes_count(event_id)
    if vote_count[0] == "success":
        vote_count = vote_count[2]
    else:
        return common.error_resp(500, "db_error", "Unknown DB error")

    if int(vote_count) < int(event_data["min_consensus"]):
        return {"consensus_reached": False, "vote_number": vote_count}

    # ---------------------------------------------------------------------------

    votes = events.get_event_votes(event_id)
    if votes[0] == "success":
        votes = votes[2]
    else:
        return common.error_resp(500, "db_error", "Unknown DB error")

    # how many people have to agree
    min_consensus = event_data["min_consensus"]
    # how many people of all those who voted have to agree
    min_consensus_ratio = event_data["min_consensus_ratio"]
    # how many people of all those who joined have to vote
    min_consensus_percentage = event_data["min_consensus_percentage"]
    end_flag = event_data["end_flag"]
    start_time = event_data["start_time"]
    end_time = event_data["end_time"]
    user_count = event_data["user_count"]
    stop_voting_delta = event_data["stop_voting_delta"]
    current_timestamp = int(time.time())

    voter_count = len(list(votes.keys()))

    answer_combinations = []
    combinations_count = []

    for voter in votes:
        answer = votes[voter]["answers"]

        if answer not in answer_combinations:
            answer_combinations.append(answer)
            combinations_count.append(1)
        else:
            idx = answer_combinations.index(answer)
            combinations_count[idx] += 1

    consensus = False
    in_consensus = []
    winners = []
    winner_ids = []
    outside_consensus = []
    losers_ids = []

    idx = 0
    for count in combinations_count:
        # min_consensus_percentage (how many users must agree),
        # min_consensus_ratio (how many voters must agree)
        if float(count)/user_count >= min_consensus_percentage and float(count)/voter_count >= min_consensus_ratio:
            consensus_vote = answer_combinations[idx]
            timestamps = []
            for voter in votes:
                answers = votes[voter]["answers"]
                if answers == consensus_vote:
                    timestamps.append(
                        votes[voter]["timestamp"] / 1000
                    )

            vote_median = statistics.mean(timestamps)
            stop_voting_timestamp = vote_median + stop_voting_delta

            valid_count = 0

            for voter in votes:
                answer = votes[voter]["answers"]
                if answer == consensus_vote and (votes[voter]["timestamp"]/1000) < stop_voting_timestamp:
                    valid_count += 1
                    in_consensus.append(voter)
                    winners.append({"user_id": voter, "timestamp": votes[voter]["timestamp"]})
                    winner_ids.append(voter)
                elif answer == consensus_vote:
                    outside_consensus.append(voter)
                    losers_ids.append(voter)

            if float(valid_count)/user_count >= min_consensus_percentage and float(valid_count)/voter_count >= min_consensus_ratio:
                consensus_time = int(time.time())
                consensus = True
            else:
                consensus_time = int(time.time())
                consensus = False
                events.end_event(event_id, True, consensus_time)

        idx += 1

    if consensus:
        events.update_vote_consensus(event_id, in_consensus)
        events.end_event(event_id, True, consensus_time)

        # set reputation
        all_event_users = events.get_event_user_ids(event_id)

        if all_event_users[0] == "success":
            all_event_users = all_event_users[2]
            event_users = []
            event_reps = []
            for event_user in all_event_users:
                event_users.append(event_user["user_id"])
                if event_user["voted"] and event_user["consensus"]:
                    event_reps.append(1)
                elif event_user["voted"]:
                    event_reps.append(-2)
                else:
                    event_reps.append(-1)
            print(usrs.update_reputation(event_users, event_reps))

        save_event_stats(event_id)
        assign_rewards(event_data, winners, scheduler)
        send_end_notification(event_id)

        return {"consensus_reached": True, "in_consensus": in_consensus, "outside_consensus": outside_consensus, "vote_number": voter_count}
    else:
        return {"consensus_reached": False, "vote_number": voter_count}


def check_avg_consensus(event_id, event_data, scheduler, forced=False):
    '''
        Function checks if the consensus is reached (or if it even can be) for experimental 'avg' events

        Parameters
        ------------
        event_id : 'int'
            event's id

        event_data: 'dict'
            dictionary containing all event's data

        scheduler : 'scheduler'
            scheduler object

        Returns
        ------------
        'dict'
            A dictionary containing key 'consensus_reached' key and coresponding value (depending on the consensus), key 'vote_number' representing number of votes (all together)
    '''

    vote_count = events.get_event_votes_count(event_id)
    if vote_count[0] == "success":
        vote_count = vote_count[2]
    else:
        return common.error_resp(500, "db_error", "Unknown DB error")

    if int(vote_count) < int(event_data["min_consensus"]) and forced == False:
        return {"consensus_reached": False, "vote_number": vote_count}

    # ---------------------------------------------------------------------------

    votes = events.get_event_votes(event_id)
    if votes[0] == "success":
        votes = votes[2]
    else:
        return common.error_resp(500, "db_error", "Unknown DB error")

    vote_values = {}
    vote_averages = {}
    vote_distances = {}
    vote_medians = {}
    vote_stdevs = {}

    for user_id in votes:
        vote = votes[user_id]
        answers = vote["answers"]
        for answer in answers:
            for field_id in answer:
                if field_id in vote_values:
                    vote_values[field_id].append(
                        float(answer[field_id])
                    )
                else:
                    vote_values[field_id] = [
                        float(answer[field_id])
                    ]

    for field_id in vote_values:
        vote_averages[field_id] = statistics.mean(vote_values[field_id])
        vote_medians[field_id] = statistics.median(vote_values[field_id])

    for user_id in votes:
        vote = votes[user_id]
        vote["distances"] = {}
        vote["user_id"] = user_id
        answers = vote["answers"]
        for answer in answers:
            for field_id in answer:
                vote_value = answer[field_id]
                vote_distance = abs(vote_medians[field_id] - float(vote_value))
                vote["distance"] = vote_distance

    sorted_votes = sorted(list(votes.values()), key=lambda k: (k["distance"], k["timestamp"]))

    number_of_votes = len(sorted_votes)
    winners_size = int(number_of_votes*(float(2)/3))

    sorted_winners = sorted_votes[0:winners_size]
    outside_consensus = sorted_votes[winners_size:]

    max_distance = sorted_winners[-1]["distance"]

    real_losers = []
    for loser in outside_consensus:
        if loser["distance"] <= max_distance:
            sorted_winners.append(loser)
        else:
            real_losers.append(loser)
    outside_consensus = real_losers

    in_consensus = []
    for winner in sorted_winners:
        winner_id = winner["user_id"]
        in_consensus.append(winner_id)

    consensus_time = int(time.time())

    events.update_vote_consensus(event_id, in_consensus)
    events.end_event(event_id, True, consensus_time)

    # set reputation
    all_event_users = events.get_event_user_ids(event_id)

    if all_event_users[0] == "success":
        all_event_users = all_event_users[2]
        event_users = []
        event_reps = []
        for event_user in all_event_users:
            event_users.append(event_user["user_id"])
            if event_user["voted"] and event_user["consensus"]:
                event_reps.append(1)
            elif event_user["voted"]:
                event_reps.append(-2)
            else:
                event_reps.append(-1)
        print(usrs.update_reputation(event_users, event_reps))

    save_event_stats(event_id)

    in_consensus = in_consensus[::-1]

    assign_rewards(event_data, in_consensus, scheduler, by_time=False)
    send_end_notification(event_id)

    return {"consensus_reached": True, "in_consensus": in_consensus, "outside_consensus": outside_consensus, "vote_number": vote_count}

# ------------------------------------------------------------------------------
# event END functions ----------------------------------------------------------


def assign_rewards(event_data, users, scheduler, by_time=True):
    '''
        Function that sets rewards

        Parameters
        ------------
        event_data: 'dict'
            dictionary containing all event's data

        users: 'list'
            a list containing dictionaries with keys 'user_id' and 'timestamp' (timestamp of the vote)

        scheduler: 'scheduler'
            scheduler object

        by_time: 'bool'
            if by_time is True, the rewards are distributed based on timestamp of the vote (faster - more)
            if its False, the rewards are distributed based on distance from the average vote

        Returns
        ------------
        True - if the rewards were distributed
        False - if the rewards were not distributed
    '''

    print("CALLED ASSIGN REWARDS WITH:", users, " AND BY_TIME:", by_time)

    rewards_ETH = []
    rewards_EVT = []
    user_ids = []

    if by_time:
        users = sorted(users, key=lambda user: user["timestamp"], reverse=True)
        for user in users:
            user_ids.append(user["user_id"])
    else:
        user_ids = users

    num_users = len(users)

    event_reward = int(event_data["reward_ETH"])
    event_reward_EVT = int(event_data["reward_EVT"])

    claim_topic = event_data["claim_topic"]

    reward_distribution = event_data["reward_distribution"]

    # new distribution code
    if reward_distribution != "linear":
        min_reward = 1.0
        rewards_list = []
        summ = 0
        factor = 8/float(num_users)
        for i in range(0, num_users):
            points = min_reward + 1/float(factor*i+1)
            rewards_list.append(points)

        last = rewards_list[-1]
        first = rewards_list[0] - last
        multi = 29/first

        for i in range(0, len(rewards_list)):
            rewards_list[i] = rewards_list[i] - last
            rewards_list[i] = (rewards_list[i] * multi) + 1

        summ = sum(rewards_list)

        rewards_list = rewards_list[::-1]

    if reward_distribution == "linear":
        rewards_list = []
        for i in range(0, num_users):
            rewards_list.append(1/float(num_users))
        summ = sum(rewards_list)

    for reward in rewards_list:
        part = reward/summ
        rewards_ETH.append(int(part * event_reward))
        rewards_EVT.append(int(part * event_reward_EVT))

    participants = usrs.get_eth_addresses(user_ids)

    if participants[0] == "success":

        events.set_rewards(event_data["id"], user_ids, rewards_ETH)
        events.set_EVT_rewards(event_data["id"], user_ids, rewards_EVT)

        participants = participants[2]
        sorted_participants = []
        for u_id in user_ids:
            sorted_participants.append(participants[u_id])

        wei_rewards = rewards_ETH
        contract_address = event_data["contract_address"]

        participants = [str(x) for x in sorted_participants]

        print("PARTICIPANTS", participants)
        print("REWARDS", wei_rewards, end=' ')
        print("CONTRACT_ADDRESS", contract_address)

        participants_batched = []
        wei_rewards_batched = []
        batch_size = config.BATCH_SIZE

        batch_idx = -1
        for i in range(0, len(participants)):
            if i % batch_size == 0:
                participants_batched.append([])
                wei_rewards_batched.append([])
                batch_idx += 1
            participants_batched[batch_idx].append(participants[i])
            wei_rewards_batched[batch_idx].append(wei_rewards[i])

        trx_batched = []

        developers_account = config.DEVELOPERS_ACCOUNT
        next_nonce = web3.eth.getTransactionCount(developers_account)

        for i in range(0, len(participants_batched)):
            trx_batched.append(
                rewards.set_rewards(
                    participants_batched[i], wei_rewards_batched[i], contract_address, next_nonce=next_nonce+i)
            )

        job_id = trx_batched[0] + "_" + contract_address

        event_id = event_data["id"]
        events_data = get_events_data()
        if "data" in events_data:
            events_data = events_data["data"]["events"]
            current_event = None
            for evt in events_data:
                if evt["event_id"] == event_id:
                    current_event = evt
                    scheduler.add_job(rewards.set_claimable_status_batched, 'interval', seconds=10, args=[
                                      trx_batched, contract_address, scheduler, job_id, claim_topic, event_id, current_event], id=job_id, name="Set rewards job: "+job_id)
            return True
        else:
            print("error getting events data")
            return False
    else:
        print("error setting rewards")
        return False


def send_end_notification(event_id):
    '''
        Function that sends end event notification (call to the socket server)

        Parameters
        ------------
        event_id: 'int'
            event's id

        Returns
        ------------
        True if the call was made
        False if something failed

    '''

    result = get_events_data(stats=True)
    if result["data"]["code"] == 200:
        for event in result["data"]["events"]:
            if event["event_id"] == event_id:
                event_data = event
                sch.make_call_to_socket_server("/end_event/", event_id, "end_event", event_data)
                return True
    return False


def save_event_stats(event_id):
    '''
        Function that stores event statistics (vote data for the chart) into the database

        Parameters
        ------------
        event_id: 'int'
            event's id

        Returns
        ------------
        True - if the statistics were stored successfuly
        False - if the storing failed

    '''

    event_stats = events.get_event_stats(event_id)
    event = events.get_event_data(event_id)

    if event_stats[0] == "success" and event[0] == "success":
        event_stats = event_stats[2]
        event = event[2]
    else:
        return common.error_resp(500, "db_error", "Unknown DB error")

    stats = event_stats

    if len(stats["votes"]) > 0:
        user_data = {}

        labels = []
        vote_data = []
        wrong_vote_data = []
        user_label_idx = 0
        user_correct = 0
        minority = 0
        majority = 0

        stats["votes"] = sorted(stats["votes"], key=lambda vote: vote["timestamp"])
        providers = len(stats["votes"])

        first_timestamp = stats["votes"][0]["timestamp"]
        last_timestamp = stats["votes"][-1]["timestamp"]
        step = (last_timestamp - first_timestamp)/10
        ts = first_timestamp

        for i in range(0, 11):
            labels.append(ts)
            vote_data.append(0)
            wrong_vote_data.append(0)
            ts += step

        answer = []

        for v in stats["votes"]:
            label_idx = 0
            timestamp = v["timestamp"]

            for label in labels:
                if timestamp - (step/2) >= label:
                    label_idx += 1

            if v["correct"] == 0:
                wrong_vote_data[label_idx] += 1
                minority += 1
            else:
                vote_data[label_idx] += 1
                if answer == []:
                    for field in v["vote"]:
                        answer.append(field["field_value"])
                majority += 1

            if "user" in v and v["user"]:
                user_label_idx = label_idx
                if v["correct"]:
                    user_correct = True

        readable_labels = []
        for label in labels:
            r_l = label - event["start_time"]*1000
            readable_labels.append(r_l)

        save_stats = []

        i = 0
        for label in readable_labels:

            stat = {
                "timestamp": label,
                "votes": vote_data[i],
                "wrong_votes": wrong_vote_data[i]
            }
            save_stats.append(stat)
            i += 1

        save = events.save_event_stats(save_stats, event_id)
        if save[0] == "success":
            return True
        else:
            return False

# ------------------------------------------------------------------------------
# experimental - DO NOT TOUCH --------------------------------------------------


def reload_jobs(data, scheduler):

    if "data" in data:

        if "key" not in data["data"]:
            return common.error_resp(400, "json_error", "Could not find key field in the JSON")

        if data["data"]["key"] != config.RELOAD_SCHEDULER_KEY:
            return common.error_resp(400, "json_error", "Wrong key")

        sch.remove_all_jobs(scheduler)
        sch.add_event_jobs(scheduler)
        sch.listen_for_contract_events(scheduler)
        print("Jobs reloaded successfuly")
        scheduler.print_jobs()

    return common.success_resp(201, "reload_jobs", "Jobs reloaded")


def kill_event(data, scheduler):

    if "data" in data:

        if "key" not in data["data"]:
            return common.error_resp(400, "json_error", "Could not find key field in the JSON")

        if data["data"]["key"] != config.KILL_EVENT_KEY:
            return common.error_resp(400, "json_error", "Wrong key")

        combinations = []
        combination_counts = []

        if "event_id" in data["data"]:

            event_id = data["data"]["event_id"]
            event_data = events.get_event_data(event_id)
            if event_data[0] == "success":
                event_data = event_data[2]
            else:
                return common.error_resp(500, "db_error", "Unknown DB error")

            avg_event = event_data["avg_event"]

            if avg_event:

                check_avg_consensus(event_id, event_data, scheduler, forced=True)
                return common.success_resp(201, "killing_event", "Killed event " + str(event_id))

            else:
                event_id = data["data"]["event_id"]
                votes = events.get_event_votes(event_id)
                if votes[0] == "success":
                    votes = votes[2]
                else:
                    return common.error_resp(500, "db_error", "Unknown DB error")

                for voter in votes:
                    answer = votes[voter]["answers"]

                    if answer in combinations:
                        combination_counts[combinations.index(answer)] += 1
                    else:
                        combinations.append(answer)
                        combination_counts.append(1)

                max_votes = 0
                winning_vote = None

                idx = 0
                for combo in combinations:
                    if combination_counts[idx] > max_votes:
                        max_votes = combination_counts[idx]
                        winning_vote = combo
                    idx += 1

                in_consensus = []
                outside_consensus = []
                winners = []
                winner_ids = []
                losers_ids = []
                valid_count = 0
                for voter in votes:
                    answer = votes[voter]["answers"]
                    if answer == winning_vote:
                        valid_count += 1
                        in_consensus.append(voter)
                        winners.append({"user_id": voter, "timestamp": votes[voter]["timestamp"]})
                        winner_ids.append(voter)
                    else:
                        outside_consensus.append(voter)
                        losers_ids.append(voter)

                consensus_time = int(time.time())
                events.update_vote_consensus(event_id, in_consensus)
                events.end_event(event_id, True, consensus_time)

                all_event_users = events.get_event_user_ids(event_id)
                all_data = events.get_event_data(event_id)
                event_data = all_data[2]

                if all_event_users[0] == "success":
                    all_event_users = all_event_users[2]
                    event_users = []
                    event_reps = []
                    for event_user in all_event_users:
                        event_users.append(event_user["user_id"])
                        if event_user["voted"] and event_user["consensus"]:
                            event_reps.append(1)
                        elif event_user["voted"]:
                            event_reps.append(-2)
                        else:
                            event_reps.append(-1)
                    print(usrs.update_reputation(event_users, event_reps))

                save_event_stats(event_id)
                assign_rewards(event_data, winners, scheduler)
                send_end_notification(event_id)

                return common.success_resp(201, "killing_event", "Killed event " + str(event_id))

        else:
            return common.error_resp(400, "json_error", "Could not find event_id field in the JSON")


def get_event_outcome(event_id):

    outcome = None
    event_data = events.get_event_data(event_id)
    event_score_data = events.get_score_event_data(event_id)
    event_consensus_answer = events.get_event_consensus_answer(event_id)

    if event_data[0] == "success" and event_score_data[0] == "success" and event_consensus_answer[0] == "success":
        event_data = event_data[2]
        event_score_data = event_score_data[2]
        event_consensus_answer = event_consensus_answer[2]

    if event_score_data != {} and event_data["consensus"] != 0:
        team_1_score_field_id = event_score_data["team_1_score_field_id"]
        team_2_score_field_id = event_score_data["team_2_score_field_id"]

        team_1_name = event_score_data["team_1_name"]
        team_2_name = event_score_data["team_2_name"]

        team_1_score = event_consensus_answer[team_1_score_field_id]
        team_2_score = event_consensus_answer[team_2_score_field_id]

        if team_1_score > team_2_score:
            outcome = team_1_name.lower()
        elif team_2_score > team_1_score:
            outcome = team_2_name.lower()
        else:
            outcome = "draw"

    result = {
        "data": {
            "code": 200,
            "id": "event_outcome",
            "message": "Event outcome successfuly retrieved",
            "outcome": outcome
        }
    }

    return result
