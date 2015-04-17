from zope.interface.registry import Components

from repeater.application import RequestSerializer
from repeater.gevent_concurrency import GEventConcurrencyUtils
from repeater.gevent_server import GEventServer
from repeater.interfaces import (
    IConcurrencyUtils,
    IRequestQueueConstructor,
    IRequestSerializer,
    IServerConstructor,
)
from repeater.redis_queue import RedisQueueConstructor


class Registry(object):

    def __init__(self, settings, _components=None):
        self.settings = settings
        self._components = _components or Components()

        if not self._components.queryUtility(IConcurrencyUtils):
            self._components.registerUtility(GEventConcurrencyUtils())

        if not self._components.queryUtility(IServerConstructor):
            self._components.registerUtility(GEventServer)

        if not self._components.queryUtility(IRequestSerializer):
            self._components.registerUtility(RequestSerializer())

        if not self._components.queryUtility(IRequestQueueConstructor):
            self._components.registerUtility(RedisQueueConstructor(self))

    def get_concurrency_utils(self):
        return self._components.queryUtility(IConcurrencyUtils)

    def get_request_serializer(self):
        return self._components.queryUtility(IRequestSerializer)

    def construct_server(self, app, host=None, port=None):
        constructor = self._components.queryUtility(IServerConstructor)
        return constructor(app, host, port)

    def construct_request_queue(self, name):
        constructor = self._components.queryUtility(IRequestQueueConstructor)
        return constructor(name)


def bootstrap(settings, _components=None):
    return Registry(settings, _components)
