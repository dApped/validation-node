# -*- coding: utf-8 -*-

from web3 import Web3, HTTPProvider

import common
import config
import scheduler as sch
from database import events

provider = config.ETH_RPC_PROVIDER
web3 = Web3(HTTPProvider(provider))

def set_rewards(participants,rewards,contract_address, next_nonce=None):

    '''
        A function that calls event contract to set rewards for the participants

        Parameters
        ------------
        participants: 'list'
            a list of user eth addresses

        rewards: 'list'
            a list of user rewards (in wei)

        contract_address: 'string'
            event's contract address

        next_nonce: 'int'
            nonce of the next transaction (should be none if making only one transaction at once)

        Returns
        ------------
        transaction hash
    '''

    developers_account = config.DEVELOPERS_ACCOUNT
    developers_account_private_key = config.DEVELOPERS_ACCOUNT_PRIVATE_KEY

    participants_length = len(participants)
    rewards_length = len(rewards)

    func = 'setRewards(address[],uint256[],bool)'
    #address = equivalent to uint160. bool = equivalent to uint8 with 1 and 0 as valid values. Rules for uint is: hex value padded on the higher-order (left) side with zero-bytes such that the length is a multiple of 32 bytes.
    func_sig = web3.sha3(text=func)[:10] #first 4 bytes (10 chars with the leading 0x) of the Keccak hash of: func_name(parameter_type1,parameter_type2,...)

    num_of_arg = 3 #number of arguments
    # ---- headers -----
    arg1_header = common.pad_hex(web3.toHex(num_of_arg * 32),32) #dynamic: location of the data part in bytes = after headers (3 arguments = 3 headers * 32 bytes)
    arg2_header = common.pad_hex(web3.toHex((num_of_arg + 1 + participants_length) * 32),32) #dynamic: location of the data part in bytes = after headers (3*32) + data of the first argument (4 x 32 bytes = array size + 3 elements)
    arg3_header = common.pad_hex(web3.toHex(1),32) #static: value/data of the argument (True = 1, False = 0)
    # ---- dynamic arguments data parts -----
    arg1_data_0 = common.pad_hex(web3.toHex(participants_length),32) #length of the array addresses
    arg1_data = ''
    for parti in participants:
        arg1_data += common.pad_hex(parti,32)

    arg2_data_0 = common.pad_hex(web3.toHex(rewards_length),32) #length of the array rewards
    arg2_data = ''
    for rew in rewards:
        arg2_data += common.pad_hex(web3.toHex(rew),32)

    data = ''.join([func_sig, arg1_header, arg2_header, arg3_header, arg1_data_0, arg1_data, arg2_data_0, arg2_data])

    print("Transaction data: ", data)

    if next_nonce == None:
        next_nonce = web3.eth.getTransactionCount(developers_account)

    print("Nonce used: ", next_nonce)

    #gas_estimate = contract.estimateGas({'from': developers_account}).setRewards(participants,rewards,True)
    gas_estimate = 1100000

    print("Gas estimate: ", gas_estimate)

    gas_price = web3.eth.gasPrice

    #set to 1000 gwei manually
    gas_price = 1000000000000

    print("Gas price used: ", gas_price)

    transaction = {
            'to': contract_address,
            'gas': gas_estimate,
            'gasPrice': gas_price,
            'nonce': next_nonce,
            'chainId': 3,
            'data': data
        }

    signed_trx = web3.eth.account.signTransaction(transaction, developers_account_private_key)
    send_raw_trx = web3.eth.sendRawTransaction(signed_trx.rawTransaction)
    print("Transaction hash for set rewards: ", send_raw_trx)

    return  send_raw_trx

def set_claimable_status_batched(trx_batched,contract_address,scheduler,job_id,claim_topic,event_id,event_data):

    '''
        A function that checks if transactons are mined and sets rewards as claimable (in the db)

        Parameters
        ------------
        trx_batched: 'list'
            a list of transaction hashes (set_rewards transactions)

        contract_address: 'str'
            event's contract address

        scheduler: 'scheduler'
            scheduler object

        job_id: 'int'
            id of the scheduler job's id

        claim_topic: 'str'
            event contract's claim topic

        event_id: 'int'
            event's id

        event_data: 'dict'
            all event's data

        Returns
        ------------
        None
    '''

    claimable_count = 0

    trx_receipts = []
    for i in range(0, len(trx_batched)):
        trx = trx_batched[i]
        trx_receipt = web3.eth.getTransactionReceipt(trx)

        if trx_receipt != None:
            status = web3.eth.getTransactionReceipt(trx)['status']

            if status == 1 or status == "0x1":
                claimable_count += 1
            else:
                print("Transaction ",trx, " failed!")

            if claimable_count == len(trx_batched):
                if events.set_reward_claimable(contract_address)[0] == "success":
                    scheduler.remove_job(job_id)
                    mark_rewards_set(contract_address, scheduler, claim_topic,event_id,event_data)
                else:
                    print("ERROR setting rewards to claimable for contract: ",contract_address)

        else:
            print("Transaction ",trx," not yet mined!")

def mark_rewards_set(contract_address, scheduler, claim_topic,event_id,event_data):

    #TODO Roman: remove from source code and make it secure!
    developers_account = '' # '***REMOVED***'
    developers_account_private_key = '' #'***REMOVED***'


    func = 'markRewardsSet()'
    next_nonce = web3.eth.getTransactionCount(developers_account)
    gas_estimate = 500000
    gas_price = 1000000000000
    func_sig = web3.sha3(text=func)[:10]

    transaction = {
            'to': contract_address,
            'gas': gas_estimate,
            'gasPrice': gas_price,
            'nonce': next_nonce,
            'chainId': 3,
            'data': str(func_sig)
        }

    signed_trx = web3.eth.account.signTransaction(transaction, developers_account_private_key)
    send_raw_trx = web3.eth.sendRawTransaction(signed_trx.rawTransaction)
    print("Transaction hash for markRewardsSet: ", send_raw_trx)

    trx = send_raw_trx

    job_id = "markRewardsSet" + str(trx)
    scheduler.add_job(check_mark_rewards_set, 'interval', seconds=10, args=[trx, job_id, contract_address, scheduler, claim_topic,event_id,event_data], id=job_id, name=""+job_id)

def check_mark_rewards_set(trx, job_id, contract_address, scheduler, claim_topic,event_id,event_data):

    trx_receipt = web3.eth.getTransactionReceipt(trx)
    if trx_receipt != None:
        status = web3.eth.getTransactionReceipt(trx)['status']
        if status == 1 or status == "0x1":
            if events.set_reward_claimable(contract_address)[0] == "success":
                print("Rewards set to claimable!")
                print("STATE:")
                print(event_data["state"])
                print("REWARD_CLAIMABLE")
                print(event_data["reward_claimable"])
                #remove this job so we don't check for setRewards to be successfull anymore
                scheduler.remove_job(job_id)

                if "reward_claimable" in event_data:
                    event_data["reward_claimable"] = 1
                    event_data["state"] = 4

                #Do a socket push: "claimable" with event data
                url_endpoint = "/claimable"
                event_type = "claimable"
                sch.make_call_to_socket_server(url_endpoint,event_id,event_type,event_data)

                #add job to check if user has claimed their reward
                filter = web3.eth.filter({
                    "fromBlock": "earliest",
                    "toBlock": "latest",
                    "address": contract_address,
                    "topics": [claim_topic]
                })
                scheduler.add_job(sch.check_contract_event, 'interval', seconds=10, args=[filter.filter_id,contract_address,4], id=contract_address+"_4", name="Events for contract: "+contract_address+" in state: 4")
            else:
                print("ERROR setting rewards to claimable for contract: ",contract_address)
        else:
            print("Transaction ",trx, " failed!")
    else:
        print("Transaction ",trx," not yet mined!")
