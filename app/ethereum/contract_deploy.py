import json
import os

from web3 import Web3, HTTPProvider

provider = os.getenv('ETH_RPC_PROVIDER')
w3 = Web3(HTTPProvider(provider))

def get_contract_application_times(contract_address):

    with open('ethereum/event.json') as f:
        data = json.load(f)

    contract = w3.eth.contract(abi=data["abi"], address=contract_address)

    times = {
        "applicationStartTime": contract.call().applicationStartTime(),
        "applicationEndTime": contract.call().applicationEndTime()
    }

    return times

def get_contract_balance(contract_address):

    return w3.eth.getBalance(contract_address)

def send_eth(address, amount, next_nonce=None):

    developers_account = os.getenv('DEVELOPERS_ACCOUNT')
    developers_account_private_key = os.getenv('DEVELOPERS_ACCOUNT_PRIVATE_KEY')

    if next_nonce == None:
        next_nonce = w3.eth.getTransactionCount(developers_account)

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

    signed_trx = w3.eth.account.signTransaction(transaction, developers_account_private_key)
    send_raw_trx = w3.eth.sendRawTransaction(signed_trx.rawTransaction)

    next_nonce += 1

    return send_raw_trx
