import json
import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

from dev_common import DevEnvironment, function_transact_with_account


def main():
    dev_env = DevEnvironment.load(DevEnvironment().provider_name_from_env())
    w3 = dev_env.w3
    owner_account = dev_env.owner_account

    contract_address = dev_env.init_contracts['VerityToken']
    contract_abi = json.loads(open(os.path.join('../app/contracts/VerityToken.json')).read())['abi']
    token_contract_instance = w3.eth.contract(address=contract_address, abi=contract_abi)

    accounts = DevEnvironment.accounts_with_validation_nodes_accounts()
    amount = 1000
    for account in accounts:
        account['address'] = Web3.toChecksumAddress(account['address'])
        token_transfer_fun = token_contract_instance.functions.transfer(account['address'], amount)
        function_transact_with_account(w3, token_transfer_fun, owner_account)


if __name__ == '__main__':
    env_path = Path('..') / '.env'
    load_dotenv(dotenv_path=env_path)
    main()
