# -*- coding: utf-8 -*-
import sys
import json
import requests
import hashlib
import hmac
import time
import string
import random

from web3 import Web3, HTTPProvider, IPCProvider

import config,common,mail
from database import users,tokens,events,bounties,private,kyc
from events import events as evts

# ------------------------------------------------------------------------------
# user data --------------------------------------------------------------------

def get_user_data(data, auth_token, user, include_bounties=False, include_kyc=False):

    '''
        Function return all user's data (including bounties and kyc data if needed)

        Parameters
        ------------
        data: 'dict'
            dictionary of user's submitted json

        auth_token : 'str'
            user's auth token

        user: 'int'
            user's id

        include_bounties: 'bool'
            flag to include bounties data

        include_kyc: 'bool'
            flag to include kyc data

        Returns
        ------------
        A dictionary of all user's events and all user's data (with added kyc and bounties data)

    '''


    check_auth = tokens.check_auth_token(auth_token)

    if check_auth[0] == "success":

        user_id = check_auth[2]["user_id"]
        expiration = check_auth[2]["expiration"]
        current_timestamp = int(time.time())
        if current_timestamp > expiration:
            return common.error_resp(400,"auth_expired","Authorization token is expired")
        elif user != user_id:
            return common.error_resp(400,"auth_invalid","Authorization token is not valid for this user")
        else:

            new_expiration = current_timestamp + config.AUTH_TOKEN_EXP

            tokens.update_auth_token(new_expiration,auth_token)

            user_info = users.get_user(user_id,"id")

            user_event_info = evts.get_user_events_data(user_id)

            if include_bounties:
                user_bounty_info = bounties.get_user_bounties(user_id)
                user_submitions = bounties.get_user_submitions(user_id)
                refered_users = users.get_refered_users(user_id)

            if include_kyc:
                kyc_position = kyc.get_position(user_id)
                user_count = users.get_user_count()
                kyc_unlocked = kyc.get_kyc_status(user_id)
                kyc_status = kyc.check_kyc(user_id)

            if user_info[0] == "success" and user_event_info[0] == "success":

                result = {
                    "data": {
                        "code": 200,
                        "id": "user_info",
                        "message": "User's info successfuly retrieved",
                        "user_id": user_info[2]["user_id"],
                        "user_name": user_info[2]["name"],
                        "user_ref": user_info[2]["ref_code"],
                        "user_surname": user_info[2]["surname"],
                        "user_email": user_info[2]["email"],
                        "user_eth_address": user_info[2]["eth_address"],
                        "user_reputation": user_info[2]["reputation"],
                        "user_email_verified": user_info[2]["email_verified"],
                        "user_signup_timestamp": user_info[2]["signup_timestamp"],
                        "events": user_event_info[2]
                    }
                }

                if include_bounties:

                    if user_bounty_info[0] == "success" and user_submitions[0] == "success" and refered_users[0] == "success":
                        result["data"]["bounties"] = user_bounty_info[2]
                        result["data"]["bounty_submitions"] = user_submitions[2]
                        result["data"]["refered_users"] = refered_users[2]
                    else:
                        return common.error_resp(500,"db_error","Unknown DB error")

                if include_kyc:
                    if kyc_position[0] == "success" and user_count[0] == "success" and kyc_unlocked[0] == "success" and kyc_status[0] == "success":
                        result["data"]["kyc"] = {
                            "position": kyc_position[2],
                            "user_count": user_count[2],
                            "kyc_start": config.KYC_FORM_START - int(time.time()),
                            "kyc_unlocked": kyc_unlocked[2],
                        }
                        if kyc_status[2] != False:
                            result["data"]["kyc"]["kyc_submitted"] = kyc_status[2]["kyc_submitted"]
                            result["data"]["kyc"]["valid"] = kyc_status[2]["valid"]

                return result

            else:

                return common.error_resp(500,"db_error","Unknown DB error")


    else:
        if check_auth[0] == "auth_not_found":
            return common.error_resp(400,check_auth[0],check_auth[1])
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

# ------------------------------------------------------------------------------
# signup and login -------------------------------------------------------------

def signup(data):

    '''
        Signup function

        Parameters
        ------------
        data: 'dict'
            dictionary of user's submitted json

        Returns
        ------------
        common success or error response
    '''

    if "data" in data:

        if "email" in data["data"]:
            email = data["data"]["email"]
        else:
            return common.error_resp(400,"json_error","Could not find email field in the JSON")

        if "password" in data["data"]:
            password = data["data"]["password"]
        else:
            return common.error_resp(400,"json_error","Could not find password field in the JSON")

        if "confirmation_url" in data["data"]:
            confirmation_url = data["data"]["confirmation_url"]
        else:
            return common.error_resp(400,"json_error","Could not find confirmation_url field in the JSON")

        if "ref" in data["data"]:
            ref = data["data"]["ref"]
        else:
            ref = ''

        salt = common.random_string()
        hashed_password = hashlib.sha512( password.encode("utf-8") + salt ).hexdigest()
        current_timestamp = int(time.time())
        ref_code = common.random_string(size=8)

        user_count = users.get_user_count()
        if user_count[0] == "success":
            user_count = user_count[2]

            # insert user to the database
            insert_result = users.insert_user(email,hashed_password,salt,current_timestamp,ref,ref_code, user_count)
            if insert_result[0] == "success":

                # create OTK and send email
                user_id = insert_result[2]
                current_timestamp = int(time.time())
                expiration = current_timestamp + config.OTK_SIGNUP_EXP
                otk_type = "signup"
                otk_value = common.random_string(size=42)

                otk_creation = tokens.create_otk(user_id,expiration,otk_type,otk_value)
                if otk_creation[0] == "success":

                    link = confirmation_url + otk_value

                    if mail.send_signup_email(email,link).status_code == 200:
                        return common.success_resp(201,"user_inserted","User added and email was sent")
                    else:
                        delete_user = users.delete_user(email)
                        if delete_user[0] == "success":
                            return common.error_resp(500,"email_error","Email couldn't be send to the user. User deleted from DB.")
                        else:
                            return common.error_resp(500,"db_error","Unknown DB error")
                else:
                    return common.error_resp(500,"db_error","Unknown DB error")



            else:
                if insert_result[0] == "duplicate":
                    return common.error_resp(400,"duplicate",insert_result[1])
                else:
                    return common.error_resp(500,"db_error","Unknown DB error")
        else:
            return common.error_resp(500,"db_error","Unknown DB count error")


    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")

def login(data):

    '''
        Login function

        Parameters
        ------------
        data: 'dict'
            dictionary of user's submitted json

        Returns
        ------------
        common success or error response
    '''

    if "data" in data:

        if "email" in data["data"]:
            email = data["data"]["email"]
        else:
            return common.error_resp(400,"json_error","Could not find email field in the JSON")

        if "password" in data["data"]:
            password = data["data"]["password"]
        else:
            return common.error_resp(400,"json_error","Could not find password field in the JSON")

        #check if user exists and return its information
        user_info = users.get_user(email,'email')
        if user_info[0] == "success":

            if user_info[2]["email_verified"] == 0:
                return common.error_resp(400,"email_unverified","Email is not verified")

            else:
                salt = user_info[2]["salt"].encode("utf-8")

                hashed_password = hashlib.sha512( password.encode("utf-8") + salt ).hexdigest()

                #password is correct, return auth_token
                if user_info[2]["password"] == hashed_password:
                    user_id = user_info[2]["user_id"]

                    #auth_token already exists
                    auth_info = tokens.get_auth_token(user_id)
                    if auth_info[0] == "success":

                        if tokens.delete_auth_token(auth_info[2]["value"])[0] != "success":

                            return common.error_resp(500,"db_error","Unknown DB error")

                    #generate new auth_token
                    auth_token_value = common.random_string(size=42)
                    current_timestamp = int(time.time())
                    auth_exp = current_timestamp + config.AUTH_TOKEN_EXP

                    if tokens.create_auth_token(user_id,auth_exp,auth_token_value)[0] == "success":
                        result = {
                            "data": {
                                "code": 200,
                                "id": "user_logged_in",
                                "message": "User successfuly logged in",
                                "auth_token": auth_token_value,
                                "user_id": user_id,
                                "user_name": user_info[2]["name"],
                                "user_surname": user_info[2]["surname"]
                            }
                        }
                        return result

                    else:
                        return common.error_resp(500,"auth_error","auth_token could not be generated")

                else:
                    # wrong password
                    return common.error_resp(400,"wrong_credentials","Wrong login credentials")

        elif user_info[0] == "user_not_found":
            # email does not exist in the database
            return common.error_resp(400,"wrong_credentials","Wrong login credentials")

        else:
            return common.error_resp(500,"db_error","Unknown DB error")

    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")

def recover_password(data):

    '''
        Recover password function

        Parameters
        ------------
        data: 'dict'
            dictionary of user's submitted json

        Returns
        ------------
        common success or error response
    '''

    if "data" in data:

        if "email" in data["data"]:
            email = data["data"]["email"]
        else:
            return common.error_resp(400,"json_error","Could not find email field in the JSON")

        # insert user to the database
        user = users.get_user(email, "email")

        if user[0] == "success":

            # create OTK and send email
            user_id = user[2]["user_id"]

            current_timestamp = int(time.time())
            expiration = current_timestamp + config.OTK_RECOVER_EXP
            otk_type = "password_reset"
            otk_value = common.random_string(size=42)

            otk_creation = tokens.create_otk(user_id,expiration,otk_type,otk_value)
            if otk_creation[0] == "success":

                link = "https://alpha.eventum.network/?otk=" + otk_value

                if mail.send_recovery_email(email,link).status_code == 200:
                    return common.success_resp(201,"otk_added","Email was sent. Check your inbox.")
                else:
                    delete_user = users.delete_user(email)
                    if delete_user[0] == "success":
                        return common.error_resp(500,"email_error","Email couldn't be send to the user. User deleted from DB.")
                    else:
                        return common.error_resp(500,"db_error","Unknown DB error")
            else:
                return common.error_resp(500,"db_error","Unknown DB error")

    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")

def update_user(data,auth_token,user):

    '''
        User update function

        Parameters
        ------------
        data: 'dict'
            dictionary of user's submitted json

        auth_token : 'str'
            user's auth token

        user: 'int'
            user's id

        Returns
        ------------
        common success or error response
    '''

    pass_flag = 0
    check_auth = tokens.check_auth_token(auth_token)
    if check_auth[0] == "success":

        user_id = check_auth[2]["user_id"]
        expiration = check_auth[2]["expiration"]
        current_timestamp = int(time.time())
        if current_timestamp > expiration:
            return common.error_resp(400,"auth_expired","Authorization token is expired")
        elif user != user_id:
            return common.error_resp(400,"auth_invalid","Authorization token is not valid for this user")
        else:
            #Extend the expiration of the auth_token
            new_expiration = current_timestamp + config.AUTH_TOKEN_EXP
            tokens.update_auth_token(new_expiration,auth_token)

            user_info = users.get_user(user_id,'id')
            if user_info[0] == "success":

                if "password" in data["data"]:
                    password = data["data"]["password"]
                    if password == '':
                        password = user_info[2]["password"]
                        pass_flag = 1
                else:
                    return common.error_resp(400,"json_error","Could not find password field in the JSON")

                if "name" in data["data"]:
                    name = data["data"]["name"]
                    if name == '':
                        if user_info[2]["name"] == None:
                            name = None
                        else:
                            name = user_info[2]["name"]
                else:
                    return common.error_resp(400,"json_error","Could not find name field in the JSON")

                if "surname" in data["data"]:
                    surname = data["data"]["surname"]
                    if surname == '':
                        if user_info[2]["surname"] == None:
                            surname = None
                        else:
                            surname = user_info[2]["surname"]
                else:
                    return common.error_resp(400,"json_error","Could not find surname field in the JSON")

                if "eth_address" in data["data"]:
                    eth_address = data["data"]["eth_address"]
                    if eth_address == '':
                        if user_info[2]["eth_address"] == None:
                            eth_address = None
                        else:
                            eth_address = user_info[2]["eth_address"]
                    else:
                        eth_address = Web3.toChecksumAddress(eth_address)
                else:
                    return common.error_resp(400,"json_error","Could not find eth_address field in the JSON")


                salt = user_info[2]["salt"]
                if pass_flag == 0:
                    hashed_password = hashlib.sha512( password.encode("utf-8") + salt ).hexdigest()
                else:
                    hashed_password = password

                user_updated = users.update_user(user_info[2]["user_id"],name,surname,hashed_password,eth_address)

                if user_updated[0] == "success":
                    return common.success_resp(200,"user_updated","User's information was updated")
                else:
                    if user_updated[0] == "duplicate":
                        return common.error_resp(400,"duplicate",user_updated[1])
                    else:
                        return common.error_resp(500,"db_error","Unknown DB error")


            else:

                return common.error_resp(500,"db_error","Unknown DB error")


    else:
        if check_auth[0] == "auth_not_found":
            return common.error_resp(400,check_auth[0],check_auth[1])
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

# ------------------------------------------------------------------------------
# OTK --------------------------------------------------------------------------

def confirm_otk(data):

    '''
        Confirm one-time-key function

        Parameters
        ------------
        data: 'dict'
            dictionary of user's submitted json

        auth_token : 'str'
            user's auth token

        user: 'int'
            user's id

        Returns
        ------------
        common success or error response
    '''

    if "data" in data:

        if "otk" in data["data"]:
            otk = data["data"]["otk"]
        else:
            return common.error_resp(400,"json_error","Could not find otk field in the JSON")

        # check otk in the database, delete it, set email to verified and return auth token + user info
        otk_info = tokens.get_otk(otk)
        if otk_info[0] == "success":

            # check for owner and expiration
            user_id = otk_info[2]["user_id"]
            expiration = otk_info[2]["expiration"]
            otk_type = otk_info[2]["type"]
            current_timestamp = int(time.time())
            if current_timestamp > expiration:
                return common.error_resp(400,"otk_expired","One time token is expired")
            else:
                auth_token_value = common.random_string(size=42)
                current_timestamp = int(time.time())

                if otk_type == "signup":
                    auth_exp = current_timestamp + config.AUTH_TOKEN_EXP

                    if (tokens.delete_otk(otk)[0] == "success" and tokens.create_auth_token(user_id,auth_exp,auth_token_value)[0] == "success" and users.confirm_email(user_id)[0] == "success"):
                        result = {
                            "data": {
                                "code": 200,
                                "id": "email_verified",
                                "message": "Email verified, auth_token returned",
                                "auth_token": auth_token_value,
                                "user_id": user_id
                            }
                        }

                        user_data = users.get_user(user_id, "id")
                        #if user_data[0] == "success":
                            #mail.send_welcome_email(user_data[2]["email"], "https://alpha.eventum.network?ref=" + user_data[2]["ref_code"])

                        return result
                    else:
                        return common.error_resp(500,"auth_error","Error confirming the email and generating auth_token")

                elif otk_type == "password_reset":
                    auth_exp = current_timestamp + config.AUTH_TOKEN_EXP

                    if (tokens.delete_otk(otk)[0] == "success" and tokens.create_auth_token(user_id,auth_exp,auth_token_value)[0] == "success"):
                        result = {
                            "data": {
                                "code": 200,
                                "id": "password_reset",
                                "message": "Logged in. Change your password.",
                                "auth_token": auth_token_value,
                                "user_id": user_id
                            }
                        }
                        return result
                    else:
                        return common.error_resp(500,"auth_error","Error confirming the email and generating auth_token")


                else:
                    return common.error_resp(500,"otk_not_found_error","One time token could not be found")



        else:
            return common.error_resp(500,"otk_not_found_error","One time token could not be found")

    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")

# ------------------------------------------------------------------------------
# other ------------------------------------------------------------------------

def generate_ref(data, auth_token):

    '''
        Function that generates a referal code (or sets the one that user put in)

        Parameters
        ------------
        data: 'dict'
            dictionary of user's submitted json

        auth_token : 'str'
            user's auth token

        Returns
        ------------
        common success or error response
    '''

    if "user_id" in data["data"]:
        user_id = data["data"]["user_id"]
        check_auth = tokens.check_auth_token(auth_token)
        if check_auth[0] == "success":
            user = check_auth[2]["user_id"]
            expiration = check_auth[2]["expiration"]
            current_timestamp = int(time.time())
            if current_timestamp > expiration:
                return common.error_resp(400,"auth_expired","Authorization token is expired")
            elif user != user_id:
                return common.error_resp(400,"auth_invalid","Authorization token is not valid for this user")
            else:
                new_expiration = current_timestamp + config.AUTH_TOKEN_EXP
                tokens.update_auth_token(new_expiration,auth_token)
        else:
            if check_auth[0] == "auth_not_found":
                return common.error_resp(400,check_auth[0],check_auth[1])
            else:
                return common.error_resp(500,"db_error","Unknown DB error")
    else:
        return common.error_resp(400,"json_error","Could not find user_id field in the JSON")

    if "ref" in data["data"]:
        ref = data["data"]["ref"]
    else:
        ref = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in list(range(8)))

    ref_update = users.update_ref(user_id, ref)

    if ref_update[0] != "success":
        return common.error_resp(500,"db_error","Unknown DB error")

    result = {
        "data": {
            "code": 201,
            "id": "ref_set",
            "ref": ref,
            "message": "Ref set successfuly"
        }
    }
    return result

def get_private_sale_address(code):

    '''
        Function that returns a private sale address mapped to a specific "code"

        Parameters
        ------------
        code: 'str'
            a randomly generated code

        Returns
        ------------
        common success or error response with eth address
    '''

    result = private.get_user_address(code)

    if result[0] == "success":

        if result[2] == None:
            return common.error_resp(500,"unknown code","Code not in database")
        else:
            return {
                "data": {
                    "user": result[2],
                    "code": 200,
                    "id": "eth_address_found"
                }
            }
    else:
        return common.error_resp(500,"db_error","Unknown DB error")

def join_kyc(data):

    if "user_id" in data["data"]:
        user_id = data["data"]["user_id"]
        check_auth = tokens.check_auth_token(auth_token)
        if check_auth[0] == "success":
            user = check_auth[2]["user_id"]
            expiration = check_auth[2]["expiration"]
            current_timestamp = int(time.time())
            if current_timestamp > expiration:
                return common.error_resp(400,"auth_expired","Authorization token is expired")
            elif user != user_id:
                return common.error_resp(400,"auth_invalid","Authorization token is not valid for this user")
            else:
                new_expiration = current_timestamp + config.AUTH_TOKEN_EXP
                tokens.update_auth_token(new_expiration,auth_token)
        else:
            if check_auth[0] == "auth_not_found":
                return common.error_resp(400,check_auth[0],check_auth[1])
            else:
                return common.error_resp(500,"db_error","Unknown DB error")
    else:
        return common.error_resp(400,"json_error","Could not find user_id field in the JSON")

    if "ref" in data["data"]:
        ref = data["data"]["ref"]

    ref_position = kyc.get_ref_position(ref)
    if ref_position[0] == "success":
        ref_position = ref_position[2]

        update_position = kyc.update_position(user_id, ref_position, ref)
        if update_position[0] != "success":
            return common.error_resp(500,"db_error","Unknown DB error")

    else:
        return common.error_resp(500,"db_error","Unknown DB error")


    result = {
        "data": {
            "code": 201,
            "id": "joined_spot",
            "spot": ref_position,
            "message": "Joined spot successfuly"
        }
    }
    return result
