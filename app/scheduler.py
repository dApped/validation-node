import logging

from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

import common
from ethereum.provider import EthProvider
from events import filters

scheduler = BackgroundScheduler(timezone=utc)

logger = logging.getLogger('flask.app')


def init():
    logger.info('Scheduler Init started')

    w3 = EthProvider().web3()
    contract_abi = common.verity_event_contract_abi()
    formatters = filters.log_entry_formatters(contract_abi)
    scheduler.add_job(filters.filter_events, 'interval', seconds=5, args=[w3, formatters])

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    logger.info('Scheduler Init done')
