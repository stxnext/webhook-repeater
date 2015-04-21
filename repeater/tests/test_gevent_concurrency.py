import unittest

import mock

from repeater.gevent_concurrency import (
    GEventConcurrencyUtils,
    GEventSemaphore,
)


class GEventConcurrencyUtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.orig_gevent_mod = GEventConcurrencyUtils.gevent_mod
        self.gevent_mod = GEventConcurrencyUtils.gevent_mod = mock.Mock()
        self.utils = GEventConcurrencyUtils()
        self.semaphore_class = self.utils.semaphore_class = mock.Mock()

    def tearDown(self):
        GEventConcurrencyUtils.gevent_mod = self.orig_gevent_mod

    def test_spawn(self):
        func = object()
        self.utils.spawn(func)
        assert self.gevent_mod.spawn.call_count == 1
        assert self.gevent_mod.spawn.mock_calls[0][1] == (func, )

    def test_sleep(self):
        sec = 10
        self.utils.sleep(sec)
        assert self.gevent_mod.sleep.call_count == 1
        assert self.gevent_mod.sleep.mock_calls[0][1] == (sec, )

    def test_semaphore(self):
        expected_sem = self.semaphore_class.return_value
        sem = self.utils.semaphore()
        assert sem == expected_sem
        assert self.semaphore_class.call_count == 1
        assert self.semaphore_class.mock_calls[0][1] == ()


class GEventSemaphoreTestCase(unittest.TestCase):

    def setUp(self):
        self.orig_gevent_mod = GEventSemaphore.gevent_mod
        self.gevent_mod = GEventSemaphore.gevent_mod = mock.Mock()
        self.semaphore_impl = self.gevent_mod.lock.Semaphore.return_value
        self.semaphore = GEventSemaphore()

    def tearDown(self):
        GEventSemaphore.gevent_mod = self.orig_gevent_mod

    def test_constuctor(self):
        assert self.gevent_mod.lock.Semaphore.call_count == 1
        assert self.gevent_mod.lock.Semaphore.mock_calls[0][1] == ()

    def test_context_protocol(self):
        with self.semaphore:
            assert self.semaphore_impl.acquire.call_count == 1
            assert self.semaphore_impl.release.call_count == 0

        assert self.semaphore_impl.acquire.call_count == 1
        assert self.semaphore_impl.release.call_count == 1

        assert self.semaphore_impl.acquire.mock_calls[0][1] == ()
        assert self.semaphore_impl.release.mock_calls[0][1] == ()
