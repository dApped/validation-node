import json
import os
import pickle
from pathlib import Path

from dotenv import load_dotenv
from web3 import HTTPProvider, Web3

from dev_common import DevEnvironment, function_transact_with_account

BASE_PATH = '../app/contracts'


def main():
    dev_env = DevEnvironment.load(DevEnvironment().provider_name_from_env())

    user_index = -1
    dispute_account = DevEnvironment.accounts()[user_index]
    print('Dispute triggered by %s' % dispute_account['address'])

    event_addresses = pickle.load(open('data/event_addresses.pkl', 'rb'))
    event_address = event_addresses[0]

    provider = os.getenv('ETH_RPC_PROVIDER')
    w3 = Web3(HTTPProvider(provider))

    verity_contract_json = json.loads(open(os.path.join(BASE_PATH, 'VerityEvent.json')).read())
    contract_instance = w3.eth.contract(address=event_address, abi=verity_contract_json['abi'])
    ((dispute_amount, _, _), _) = contract_instance.functions.getDisputeData().call()

    if dispute_amount > 0:
        print('Dispute amount', dispute_amount)
        verity_token_json = json.loads(open(os.path.join(BASE_PATH, 'VerityToken.json')).read())
        verity_token_instance = w3.eth.contract(
            address=dev_env.init_contracts['VerityToken'], abi=verity_token_json['abi'])
        increase_allowance_fun = verity_token_instance.functions.increaseApproval(
            event_address, dispute_amount)
        function_transact_with_account(w3, increase_allowance_fun, dispute_account)

    tx = function_transact_with_account(w3, contract_instance.functions.triggerDispute(),
                                        dispute_account)

    if 'docker' not in provider:
        print("https://ropsten.etherscan.io/tx/%s" % Web3.toHex(tx))
    else:
        print('Done')


if __name__ == '__main__':
    env_path = Path('..') / '.env'
    load_dotenv(dotenv_path=env_path)
    main()
