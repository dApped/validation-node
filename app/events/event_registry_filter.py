import logging
import time
from datetime import datetime, timedelta, timezone

import requests

import common
from database import database
from events import consensus, verity_event_filters
from queue_service import transactions

logger = logging.getLogger()

NEW_VERITY_EVENT = 'NewVerityEvent'


def process_new_verity_events(scheduler, w3, event_contract_abi, entries):
    for entry in entries:
        contract_block_number = entry['blockNumber']
        event_address = entry['args']['eventAddress']
        init_event(scheduler, w3, event_contract_abi, event_address, contract_block_number)


def is_node_registered_on_event(w3, contract_abi, node_id, event_id):
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    node_ids = contract_instance.functions.getEventResolvers().call()
    node_ids = set(node_ids)
    return node_id in node_ids


def node_claim_reward(w3, event_id):
    # TODO check if node approve rewards
    event_instance = database.VerityEvent.instance(w3, event_id)
    node_claim_reward_fun = event_instance.functions.nodeClaimReward()
    transactions.queue_transaction(w3, node_claim_reward_fun, event_id=event_id)


def call_event_contract_for_metadata(contract_instance, event_id):
    try:
        state = contract_instance.functions.getState().call()
        if state > 2:
            logger.info('[%s] Event with state: %d. It is not in waiting|application|running state',
                        event_id, state)
            return None

        (application_start_time, application_end_time, event_start_time, event_end_time,
         leftovers_recoverable_after) = contract_instance.functions.getEventTimes().call()
        if event_end_time < int(time.time()):
            logger.info('[%s] Event end time in the past: %d', event_id, event_end_time)
            return None

        owner = contract_instance.functions.owner().call()
        token_address = contract_instance.functions.tokenAddress().call()
        node_addresses = contract_instance.functions.getEventResolvers().call()
        event_name = contract_instance.functions.eventName().call()
        data_feed_hash = contract_instance.functions.dataFeedHash().call()
        is_master_node = contract_instance.functions.isMasterNode().call()
        consensus_rules = contract_instance.functions.getConsensusRules().call()
        (min_total_votes, min_consensus_votes, min_consensus_ratio, min_participant_ratio,
         max_participants, rewards_distribution_function) = consensus_rules
        validation_round = contract_instance.functions.rewardsValidationRound().call()
        ((dispute_amount, dispute_timeout, dispute_multiplier, dispute_round, _),
         disputer) = contract_instance.functions.getDisputeData().call()
        staking_amount = contract_instance.functions.stakingAmount().call()
        event = database.VerityEvent(
            event_id, owner, token_address, node_addresses, leftovers_recoverable_after,
            application_start_time, application_end_time, event_start_time, event_end_time,
            event_name, data_feed_hash, state, is_master_node, min_total_votes, min_consensus_votes,
            min_consensus_ratio, min_participant_ratio, max_participants,
            rewards_distribution_function, validation_round, dispute_amount, dispute_timeout,
            dispute_multiplier, dispute_round, disputer, staking_amount)
    except Exception:
        logger.exception("Node does not support this type of event")
        return None
    return event


def schedule_consensus_not_reached_job(scheduler, event_id, event_end_time):
    logger.info('[%s] Scheduling process_consensus_not_reached_job', event_id)
    event_end_datetime = datetime.fromtimestamp(event_end_time, timezone.utc)
    job_datetime = event_end_datetime + timedelta(minutes=1)
    job_id = database.VerityEvent.consensus_not_reached_job_id(event_id)
    scheduler.add_job(
        consensus.process_consensus_not_reached,
        'date',
        run_date=job_datetime,
        replace_existing=True,
        args=[event_id],
        id=job_id)
    logger.info('[%s] Scheduled process_consensus_not_reached_job at %s', event_id, job_datetime)


def schedule_post_application_end_time_job(scheduler, w3, event_id, application_end_time):
    application_end_datetime = datetime.fromtimestamp(application_end_time, timezone.utc)
    job_datetime = application_end_datetime + timedelta(minutes=1)
    job_id = database.VerityEvent.post_application_end_time_job_id(event_id)
    if datetime.now(timezone.utc) > job_datetime:
        logger.info('[%s] Skipping post_application_end_time_job', event_id)
        return

    logger.info('[%s] Scheduling post_application_end_time_job', event_id)
    application_end_datetime = datetime.fromtimestamp(application_end_time, timezone.utc)
    job_datetime = application_end_datetime + timedelta(minutes=1)
    scheduler.add_job(
        verity_event_filters.post_application_end_time_job,
        'date',
        run_date=job_datetime,
        replace_existing=True,
        args=[w3, event_id],
        id=job_id)
    logger.info('[%s] Scheduled post_application_end_time_job at %s', event_id, job_datetime)


def init_event(scheduler, w3, contract_abi, event_id, contract_block_number):
    node_id = common.node_id()
    if not is_node_registered_on_event(w3, contract_abi, node_id, event_id):
        logger.info('[%s] Node %s is not included in the event', event_id, node_id)
        return
    if database.VerityEvent.get(event_id) is not None:
        logger.info('[%s] Event already exists in the database. Skipping it', event_id)
        return

    logger.info('[%s] Initializing event', event_id)
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    event = call_event_contract_for_metadata(contract_instance, event_id)
    if not event:
        logger.info('[%s] Cannot initialize event. Skipping it', event_id)
        return

    event.create()
    event_metadata = event.metadata()
    event_metadata.contract_block_number = contract_block_number
    event_metadata.previous_consensus_answers = common.consensus_answers_from_contract(
        contract_instance)
    event_metadata.update()
    verity_event_filters.init_event_filters(w3, contract_abi, event.event_id)
    schedule_post_application_end_time_job(scheduler, w3, event_id, event.application_end_time)
    schedule_consensus_not_reached_job(scheduler, event_id, event.event_end_time)
    logger.info('[%s] Event initialized', event_id)


def init_event_registry_filter(scheduler, w3, event_registry_abi, verity_event_abi,
                               event_registry_address):
    contract_instance = w3.eth.contract(address=event_registry_address, abi=event_registry_abi)
    from_block = contract_instance.functions.creationBlock().call()
    filter_ = contract_instance.events[NEW_VERITY_EVENT].createFilter(
        fromBlock=from_block, toBlock='latest')
    database.Filters.create(event_registry_address, filter_.filter_id, NEW_VERITY_EVENT)
    logger.info('[%s] Requesting all entries for %s from EventRegistry with filter_id: %s',
                event_registry_address, NEW_VERITY_EVENT, filter_.filter_id)
    entries = filter_.get_all_entries()
    process_new_verity_events(scheduler, w3, verity_event_abi, entries)


def recover_filter(scheduler, w3, verity_event_abi, event_registry_address, filter_id=None):
    logger.info('Recovering EventRegistry')
    filter_list = None
    if filter_id is not None:
        filter_list = [filter_id]
    try:
        database.Filters.delete_and_uninstall_filters(w3, event_registry_address, filter_list)
        event_registry_abi = common.event_registry_contract_abi()
        init_event_registry_filter(scheduler, w3, event_registry_abi, verity_event_abi,
                                   event_registry_address)
    except Exception as e:
        logger.info('Unexpected exception during EventRegistry recovery: %s', e)


def filter_event_registry(scheduler, w3, event_registry_address, verity_event_abi, formatters):
    """ Runs in a cron job and checks for new VerityEvents """
    filter_list = database.Filters.get_list(event_registry_address)
    if not filter_list:
        sleep_minutes = 5
        logger.info('[%s] EventRegistry empty filter list. Sleeping %d minutes',
                    event_registry_address, sleep_minutes)
        common.pause_job(scheduler, 'event_registry_filter', minutes=sleep_minutes)
        recover_filter(scheduler, w3, verity_event_abi, event_registry_address)
        return
    filter_id = filter_list[0]['filter_id']
    filter_ = w3.eth.filter(filter_id=filter_id)
    filter_.log_entry_formatter = formatters[NEW_VERITY_EVENT]
    try:
        entries = filter_.get_new_entries()
        database.EventRegistry.set_last_run_timestamp(int(time.time()))
    except ValueError as e:
        logger.info('[%s] EventRegistry ValueError filter_id: %s %s', event_registry_address,
                    filter_id, e)
        recover_filter(scheduler, w3, verity_event_abi, event_registry_address, filter_id)
        return
    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
        sleep_minutes = 5
        logger.info('[%s] EventRegistry %s exception. Sleeping for %d minutes then recover it',
                    event_registry_address, e.__class__.__name__, sleep_minutes)
        common.pause_job(scheduler, 'event_registry_filter', minutes=sleep_minutes)
        recover_filter(scheduler, w3, verity_event_abi, event_registry_address, filter_id)
        return
    except Exception:
        sleep_minutes = 5
        logger.exception(
            'EventRegistry unexpected exception. Sleeping for %d minutes then recover it',
            sleep_minutes)
        common.pause_job(scheduler, 'event_registry_filter', minutes=sleep_minutes)
        recover_filter(scheduler, w3, verity_event_abi, event_registry_address, filter_id)
        return
    process_new_verity_events(scheduler, w3, verity_event_abi, entries)
