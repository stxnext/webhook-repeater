import mock
import unittest

from repeater.redis_queue import (
    RedisQueue,
    RedisQueueConstructor,
)


class RedisQueueConstructorTestCase(unittest.TestCase):

    def setUp(self):
        self.registry = mock.Mock()
        self.registry.settings = {
            'redis_host': 'host',
            'redis_port': 1234,
            'redis_db': 0,
        }
        self.constructor = RedisQueueConstructor(self.registry)
        self.redis_queue = self.constructor.redis_queue = mock.Mock()
        self.redis_mod = self.constructor.redis_mod = mock.Mock()
        self.redis_inst = self.redis_mod.Redis.return_value

    def test_constructor(self):
        queue = self.constructor('name')
        assert self.redis_mod.Redis.call_count == 1
        assert self.redis_mod.Redis.mock_calls[0][2] == {
            'host': 'host',
            'port': 1234,
            'db': 0
        }
        assert self.redis_queue.call_count == 1
        assert self.redis_queue.mock_calls[0][1] == (
            'name',
            self.redis_inst,
            self.registry
        )
        assert queue == self.redis_queue.return_value

        expected_queue = self.redis_queue.return_value = mock.Mock()
        queue = self.constructor('name2')
        assert self.redis_queue.call_count == 2
        assert self.redis_queue.mock_calls[1][1] == (
            'name2',
            self.redis_inst,
            self.registry
        )
        assert queue == expected_queue


class RedisQueueTestCase(unittest.TestCase):

    def setUp(self):
        self.redis_inst = mock.Mock()
        self.registry = mock.Mock()
        self.get_serializer = self.registry.get_request_serializer
        self.serializer = self.get_serializer.return_value
        self.queue = RedisQueue('name1', self.redis_inst, self.registry)

    def test_append(self):
        request = object()
        dump = self.serializer.dumps.return_value
        self.queue.append(request)
        assert self.serializer.dumps.call_count == 1
        assert self.serializer.dumps.mock_calls[0][1] == (request, )
        assert self.redis_inst.rpush.call_count == 1
        assert self.redis_inst.rpush.mock_calls[0][1] == ('name1', dump)

    def test_pop(self):
        self.queue.pop()
        assert self.redis_inst.lpop.call_count == 1
        assert self.redis_inst.lpop.mock_calls[0][1] == ('name1', )

    def test_top(self):
        dump = object()
        obj = object()
        self.redis_inst.lrange.return_value = [dump]
        self.serializer.loads.return_value = obj
        retval = self.queue.top()
        assert retval == obj
        assert self.redis_inst.lrange.call_count == 1
        assert self.redis_inst.lrange.mock_calls[0][1] == ('name1', 0, 0)
        assert self.serializer.loads.call_count == 1
        assert self.serializer.loads.mock_calls[0][1] == (dump, )

    def test_nonzero(self):
        self.redis_inst.llen.return_value = 10
        assert bool(self.queue)
        assert self.redis_inst.llen.call_count == 1
        assert self.redis_inst.llen.mock_calls[0][1] == ('name1', )

        self.redis_inst.llen.return_value = 0
        assert not bool(self.queue)
        assert self.redis_inst.llen.call_count == 2
        assert self.redis_inst.llen.mock_calls[1][1] == ('name1', )
