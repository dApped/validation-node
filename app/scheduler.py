import logging

from apscheduler.schedulers.background import BackgroundScheduler

from events import events, filters

scheduler = BackgroundScheduler()

logger = logging.getLogger('flask.app')


def init():
    logger.info('Scheduler Init started')

    scheduler.add_job(filters.filter_events, 'interval', seconds=5, args=[events.w3])

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    logger.info('Scheduler Init done')
