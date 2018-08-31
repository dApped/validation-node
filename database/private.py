# -*- coding: utf-8 -*-
import sqlite3
from . import connection
import json
import time
from datetime import datetime

def get_user_address(code):

    cnx = cur = None

    eth_mail = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''SELECT name, eth_address, email FROM private_sale WHERE code = %s'''

        cur.execute(event_query, (code, ))

        for name, eth_address, email in cur:
            eth_mail = {
                "name": name,
                "eth_address": eth_address,
                "email": email
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

        succ_message = ["success","DB operation was successful", eth_mail]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def insert_private_sale_user(name, eth_address, email, code):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''

        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        insert_query = '''INSERT INTO private_sale
                        (name, eth_address, email, code)
                        VALUES (%s, %s, %s, %s)'''

        ''' Construct query '''
        current_timestamp = int(round(time.time() * 1000))

        params = (name, eth_address, email, code)

        ''' Execute INSERT statement '''
        cur.execute(insert_query, params)
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

        print(err_message)
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

def get_private_sale_users():

    cnx = cur = None

    usrs = []

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        event_query =  '''SELECT name, eth_address, email, code, email_sent FROM private_sale'''

        cur.execute(event_query)

        for name, eth_address, email, code, email_sent in cur:
            user = {
                "name": name,
                "eth_address": eth_address,
                "email": email,
                "code": code,
                "email_sent": email_sent
            }
            usrs.append(user)

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

        succ_message = ["success","DB operation was successful", usrs]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def update_email_sent(email):

        cnx = cur = None

        try:
            ''' Connect to DB with connection info saved in connection.py '''

            cnx = sqlite3.connect(connection.connection_info())
            cur = cnx.cursor()

            update_query = '''UPDATE private_sale SET email_sent = 1 WHERE email = %s'''

            ''' Construct query '''
            current_timestamp = int(round(time.time() * 1000))

            params = (email)

            ''' Execute INSERT statement '''
            cur.execute(update_query, params)
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

            print(err_message)
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
