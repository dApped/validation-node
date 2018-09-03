import sqlite3
import time

from . import connection

# ------------------------------------------------------------------------------
# event data -------------------------------------------------------------------


def get_events():
    '''
        Info:
            Function that returns all event data for all events
    '''

    cnx = cur = None
    events = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT events.id,events.name,events.image,events.resource,events.resource_type,min_reputation,events.max_users,contract_address,reward_ETH,reward_EVT,reward_claimable,join_start,time_to_join,start_time,end_time,events.subject,events.end_flag,events.description,event_fields.id,event_fields.field,event_fields.type,
        event_fields.validation_required,event_fields.max, event_fields.min, event_fields.validation_type,event_answers.label,event_answers.value,events.join_topic, events.claim_topic,categories.name,categories.image,categories.description,rules,events.avg_event,events.hidden, c.count FROM events
                                JOIN event_fields ON event_fields.event_id = events.id
                                JOIN categories ON categories.id = events.category_id
                                LEFT JOIN (SELECT event_id, COUNT(*) as count FROM event_users GROUP BY event_id) as c ON events.id = c.event_id
                                LEFT JOIN event_answers ON event_fields.id = event_answers.field_id AND event_answers.event_id = events.id'''

        cur.execute(event_query)

        for event_id, event_name, image, resource, resource_type, min_reputation, max_users, contract_address, reward_ETH, reward_EVT, reward_claimable, join_start, time_to_join, start_time, end_time, subject, end_flag, description, field_id, field, field_type, validation_required, val_max, val_min, input_type, label, value, join_topic, claim_topic, category_name, category_image, category_description, rules, avg_event, hidden, user_count in cur:
            event = {}
            event["event_id"] = event_id
            event["title"] = event_name
            event["image"] = image
            event["contract_address"] = contract_address
            event["reward_ETH"] = str(reward_ETH)
            event["reward_EVT"] = reward_EVT
            event["max_users"] = max_users

            event["join_start"] = join_start
            event["time_to_join"] = time_to_join
            event["start_time"] = start_time
            event["end_time"] = end_time

            # relative times
            current_timestamp = int(time.time())
            event["join_start_relative"] = join_start - current_timestamp
            event["time_to_join_relative"] = time_to_join - current_timestamp
            event["start_time_relative"] = start_time - current_timestamp
            event["end_time_relative"] = end_time - current_timestamp
            # ------------

            event["end_flag"] = end_flag
            event["subject"] = subject
            event["resource"] = resource
            event["resource_type"] = resource_type
            event["description"] = description
            event["reward_claimable"] = reward_claimable
            event["join_topic"] = join_topic
            event["claim_topic"] = claim_topic
            event["min_reputation"] = min_reputation
            event["category_name"] = category_name
            event["category_image"] = category_image
            event["category_description"] = category_description
            event["rules"] = rules
            event["avg_event"] = avg_event

            event["hidden"] = hidden
            if user_count == None:
                user_count = 0
            event["user_count"] = user_count

            event["maxed_up"] = False
            if event["user_count"] >= event["max_users"]:
                event["maxed_up"] = True

            if event_id not in events:
                events[event_id] = event

            event["fields"] = []
            event["input_methods"] = []
            new_field = False
            field = {"field_id": field_id, "label": field}
            if field not in events[event_id]["fields"]:
                events[event_id]["fields"].append(field)
                new_field = True

            input_method = {}
            input_method["type"] = field_type
            input_method["field_id"] = field_id

            input_method["required"] = validation_required
            input_method["val_min"] = val_min
            input_method["val_max"] = val_max
            input_method["input_type"] = input_type

            if label != None:
                input_method["values"] = [{"label": label, "value": value}]

            if input_method not in events[event_id]["input_methods"]:
                if new_field:
                    events[event_id]["input_methods"].append(input_method)
                else:
                    events[event_id][
                        "input_methods"][len(events[event_id]["input_methods"])
                                         - 1]["values"].append({
                                             "label": label,
                                             "value": value
                                         })

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", events]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_user_events(user_id):
    '''
        Info:
            Function that returns all events with user data
    '''

    cnx = cur = None
    events = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT events.id, events.end_flag, event_users.user_id, event_users.reward_ETH, event_users.reward_EVT, event_users.reward_claimed, votes.field_id, votes.field_value, votes.timestamp FROM events
                        LEFT JOIN event_users ON event_users.event_id = events.id AND event_users.user_id = %s
                        LEFT JOIN votes ON votes.event_id = events.id AND votes.user_id = %s
                        ORDER BY events.id, field_id
                        '''

        params = (user_id, user_id)
        ''' Execute INSERT statement '''
        cur.execute(event_query, params)

        for event_id, end_flag, user_id, reward_ETH, reward_EVT, reward_claimed, field_id, field_value, vote_timestamp in cur:
            event = {}
            event["event_id"] = event_id
            event["user_joined"] = user_id != None
            event["user_in_consensus"] = 0
            event["end_flag"] = end_flag

            if reward_ETH != None:
                event["user_reward_EVT"] = reward_EVT
                event["user_reward_ETH"] = str(reward_ETH)
                # old way
                event["user_reward"] = str(reward_ETH)
                event["reward_claimed"] = reward_claimed

                if event["user_reward_ETH"] > 0:
                    event["user_in_consensus"] = 1
            else:
                event["user_reward"] = 0

            if field_value == None:
                event["answers"] = []
            else:
                #event["answers"] = [field_value]
                event["answers"] = [{
                    "field_id": field_id,
                    "field_value": field_value
                }]
                event["vote_timestamp"] = vote_timestamp

            event["user_voted"] = field_id != None and field_value != None

            if event_id not in events:
                events[event_id] = event
            else:
                if field_id != None and field_value != None:
                    events[event_id]["answers"].append({
                        "field_id":
                        field_id,
                        "field_value":
                        field_value
                    })
                    events[event_id]["vote_timestamp"] = vote_timestamp
    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = [
            "success", "DB operation was successful",
            list(events.values())
        ]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_id(contract_address):

    cnx = cur = None
    event_id = None
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT id FROM events
                        WHERE contract_address = %s
                        '''

        params = (contract_address, )
        ''' Execute INSERT statement '''
        cur.execute(event_query, params)

        for c in cur:
            event_id = c[0]

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", event_id]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_data(event_id):
    '''
        Info:
            Function that returns event all data for one event
    '''

    cnx = cur = None
    event = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT events.id, events.contract_address, events.claim_topic, name, max_users, min_consensus, min_consensus_ratio, min_consensus_percentage, end_flag, consensus, join_start, time_to_join, start_time, end_time, stop_voting_delta, events.reward_ETH, events.reward_EVT, events.avg_event, events.reward_distribution, COUNT(*) FROM events
                        JOIN event_users ON event_users.event_id = events.id
                        WHERE events.id = %s
                        '''

        params = (event_id, )
        ''' Execute INSERT statement '''
        cur.execute(event_query, params)

        for idd, contract_address, claim_topic, name, max_users, min_consensus, min_consensus_ratio, min_consensus_percentage, end_flag, consensus, join_start, time_to_join, start_time, end_time, stop_voting_delta, reward_ETH, reward_EVT, avg_event, reward_distribution, user_count in cur:
            event = {}
            event["id"] = idd
            event["contract_address"] = contract_address
            event["claim_topic"] = claim_topic
            event["name"] = name
            event["max_users"] = max_users
            event["min_consensus"] = min_consensus
            event["min_consensus_ratio"] = min_consensus_ratio
            event["min_consensus_percentage"] = min_consensus_percentage
            event["end_flag"] = end_flag
            event["join_start"] = join_start
            event["time_to_join"] = time_to_join
            event["start_time"] = start_time
            event["end_time"] = end_time
            event["avg_event"] = avg_event
            event["reward_distribution"] = reward_distribution
            event["consensus"] = consensus

            #current_timestamp = int(time.time())
            #event["join_start_relative"] = join_start - current_timestamp
            #event["time_to_join_relative"] = time_to_join - current_timestamp
            #event["start_time_relative"] = start_time - current_timestamp
            #event["end_time_relative"] = end_time - current_timestamp

            event["stop_voting_delta"] = stop_voting_delta
            event["reward_ETH"] = reward_ETH
            event["reward_EVT"] = reward_EVT
            event["user_count"] = user_count

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", event]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_users(event_address):
    '''
        Info:
            Function that returns all users that joined (confirmed) the event (their addresses)
    '''

    cnx = cur = None
    users = []
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        users_query = '''SELECT users.eth_address FROM event_users
                        JOIN users ON event_users.user_id = users.id
                        WHERE event_id = (SELECT id FROM events WHERE contract_address = %s)'''

        params = (event_address, )
        ''' Execute INSERT statement '''
        cur.execute(users_query, params)

        for c in cur:
            users.append(c[0])

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", users]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_user_ids(event_id):
    '''
        Info:
            Function that returns all users that joined (confirmed) the event (their addresses)
    '''

    cnx = cur = None
    users = []
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        users_query = '''SELECT DISTINCT event_users.user_id, votes.before_consensus FROM event_users
                        LEFT JOIN votes ON event_users.user_id = votes.user_id AND event_users.event_id = votes.event_id
                        WHERE event_users.event_id = %s'''

        params = (event_id, )
        ''' Execute INSERT statement '''
        cur.execute(users_query, params)

        for user_id, before_consensus in cur:
            user = {
                "user_id": user_id,
            }

            if before_consensus == 1:
                # voted, correct
                user["voted"] = True
                user["consensus"] = True
            elif before_consensus == 0:
                # voted, incorrect
                user["voted"] = True
                user["consensus"] = False
            else:
                user["voted"] = False
                user["consensus"] = False
            users.append(user)

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", users]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def save_event_stats(stats, event_id):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        stats_query = '''
            INSERT INTO event_stats (event_id, timestamp, votes, wrong_votes)
            VALUES
        '''
        params = []

        for stat in stats:
            stats_query += "(%s, %s, %s, %s),"
            params.append(event_id)
            params.append(stat["timestamp"])
            params.append(stat["votes"])
            params.append(stat["wrong_votes"])

        stats_query = stats_query[:-1]
        ''' Construct query '''
        params = tuple(params)
        ''' Execute INSERT statement '''
        cur.execute(stats_query, params)
        affected = cur.rowcount
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:
        if affected == 0:
            err_message = ["db_error", "User or event doesn't exist"]
            return err_message
        else:
            succ_message = ["success", "DB operation was successful"]
            return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_fields(event_id):
    '''
        Info:
            Function that returns all event fields
    '''

    cnx = cur = None
    fields = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT event_fields.id, event_fields.field, event_fields.type, event_fields.validation_required, event_fields.max, event_fields.min, event_fields.validation_type, event_answers.label, event_answers.value
                        FROM event_fields
                        LEFT JOIN event_answers ON event_answers.field_id = event_fields.id
                        WHERE event_fields.event_id = %s'''

        params = (event_id, )
        cur.execute(event_query, params)

        for field_id, field, type, validation_required, max, min, validation_type, answer_label, answer_value in cur:

            if field_id not in fields:
                fields[field_id] = {
                    "field": field,
                    "type": type,
                    "validation_required": validation_required,
                    "max": max,
                    "min": min,
                    "validation_type": validation_type
                }
            else:
                if answer_label != None and answer_value != None:
                    fields[field_id]["answers"].append({
                        "label": answer_label,
                        "value": answer_value
                    })

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", fields]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


# ------------------------------------------------------------------------------
# event stats ------------------------------------------------------------------


def get_saved_all_events_stats():
    '''
        Info:
            Function that returns all events stats
    '''

    cnx = cur = None
    events = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT event_id, timestamp, votes, wrong_votes
                        FROM event_stats
                        ORDER BY timestamp ASC
                        '''
        ''' Execute INSERT statement '''
        cur.execute(event_query)

        for event_id, timestamp, votes, wrong_votes in cur:
            if event_id not in events:
                events[event_id] = {
                    "vote_data": [],
                    "wrong_vote_data": [],
                    "labels": []
                }

            events[event_id]["labels"].append(timestamp)
            events[event_id]["vote_data"].append(votes)
            events[event_id]["wrong_vote_data"].append(wrong_votes)

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", events]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_all_events_stats(voter_id=None):

    cnx = cur = None
    events = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT event_id, user_id, field_id, field_value, timestamp, before_consensus, events.consensus_time
                        FROM votes
                        JOIN events ON votes.event_id = events.id
                        ORDER BY timestamp ASC, field_id ASC'''
        ''' Execute INSERT statement '''
        cur.execute(event_query)

        c_time = 0
        for event_id, user_id, field_id, field_value, timestamp, before_consensus, consensus_time in cur:

            if event_id not in events:
                events[event_id] = {
                    "consensus_time": consensus_time,
                    "votes": {}
                }

            votes = events[event_id]["votes"]

            vote = {"field_id": field_id, "field_value": field_value}

            if user_id not in votes:
                votes[user_id] = {
                    "timestamp": timestamp,
                    "correct": before_consensus,
                    "vote": [vote]
                }
                if voter_id != None and user_id == voter_id:
                    votes[user_id]["user":True]
            else:
                votes[user_id]["vote"].append(vote)

        for event_id in events:
            events[event_id]["votes"] = list(
                events[event_id]["votes"].values())

        data = events

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", data]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_stats(event_id, voter_id=None):
    '''
        Info:
            Function that returns all events stats
    '''

    cnx = cur = None
    votes = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT user_id, field_id, field_value, timestamp, before_consensus, events.consensus_time
                        FROM votes
                        JOIN events ON votes.event_id = events.id
                        WHERE event_id = %s
                        ORDER BY timestamp ASC'''

        params = (event_id, )
        ''' Execute INSERT statement '''
        cur.execute(event_query, params)

        c_time = 0
        for user_id, field_id, field_value, timestamp, before_consensus, consensus_time in cur:

            vote = {"field_id": field_id, "field_value": field_value}
            c_time = consensus_time

            if user_id not in votes:
                votes[user_id] = {
                    "timestamp": timestamp,
                    "correct": before_consensus,
                    "vote": [vote]
                }
                if voter_id != None and user_id == voter_id:
                    votes[user_id]["user":True]
            else:
                votes[user_id]["vote"].append(vote)

        data = {"votes": list(votes.values()), "consensus_time": c_time}

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", data]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_consensus_answer(event_id):

    cnx = cur = None
    answers = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT field_id, field_value FROM votes WHERE before_consensus = 1 AND event_id = %s GROUP BY field_id'''

        params = (event_id, )
        ''' Execute INSERT statement '''
        cur.execute(event_query, params)

        for field_id, field_value in cur:
            answers[field_id] = field_value

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", answers]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


# ------------------------------------------------------------------------------
# event joining ----------------------------------------------------------------


def join_event(user_address, event_address):
    '''
        Info:
            Function to add a user to the event
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        join_event_query = '''INSERT INTO event_users (user_id, event_id)
                                SELECT users.id, events.id FROM users
                                JOIN events
                                WHERE users.eth_address = %s AND events.contract_address = %s'''
        ''' Construct query '''
        params = (user_address, event_address)
        ''' Execute INSERT statement '''
        cur.execute(join_event_query, params)
        affected = cur.rowcount
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:
        if affected == 0:
            err_message = ["db_error", "User or event doesn't exist"]
            return err_message
        else:
            succ_message = ["success", "DB operation was successful"]
            return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def join_event_with_id(user_id, event_id):
    '''
        Info:
            Function to add a user to the event
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        join_event_query = '''INSERT INTO event_users (user_id, event_id)
                                VALUES (%s, %s)'''
        ''' Construct query '''
        params = (user_id, event_id)
        ''' Execute INSERT statement '''
        cur.execute(join_event_query, params)
        affected = cur.rowcount
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:
        if affected == 0:
            err_message = ["db_error", "User or event doesn't exist"]
            return err_message
        else:
            succ_message = ["success", "DB operation was successful"]
            return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def verify_join(user_address, event_address):
    '''
        Info:
            Function to verify a user to the event
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        join_event_query = '''UPDATE event_users
                                SET verified = 1
                                WHERE user_id = (SELECT id FROM users WHERE eth_address = %s) AND event_id = (SELECT id FROM events WHERE contract_address = %s)'''
        ''' Construct query '''
        params = (user_address, event_address)
        ''' Execute INSERT statement '''
        cur.execute(join_event_query, params)
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful"]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


# ------------------------------------------------------------------------------
# event voting -----------------------------------------------------------------


def vote_event(user_id, event_id, before_consensus, answers, ip_address):
    '''
        Info:
            Function to cast a vote on an event
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''

        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        vote_event_query = '''INSERT INTO votes
                        (user_id, event_id, before_consensus, field_id, field_value, timestamp, ip_address)
                        VALUES'''
        ''' Construct query '''
        current_timestamp = int(round(time.time() * 1000))

        params = []

        for answer in answers:
            field_id = answer["field_id"]
            field_value = answer["field_value"]

            vote_event_query += """(%s, %s, %s, %s, %s, %s, %s)"""
            params += [
                user_id, event_id, before_consensus, field_id, field_value,
                current_timestamp, ip_address
            ]
            vote_event_query += ","
        vote_event_query = vote_event_query[:-1]
        ''' Execute INSERT statement '''
        cur.execute(vote_event_query, tuple(params))
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        print(err_message)
        return err_message

    else:

        succ_message = ["success", "DB operation was successful"]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


# ------------------------------------------------------------------------------
# event votes ------------------------------------------------------------------


def get_event_votes(event_id):
    '''
        Info:
            Function that returns all votes on an event
    '''

    cnx = cur = None
    votes = {}

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        votes_query = '''SELECT user_id, field_id, field_value, timestamp FROM votes WHERE event_id = %s ORDER BY user_id, field_id'''

        params = (event_id, )
        ''' Execute INSERT statement '''
        cur.execute(votes_query, params)

        for user_id, field_id, field_value, timestamp in cur:
            vote = {}

            if user_id not in votes:
                votes[user_id] = {}
                votes[user_id]["answers"] = [{field_id: field_value}]
                votes[user_id]["timestamp"] = timestamp
            else:
                votes[user_id]["answers"].append({field_id: field_value})

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", votes]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_votes_count(event_id):

    cnx = cur = None
    count = 0

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        votes_query = '''SELECT COUNT(DISTINCT user_id) FROM votes WHERE event_id = %s'''

        params = (event_id, )
        ''' Execute INSERT statement '''
        cur.execute(votes_query, params)

        for cnt in cur:
            count = cnt[0]

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", count]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_events_votes(event_ids):
    '''
        Info:
            Function that returns all votes on events (event_ids)
    '''

    cnx = cur = None
    events = {}

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        votes_query = '''SELECT event_id, user_id, timestamp, before_consensus FROM votes  WHERE event_id  IN '''

        sub_query = "("
        for event_id in event_ids:
            sub_query += "%s,"
        sub_query = sub_query[:-1]
        sub_query += ") "

        votes_query_part_2 = '''GROUP BY user_id, event_id ORDER BY timestamp'''

        votes_query = votes_query + sub_query + votes_query_part_2

        params = tuple(event_ids)
        ''' Execute INSERT statement '''
        cur.execute(votes_query, params)

        for event_id, user_id, timestamp, before_consensus in cur:

            if event_id not in events:
                events[event_id] = []

            events[event_id].append(user_id)

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", events]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_correct_votes(event_id):
    cnx = cur = None
    votes = {}

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        votes_query = '''SELECT user_id, field_id, field_value, timestamp FROM votes WHERE event_id = %s AND before_consensus = 1 ORDER BY user_id, field_id'''

        params = (event_id, )
        ''' Execute INSERT statement '''
        cur.execute(votes_query, params)

        for user_id, field_id, field_value, timestamp in cur:
            vote = {}

            if user_id not in votes:
                votes[user_id] = {}
                votes[user_id]["answers"] = [{field_id: field_value}]
                votes[user_id]["timestamp"] = timestamp
            else:
                votes[user_id]["answers"].append({field_id: field_value})

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", votes]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_wrong_votes(event_id):
    cnx = cur = None
    votes = {}

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        votes_query = '''SELECT user_id, field_id, field_value, timestamp FROM votes WHERE event_id = %s AND before_consensus = 0 ORDER BY user_id, field_id'''

        params = (event_id, )
        ''' Execute INSERT statement '''
        cur.execute(votes_query, params)

        for user_id, field_id, field_value, timestamp in cur:
            vote = {}

            if user_id not in votes:
                votes[user_id] = {}
                votes[user_id]["answers"] = [{field_id: field_value}]
                votes[user_id]["timestamp"] = timestamp
            else:
                votes[user_id]["answers"].append({field_id: field_value})

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", votes]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


# ------------------------------------------------------------------------------
# event end --------------------------------------------------------------------


def end_event(event_id, consensus_reached, consensus_time):
    '''
        Info:
            Function that sets the end_flag to 1 on an event
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        end_event_query = '''UPDATE events SET end_flag = 1, consensus = %s, consensus_time = %s WHERE id = %s'''

        params = (consensus_reached, consensus_time, event_id)
        ''' Execute INSERT statement '''
        cur.execute(end_event_query, params)
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful"]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def update_vote_consensus(event_id, before_list):
    '''
        Info:
            Function that sets user votes' parameter "before_consensus" to 1, indicating that vote was part of the consensus
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        before_event_query = '''UPDATE votes SET before_consensus = 1 WHERE event_id = %s AND user_id IN '''

        params = [event_id]
        q_ext = "("
        for user_id in before_list:
            params.append(user_id)
            q_ext += "%s,"
        q_ext = q_ext[:-1]
        q_ext += ")"
        before_event_query += q_ext
        ''' Execute INSERT statement '''
        cur.execute(before_event_query, params)
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful"]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


# ------------------------------------------------------------------------------
# event rewards ----------------------------------------------------------------


def set_rewards(event_id, users, rewards):
    '''
        Info:
            Function to set rewards for users that were part of the consensus
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''

        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        # TODO change this to update
        query_1 = '''INSERT INTO event_users (event_id, user_id, reward_ETH) VALUES '''
        query_2 = ''' ON DUPLICATE KEY UPDATE reward_ETH=VALUES(reward_ETH)'''
        query_middle = ""

        for user in users:
            query_middle = query_middle + "(%s, %s, %s),"
        query_middle = query_middle[:-1]

        whole_query = query_1 + query_middle + query_2

        params = []
        for i in range(0, len(users)):
            params.append(str(event_id))
            params.append(str(users[i]))
            params.append(str(rewards[i]))
        ''' Execute INSERT statement '''
        cur.execute(whole_query, params)
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful"]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def set_EVT_rewards(event_id, users, rewards):
    '''
        Info:
            Function to set EVT rewards for users that were part of the consensus
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''

        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        # TODO change this to update
        query_1 = '''INSERT INTO event_users (event_id, user_id, reward_EVT) VALUES '''
        query_2 = ''' ON DUPLICATE KEY UPDATE reward_EVT=VALUES(reward_EVT)'''
        query_middle = ""

        for user in users:
            query_middle = query_middle + "(%s, %s, %s),"
        query_middle = query_middle[:-1]

        whole_query = query_1 + query_middle + query_2

        params = []
        for i in range(0, len(users)):
            params.append(str(event_id))
            params.append(str(users[i]))
            params.append(str(rewards[i]))
        ''' Execute INSERT statement '''
        cur.execute(whole_query, params)
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful"]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def set_reward_claimable(contract_address):
    '''
        Info:
            Function that updates reward_claimable field in events table to 1
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''UPDATE events SET reward_claimable = 1 WHERE contract_address = %s'''

        params = (contract_address, )
        ''' Execute INSERT statement '''
        cur.execute(event_query, params)
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful"]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def set_reward_claimed(contract_address, user_address):
    '''
        Info:
            Function that updates reward_claimed field in event_users table to 1
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''UPDATE event_users SET reward_claimed = 1 WHERE event_id = (SELECT id FROM events WHERE contract_address = %s) AND user_id = (SELECT id FROM users WHERE eth_address = %s) '''

        params = (contract_address, user_address)
        ''' Execute INSERT statement '''
        cur.execute(event_query, params)
        affected = cur.rowcount
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:
        if affected == 0:
            err_message = ["db_error", "User or event doesn't exist"]
            return err_message
        else:
            succ_message = ["success", "DB operation was successful"]
            return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

    pass


# ------------------------------------------------------------------------------
# sport events -----------------------------------------------------------------


def get_score_event_data(event_id):

    cnx = cur = None
    score_event = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT team_1_name, team_2_name, team_1_score_field_id, team_2_score_field_id FROM score_events
                        WHERE event_id = %s
                        '''

        params = (event_id, )
        ''' Execute INSERT statement '''
        cur.execute(event_query, params)

        for team_1_name, team_2_name, team_1_score_field_id, team_2_score_field_id in cur:
            score_event = {
                "team_1_name": team_1_name,
                "team_2_name": team_2_name,
                "team_1_score_field_id": team_1_score_field_id,
                "team_2_score_field_id": team_2_score_field_id
            }

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", score_event]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


# ------------------------------------------------------------------------------
# experimental functions -------------------------------------------------------


def get_all_users():
    cnx = cur = None
    users = []

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query = '''SELECT id FROM users'''
        ''' Execute INSERT statement '''
        cur.execute(query)

        for c in cur:
            users.append(c[0])

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", users]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def insert_vote(user_id, event_id, field_id, field_value, timestamp, cons):
    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''

        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        vote_event_query = '''INSERT INTO votes
                        (user_id, event_id, field_id, field_value, timestamp, before_consensus)
                        VALUES '''
        ''' Construct query '''
        current_timestamp = int(time.time())

        params = []

        vote_event_query += """(%s, %s, %s, %s, %s, %s)"""
        params += [user_id, event_id, field_id, field_value, timestamp, cons]
        ''' Execute INSERT statement '''
        cur.execute(vote_event_query, tuple(params))
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        print(err_message)
        return err_message

    else:

        succ_message = ["success", "DB operation was successful"]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_event_names():
    '''
        Info:
            Function that returns event all data for one event
    '''

    cnx = cur = None
    events = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT id, name FROM events'''
        ''' Execute INSERT statement '''
        cur.execute(event_query)

        for idd, name in cur:
            events[idd] = name

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", events]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_consensus_answers():

    #SELECT * FROM votes WHERE before_consensus = 1 GROUP BY field_id ORDER BY field_id
    cnx = cur = None
    answers = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT event_id, field_id, field_value FROM votes WHERE before_consensus = 1 GROUP BY field_id, field_value ORDER BY field_id'''
        ''' Execute INSERT statement '''
        cur.execute(event_query)

        for event_id, field_id, field_value in cur:
            if event_id in answers:
                answers[event_id].append(field_value)
            else:
                answers[event_id] = [field_value]

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", answers]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def get_avg_consensus_answers(event_ids):

    #SELECT * FROM votes WHERE before_consensus = 1 GROUP BY field_id ORDER BY field_id
    cnx = cur = None
    answers = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query = '''SELECT event_id, field_id, field_value FROM votes WHERE before_consensus = 1 AND event_id IN '''

        event_query += "("
        for event_id in event_ids:
            event_query += "%s,"

        event_query = event_query[:-1]
        event_query += ")"

        event_query_part_2 = ''' ORDER BY field_id'''
        ''' Execute INSERT statement '''
        cur.execute(event_query, tuple(event_ids))

        for event_id, field_id, field_value in cur:
            if event_id in answers:
                answers[event_id].append(field_value)
            else:
                answers[event_id] = [field_value]

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = ["success", "DB operation was successful", answers]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


# ------------------------------------------------------------------------------
# event creation ---------------------------------------------------------------


def create_event(event_id, image, name, subject, description, category_id,
                 resource, resource_type, contract_address, max_users,
                 min_consensus, join_start, time_to_join, start_time, end_time,
                 reward_ETH, reward_EVT, avg_event, reward_distribution):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''

        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        # TODO change this to update
        query = '''INSERT INTO events (id, image, name, subject, description, category_id, resource, resource_type, contract_address, max_users, min_consensus, join_start, time_to_join, start_time, end_time, reward_ETH, reward_EVT, hidden, avg_event, reward_distribution)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)'''

        params = (event_id, image, name, subject, description, category_id,
                  resource, resource_type, contract_address, max_users,
                  min_consensus, join_start, time_to_join, start_time,
                  end_time, reward_ETH, reward_EVT, avg_event,
                  reward_distribution)
        ''' Execute INSERT statement '''
        cur.execute(query, params)
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = [
            "success", "DB operation was successful", cur.lastrowid
        ]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def create_event_field(event_id, field, type, validation_required, max, min,
                       validation_type):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''

        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        # TODO change this to update
        query = '''INSERT INTO event_fields (event_id, field, type, validation_required, max, min, validation_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)'''

        params = (event_id, field, type, validation_required, max, min,
                  validation_type)
        ''' Execute INSERT statement '''
        cur.execute(query, params)
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = [
            "success", "DB operation was successful", cur.lastrowid
        ]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def create_field_answer(event_id, field_id, label, value):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''

        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        # TODO change this to update
        query = '''INSERT INTO event_answers (event_id, field_id, label, value)
                    VALUES (%s, %s, %s, %s)'''

        params = (event_id, field_id, label, value)
        ''' Execute INSERT statement '''
        cur.execute(query, params)
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:

        succ_message = [
            "success", "DB operation was successful", cur.lastrowid
        ]
        return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()


def add_contract_address_to_event(event_id, contract_address):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        update_query = '''UPDATE events SET contract_address = %s WHERE id = %s AND contract_address = "" '''
        ''' Construct query '''
        params = (contract_address, event_id)
        ''' Execute INSERT statement '''
        cur.execute(update_query, params)
        affected = cur.rowcount
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error", "Unknown DB error"]
        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error", "Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error", "Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate", err.msg]
        else:
            err_message = ["db_error", err.msg]

        return err_message

    else:
        if affected == 0:
            err_message = ["db_error", "User or event doesn't exist"]
            return err_message
        else:
            succ_message = ["success", "DB operation was successful"]
            return succ_message

    finally:
        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()
