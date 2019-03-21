import logging
import queue
import threading
import time
import uuid

logger = logging.getLogger()

QUEUE_IN = queue.Queue()
RESULTS_DICT = {}


class Job:
    def __init__(self, event_id, contract_function_name, function, *args):
        self.id_ = uuid.uuid4()
        self.event_id = event_id
        self.contract_function_name = contract_function_name
        self.function = function
        self.args = args


class JobResult:
    def __init__(self, id_, event_id, result):
        self.id_ = id_
        self.event_id = event_id
        self.result = result


def run_queue_worker(queue_in, results_dict):
    while True:
        try:
            job = queue_in.get(block=False)
        except queue.Empty:
            job = None

        if job is None:
            time.sleep(1)
            continue

        logger.info('[%s][%s] Queue executing %s job. Queue size: %d', job.event_id, job.id_,
                    job.contract_function_name, queue_in.qsize())
        result = job.function(*job.args)
        queue_in.task_done()
        results_dict[job.id_] = JobResult(job.id_, job.event_id, result)
        logger.info('[%s][%s] Queue completed the job', job.event_id, job.id_)


def init():
    logger.info('Queue Service Init started')
    t = threading.Thread(
        target=run_queue_worker, args=(
            QUEUE_IN,
            RESULTS_DICT,
        ))
    t.start()
    logger.info('Queue Service Init done')
