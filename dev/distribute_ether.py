from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

from dev_common import DevEnvironment, send_raw_transaction


def main():
    dev_env = DevEnvironment.load(DevEnvironment().provider_name_from_env())
    w3 = dev_env.w3
    owner_account = dev_env.owner_account

    accounts = DevEnvironment.accounts_with_validation_nodes_accounts()
    next_nonce = None
    for account in accounts:
        raw_trx, next_nonce = send_raw_transaction(w3, owner_account, account['address'],
                                                   Web3.toWei('1', 'ether'), next_nonce)
        print(account['address'], w3.toHex(raw_trx))


if __name__ == '__main__':
    env_path = Path('..') / '.env'
    load_dotenv(dotenv_path=env_path)
    main()
