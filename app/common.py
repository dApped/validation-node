import json
import os
import time


def calculate_event_state(end_flag, time_to_join, start_time, end_time, reward_claimable):
    current_timestamp = int(time.time())

    if end_flag:
        state = 3
        if reward_claimable:
            state = 4
    else:
        if current_timestamp < start_time and current_timestamp < time_to_join:
            state = 0  # upcoming joinable
        elif current_timestamp < start_time and current_timestamp >= time_to_join:
            state = 1  # upcoming unjoinable
        elif current_timestamp >= start_time and current_timestamp < end_time:
            state = 2  # live
        else:
            state = 3  # done
            if reward_claimable:
                state = 4

    return state


def contract_abi():
    return json.loads(open(os.path.join(os.getenv('DATA_DIR'), 'VerityEvent.json')).read())['abi']
