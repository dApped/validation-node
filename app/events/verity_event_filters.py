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

logger = logging.getLogger('flask.app')


def process_join_events(_, event_id, entries):
    logger.info('Adding %d %s entries for %s event', len(entries), JOIN_EVENT_FILTER, event_id)
    participants = [entry['args']['wallet'] for entry in entries]
    database.Participants.create(event_id, participants)


def process_state_transition(_, event_id, entries):
    event = database.VerityEvent.get(event_id)
    entry = entries[0]
    event.state = entry['args']['newState']
    logger.info('Event %s state transition detected. New state %d', event_id, event.state)
    event.update()


def process_validation_start(w3, event_id, entries):
    entry = entries[0]
    event = database.VerityEvent.get(event_id)

    validation_round = entry['args']['validationRound']
    event.rewards_validation_round = validation_round
    event.update()

    if not event.is_master_node:
        rewards.validate_rewards(w3, event_id, validation_round)


def process_validation_restart(w3, event_id, entries):
    entry = entries[0]
    event = database.VerityEvent.get(event_id)

    validation_round = entry['args']['validationRound']
    logger.info('Validation round %d restart', validation_round)
    # validation round starts from 1, instead of 0
    is_master_node = w3.eth.defaultAccount == event.node_addresses[validation_round - 1]

    event.rewards_validation_round = validation_round
    event.is_master_node = is_master_node
    event.update()

    # if node is master node, set consensus rewards
    if is_master_node:
        logger.info('Validation round %d I am Master node', validation_round)
        # TODO if this blocks other filters, use scheduler
        rewards.set_consensus_rewards(w3, event_id)
    else:
        logger.info('Validation round %d I am NOT Master node', validation_round)


def process_error_event(_, event_id, entries):
    for entry in entries:
        logger.error('event_id: %s, %s', event_id, entry)


def process_dispute_triggered(w3, event_id, entries):
    entry = entries[0]
    dispute_started_by = entry['args']['byAddress']
    logger.info('Dispute on event %s triggered by %s', event_id, dispute_started_by)
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
    if (filter_name == JOIN_EVENT_FILTER
            and event.application_start_time >= current_timestamp <= event.event_start_time):
        # JoinEvent is used till event_start_time so that we capture all participants
        return True
    if (filter_name in {VALIDATION_STARTED_FILTER, VALIDATION_RESTART_FILTER,
                        DISPUTE_TRIGGERED_FILTER}
            and current_timestamp >= event.event_start_time):
        return True
    return False


def init_event_filters(w3, contract_abi, event_id):
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    for filter_name, filter_func in EVENT_FILTERS:
        logger.info('Initializing %s filter for %s event', filter_name, event_id)
        filter_ = contract_instance.events[filter_name].createFilter(
            fromBlock='earliest', toBlock='latest')
        database.Filters.create(event_id, filter_.filter_id)
        logger.info('Requesting all entries for %s on %s', filter_name, event_id)
        entries = filter_.get_all_entries()
        if filter_name in {DISPUTE_TRIGGERED_FILTER,
                           VALIDATION_STARTED_FILTER,
                           VALIDATION_RESTART_FILTER} or not entries:
            logger.info("Not calling event handler for filter %s on %s", filter_name, event_id)
            continue
        filter_func(w3, event_id, entries)


def filter_events(w3, formatters):
    '''filter_events runs in a cron job and requests new entries for all events'''
    event_ids = database.VerityEvent.get_ids_list()
    for event_id in event_ids:
        filter_ids = database.Filters.get_list(event_id)
        for (filter_name, filter_func), filter_id in zip(EVENT_FILTERS, filter_ids):
            if not should_apply_filter(filter_name, event_id):
                continue
            filter_ = w3.eth.filter(filter_id=filter_id)
            filter_.log_entry_formatter = formatters[filter_name]
            try:
                entries = filter_.get_new_entries()
                if not entries:
                    continue
                filter_func(w3, event_id, entries)
            except Exception as e:
                # TODO remove this when bug is fixed
                logger.error(event_id, filter_name)
                logger.exception(e)
