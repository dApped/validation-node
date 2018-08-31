import config,common,mail
from database import bounties,tokens,kyc
from database import users as usrs
import boto3, botocore

import time
import utils

def join_kyc(data, auth_token):

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

        if "ref" in data["data"]:
            ref = data["data"]["ref"]
        else:
            return common.error_resp(400,"json_error","Could not find ref field in the JSON")

        ref_user_id = kyc.get_user_from_ref(ref)
        ref_user_status = kyc.get_kyc_status(ref_user_id)
        user_status = kyc.get_kyc_status(user_id)

        if ref_user_status[0] == "success" and user_status[0] == "success":
            ref_user_status = ref_user_status[2]
            user_status = user_status[2]
            if ref_user_status != 0:
                return common.error_resp(400, "ref_kyc_open","Referrer's kyc is already open")
            if user_status != 0:
                return common.error_resp(400, "user_kyc_open","Your kyc is already open")


        ref_position = kyc.get_ref_position(ref)
        user_position = kyc.get_position(user_id)

        if ref_position[0] == "success":
            user_position= user_position[2]
            ref_position = ref_position[2]
            count = kyc.get_spot_user_number(ref_position)
            if count[0] == "success":
                count = count[2]
            else:
                return common.error_resp(500,"db_error","Unknown DB error")

            if user_position == ref_position:
                return common.error_resp(400, "same_spot","Users spot is the same")

            if user_position <= ref_position:
                return common.error_resp(400,"worse_spot","Users spot is better")

            if count >= 2:
                return common.error_resp(400,"max_reached","Too many users alredy on that spot")

            if ref_position != None and count != None:
                update = kyc.update_position(user_id, ref_position, ref)
                users_count = usrs.get_user_count()
                if update[0] == "success" and users_count[0] == "success":
                    return common.success_resp(201,"user_joined","You have successfuly joined your friend at spot: " + str(ref_position) + "/" + str(users_count[2]))
                else:
                    return common.error_resp(500,"db_error","Unknown DB error")
            else:
                return common.error_resp(500,"db_error","Unknown DB error")
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")

def request_kyc_window(data, auth_token):

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

        kyc_status = kyc.get_kyc_status(user_id)

        if kyc_status[0] == "success":
            kyc_status = kyc_status[2]
        else:
            return common.error_resp(500,"db_error","Unknown DB error")

        if kyc_status == 2:
            #kyc_open = kyc.open_kyc_window(user_id)

            request_window = kyc.request_kyc_window(user_id)
            if request_window[0] == "success":
                update_status = kyc.update_kyc_status(user_id, 3)
                if update_status[0] == "success":
                    return common.success_resp(201,"kyc_window_requested","User's kyc window has been requested")
                else:
                    common.error_resp(500,"db_error","Unknown DB error")
            else:
                return common.error_resp(500,"db_error","Unknown DB error")
        else:
            return common.error_resp(400,"kyc_not_closed","User's kyc window is not closed")
    else:
        return common.error_resp(400,"json_error","Could not find data field in the JSON")

def submit_kyc(data, files, auth_token):

    if "user_id" in data:
        user_id = int(data["user_id"])
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

    if "first_name" in data:
        first_name = data["first_name"]
    else:
        return common.error_resp(400,"json_error","Could not find first_name field in the JSON")

    if "last_name" in data:
        last_name = data["last_name"]
    else:
        return common.error_resp(400,"json_error","Could not find last_name field in the JSON")

    if "bday" in data:
        bday = data["bday"]
    else:
        return common.error_resp(400,"json_error","Could not find bday field in the JSON")

    if "address" in data:
        address = data["address"]
    else:
        return common.error_resp(400,"json_error","Could not find address field in the JSON")

    if "postal_code" in data:
        postal_code = data["postal_code"]
    else:
        return common.error_resp(400,"json_error","Could not find postal_code field in the JSON")

    if "city" in data:
        city = data["city"]
    else:
        return common.error_resp(400,"json_error","Could not find city field in the JSON")

    if "country" in data:
        country = data["country"]
    else:
        return common.error_resp(400,"json_error","Could not find country field in the JSON")

    if "nationality" in data:
        nationality = data["nationality"]
    else:
        return common.error_resp(400,"json_error","Could not find nationality field in the JSON")

    if "email" in data:
        email = data["email"]
    else:
        return common.error_resp(400,"json_error","Could not find email field in the JSON")

    if "mobile" in data:
        mobile = data["mobile"]
    else:
        return common.error_resp(400,"json_error","Could not find mobile field in the JSON")

    if "wallet_address" in data:
        wallet_address = data["wallet_address"]
    else:
        return common.error_resp(400,"json_error","Could not find wallet_address field in the JSON")

    if "eth_amount" in data:
        eth_amount = data["eth_amount"]
    else:
        return common.error_resp(400,"json_error","Could not find eth_amount field in the JSON")

    if "id_number" in data:
        id_number = data["id_number"]
    else:
        return common.error_resp(400,"json_error","Could not find id_number field in the JSON")

    if "id_type" in data:
        id_type = data["id_type"]
    else:
        return common.error_resp(400,"json_error","Could not find id_tyoe field in the JSON")

    if "contact_terms" in data:
        contact_terms = data["contact_terms"]
        if contact_terms == "on":
            contact_terms = 1
        else:
            contact_terms = 0
    else:
        contact_terms = 0


    if not upload_file_to_s3(files["id_front"], config.S3_BUCKET, user_id):
        return common.error_resp(500,"file_error","Unknown file upload error")
    if not upload_file_to_s3(files["selfie"], config.S3_BUCKET, user_id, folder="/selfie"):
        return common.error_resp(500,"file_error","Unknown file upload error")
    if not upload_file_to_s3(files["utility"], config.S3_BUCKET, user_id, folder="/utility"):
        return common.error_resp(500,"file_error","Unknown file upload error")

    if "id_back" in files:
        if not upload_file_to_s3(files["id_back"], config.S3_BUCKET, user_id):
            return common.error_resp(500,"file_error","Unknown file upload error")

    kyc_status = kyc.get_kyc_status(user_id)
    if kyc_status[0] == "success":
        if kyc_status[2] == 1:
            kyc_submit = kyc.submit(user_id, first_name, last_name, bday, address, postal_code, city, country, nationality, email, mobile, wallet_address, eth_amount, id_number, id_type, contact_terms)

            if kyc_submit[0] == "success":
                return common.success_resp(201,"user_joined","KYC successfuly submited")
            else:
                return common.error_resp(500,"db_error","Unknown DB error")
        else:
            return common.error_resp(400,"kyc_error","User's kyc is closed")
    else:
        return common.error_resp(500,"db_error","Unknown DB error")

def upload_file_to_s3(file, bucket_name, user_id, acl="private", folder=""):

    s3 = boto3.client(
       "s3",
       aws_access_key_id=config.S3_KEY,
       aws_secret_access_key=config.S3_SECRET
    )

    try:

        s3.upload_fileobj(
            file,
            bucket_name,
            str(user_id) + folder + "/" + file.filename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type
            }
        )

        return True

    except Exception as e:
        # This is a catch all exception, edit this part to fit your needs.
        print(("Upload S3 error: ", e))
        return False
