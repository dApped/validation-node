import logging

from database import events

logger = logging.getLogger('flask.app')


def filter_join_events(w3, contract_abi):
    node_events = events.get_all_events()
    for event in node_events:
        #if event.state != 1:
        #    continue
        contract_instance = w3.eth.contract(address=event.event_address, abi=contract_abi)
        logger.info('FILTERS  %s' % event.event_address)
        event_filter = contract_instance.events.JoinEvent.createFilter(
            fromBlock='earliest', toBlock='latest')
        entries = event_filter.get_all_entries()

        if not entries:
            continue
        participants = [entry['args']['wallet'] for entry in entries]


        events.store_participants(event.event_address, participants)
