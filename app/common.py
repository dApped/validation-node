import json
import os


def verity_event_contract_abi():
    return json.loads(open(os.path.join(os.getenv('DATA_DIR'), 'VerityEvent.json')).read())['abi']
