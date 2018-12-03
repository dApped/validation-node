import functools
import logging
import time

from web3.utils.contracts import find_matching_event_abi
from web3.utils.events import get_event_data

import common
from database import database
from database.database import VerityEvent
from ethereum import rewards
from events import event_registry_filter

logger = logging.getLogger()

FINAL_STATES = {4, 5}


def process_join_events(_scheduler, _w3, event_id, entries):
    logger.info('[%s] Adding %d %s entries', event_id, len(entries), JOIN_EVENT_FILTER)
    participants = [entry['args']['wallet'] for entry in entries]
    database.Participants.create(event_id, participants)


def process_state_transition(_scheduler, w3, event_id, entries):
    event = database.VerityEvent.get(event_id)
    entry = entries[-1]
    event.state = entry['args']['newState']
    logger.info('[%s] Event state transition, new state: %d', event_id, event.state)
    event.update()
    if event.state in FINAL_STATES:
        logger.info('[%s] Event reached a final state. Removing from DB', event_id)
        VerityEvent.delete_all_event_data(w3, event_id)
        # TODO: Unregister WebSocket connections


def process_validation_start(scheduler, w3, event_id, entries):
    entry = entries[-1]
    event = database.VerityEvent.get(event_id)
    if event is None:
        logger.info('[%s] Event does not exist', event_id)
        return

    validation_round = entry['args']['validationRound']
    event.rewards_validation_round = validation_round
    event.update()

    if not scheduler:
        logger.warning('[%s] Scheduler is not set', event_id)
        return
    if not event.metadata().is_consensus_reached:
        logger.info('[%s] Cannot validate rewards becasue consensus was not reached', event_id)
        return
    if not event.is_master_node:
        scheduler.add_job(rewards.validate_rewards, args=[w3, event_id, validation_round])


def process_validation_restart(scheduler, w3, event_id, entries):
    entry = entries[-1]
    event = database.VerityEvent.get(event_id)

    validation_round = entry['args']['validationRound']
    logger.info('[%s] Validation round %d restart', event_id, validation_round)
    # validation round starts from 1, instead of 0
    is_master_node = w3.eth.defaultAccount == event.node_addresses[validation_round - 1]

    event.rewards_validation_round = validation_round
    event.is_master_node = is_master_node
    event.update()

    if not scheduler:
        logger.warning('Scheduler is not set')
        return
    # if node is master node, set consensus rewards
    if is_master_node:
        logger.info('[%s] Validation round %d I am Master node', event_id, validation_round)
        scheduler.add_job(rewards.set_consensus_rewards, args=[w3, event_id])
    else:
        logger.info('[%s] Validation round %d I am NOT Master node', event_id, validation_round)


def process_error_event(_scheduler, _w3, event_id, entries):
    for entry in entries:
        logger.error('event_id: %s, %s', event_id, entry)


def process_dispute_triggered(_scheduler, w3, event_id, entries):
    entry = entries[-1]
    dispute_started_by = entry['args']['byAddress']
    logger.info('[%s] Dispute tarted by %s', event_id, dispute_started_by)
    VerityEvent.delete_all_event_data(w3, event_id)
    event_registry_filter.init_event(w3, common.verity_event_contract_abi(), event_id)


STATE_TRANSITION_FILTER = 'StateTransition'
JOIN_EVENT_FILTER = 'JoinEvent'
ERROR_FILTER = 'Error'
VALIDATION_STARTED_FILTER = 'ValidationStarted'
VALIDATION_RESTART_FILTER = 'ValidationRestart'
DISPUTE_TRIGGERED_FILTER = 'DisputeTriggered'

EVENT_FILTERS = [(JOIN_EVENT_FILTER, process_join_events),
                 (STATE_TRANSITION_FILTER, process_state_transition),
                 (ERROR_FILTER, process_error_event),
                 (VALIDATION_STARTED_FILTER, process_validation_start),
                 (VALIDATION_RESTART_FILTER, process_validation_restart),
                 (DISPUTE_TRIGGERED_FILTER, process_dispute_triggered)]


def log_entry_formatters(contract_abi, filter_names):
    formatters = {}
    for filter_name in filter_names:
        formatter = functools.partial(get_event_data,
                                      find_matching_event_abi(contract_abi, filter_name))
        formatters[filter_name] = formatter
    return formatters


def should_apply_filter(filter_name, event_id):
    if filter_name in {ERROR_FILTER, STATE_TRANSITION_FILTER}:
        return True

    current_timestamp = int(time.time())
    event = database.VerityEvent.get(event_id)
    if event is None:
        return False
    if (filter_name == JOIN_EVENT_FILTER
            and event.application_start_time <= current_timestamp <= event.event_start_time):
        # JoinEvent is used till event_start_time so that we capture all participants
        return True
    if (filter_name in {
            VALIDATION_STARTED_FILTER, VALIDATION_RESTART_FILTER, DISPUTE_TRIGGERED_FILTER
    } and current_timestamp >= event.event_start_time):
        return True
    return False


def init_event_filters(w3, contract_abi, event_id):
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    for filter_name, filter_func in EVENT_FILTERS:
        init_event_filter(w3, filter_name, filter_func, contract_instance, event_id)


def init_event_filter(w3, filter_name, filter_func, contract_instance, event_id):
    logger.info('[%s] Initializing %s filter', event_id, filter_name)
    filter_ = contract_instance.events[filter_name].createFilter(
        fromBlock='earliest', toBlock='latest')
    database.Filters.create(event_id, filter_.filter_id)
    logger.info('[%s] Requesting all entries for %s', event_id, filter_name)
    entries = filter_.get_all_entries()
    if filter_name in {
            DISPUTE_TRIGGERED_FILTER, VALIDATION_STARTED_FILTER, VALIDATION_RESTART_FILTER
    } or not entries:
        logger.info("[%s] No entries for filter %s", event_id, filter_name)
        return
    filter_func(None, w3, event_id, entries)


def recover_filter(w3, event_id, filter_name, filter_func, filter_id):
    logger.info("[%s] Recovering filter %s", event_id, filter_name)
    database.Filters.remove_from_list(event_id, filter_id)
    contract_abi = common.verity_event_contract_abi()
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    init_event_filter(w3, filter_name, filter_func, contract_instance, event_id)


def filter_events(scheduler, w3, formatters):
    '''filter_events runs in a cron job and requests new entries for all events'''
    event_ids = database.VerityEvent.get_ids_list()
    for event_id in event_ids:
        filter_ids = database.Filters.get_list(event_id)
        if database.VerityEvent.get(event_id) is None:
            logger.info('[%s] Event is not in the database', event_id)
            continue
        for (filter_name, filter_func), filter_id in zip(EVENT_FILTERS, filter_ids):
            if not should_apply_filter(filter_name, event_id):
                continue
            filter_ = w3.eth.filter(filter_id=filter_id)
            filter_.log_entry_formatter = formatters[filter_name]

            try:
                entries = filter_.get_new_entries()
            except Exception as e:
                event = database.VerityEvent.get(event_id)
                if event is None or event.state in FINAL_STATES:
                    # Event was just finished
                    continue
                logger.exception(e)
                recover_filter(w3, event_id, filter_name, filter_func, filter_id)
                continue

            if not entries:
                continue
            filter_func(scheduler, w3, event_id, entries)