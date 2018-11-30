import argparse
import json
import operator
import os
import pickle
import random
from collections import defaultdict
from eth_account.messages import defunct_hash_message
from web3.auto import w3 as w3_auto
from web3 import Web3
import requests

from dev_common import DevEnvironment

BASE_PATH = '../app/contracts'


class Stats:
    def __init__(self, event_id, n_users, n_votes_per_user):
        self.event_id = event_id
        self.n_users = n_users
        self.n_votes_per_user = n_votes_per_user
        self.n_votes = self.n_users * n_votes_per_user
        self.status_code = {}
        self.node_votes = {}
        self.vote_error_count = 0
        self.votes_distribution = {}
        self.user_distribution = defaultdict(set)

    def __str__(self):
        ignore_autoformat_attrs = {'user_distribution'}
        attrs = vars(self)
        string = '\n'.join(
            ['%s: %s' % (k, v) for k, v in attrs.items() if k not in ignore_autoformat_attrs])
        string += '\n\n'

        max_key = max(self.votes_distribution.items(), key=operator.itemgetter(1))[0]
        min_key = min(self.votes_distribution.items(), key=operator.itemgetter(1))[0]
        string += '%d users voted %d: %s\n' % (len(self.user_distribution[max_key]), max_key,
                                               self.user_distribution[max_key])
        if max_key != min_key:
            string += '%d users voted %d: %s\n' % (len(self.user_distribution[min_key]), min_key,
                                                   self.user_distribution[min_key])
        return string


def filter_users(users):
    if len(users) < 10:
        print('Warning: There are only %d users which can vote' % len(users))
    return users


def do_answer(fields, select_answer):
    answers = []
    for field in fields:
        answ = {'field_name': field['name']}
        if field['type'] == 'dropdown' and field['answers']:
            answ['field_value'] = field['answers'][select_answer]
        elif field['type'].lower() == 'text':
            answ['field_value'] = 'text-%d' % select_answer
        else:
            answ['field_value'] = select_answer
        answers.append(answ)
    return answers


def sign_user_vote(data, private_key):
    message_hash = defunct_hash_message(text=str(data['data']))
    signature = w3_auto.eth.account.signHash(message_hash, private_key=private_key)
    return signature['signature'].hex()

def vote(args, answer_options, event_id, users):
    stats = Stats(event_id, len(users), len(args.ports))

    if args.env == 'ropsten':
        print('Voting to ropsten')
        address_ports = [("ec2-18-185-117-85.eu-central-1.compute.amazonaws.com", 80),
                         ("ec2-18-185-32-196.eu-central-1.compute.amazonaws.com", 80),
                         ("ec2-18-196-1-187.eu-central-1.compute.amazonaws.com", 80)]
    else:
        print('Voting to localhost')
        address_ports = [('localhost', p) for p in args.ports]

    for user in users:
        user_id = user['address']
        # consensus-ratio
        select_answer = 0
        if random.random() > args.desired_consensus_ratio:
            select_answer = 1
        stats.votes_distribution[select_answer] = stats.votes_distribution.get(select_answer, 0) + 1
        stats.user_distribution[select_answer].add(user_id)
        vote_json = do_answer(answer_options, select_answer)

        payload = {'data': {'user_id': Web3.toChecksumAddress(user_id), 'event_id': event_id, 'answers': vote_json}}
        payload['signedData'] = sign_user_vote(payload, user['pvt_key'])

        for addr, port in address_ports:
            print('Sending to %s' % addr)
            # vote-error-ratio
            if random.random() < args.desired_vote_error_ratio:
                stats.vote_error_count += 1
                continue
            stats.node_votes[port] = stats.node_votes.get(port, 0) + 1

            # send request
            target = "http://%s:%d/vote" % (addr, port)
            try:
                r = requests.post(
                    target, json=payload, headers={'HTTP_X_FORWARDED_FOR': addr}, timeout=2)
            except Exception as e:
                print('Exception in post request', e)
            else:
                stats.status_code[r.status_code] = stats.status_code.get(r.status_code, 0) + 1
    return stats

def main(args):
    user_accounts = DevEnvironment.accounts()
    if args.inverse_accounts:
        user_accounts = user_accounts[::-1]

    event_data = json.loads(open(os.path.join('data', "new_event.json")).read())
    answer_options = event_data['fields']

    f = open('data/event_addresses.pkl', 'rb')
    event_addresses = pickle.load(f)
    event_id = event_addresses[0]
    # Or hardcode for which event you want to vote
    # event_id = '0x2d200647C423C986dA845E6D6783813084A513F9'

    stats = vote(args, answer_options, event_id, user_accounts)
    print(stats)


if __name__ == '__main__':
    random.seed(42)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--env',
        default='localhost',
        type=str,
        help='Target environment: localhost or ropsten',
        choices=['localhost', 'ropsten'])
    parser.add_argument('--ports', default='5000', type=str, help='Localhost ports to call')
    parser.add_argument(
        '--desired-vote-error-ratio',
        default=0.0,
        type=float,
        help='Desired percentage of votes that are not send')
    parser.add_argument(
        '--desired-consensus-ratio', default=1.0, type=float, help='Desired consensus ratio')
    parser.add_argument(
        '--inverse-accounts', default=False, type=bool, help='Inverse accounts to vote')
    args = parser.parse_args()
    args.ports = [int(port) for port in args.ports.split(',')]
    main(args)
