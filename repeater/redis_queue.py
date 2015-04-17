
import redis
from zope.interface import implementer

from repeater.interfaces import (
    IRequestQueue,
    IRequestQueueConstructor,
)


@implementer(IRequestQueueConstructor)
class RedisQueueConstructor(object):

    def __init__(self, registry):
        self.registry = registry
        self.redis = None

    def __call__(self, name):
        if not self.redis:
            settings = self.registry.settings
            self.redis = redis.Redis(
                host=settings['redis_host'],
                port=settings['redis_port'],
                db=settings['redis_db']
            )
        return RedisQueue(name, self.redis, self.registry)


@implementer(IRequestQueue)
class RedisQueue(object):

    def __init__(self, name, redis, registry):
        self.registry = registry
        self.redis = redis
        self.name = name

    def append(self, req):
        serializer = self.registry.get_request_serializer()
        string = serializer.dumps(req)
        self.redis.rpush(self.name, string)

    def pop(self):
        self.redis.lpop(self.name)

    def top(self):
        string = self.redis.lrange(self.name, 0, 0)[0]
        serializer = self.registry.get_request_serializer()
        return serializer.loads(string)

    def __nonzero__(self):
        return self.redis.llen(self.name)
