from .coroutines import (IOQueue, QueueConnection, coroutine_sink)
from .scheduler import (run_job, Scheduler)
from ..datamodel import (get_workflow)
import threading


@coroutine_sink
def splice_sink(a, b):
    while True:
        value = yield
        b.send(value)
        a.send(value)


def siphon_source(source, sink):
    for value in source:
        sink.send(value)
        yield value


class Logger(IOQueue):
    def __init__(self):
        super(Logger, self).__init__()

    @coroutine_sink
    def job_sink(self):
        msg_sink = self.sink()
        while True:
            key, job = yield
            msg_sink.send(('start', key, job))

    @coroutine_sink
    def result_sink(self):
        msg_sink = self.sink()
        while True:
            key, status, result = yield
            msg_sink.send((status, key, result))


def logging_worker(n_threads, display):
    """Sets up a number of threads, each polling for jobs.

    :param n_threads:
        Number of threads to spawn.
    :type n_threads: int

    :param display:
        Display routine; gets passed information about jobs
        running.
    :type display: coroutine sink

    :returns:
        Connection to the job and result queues
    :rtype: :py:class:`Connection`
    """
    job_q = IOQueue()
    result_q = IOQueue()

    worker_connection = QueueConnection(job_q, result_q)
    scheduler_connection = QueueConnection(result_q, job_q)

    log = Logger()

    def worker(source, sink):
        splice = splice_sink(sink, log.result_sink())
        for key, job in siphon_source(source, log.job_sink()):
            try:
                result = run_job(job)
                splice.send((key, 'done', result))

            except Exception as error:
                splice.send((key, 'error', error))

    for i in range(n_threads):
        t = threading.Thread(
            target=worker,
            args=worker_connection.setup())

        t.daemon = True
        t.start()

    t_log = threading.Thread(target=display, args=(log,))
    t_log.daemon = True
    t_log.start()

    return scheduler_connection


def run_logging(wf, n_threads, display):
    """
    Returns the result of evaluating the workflow; runs in several threads.

    :param wf:
        Workflow to compute
    :type wf: :py:class:`Workflow` or :py:class:`PromisedObject`

    :param display:
        Display routine; gets passed information about jobs
        running.
    :type display: coroutine sink

    :param n_threads:
        Number of threads to use
    :type n_threads: int

    :param error_handler:
        Function to run in case a worker returns an error.
    """
    worker = logging_worker(n_threads, display)
    return Scheduler(error_handler=display.error_handler)\
        .run(worker, get_workflow(wf))