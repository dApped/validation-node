import json
import os

from web3 import Web3

from dev_common import DevEnvironment

BASE_PATH = '../app/contracts'


def deploy_contract(w3, contract_name, owner_pvt):
    contract_json_path = os.path.join(BASE_PATH, '%s.json' % contract_name)
    contract_json = json.loads(open(contract_json_path).read())
    contract = w3.eth.contract(abi=contract_json['abi'], bytecode=contract_json['bytecode'])

    gas_estimate = 4000000
    next_nonce = w3.eth.getTransactionCount(w3.eth.defaultAccount)

    transaction = {
        'from': w3.eth.defaultAccount,
        'gas': gas_estimate,
        'gasPrice': 200000000000,
        'nonce': next_nonce,
    }

    constructor_txn = contract.constructor().buildTransaction(transaction)
    signed_txn = w3.eth.account.signTransaction(constructor_txn, private_key=owner_pvt)
    raw_txn = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

    tx_contract = w3.eth.waitForTransactionReceipt(raw_txn)
    contract_address = tx_contract['contractAddress']
    print('%s contract deployed to contract %s with tx_hash %s' % (contract_name, contract_address,
                                                                   Web3.toHex(raw_txn)))

    return contract_address


def main():
    dev_env = DevEnvironment()

    dev_env.w3.eth.defaultAccount = dev_env.owner_account['address']
    print('Owner Account balance %d ETH' % dev_env.w3.eth.getBalance(dev_env.w3.eth.defaultAccount))

    contracts_to_deploy = ['EventRegistry', 'NodeRegistry']
    if dev_env.provider_name == 'local':
        contracts_to_deploy.append('VerityToken')

    for contract_name in contracts_to_deploy:
        contract_deploy_address = deploy_contract(dev_env.w3, contract_name,
                                                  dev_env.owner_account['pvt_key'])
        dev_env.init_contracts[contract_name] = dev_env.w3.toChecksumAddress(
            contract_deploy_address)

    print()
    print('****COPY to .env file ****')
    print('EVENT_REGISTRY_ADDRESS=%s ' % dev_env.init_contracts['EventRegistry'])
    print('NODE_REGISTRY_ADDRESS=%s ' % dev_env.init_contracts['NodeRegistry'])
    print('************************')
    dev_env.dump()


if __name__ == "__main__":
    main()
