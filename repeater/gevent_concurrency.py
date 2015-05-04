"""
This module provides utilities for concurrency. See interfaces.py
for documentation.
"""
import gevent
import gevent.lock
import gevent.monkey
from zope.interface import implementer

from repeater.interfaces import (
    IConcurrencyUtils,
    ISemaphore,
)


@implementer(ISemaphore)
class GEventSemaphore(object):

    gevent_mod = gevent

    def __init__(self):
        self.sem = self.gevent_mod.lock.Semaphore()

    def __enter__(self):
        self.sem.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.sem.release()


@implementer(IConcurrencyUtils)
class GEventConcurrencyUtils(object):

    gevent_mod = gevent
    semaphore_class = GEventSemaphore

    def __init__(self):
        # need this because of wsgiproxy (which use httplib)
        # and redis-py (which use standard socket module)
        self.gevent_mod.monkey.patch_socket()
        self.gevent_mod.monkey.patch_ssl()

    def spawn(self, func):
        self.gevent_mod.spawn(func)

    def semaphore(self):
        return self.semaphore_class()

    def sleep(self, sec):
        self.gevent_mod.sleep(sec)
