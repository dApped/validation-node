import config,common,mail
from database import bounties,tokens
from database import users as usrs
import time
import utils
import facebook

def join_bounty(data, auth_token):

    if "data" in data:

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

        if "bounty_id" in data["data"]:
            bounty_id = data["data"]["bounty_id"]
        else:
            return common.error_resp(400,"json_error","Could not find bounty_id field in the JSON")

        if "username" in data["data"]:
            username = data["data"]["username"]
        else:
            return common.error_resp(400,"json_error","Could not find username field in the JSON")

        join = bounties.join_bounty(user_id, bounty_id, username)

        if bounty_id == 1 and join[0] == "success":
            followers = utils.get_twitter_followers_count(username)
            print("FOLLOWERS:", followers)
            if followers != "error":

                if followers > 100000:
                    multiplier = 60.0
                elif followers > 50000:
                    multiplier = 30.0
                elif followers > 30000:
                    multiplier = 20.0
                elif followers > 15000:
                    multiplier = 10.0
                elif followers > 5000:
                    multiplier = 5.0
                elif followers > 1500:
                    multiplier = 2.5
                elif followers > 1000:
                    multiplier = 1.5
                else:
                    multiplier = 1.0

                print("MULTIPLIER:", multiplier)
                update = bounties.update_multiplier(user_id, 1, multiplier)

            else:
                print("ERROR WITH TWEEPLY")

        if join[0] == "success":
            return common.success_resp(201,"user_joined","User joined the bounty")
        elif join[0] == "duplicate":
            return common.error_resp(400,"joined_error","User already joined")
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")

def submit_bounty(data, auth_token):

    if "data" in data:

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

        if "bounty_id" in data["data"]:
            bounty_id = data["data"]["bounty_id"]
        else:
            return common.error_resp(400,"json_error","Could not find bounty_id field in the JSON")

        if "submition" in data["data"]:
            submition = data["data"]["submition"]
        else:
            return common.error_resp(400,"json_error","Could not find submition field in the JSON")

        joined = bounties.get_user_bounties(user_id)
        if joined[0] == "success":

            count = bounties.day_post_count(user_id, bounty_id)

            #if count >= 2:
                #return common.error_resp(400, "max_submissions_reached", "Daily max submissions already reached")

            joined = joined[2][bounty_id]
            if joined["user_joined"]:
                submit = bounties.submit_bounty(user_id, bounty_id, submition)
            else:
                return common.error_resp(400,"db_error","User not joined on bounty")
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

        if submit[0] == "success":
            return common.success_resp(201,"user_joined","User submited the bounty")
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")

def verify_bounty(data, auth_token):

    if "data" in data:

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

        if "user_id" in data["data"]:
            user_id = data["data"]["user_id"]
        else:
            return common.error_resp(400,"json_error","Could not find user_id field in the JSON")

        if "bounty_id" in data["data"]:
            bounty_id = data["data"]["bounty_id"]
        else:
            return common.error_resp(400,"json_error","Could not find bounty_id field in the JSON")

        if "platform_user_id" in data["data"]:
            platform_user_id = data["data"]["platform_user_id"]
        else:
            return common.error_resp(400,"json_error","Could not find platform_user_id field in the JSON")

        if "token" in data["data"]:
            token = data["data"]["token"]
        else:
            return common.error_resp(400,"json_error","Could not find token field in the JSON")

        try:
            graph = facebook.GraphAPI(access_token=token, version=2.7)
            friends = graph.get_object(id='me', fields='friends')
            friends = friends["friends"]["summary"]["total_count"]

            if friends > 5000:
                multiplier = 10.0
            elif friends > 1000:
                multiplier = 5.0
            elif friends > 500:
                multiplier = 2.0
            else:
                multiplier = 1.0

            update = bounties.update_multiplier(user_id, bounty_id, multiplier)
            if update[0] != "success":
                print(update)

        except:
            print("ERROR IN FACEBOOK GRAPH API")


        update = bounties.set_platform_user_id(user_id, bounty_id, platform_user_id, token)
        if update[0] == "success":
            return common.success_resp(201,"user_joined","Bounty verified")
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

        if submit[0] == "success":
            return common.success_resp(201,"user_joined","User submited the bounty")
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")

def edit_bounty_username(data, auth_token):

    if "data" in data:

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

        if "user_id" in data["data"]:
            user_id = data["data"]["user_id"]
        else:
            return common.error_resp(400,"json_error","Could not find user_id field in the JSON")

        if "bounty_id" in data["data"]:
            bounty_id = data["data"]["bounty_id"]
        else:
            return common.error_resp(400,"json_error","Could not find bounty_id field in the JSON")

        if "bounty_username" in data["data"]:
            bounty_username = data["data"]["bounty_username"]
        else:
            return common.error_resp(400,"json_error","Could not find bounty_username field in the JSON")

        if bounty_id == 1:
            followers = utils.get_twitter_followers_count(bounty_username)

            if followers != "error":

                if followers > 100000:
                    multiplier = 60.0
                elif followers > 50000:
                    multiplier = 30.0
                elif followers > 30000:
                    multiplier = 20.0
                elif followers > 15000:
                    multiplier = 10.0
                elif followers > 5000:
                    multiplier = 5.0
                elif followers > 1500:
                    multiplier = 2.5
                elif followers > 1000:
                    multiplier = 1.5
                else:
                    multiplier = 1.0

                update = bounties.update_multiplier(user_id, 1, multiplier)

            else:
                print("ERROR WITH TWEEPLY")

        update = bounties.set_bounty_username(user_id, bounty_id, bounty_username)
        if update[0] == "success":
            return common.success_resp(201,"user_joined","Bounty verified")
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

        if submit[0] == "success":
            return common.success_resp(201,"user_joined","User submited the bounty")
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")
