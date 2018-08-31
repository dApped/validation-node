# -*- coding: utf-8 -*-
import sqlite3
from . import connection
import json
from datetime import datetime

def insert_user(email,password,salt,current_timestamp,ref,ref_code, position):
    '''
        Info:
            Function to add new user to database with his email and password
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''INSERT INTO users
                        (email,password,salt,signup_timestamp,ref,ref_code,kyc_position,kyc_original_position)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)'''

        ''' Construct query '''
        query_par = (email,password,salt,current_timestamp,ref,ref_code,position,position)

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

        last_id = cur.lastrowid
        succ_message = ["success","DB operation was successful",last_id]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def delete_user(email):
    '''
        Info:
            Delete user from the database
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''DELETE FROM users
                        WHERE email = %s
                        '''

        ''' Construct query '''
        query_par = (email,)

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

def get_user(user_value,user_field):
    '''
        Info:
            Get user info from the database
            user_field - should NEVER be passed directly from the user input - SQL injection possibility!
    '''

    cnx = cur = None
    user = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT id,name,surname,password,salt,email,eth_address,reputation,email_verified,signup_timestamp,ref_code FROM users WHERE ''' + user_field + ''' = %s '''

        ''' Construct query '''
        query_par = (user_value,)

        ''' Execute INSERT statement '''
        cur.execute(select_query,query_par)

        for id,name,surname,password,salt,email,eth_address,reputation,email_verified,signup_timestamp,ref in cur:
            user = {}
            user["user_id"] = id
            user["name"] = name
            user["surname"] = surname
            user["password"] = password
            user["salt"] = salt
            user["email"] = email
            user["eth_address"] = eth_address
            user["reputation"] = reputation
            user["email_verified"] = email_verified
            user["signup_timestamp"] = signup_timestamp
            user["ref_code"] = ref

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

        count = cur.rowcount
        if count > 0:
            succ_message = ["success","DB operation was successful",user]
            return succ_message
        else:
            err_message = ["user_not_found","User does not exist"]
            return err_message



    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def confirm_email(user_id):
    '''
        Info:
            Confirm email for a user
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''UPDATE users
                        SET email_verified = 1
                        WHERE id = %s
                        '''

        ''' Construct query '''
        query_par = (user_id,)

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

def update_user(user_id,name,surname,password,eth_address):
    '''
        Info:
            Update user info
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()


        user_query = '''UPDATE users
                        SET name = %s, surname = %s, password = %s, eth_address = %s
                        WHERE id = %s
                        '''

        ''' Construct query '''
        query_par = (name,surname,password,eth_address,user_id)

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

def get_eth_addresses(users):

    '''
        Info:
            Get eth addresses of users
    '''

    cnx = cur = None
    user = None
    addresses = {}
    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT id, eth_address FROM users WHERE id IN '''
        select_query += '('

        for user in users:
            select_query += "%s,"

        select_query = select_query[:-1]
        select_query += ")"

        select_query += " AND eth_address IS NOT NULL"

        ''' Construct query '''
        query_par = tuple(users)

        ''' Execute INSERT statement '''
        cur.execute(select_query,query_par)

        for id, eth_address in cur:
            addresses[id] = eth_address

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

        count = cur.rowcount
        if count > 0:
            succ_message = ["success","DB operation was successful",addresses]
            return succ_message
        else:
            err_message = ["user_not_found","User does not exist"]
            return err_message



    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def update_reputation(users, reps):
    '''
        Info:
            Update user reputation
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()


        user_query = '''INSERT INTO users (id, reputation) VALUES '''

        user_query_end = ''' ON DUPLICATE KEY UPDATE reputation = reputation + VALUES(reputation) '''

        query_par = []
        ''' Construct query '''
        for i in range(0, len(users)):
            user_query += "(%s, %s),"
            query_par.append(users[i])
            query_par.append(reps[i])
        user_query = user_query[:-1]
        user_query += user_query_end

        ''' Execute INSERT statement '''
        cur.execute(user_query,tuple(query_par))
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

def update_ref(user_id, ref = None):
    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()


        user_query = '''UPDATE users
                        SET ref_code = %s
                        WHERE id = %s
                        '''

        ''' Construct query '''
        query_par = (ref, user_id)

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

def get_refered_users(user_id):

    cnx = cur = None
    users = []

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT name,surname FROM users WHERE ref = (SELECT ref_code FROM users WHERE id = %s) '''

        ''' Construct query '''
        query_par = (user_id,)

        ''' Execute INSERT statement '''
        cur.execute(select_query,query_par)

        for name, surname in cur:
            user = ""

            if name  != "" and name != None:
                user = name + " "
            if surname != "" and surname != None:
                user += surname
            if user == "":
                user = "Unknown user"

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

        succ_message = ["success","DB operation was successful",users]
        return succ_message



    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_user_count():

    cnx = cur = None
    user = None

    cnt = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        count_query = '''SELECT COUNT(id) FROM users'''


        ''' Execute INSERT statement '''
        cur.execute(count_query)

        for count in cur:
            cnt = count[0]

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
        if count > 0:
            succ_message = ["success","DB operation was successful",cnt]
            return succ_message
        else:
            err_message = ["user_count_error","Count error"]
            return err_message



    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_all_users():

    cnx = cur = None
    users = []

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT id FROM users'''


        ''' Execute INSERT statement '''
        cur.execute(select_query)

        for user_id in cur:

            users.append(user_id[0])

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

        succ_message = ["success","DB operation was successful",users]
        return succ_message



    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_all_users_data():

    cnx = cur = None
    users = []

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT id, name, surname, email, ref_code FROM users WHERE email_verified = 1 AND temp_email = 0 ORDER BY id'''


        ''' Execute INSERT statement '''
        cur.execute(select_query)

        for id, name, surname, email, ref_code in cur:
            user = {
                "id": id,
                "email": email,
                "name": name,
                "surname": surname,
                "ref_code": ref_code
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

        succ_message = ["success","DB operation was successful",users]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_all_users_data_2():

    cnx = cur = None
    users = []

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT id, name, surname, email, ref_code, eth_address FROM users'''


        ''' Execute INSERT statement '''
        cur.execute(select_query)

        for id, name, surname, email, ref_code, eth_address in cur:
            user = {
                "id": id,
                "email": email,
                "name": name,
                "surname": surname,
                "ref_code": ref_code,
                "eth_address": eth_address
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

        succ_message = ["success","DB operation was successful",users]
        return succ_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_all_users_kyc_data():

    cnx = cur = None
    users = []

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT id, name, surname, email, ref_code, kyc_open, kyc_position FROM users WHERE email_verified = 1 ORDER BY kyc_position'''


        ''' Execute INSERT statement '''
        cur.execute(select_query)

        for id, name, surname, email, ref_code, kyc_open, kyc_position in cur:
            user = {
                "id": id,
                "email": email,
                "name": name,
                "surname": surname,
                "ref_code": ref_code,
                "kyc_open": kyc_open,
                "kyc_position": kyc_position
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

        succ_message = ["success","DB operation was successful",users]
        return succ_message



    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def update_user_eth_addres(email, eth_address):
    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()


        user_query = '''UPDATE users
                        SET eth_address = %s
                        WHERE email = %s
                        '''

        ''' Construct query '''
        query_par = (eth_address, email)

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

def update_user_id_eth_addres(user_id, eth_address):
    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()


        user_query = '''UPDATE users
                        SET eth_address = %s
                        WHERE id = %s
                        '''

        ''' Construct query '''
        query_par = (eth_address, user_id)

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
