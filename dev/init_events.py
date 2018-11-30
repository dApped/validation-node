import json
import os
import pickle
import time
from multiprocessing.dummy import Pool as ThreadPool

from web3 import Web3

from dev_common import (DISPUTE_STAKING_AMOUNT, GAS_AMOUNT_FACTOR,
                        GAS_PRICE_FACTOR, STAKING_AMOUNT,
                        VALIDATION_NODE_ACCOUNTS, DevEnvironment,
                        deploy_event_contract, function_transact_with_account,
                        send_raw_transaction)

BASE_PATH = '../app/contracts'


def create_event_contract(w3, verity_event_json, verity_token_json, event_data,
                          token_contract_address, event_registry_address, owner_account,
                          time_to_join_sec):
    event_data['time_to_join'] = int(time.time()) + time_to_join_sec
    event_data['start_time'] = int(time.time()) + time_to_join_sec + 2
    event_data['end_time'] = int(time.time()) + 50000

    event_name = event_data['name']
    application_start_time = event_data["join_start"]
    application_end_time = event_data["time_to_join"]
    event_start_time = event_data['start_time']
    event_end_time = event_data['end_time']

    node_addresses = [node_account['address'] for node_account in VALIDATION_NODE_ACCOUNTS]
    leftovers_recoverable_after = event_end_time + 1000
    # [minTotalVotes, minConsensusVotes, minConsensusRatio, minParticipantRatio, maxParticipants,
    # distribution]
    consensus_rules = [6, 5, 60, 50, 10, 0]
    staking_amount = STAKING_AMOUNT

    dispute_staking_amount = DISPUTE_STAKING_AMOUNT
    dispute_multiplier = 1
    dispute_timeout = 300
    dispute_rules = [dispute_staking_amount, dispute_timeout, dispute_multiplier]
    print('Event registry address', event_registry_address)
    verity_event = w3.eth.contract(
        abi=verity_event_json['abi'], bytecode=verity_event_json['bytecode'])

    constructor_txn = verity_event.constructor(
        event_name, application_start_time, application_end_time, event_start_time, event_end_time,
        token_contract_address, event_registry_address, node_addresses, leftovers_recoverable_after,
        consensus_rules, staking_amount, dispute_rules, 'ipfshash')

    event_contract_address, next_nonce = deploy_event_contract(w3, constructor_txn, owner_account)
    print('Contract address', event_contract_address)

    # Send rewards to event contract
    reward_eth = Web3.toWei(0.1, 'ether')
    reward_vty = 500

    if reward_eth > 0:
        rewards_txn, _ = send_raw_transaction(w3, owner_account, event_contract_address, reward_eth,
                                              next_nonce)
        w3.eth.waitForTransactionReceipt(rewards_txn)
        print('Rewards transaction: %s' % rewards_txn.hex())

    verity_token_instance = w3.eth.contract(
        address=token_contract_address, abi=verity_token_json['abi'])
    transfer_vty_fun = verity_token_instance.functions.transfer(event_contract_address, reward_vty)
    # owner_account has vty tokens on local chain as this is address that deployed token contract
    function_transact_with_account(w3, transfer_vty_fun, owner_account)

    contract_instance = w3.eth.contract(
        address=event_contract_address, abi=verity_event_json['abi'])
    event_balance = contract_instance.functions.getBalance().call()
    print('Event Rewards: %d WEI, %d VTY' % (event_balance[0], event_balance[1]))
    print()
    return event_contract_address


def join_users_to_event(w3, provider, verity_event_json, verity_token_json, verity_event_address,
                        verity_token_address):
    accounts = DevEnvironment.accounts()
    with ThreadPool(len(accounts)) as pool:
        args = [(w3, verity_event_json, verity_token_json, verity_event_address,
                 verity_token_address, account) for account in accounts]
        pool.starmap(join_user, args)

    if 'local' not in provider:
        print("Check https://ropsten.etherscan.io/address/%s if all users joined successfully" %
              verity_event_address)
    else:
        print('Done')


def join_user(w3, verity_event_json, verity_token_json, contract_address, verity_token_address,
              account):
    print('Joining user', account['address'])

    verity_event_instance = w3.eth.contract(address=contract_address, abi=verity_event_json['abi'])
    address = Web3.toChecksumAddress(account['address'])

    if STAKING_AMOUNT > 0:
        verity_token_instance = w3.eth.contract(
            address=verity_token_address, abi=verity_token_json['abi'])
        increase_allowance_fun = verity_token_instance.functions.increaseApproval(
            contract_address, STAKING_AMOUNT)
        function_transact_with_account(w3, increase_allowance_fun, account)

    nonce = w3.eth.getTransactionCount(address)
    gas_price = int(w3.eth.generateGasPrice() * GAS_PRICE_FACTOR)
    transaction = {
        'from': address,
        'gasPrice': gas_price,
        'nonce': nonce,
    }
    tnx = verity_event_instance.functions.joinEvent().buildTransaction(transaction)
    tnx['gas'] = int(w3.eth.estimateGas(tnx) * GAS_AMOUNT_FACTOR)
    signed_txn = w3.eth.account.signTransaction(tnx, private_key=account['pvt_key'])
    w3.eth.sendRawTransaction(signed_txn.rawTransaction)


def main():
    try:
        dev_env = DevEnvironment.load(DevEnvironment().provider_name_from_env())
    except Exception:
        print('DevEnv for target environment does not exists. Creating new.')
        dev_env = DevEnvironment()

    event_data = json.loads(open('data/new_event.json').read())

    verity_event_json = json.loads(open(os.path.join(BASE_PATH, 'VerityEvent.json')).read())
    verity_token_json = json.loads(open(os.path.join(BASE_PATH, 'VerityToken.json')).read())

    event_addresses = []
    for _ in range(1):
        contract_address = create_event_contract(dev_env.w3, verity_event_json, verity_token_json,
                                                 event_data, dev_env.init_contracts['VerityToken'],
                                                 dev_env.init_contracts['EventRegistry'],
                                                 dev_env.owner_account, dev_env.time_to_join_sec)
        join_users_to_event(dev_env.w3, dev_env.provider_name, verity_event_json, verity_token_json,
                            contract_address, dev_env.init_contracts['VerityToken'])
        event_addresses.append(contract_address)

    with open('data/event_addresses.pkl', 'wb') as fp:
        pickle.dump(event_addresses, fp)


if __name__ == "__main__":
    main()
