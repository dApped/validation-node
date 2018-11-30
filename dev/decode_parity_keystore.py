import json
import os
import pickle

import eth_keyfile
from web3 import HTTPProvider, Web3


def main():
    parity_keys_dir = os.path.expanduser(
        '~/Library/Application Support/io.parity.ethereum/keys/DevelopmentChain')
    provider = os.getenv('ETH_RPC_PROVIDER')
    w3 = Web3(HTTPProvider(provider))

    secrets = []
    for ks in os.listdir(parity_keys_dir):
        ks_file = os.path.join(parity_keys_dir, ks)
        with open(ks_file) as file:
            keystore_json = json.load(file)

            password = ''
            pvt_key = Web3.toHex(eth_keyfile.decode_keyfile_json(keystore_json, b''))
            address = keystore_json['address']

            secret = {
                'address': address,
                'pvt_key': pvt_key,
                'password': password
            }
            secrets.append(secret)

    # Prints out accounts and private keys in order, so we can set our
    # node addresses to those that will be joining events: [1,2,3]
    ordered_accounts = []
    for acc in w3.eth.accounts:
        for secret in secrets:
            h_add = '0x%s' % secret['address']
            if acc.lower() == h_add:
                ordered_accounts.append(secret)
                print(acc, secret['pvt_key'], secret['password'])
                continue
    with open('data/secrets.pkl', 'wb') as fp:
        pickle.dump(ordered_accounts, fp)


if __name__ == '__main__':
    main()
