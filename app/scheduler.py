import logging

from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

from events import filters
from ethereum.provider import EthProvider
scheduler = BackgroundScheduler(timezone=utc)

logger = logging.getLogger('flask.app')


def init():
    logger.info('Scheduler Init started')

    w3 = EthProvider().web3()
    scheduler.add_job(filters.filter_events, 'interval', seconds=5, args=[w3])

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    logger.info('Scheduler Init done')
