from zope.interface.registry import Components

from repeater.application import RequestSerializer as _RequestSerializer
from repeater.gevent_concurrency import GEventConcurrencyUtils
from repeater.gevent_server import GEventServer
from repeater.interfaces import (
    IConcurrencyUtils,
    IRequestQueueConstructor,
    IRequestSerializer,
    IServerConstructor,
)
from repeater.redis_queue import RedisQueueConstructor


class DefaultComponents(object):
    ConcurrencyUtils = GEventConcurrencyUtils
    ServerConstructor = GEventServer
    RequestSerializer = _RequestSerializer
    QueueConstructor = RedisQueueConstructor


class Registry(object):

    components_class = Components
    default_components = DefaultComponents

    def __init__(self, settings, _components=None):
        self.settings = settings
        self._components = _components or self.components_class()

        if not self._components.queryUtility(IConcurrencyUtils):
            self._components.registerUtility(
                self.default_components.ConcurrencyUtils()
            )

        if not self._components.queryUtility(IServerConstructor):
            self._components.registerUtility(
                self.default_components.ServerConstructor
            )

        if not self._components.queryUtility(IRequestSerializer):
            self._components.registerUtility(
                self.default_components.RequestSerializer()
            )

        if not self._components.queryUtility(IRequestQueueConstructor):
            self._components.registerUtility(
                self.default_components.QueueConstructor(self)
            )

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
