import logging

from database import events

logger = logging.getLogger('flask.app')

JOIN_EVENT = 'JoinEvent'
ERROR = 'Error'
EVENTS = [JOIN_EVENT, ERROR]


def init_event_filters(w3, contract_abi, event_id):
    contract_instance = w3.eth.contract(address=event_id, abi=contract_abi)
    for event_name in EVENTS:
        logger.info('Initializing %s filter for %s event', event_name, event_id)
        event_filter = contract_instance.events[event_name].createFilter(
            fromBlock='earliest', toBlock='latest')
        events.Filters.create(event_id, event_filter.filter_id)
        logger.info('Requesting all entries for %s filter for %s event', event_name, event_id)
        entries = event_filter.get_all_entries()
        if not entries:
            continue
        process_entries(w3, event_name, event_id, entries)


def filter_events(w3):
    '''filter_events runs in a cron job and requests new entries for all events'''
    event_ids = events.Event.get_ids_list()
    for event_id in event_ids:
        filter_ids = events.Filters.get_list(event_id)
        for event_name, filter_id in zip(EVENTS, filter_ids):
            event_filter = w3.eth.filter(filter_id=filter_id)
            entries = event_filter.get_new_entries()
            if not entries:
                continue
            process_entries(w3, event_name, event_id, entries)


def process_entries(w3, event_name, event_id, entries):
    if event_name == JOIN_EVENT:
        process_join_events(w3, event_id, entries)
    elif event_name == ERROR:
        process_error_events(event_id, entries)
    else:
        logger.error('Unknown event name for event_id %s, %s', event_id, event_name)


def process_join_events(w3, event_id, entries):
    logger.info('Adding %d %s entries for %s event', len(entries), JOIN_EVENT, event_id)
    participants = [w3.eth.getTransaction(entry['transactionHash'])['from'] for entry in entries]
    events.Participants.create(event_id, participants)


def process_error_events(event_id, entries):
    for entry in entries:
        logger.error('event_id: %s, %s', event_id, entry)
