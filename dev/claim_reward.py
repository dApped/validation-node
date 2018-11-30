import json
import os
import pickle
from pathlib import Path

from dotenv import load_dotenv
from web3 import HTTPProvider, Web3

from dev_common import DevEnvironment, function_transact_with_account

BASE_PATH = '../app/contracts'


def main():
    provider = os.getenv('ETH_RPC_PROVIDER')
    w3 = Web3(HTTPProvider(provider))

    if 'host.docker.internal' in provider:
        print('Using localhost')
        in_consensus_account = {
            'address': w3.toChecksumAddress('0x273ec1Fb662244b11F2F13015a7D0FD6D66a8Cb3'),
            'pvt_key': '0x413493bdb11d4c0188412c0c8ce6109a6506069e802b35bd2bb344bfa692996e'
        }
        token_contract_address = w3.toChecksumAddress('0x3B241cfFb68A23DdEF1E318F64FC49D85Ec2BFb7')
    else:
        print('Using ropsten')
        in_consensus_account = {
            'address': w3.toChecksumAddress('0xf670De5a0dE38fF5B48233e310a5ACb5293Bcee5'),
            'pvt_key': '0xd32069b398e2ff0739cde4d3184c4f712b770847c2b9e685efd4e37e2b28e0c0'
        }
        token_contract_address = w3.toChecksumAddress('0x4af4114f73d1c1c903ac9e0361b379d1291808a2')

    user_index = 1

    in_consensus_account = DevEnvironment.accounts()[user_index]
    in_consensus_account['address'] = Web3.toChecksumAddress(in_consensus_account['address'])

    # Load verity token contract
    token_json = json.loads(open(os.path.join(BASE_PATH, 'VerityToken.json')).read())
    verity_token_instance = w3.eth.contract(address=token_contract_address, abi=token_json['abi'])

    # Load verity event contract
    f = open('data/event_addresses.pkl', 'rb')
    event_addresses = pickle.load(f)
    verity_event_contract_address = w3.toChecksumAddress(event_addresses[0])
    # verity_event_contract_address = '0xe460eD2c4Ac83dc2eb760Bc58fD12e51f6D96e9B'
    verity_event_json = json.loads(open(os.path.join(BASE_PATH, 'VerityEvent.json')).read())
    verity_event_instance = w3.eth.contract(
        address=verity_event_contract_address, abi=verity_event_json['abi'])

    print('Claimig rewards for user %s' % in_consensus_account['address'])

    (my_eth_rewards, my_token_rewards) = verity_event_instance.functions.getReward().call()
    print('My rewards %d WEI %d VTY' % (my_eth_rewards, my_token_rewards))

    start_balance = verity_token_instance.functions.balanceOf(
        in_consensus_account['address']).call()
    print('Starting balance %d' % start_balance)

    # Claim reward
    tx = function_transact_with_account(w3, verity_event_instance.functions.claimReward(),
                                        in_consensus_account)
    print('Claimied reward tx hash: %s' % Web3.toHex(tx))

    end_balance = verity_token_instance.functions.balanceOf(in_consensus_account['address']).call()
    balance_delta = end_balance - start_balance
    print('User got reward of %d wei' % balance_delta)

    contract_reward_user_ids = verity_event_instance.functions.getRewardsIndex().call()
    (contract_reward_ether, contract_reward_token
     ) = verity_event_instance.functions.getRewards(contract_reward_user_ids).call()

    print('Users in reward structure')
    for er, tr, uid in zip(contract_reward_ether, contract_reward_token, contract_reward_user_ids):
        print('%s: %d ETH %d VTY' % (uid, er, tr))


if __name__ == '__main__':
    env_path = Path('..') / '.env'
    load_dotenv(dotenv_path=env_path)
    main()
