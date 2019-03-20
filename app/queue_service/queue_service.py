import logging
import queue
import threading
import time

logger = logging.getLogger()

QUEUE_IN = queue.Queue()
QUEUE_OUT = queue.Queue()


def run_queue_worker(queue_in, queue_out):
    while True:
        try:
            job = queue_in.get(block=False)
        except queue.Empty:
            job = None

        if job is None:
            time.sleep(1)
            continue

        func = job[0]
        args = job[1:]
        logger.info('Received job with %s %s', func, args)
        result = func(*args)
        queue_in.task_done()
        queue_out.put(result)


def init():
    logger.info('Queue Service Init started')
    t = threading.Thread(
        target=run_queue_worker, args=(
            QUEUE_IN,
            QUEUE_OUT,
        ))
    t.start()
    logger.info('Queue Service Init done')
