# -*- coding: utf-8 -*-
import sqlite3
from . import connection
import json
import time
from datetime import datetime

def get_position(user_id):

    cnx = cur = None

    position = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''SELECT kyc_position FROM users WHERE id = %s'''

        cur.execute(query, (user_id, ))

        for pos in cur:
            position = pos[0]


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

        succ_message = ["success","DB operation was successful",position]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def update_position(user_id, position, kyc_ref):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''UPDATE users SET kyc_position = %s, kyc_ref = %s WHERE id = %s'''


        cur.execute(query, (position, kyc_ref, user_id))
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

def get_ref_position(ref_code):

    cnx = cur = None

    position = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''SELECT kyc_original_position FROM users WHERE ref_code = %s'''

        cur.execute(query, (ref_code, ))

        for pos in cur:
            position = pos[0]


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

        succ_message = ["success","DB operation was successful",position]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_spot_user_number(spot):

    cnx = cur = None

    count = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''SELECT COUNT(*) FROM users WHERE kyc_position = %s OR kyc_original_position = %s'''

        cur.execute(query, (spot, spot))

        for cnt in cur:
            count = cnt[0]

        print(count)


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

        succ_message = ["success","DB operation was successful",count]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_kyc_status(user_id):

    cnx = cur = None

    kyc_open = False

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''SELECT kyc_open FROM users WHERE id = %s'''

        cur.execute(query, (user_id, ))

        for c in cur:
            kyc_open = c[0]


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

        succ_message = ["success","DB operation was successful", kyc_open]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def submit(user_id, first_name, last_name, bday, address, postal_code, city, country, nationality, email, mobile, wallet_address, eth_amount, id_number, id_type, contact_terms):

    cnx = cur = None

    kyc_open = False

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''INSERT INTO kyc (user_id, first_name, last_name, date_of_birth, address, postal_code, city, country, nationality, email, mobile, wallet_address, eth_amount, id_number, id_type, contact_terms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''

        cur.execute(query, (user_id, first_name, last_name, bday, address, postal_code, city, country, nationality, email, mobile, wallet_address, eth_amount, id_number, id_type, contact_terms))

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

def check_kyc(user_id):

    cnx = cur = None

    submitted = False

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''SELECT id, valid FROM kyc WHERE user_id = %s'''

        cur.execute(query, (user_id, ))

        for id, valid in cur:
            submitted = {
                "kyc_submitted": True,
                "valid": valid
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

        succ_message = ["success","DB operation was successful", submitted]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_user_from_ref(ref_code):

    cnx = cur = None

    user_id = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''SELECT user_id FROM users WHERE ref_code = %s'''

        cur.execute(query, (ref_code, ))

        for uid in cur:
            user_id = uid[0]


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

        succ_message = ["success","DB operation was successful",user_id]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def open_kyc_window(user_id):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''UPDATE users SET kyc_open = 1 WHERE id = %s'''

        cur.execute(query, (user_id,))
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

def request_kyc_window(user_id):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''INSERT INTO kyc_requests (user_id, timestamp) VALUES (%s, %s)'''
        current_timestamp = int(time.time())

        cur.execute(query, (user_id, current_timestamp))
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

def update_kyc_status(user_id, status):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''UPDATE users SET kyc_open = %s WHERE id = %s'''

        cur.execute(query, (status, user_id))
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

def set_kyc_open(user_ids):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''UPDATE users
                        SET kyc_open = 1
                        WHERE id IN
                        '''
        user_query += '('

        for user_id in user_ids:
            user_query += "%s,"
        user_query = user_query[:-1]
        user_query += ')'

        ''' Construct query '''
        query_par = tuple(user_ids)

        ''' Execute INSERT statement '''
        cur.execute(user_query,query_par)
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

def remove_requests(user_ids):

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''DELETE FROM kyc_requests
                        WHERE user_id IN
                        '''
        user_query += '('

        for user_id in user_ids:
            user_query += "%s,"
        user_query = user_query[:-1]
        user_query += ')'

        ''' Construct query '''
        query_par = tuple(user_ids)

        ''' Execute INSERT statement '''
        cur.execute(user_query,query_par)
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

def get_kyc_users():

    cnx = cur = None

    users = []

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''SELECT user_id, first_name, last_name, date_of_birth, address, postal_code, city, country, nationality, email, mobile, wallet_address, eth_amount, id_number, id_type, contact_terms, valid FROM kyc'''

        cur.execute(query)

        for user_id, first_name, last_name, date_of_birth, address, postal_code, city, country, nationality, email, mobile, eth_address, eth_amount, id_number, id_type, contact_terms, valid in cur:
            user = {
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": date_of_birth,
                "address": address,
                "postal_code": postal_code,
                "city": city,
                "country": country,
                "nationality": nationality,
                "email": email,
                "mobile": mobile,
                "eth_address": eth_address,
                "eth_amount": eth_amount,
                "id_number": id_number,
                "id_type": id_type,
                "contact_terms": contact_terms,
                "valid": valid
            }
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

def get_kyc_requests():

    cnx = cur = None

    users = []

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        query =  '''SELECT k_req.user_id, k_req.timestamp, users.email FROM kyc_requests as k_req
                    JOIN users ON k_req.user_id = users.id
        '''

        cur.execute(query)

        for user_id, timestamp, email in cur:
            user = {
                "user_id": user_id,
                "timestamp": timestamp,
                "email": email
            }
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
