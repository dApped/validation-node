import os

from web3 import Web3, HTTPProvider

import common

provider = os.getenv('ETH_RPC_PROVIDER')
web3 = Web3(HTTPProvider(provider))

def get_contract_application_times(contract_address):

    event_abi = common.get_content("http://api.verity.network/contract/abi")

    contract = web3.eth.contract(abi=event_abi, address=contract_address)

    times = {
        "applicationStartTime": contract.call().applicationStartTime(),
        "applicationEndTime": contract.call().applicationEndTime()
    }

    return times

def get_contract_balance(contract_address):

    return web3.eth.getBalance(contract_address)

def send_eth(address, amount, next_nonce=None):

    developers_account = os.getenv('DEVELOPERS_ACCOUNT')
    developers_account_private_key = os.getenv('DEVELOPERS_ACCOUNT_PRIVATE_KEY')

    if next_nonce == None:
        next_nonce = web3.eth.getTransactionCount(developers_account)

    gas_estimate = 21000
    gas_price = 10000000000

    transaction = {
            'to': address,
            'gas': gas_estimate,
            'gasPrice': gas_price,
            'nonce': next_nonce,
            'chainId': 3,
            'value': amount
        }

    signed_trx = web3.eth.account.signTransaction(transaction, developers_account_private_key)
    send_raw_trx = web3.eth.sendRawTransaction(signed_trx.rawTransaction)

    next_nonce += 1

    return send_raw_trx
