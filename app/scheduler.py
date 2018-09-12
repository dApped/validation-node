import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from web3 import HTTPProvider, Web3

import common
from events import filters

scheduler = BackgroundScheduler()

logger = logging.getLogger(__name__)


def init():
    logger.info('Scheduler Init started')
    provider = os.getenv('ETH_RPC_PROVIDER')
    w3 = Web3(HTTPProvider(provider))

    contract_abi = common.contract_abi()

    scheduler.add_job(
        filters.filter_join_events, 'interval', seconds=5, args=[w3, contract_abi, False])
    scheduler.add_job(filters.filter_join_events, args=[w3, contract_abi, True])

    logger.info('Scheduler Init done')
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
