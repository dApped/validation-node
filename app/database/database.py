import os
import redis

redis_db = redis.StrictRedis(host=os.getenv('REDIS_URL', '127.0.0.1'), port=6379, db=0)
