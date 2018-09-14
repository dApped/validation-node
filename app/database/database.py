import logging
import os

import redis

logger = logging.getLogger('flask.app')
redis_db = redis.StrictRedis(
    host=os.getenv('REDIS_URL', '127.0.0.1'), port=6379, db=0, decode_responses=True)


def flush_database():
    logger.info('Flushing database')
    redis_db.flushdb()
