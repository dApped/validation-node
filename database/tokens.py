# -*- coding: utf-8 -*-
import sqlite3
from . import connection
import json
from datetime import datetime

def create_otk(user_id,expiration,type,value):
    '''
        Info:
            Creat new otk for the user
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''INSERT INTO otk
                        (user_id,expiration,type,value)
                        VALUES (%s,%s,%s,%s)'''

        ''' Construct query '''
        query_par = (user_id,expiration,type,value)

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

def get_otk(value):
    '''
        Info:
            Retrieve otk
    '''

    cnx = cur = None
    otk = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT user_id,expiration,type FROM otk WHERE value = %s '''


        ''' Construct query '''
        query_par = (value,)

        ''' Execute INSERT statement '''
        cur.execute(select_query,query_par)


        for user_id,expiration,type in cur:
            otk = {}
            otk["user_id"] = user_id
            otk["expiration"] = expiration
            otk["type"] = type

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
            succ_message = ["success","DB operation was successful",otk]
            return succ_message
        else:
            err_message = ["otk_not_found","Otk was not found"]
            return err_message



    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def delete_otk(value):
    '''
        Info:
            Delete otk
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''DELETE FROM otk
                        WHERE value = %s
                        '''

        ''' Construct query '''
        query_par = (value,)

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

def create_auth_token(user_id,expiration,value):
    '''
        Info:
            Create new auth token for the user
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''INSERT INTO auth_tokens
                        (user_id,expiration,value)
                        VALUES (%s,%s,%s)'''

        ''' Construct query '''
        query_par = (user_id,expiration,value)

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

def get_auth_token(user_id):
    '''
        Info:
            Retrieve auth_token from user id
    '''

    cnx = cur = None
    auth_token = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT expiration,value FROM auth_tokens WHERE user_id = %s '''

        ''' Construct query '''
        query_par = (user_id,)

        ''' Execute INSERT statement '''
        cur.execute(select_query,query_par)

        for expiration,value in cur:
            auth_token = {}
            auth_token["expiration"] = expiration
            auth_token["value"] = value

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
            succ_message = ["success","DB operation was successful",auth_token]
            return succ_message
        else:
            err_message = ["auth_not_found","Auth_token was not found"]
            return err_message



    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def check_auth_token(value):
    '''
        Info:
            Check auth_token by token value
    '''

    cnx = cur = None
    auth_token = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        select_query = '''SELECT expiration,user_id FROM auth_tokens WHERE value = %s '''

        ''' Construct query '''
        query_par = (value,)

        ''' Execute INSERT statement '''
        cur.execute(select_query,query_par)

        for expiration,user_id in cur:
            auth_token = {}
            auth_token["expiration"] = expiration
            auth_token["user_id"] = user_id

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
            succ_message = ["success","DB operation was successful",auth_token]
            return succ_message
        else:
            err_message = ["auth_not_found","Auth_token was not found"]
            return err_message

    finally:

        ''' Close connection and cursor no matter what happens '''
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def update_auth_token(expiration,token_value):
    '''
        Info:
            Update expiration on auth_token
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''UPDATE auth_tokens
                        SET expiration = %s
                        WHERE value = %s
                        '''

        ''' Construct query '''
        query_par = (expiration,token_value)

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

def delete_auth_token(value):
    '''
        Info:
            Delete authorization token
    '''

    cnx = cur = None

    try:
        ''' Connect to DB with connection info saved in connection.py '''
        cnx = sqlite3.connect(connection.connection_info())
        cur = cnx.cursor()

        user_query = '''DELETE FROM auth_tokens
                        WHERE value = %s
                        '''

        ''' Construct query '''
        query_par = (value,)

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
