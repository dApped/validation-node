import functools
import logging
import time
from datetime import datetime, timedelta, timezone

import requests
from eth_abi.exceptions import NonEmptyPaddingBytes
from web3.utils.contracts import find_matching_event_abi
from web3.utils.events import get_event_data

import common
from database import database
from database.database import VerityEvent
from ethereum import rewards
from events import event_registry_filter
from queue_service import transactions

logger = logging.getLogger()

FINAL_STATES = {4, 5}


def process_join_events(_scheduler, _w3, event_id, entries, should_log):
    if should_log:
        logger.info('[%s] Adding %d %s entries', event_id, len(entries), JOIN_EVENT_FILTER)
    participants = [entry['args']['wallet'] for entry in entries]
    database.Participants.create(event_id, participants)


def process_state_transition(_scheduler, w3, event_id, entries, should_log):
    event = database.VerityEvent.get(event_id)
    if event is None:
        logger.info('[%s] Event does not exist', event_id)
        return

    entry = entries[-1]
    event.state = entry['args']['newState']
    event.update()
    if should_log:
        logger.info('[%s] Event state transition, new state: %d', event_id, event.state)
    if event.state in FINAL_STATES:
        logger.info('[%s] Event reached a final state. Removing from DB', event_id)
        event_registry_filter.node_claim_reward(w3, event_id, should_log=True)
        VerityEvent.delete_all_event_data(w3, event_id)


def process_event_failed(_scheduler, w3, event_id, entries, _should_log):
    entry = entries[-1]
    description = entry['args']['description']
    logger.info('[%s] Event failed: %s. Removing from DB', event_id, description)
    VerityEvent.delete_all_event_data(w3, event_id)


def process_validation_start(scheduler, w3, event_id, entries, should_log):
    entry = entries[-1]
    event = database.VerityEvent.get(event_id)
    if event is None:
        logger.info('[%s] Event does not exist', event_id)
        return
    event_instance = database.VerityEvent.instance(w3, event_id)
    if event_instance.functions.validationState().call() != 1:
        if should_log:
            logger.info('[%s] Event is not in validating state', event_id)
        return

    validation_round = entry['args']['validationRound']
    event.rewards_validation_round = validation_round
    event.update()

    logger.info('[%s] Validation round %d started', event_id, validation_round)
    if not scheduler:
        logger.info('[%s] Scheduler is not set in process_validation_start', event_id)
        return
    if not event.is_master_node:
        scheduler.add_job(rewards.validate_event_data_on_blockchain,
                          args=[w3, event_id, validation_round])


def process_validation_restart(scheduler, w3, event_id, entries, _should_log):
    entry = entries[-1]
    event = database.VerityEvent.get(event_id)
    if event is None:
        logger.info('[%s] Event does not exist', event_id)
        return

    validation_round = entry['args']['validationRound']
    new_master = entry['args']['newMaster']
    logger.info('[%s] Validation round %d restart', event_id, validation_round)

    is_master_node = w3.eth.defaultAccount == new_master
    event.rewards_validation_round = validation_round
    event.is_master_node = is_master_node
    event.update()

    if not scheduler:
        logger.info('[%s] Scheduler is not set in process_validation_restart', event_id)
        return
    # if node is master node, set consensus rewards
    if is_master_node:
        logger.info('[%s] Validation round %d I am Master node', event_id, validation_round)
        scheduler.add_job(rewards.event_data_to_blockchain, args=[w3, event_id])
    else:
        logger.info('[%s] Validation round %d I am NOT Master node', event_id, validation_round)


def process_error_event(_scheduler, _w3, event_id, entries, should_log):
    for entry in entries:
        if should_log:
            logger.info('[%s] Error: %s', event_id, entry)


def process_dispute_triggered(scheduler, w3, event_id, entries, should_log):
    entry = entries[-1]
    dispute_started_by = entry['args']['byAddress']
    logger.info('[%s] Dispute started by %s', event_id, dispute_started_by)
    event = database.VerityEvent.get(event_id)
    if event is None:
        logger.info('[%s] Event does not exist in the database', event_id)
        return
    contract_block_number = event.metadata().contract_block_number

    VerityEvent.delete_all_event_data(w3, event_id)
    event_registry_filter.init_event(scheduler, w3, common.verity_event_contract_abi(), event_id,
                                     contract_block_number, should_log)


STATE_TRANSITION_FILTER = 'StateTransition'
JOIN_EVENT_FILTER = 'JoinEvent'
ERROR_FILTER = 'Error'
VALIDATION_STARTED_FILTER = 'ValidationStarted'
VALIDATION_RESTART_FILTER = 'ValidationRestart'
DISPUTE_TRIGGERED_FILTER = 'DisputeTriggered'
EVENT_FAILED_FILTER = 'EventFailed'

EVENT_FILTERS = {
    JOIN_EVENT_FILTER: process_join_events,
    STATE_TRANSITION_FILTER: process_state_transition,
    ERROR_FILTER: process_error_event,
    VALIDATION_STARTED_FILTER: process_validation_start,
    VALIDATION_RESTART_FILTER: process_validation_restart,
    DISPUTE_TRIGGERED_FILTER: process_dispute_triggered,
    EVENT_FAILED_FILTER: process_event_failed
}


def log_entry_formatters(contract_abi, filter_names):
    formatters = {}
    for filter_name in filter_names:
        formatter = functools.partial(get_event_data,
                                      find_matching_event_abi(contract_abi, filter_name))
        formatters[filter_name] = formatter
    return formatters


def should_apply_filter(filter_name, event_id):
    if filter_name in {ERROR_FILTER, STATE_TRANSITION_FILTER, EVENT_FAILED_FILTER}:
        return True

    current_timestamp = int(time.time())
    event = database.VerityEvent.get(event_id)
    if event is None:
        return False
    if (filter_name == JOIN_EVENT_FILTER
            and event.application_start_time <= current_timestamp <= event.event_end_time):
        # JoinEvent is used till event_end_time so that we capture all participants
        return True
    if (filter_name in {
            VALIDATION_STARTED_FILTER, VALIDATION_RESTART_FILTER, DISPUTE_TRIGGERED_FILTER
    } and current_timestamp >= event.event_start_time):
        return True
    return False


def init_event_filters(scheduler, w3, contract_abi, event_id):
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    for filter_name, filter_func in EVENT_FILTERS.items():
        init_event_filter(scheduler, w3, filter_name, filter_func, contract_instance, event_id)


def init_event_filter(scheduler, w3, filter_name, filter_func, contract_instance, event_id,
                      should_log=True):
    if should_log:
        logger.info('[%s] Initializing %s filter', event_id, filter_name)
    event = database.VerityEvent.get(event_id)
    if event is None:
        logger.info('[%s] Event does not exists in the database', event_id)
        return
    contract_block_number = event.metadata().contract_block_number
    filter_ = contract_instance.events[filter_name].createFilter(fromBlock=contract_block_number,
                                                                 toBlock='latest')
    database.Filters.create(event_id, filter_.filter_id, filter_name)
    if should_log:
        logger.info('[%s] Requesting all entries for %s from %d block', event_id, filter_name,
                    contract_block_number)
    entries = filter_.get_all_entries()
    if filter_name in {VALIDATION_RESTART_FILTER} or not entries:
        if should_log:
            logger.info('[%s] No entries for filter %s', event_id, filter_name)
        return
    filter_func(scheduler, w3, event_id, entries, should_log)


def recover_filter(scheduler, w3, event_id, filter_name, filter_func, filter_id=None,
                   should_log=False):
    try:
        event = database.VerityEvent.get(event_id)
        if event is None or event.state in FINAL_STATES:
            logger.info('[%s] Event is finished. No need to recover %s filter', event_id,
                        filter_name)
            return True
        if filter_id is not None:
            database.Filters.delete_filter(event_id, filter_id, filter_name)
        contract_abi = common.verity_event_contract_abi()
        contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
        init_event_filter(scheduler, w3, filter_name, filter_func, contract_instance, event_id,
                          should_log)
    except Exception as e:
        logger.info('[%s] Exception %s with recovering %s filter', event_id, e.__class__.__name__,
                    filter_name)
        return False
    return True


def recover_all_filters(scheduler, w3, event_id, filter_list=None):
    logger.info('[%s] Recovering all filters', event_id)
    if filter_list:
        filter_ids = [filter_dict['filter_id'] for filter_dict in filter_list]
        database.Filters.uninstall(w3, filter_ids)
    database.Filters.delete(event_id)

    for filter_name, filter_func in EVENT_FILTERS.items():
        success = recover_filter(scheduler, w3, event_id, filter_name, filter_func,
                                 should_log=False)
        if not success:
            return False
    return True


def filter_events(scheduler, w3, formatters):
    '''filter_events runs in a cron job and requests new entries for all events'''
    event_ids = database.VerityEvent.get_ids_list()
    for event_id in event_ids:
        filter_list = database.Filters.get_list(event_id)

        event = database.VerityEvent.get(event_id)
        if event is None:
            logger.info('[%s] Event is not in the database', event_id)
            continue

        event_metadata = event.metadata()
        if not event_metadata.should_run_filters:
            continue

        if len(filter_list) != len(EVENT_FILTERS):
            logger.info('[%s] There are only %d/%d filters. Reinitialize them', event_id,
                        len(filter_list), len(EVENT_FILTERS))
            success = recover_all_filters(scheduler, w3, event_id, filter_list)
            if not success:
                schedule_post_unexpected_exception_job(scheduler, w3, event_id, event_metadata,
                                                       filter_list=None)
            continue
        proccess_filters_for_event(scheduler, w3, formatters, event_id, filter_list, event_metadata)


def proccess_filters_for_event(scheduler, w3, formatters, event_id, filter_list, event_metadata):
    for filter_dict in filter_list:
        filter_id, filter_name = filter_dict['filter_id'], filter_dict['filter_name']
        filter_func = EVENT_FILTERS[filter_name]
        if not should_apply_filter(filter_name, event_id):
            continue
        filter_ = w3.eth.filter(filter_id=filter_id)
        filter_.log_entry_formatter = formatters[filter_name]

        try:
            entries = filter_.get_new_entries()
        except ValueError:
            logger.info('[%s] Event %s filter not found', event_id, filter_name)
            recover_filter(scheduler, w3, event_id, filter_name, filter_func, filter_id=filter_id,
                           should_log=False)
            continue
        except NonEmptyPaddingBytes as e:
            logger.info('[%s] NonEmptyPaddingBytes error with %s filter', event_id, filter_name)
            recover_filter(scheduler, w3, event_id, filter_name, filter_func, filter_id=filter_id,
                           should_log=False)
            continue
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            sleep_minutes = 5
            logger.info('[%s] %s with %s filter. Sleeping %d minutes', event_id,
                        e.__class__.__name__, filter_name, sleep_minutes)
            common.pause_job(scheduler, 'filter_events', minutes=sleep_minutes)
            recover_all_filters(scheduler, w3, event_id, filter_list)
            return
        except Exception:
            if not event_metadata.filters_exception_reported:
                # Only log unexpected exception once
                logger.exception('Event %s filter unexpected exception', filter_name)
                event_metadata.filters_exception_reported = True
                event_metadata.update()
            schedule_post_unexpected_exception_job(scheduler, w3, event_id, event_metadata,
                                                   filter_list)
            return
        if not entries:
            continue
        filter_func(scheduler, w3, event_id, entries, should_log=True)


def schedule_post_unexpected_exception_job(scheduler, w3, event_id, event_metadata, filter_list):
    event_metadata.should_run_filters = False
    event_metadata.update()

    job_datetime = datetime.now(timezone.utc) + timedelta(minutes=5)
    logger.info('[%s] Scheduling post_unexpected_exception_job at %s', event_id, job_datetime)
    scheduler.add_job(post_unexpected_exception_job, 'date', run_date=job_datetime,
                      args=[scheduler, w3, event_id, filter_list])


def post_unexpected_exception_job(scheduler, w3, event_id, filter_list):
    logger.info('[%s] Running post_unexpected_exception_job', event_id)
    event = database.VerityEvent.get(event_id)
    if event is None:
        logger.info('[%s] Event is not in the database', event_id)
        return
    recover_all_filters(scheduler, w3, event_id, filter_list)
    event_metadata = event.metadata()
    event_metadata.should_run_filters = True
    event_metadata.update()
    logger.info('[%s] Finished post_unexpected_exception_job', event_id)


def post_application_end_time_job(scheduler, w3, event_id):
    """ Triggers state change on the event contract and reinitializes JoinEvent filter """
    logger.info('[%s] Running post_application_end_time_job', event_id)
    event = database.VerityEvent.get(event_id)
    if event is None:
        logger.info('[%s] Event not found', event_id)
        return
    event_metadata = event.metadata()

    if event.is_master_node and not event_metadata.is_consensus_reached:
        logger.info('[%s] Master node is triggering contract state change', event_id)
        event_instance = event.instance(w3, event_id)
        trigger_state_change_fun = event_instance.functions.triggerStateChange()
        transactions.queue_transaction(w3, trigger_state_change_fun, event_id=event_id)

    logger.info('[%s] Requesting all entries for JoinEvent filter', event_id)
    filter_list = database.Filters.get_list(event_id)
    for filter_dict in filter_list:
        filter_id, filter_name = filter_dict['filter_id'], filter_dict['filter_name']
        if filter_name != JOIN_EVENT_FILTER:
            continue
        filter_func = EVENT_FILTERS[filter_name]
        recover_filter(scheduler, w3, event_id, filter_name, filter_func, filter_id)
        break
    logger.info('[%s] Finished post_application_end_time_job', event_id)
