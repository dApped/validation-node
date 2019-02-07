import logging

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

import common
from database import database
from ethereum.provider import NODE_WEB3
from events import event_registry_filter, node_registry, verity_event_filters

scheduler = BackgroundScheduler(timezone=utc)

logger = logging.getLogger()


class SchedulerFilter(logging.Filter):
    @staticmethod
    def filter(record):
        if record.msg.find('Running job') >= 0:
            return False
        if record.msg.find('executed successfully') >= 0:
            return False
        return True


def configure_scheduler_logging():
    # Disable logging of cron jobs
    scheduler_filter = SchedulerFilter()
    logging.getLogger('apscheduler.executors.default').addFilter(scheduler_filter)
    logging.getLogger('apscheduler.executors.default').propagate = True
    logging.getLogger('apscheduler.executors.default').setLevel(logging.INFO)
    logging.getLogger('apscheduler.scheduler').setLevel(logging.ERROR)


def remove_job(job_id):
    try:
        scheduler.remove_job(job_id)
        logger.info('Job successfully removed: %s', job_id)
        return True
    except JobLookupError as e:
        logger.info(e)
    except Exception as e:
        logger.exception(e)
    return False


def init():
    logger.info('Scheduler Init started')
    configure_scheduler_logging()

    node_registry_address = database.ContractAddress.node_registry()
    event_registry_address = database.ContractAddress.event_registry()
    event_registry_abi = common.event_registry_contract_abi()
    verity_event_abi = common.verity_event_contract_abi()
    node_registry_abi = common.node_registry_contract_abi()

    event_registry_filter_names = [event_registry_filter.NEW_VERITY_EVENT]
    event_registry_formatters = verity_event_filters.log_entry_formatters(
        event_registry_abi, event_registry_filter_names)

    verity_event_filter_names = list(verity_event_filters.EVENT_FILTERS.keys())
    verity_event_formatters = verity_event_filters.log_entry_formatters(
        verity_event_abi, verity_event_filter_names)

    scheduler.add_job(
        verity_event_filters.filter_events,
        'interval',
        seconds=10,
        args=[scheduler, NODE_WEB3, verity_event_formatters],
    )

    scheduler.add_job(
        event_registry_filter.filter_event_registry,
        'interval',
        seconds=10,
        args=[
            scheduler, NODE_WEB3, event_registry_address, verity_event_abi,
            event_registry_formatters
        ],
        id='event_registry_filter')

    scheduler.add_job(
        node_registry.update_node_ips,
        'interval',
        seconds=60,
        args=[node_registry_abi, node_registry_address])
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    logger.info('Scheduler Init done')
