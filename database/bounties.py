# -*- coding: utf-8 -*-
import sqlite3
from . import connection
import json
import time
from datetime import datetime

def get_user_bounties(user_id):

    cnx = cur = None
    bounties = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''SELECT bounties.id, cnt.count, bounties.max_users, bounties.token_reward, name, bounties.description, bounty_users.username, bounties.username_required, bounty_users.id, bounty_users.platform_user_id, bounty_users.multiplier
                            FROM bounties
                            LEFT JOIN bounty_users ON bounty_users.bounty_id = bounties.id AND bounty_users.user_id = %s
                            LEFT JOIN (SELECT bounty_id, COUNT(*) as count FROM bounty_users GROUP BY bounty_id) as cnt ON bounties.id = cnt.bounty_id'''

        cur.execute(event_query, (user_id, ))

        for idd, count, max_users, token_reward, name, description, username, username_required, user_id, platform_user_id, multiplier in cur:
            if count == None:
                count = 0
            ratio = float(count) / max_users

            verified = False
            if platform_user_id != None:
                verified = True

            bounties[idd] = {
                "name": name,
                "description": description,
                "user_joined": user_id != None,
                "ratio": max_users,
                "token_reward": token_reward,
                "multiplier": multiplier,
                "username": username,
                "username_required": username_required,
                "verified": verified
            }

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful", bounties]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def join_bounty(user_id, bounty_id, username):

    cnx = cur = None
    bounties = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        join_query =  '''INSERT INTO bounty_users (user_id, bounty_id, username)
                                VALUES (%s, %s, %s)'''

        cur.execute(join_query, (user_id, bounty_id, username))
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful"]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def set_platform_user_id(user_id, bounty_id, platform_user_id, token):

    cnx = cur = None
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''UPDATE bounty_users
                        SET platform_user_id = %s, token = %s
                        WHERE user_id = %s AND bounty_id = %s'''

        cur.execute(event_query, (platform_user_id, token, user_id, bounty_id))
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful"]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def set_bounty_username(user_id, bounty_id, bounty_username):

    cnx = cur = None
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''UPDATE bounty_users
                        SET username = %s
                        WHERE user_id = %s AND bounty_id = %s'''

        cur.execute(event_query, (bounty_username, user_id, bounty_id))
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful"]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def submit_bounty(user_id, bounty_id, submition):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        current_timestamp = int(time.time())

        event_query =  '''INSERT INTO bounty_submitions (user_id, bounty_id, submition, timestamp)
                                VALUES (%s, %s, %s, %s)'''
        cur.execute(event_query, (user_id, bounty_id, submition, current_timestamp))
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful"]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_user_submitions(user_id):

    cnx = cur = None
    bounties = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''SELECT bounties.id, bounty_submitions.user_id, bounty_submitions.submition, bounty_submitions.timestamp FROM bounties
                            LEFT JOIN bounty_submitions ON bounty_submitions.bounty_id = bounties.id
                            WHERE user_id = %s OR user_id IS NULL'''

        cur.execute(event_query, (user_id,))

        for idd, user_id, submition, timestamp in cur:

            sub_dict = {
                "submition": submition,
                "timestamp": timestamp
            }

            if idd in bounties and submition != None:
                bounties[idd].append(sub_dict)
            elif submition != None:
                bounties[idd] = [sub_dict]

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful", bounties]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_all_submitions():

    cnx = cur = None
    submitions = []
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''SELECT id, user_id, bounty_id, submition, timestamp FROM bounty_submitions'''

        cur.execute(event_query)

        for id, user_id, bounty_id, submition_link, timestamp in cur:
            submition = {}
            submition["id"] = id
            submition["user_id"] = user_id
            submition["bounty_id"] = bounty_id
            submition["submition"] = submition_link
            submition["timestamp"] = timestamp
            submitions.append[submition]

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful", submitions]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_telegram_users():

    cnx = cur = None
    users = []
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''SELECT users.id, users.email, users.ref, users.ref_code FROM users
                        JOIN bounty_users ON bounty_users.user_id = users.id
                        WhERE bounty_id = 0'''

        cur.execute(event_query)

        for id, email, ref, ref_code in cur:
            user = {}
            user["id"] = id
            user["email"] = email
            user["ref"] = ref
            user["ref_code"] = ref_code
            users.append(user)

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful", users]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_twitter_users():

    cnx = cur = None
    users = []
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''SELECT bounty_users.id, bounty_id, user_id, username, multiplier, users.email FROM bounty_users
                        JOIN users ON bounty_users.user_id = users.id
                        WHERE bounty_id = 1'''

        cur.execute(event_query)

        for id, bounty_id, user_id, username, multiplier, email in cur:
            user = {}
            user["id"] = id
            user["bounty_id"] = bounty_id
            user["user_id"] = user_id
            user["username"] = username
            user["multiplier"] = multiplier
            user["email"] = email
            users.append(user)

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful", users]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_facebook_users():

    cnx = cur = None
    users = []
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''SELECT id, bounty_id, user_id, username, multiplier FROM bounty_users WHERE bounty_id = 3'''

        cur.execute(event_query)

        for id, bounty_id, user_id, username, multiplier in cur:
            user = {}
            user["id"] = id
            user["bounty_id"] = bounty_id
            user["user_id"] = user_id
            user["username"] = username
            user["multiplier"] = multiplier
            users.append(user)

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful", users]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def update_username(bounty_user_id, new_username, bounty_id):

    cnx = cur = None
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''UPDATE bounty_users
                        SET username =  %s
                        WHERE user_id = %s AND bounty_id = %s'''

        cur.execute(event_query, (new_username, bounty_user_id, bounty_id))
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful"]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def update_multiplier(user_id, bounty_id, multiplier):

    cnx = cur = None
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''UPDATE bounty_users
                        SET multiplier =  %s
                        WHERE bounty_id = %s AND user_id = %s'''

        cur.execute(event_query, (multiplier, bounty_id, user_id))
        cnx.commit()

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful"]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def day_post_count(user_id, bounty_id):

    cnx = cur = None
    count = 0
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        current_timestamp = int(time.time())


        event_query =  '''SELECT COUNT(*) FROM bounty_submitions WHERE user_id = %s AND bounty_id = %s AND timestamp > (current_timestamp - 86400)'''
        params = (user_id, bounty_id)

        cur.execute(event_query, params)

        for count in cur:
            count = count[0]

    except sqlite3.Error as err:

        err_message = ["db_error","Unknown DB error"]

        ''' Catch  'all' errors '''
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            err_message = ["db_error","Wrong DB username or password"]
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            err_message = ["db_error","Database does not exist"]
        elif err.errno == 1062:
            err_message = ["duplicate",err.msg]
        else:
            err_message = ["db_error",err.msg]

        return err_message

    else:

        succ_message = ["success","DB operation was successful", count]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()
