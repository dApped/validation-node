# -*- coding: utf-8 -*-
import sys
import json
import hashlib
import hmac
import time
import string
import random

import tweepy

from web3 import Web3, HTTPProvider, IPCProvider

import config,common

provider = config.ETH_RPC_PROVIDER
web3 = Web3(HTTPProvider(provider))


def contract_constructor_abi(join_after_x_min=15,close_join_after_x_min=15):

    ttj_start = int(time.time()) + join_after_x_min*60
    print(ttj_start)
    ttj_end = ttj_start + close_join_after_x_min*60
    print(ttj_end)

    abi_encoded = common.pad_hex(web3.toHex(ttj_start),32) + common.pad_hex(web3.toHex(ttj_end),32)

    return abi_encoded

def test_eth_filters():

    func = 'joinEvent()'
    #address = equivalent to uint160. bool = equivalent to uint8 with 1 and 0 as valid values. Rules for uint is: hex value padded on the higher-order (left) side with zero-bytes such that the length is a multiple of 32 bytes.
    func_sig = web3.sha3(text=func)[:10]
    print(func_sig)

    # TODO Roman: set new contract address
    contract_address = '' # "***REMOVED***"

    topic = '' #"***REMOVED***"

    filter = web3.eth.filter({
        "fromBlock": "earliest",
        "toBlock": "pending",
        "address": contract_address,
        "topics": [topic]
    })

    filter2 = web3.eth.filter({
        "fromBlock": "earliest",
        "toBlock": "latest",
        "address": contract_address,
        "topics": [topic]
    })


    new_log = web3.eth.getFilterChanges(filter.filter_id)
    print(("New logs: ", new_log, " for contract: ",contract_address," at state: 666"))

    new_log = web3.eth.getFilterChanges(filter2.filter_id)
    print(("New logs: ", new_log, " for contract: ",contract_address," at state: 0"))

def get_twitter_followers_count(username):
    auth = tweepy.OAuthHandler(config.TW_CONSUMER_KEY, config.TW_CONSUMER_SECRET)
    auth.set_access_token(config.TW_ACCESS_TOKEN_KEY, config.TW_ACCESS_TOKEN_SECRET)

    try:
        # Creation of the actual interface, using authentication
        api = tweepy.API(auth)

        user = api.get_user(username)

        return user.followers_count
    except:
        return "error"
