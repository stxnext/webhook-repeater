import gevent
import gevent.lock
import gevent.monkey
from zope.interface import implementer

from repeater.interfaces import (
    IConcurrencyUtils,
    ISemaphore,
)


@implementer(IConcurrencyUtils)
class GEventConcurrencyUtils(object):

    def __init__(self):
        # need this because of wsgiproxy (which use httplib)
        # and redis-py (which use standard socket module)
        gevent.monkey.patch_socket()

    def spawn(self, func):
        gevent.spawn(func)

    def semaphore(self):
        return GEventSemaphore()

    def sleep(self, sec):
        gevent.sleep(sec)


@implementer(ISemaphore)
class GEventSemaphore(object):

    def __init__(self):
        self.sem = gevent.lock.Semaphore()

    def __enter__(self):
        self.sem.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.sem.release()
