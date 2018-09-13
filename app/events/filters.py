import logging

from database import events

logger = logging.getLogger('flask.app')

JOIN_EVENT = 'JoinEvent'
ERROR = 'Error'
EVENTS = [JOIN_EVENT, ERROR]


def init_filters_for_event(w3, contract_abi, event_id):
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    for event_name in EVENTS:
        event_filter = contract_instance.events[event_name].createFilter(
            fromBlock='earliest', toBlock='latest')
        events.Filters.push(event_id, event_filter.filter_id)
        entries = event_filter.get_all_entries()
        if not entries:
            continue
        process_entries(event_name, event_id, entries)


def filter_events(w3):
    event_ids = events.event_ids()
    for event_id in event_ids:
        filter_ids = events.Filters.lrange(event_id)
        for event_name, filter_id in zip(EVENTS, filter_ids):
            event_filter = w3.eth.filter(filter_id=filter_id)
            entries = event_filter.get_new_entries()
            if not entries:
                continue
            process_entries(event_name, event_id, entries)


def process_entries(event_name, event_id, entries):
    if event_name == JOIN_EVENT:
        process_join_events(event_id, entries)
    elif event_name == ERROR:
        process_error_events(event_id, entries)
    else:
        logger.error('Unknown event name for event_id %s, %s', event_id, event_name)


def process_join_events(event_id, entries):
    logger.info("Adding %d %s entries", len(entries), JOIN_EVENT)
    participants = [entry['args']['wallet'] for entry in entries]
    events.store_participants(event_id, participants)


def process_error_events(event_id, entries):
    for entry in entries:
        logger.error("event_id: %s, %s", event_id, entry)
