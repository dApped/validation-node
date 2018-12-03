import logging

import common
from database import database
from events import verity_event_filters

logger = logging.getLogger()

NEW_VERITY_EVENT = 'NewVerityEvent'


def process_new_verity_events(w3, event_contract_abi, entries):
    for entry in entries:
        event_address = entry['args']['eventAddress']
        init_event(w3, event_contract_abi, event_address)


def is_node_registered_on_event(w3, contract_abi, node_id, event_id):
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    node_ids = contract_instance.functions.getEventResolvers().call()
    node_ids = set(node_ids)
    return node_id in node_ids


def call_event_contract_for_metadata(w3, contract_abi, event_id):
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)

    state = contract_instance.functions.getState().call()
    if state > 2:
        logger.info(
            '[%s] Skipping event with state: %d. It is not in waiting|application|running state',
            event_id, state)
        return None

    owner = contract_instance.functions.owner().call()
    token_address = contract_instance.functions.tokenAddress().call()
    node_addresses = contract_instance.functions.getEventResolvers().call()
    (application_start_time, application_end_time, event_start_time, event_end_time,
     leftovers_recoverable_after) = contract_instance.functions.getEventTimes().call()
    event_name = contract_instance.functions.eventName().call()
    data_feed_hash = contract_instance.functions.dataFeedHash().call()
    is_master_node = contract_instance.functions.isMasterNode().call()
    consensus_rules = contract_instance.functions.getConsensusRules().call()
    (min_total_votes, min_consensus_votes, min_consensus_ratio, min_participant_ratio,
     max_participants, rewards_distribution_function) = consensus_rules
    validation_round = contract_instance.functions.rewardsValidationRound().call()
    ((dispute_amount, dispute_timeout, dispute_multiplier, dispute_round),
     disputer) = contract_instance.functions.getDisputeData().call()
    staking_amount = contract_instance.functions.stakingAmount().call()
    event = database.VerityEvent(
        event_id, owner, token_address, node_addresses, leftovers_recoverable_after,
        application_start_time, application_end_time, event_start_time, event_end_time, event_name,
        data_feed_hash, state, is_master_node, min_total_votes, min_consensus_votes,
        min_consensus_ratio, min_participant_ratio, max_participants, rewards_distribution_function,
        validation_round, dispute_amount, dispute_timeout, dispute_multiplier, dispute_round,
        disputer, staking_amount)
    return event


def init_event(w3, contract_abi, event_id):
    node_id = common.node_id()
    if not is_node_registered_on_event(w3, contract_abi, node_id, event_id):
        logger.info('[%s] Node %s is not included in the event', event_id, node_id)
        return
    logger.info('[%s] Initializing event', event_id)

    event = call_event_contract_for_metadata(w3, contract_abi, event_id)
    if not event:
        return
    event.create()
    verity_event_filters.init_event_filters(w3, contract_abi, event.event_id)
    logger.info('[%s] Event initialized', event_id)


def init_event_registry_filter(w3, event_registry_abi, verity_event_abi, event_registry_address):
    contract_instance = w3.eth.contract(address=event_registry_address, abi=event_registry_abi)
    filter_ = contract_instance.events[NEW_VERITY_EVENT].createFilter(
        fromBlock='earliest', toBlock='latest')
    database.Filters.create(event_registry_address, filter_.filter_id)
    logger.info('[%s] Requesting all entries for %s from EventRegistry', event_registry_address,
                NEW_VERITY_EVENT)
    entries = filter_.get_all_entries()
    process_new_verity_events(w3, verity_event_abi, entries)


def filter_event_registry(w3, event_registry_address, verity_event_abi, formatters):
    '''filter_event_registry runs in a cron job and checks for new events'''
    filter_id = database.Filters.get_list(event_registry_address)[0]
    filter_ = w3.eth.filter(filter_id=filter_id)
    filter_.log_entry_formatter = formatters[NEW_VERITY_EVENT]
    entries = filter_.get_new_entries()
    process_new_verity_events(w3, verity_event_abi, entries)
