import logging

from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

import common
from ethereum.provider import NODE_WEB3
from events import event_registry_filter, verity_event_filters

scheduler = BackgroundScheduler(timezone=utc)

logger = logging.getLogger('flask.app')


def init():
    logger.info('Scheduler Init started')

    event_registry_address = common.event_registry_address()
    event_registry_abi = common.event_registry_contract_abi()
    verity_event_abi = common.verity_event_contract_abi()

    event_registry_filter_names = [event_registry_filter.NEW_VERITY_EVENT]
    event_registry_formatters = verity_event_filters.log_entry_formatters(
        event_registry_abi, event_registry_filter_names)

    verity_event_filter_names = [name for name, _ in verity_event_filters.EVENT_FILTERS]
    verity_event_formatters = verity_event_filters.log_entry_formatters(
        verity_event_abi, verity_event_filter_names)

    scheduler.add_job(
        verity_event_filters.filter_events,
        'interval',
        seconds=5,
        args=[NODE_WEB3, verity_event_formatters])

    scheduler.add_job(
        event_registry_filter.filter_event_registry,
        'interval',
        seconds=5,
        args=[NODE_WEB3, event_registry_address, verity_event_abi, event_registry_formatters])

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    logger.info('Scheduler Init done')
