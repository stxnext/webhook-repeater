import unittest

import mock

from repeater.registry import (
    bootstrap,
    Registry,
)


class RegistryTestCase(unittest.TestCase):

    def setUp(self):
        self.orig_components_class = Registry.components_class
        self.orig_default_components = Registry.default_components
        self.components_class = Registry.components_class = mock.Mock()
        self.default_components = Registry.default_components = mock.Mock()
        self.components = self.components_class.return_value

    def tearDown(self):
        Registry.components_class = self.orig_components_class
        Registry.default_components = self.orig_components_class

    def test_default_initialization(self):
        self.components.queryUtility.return_value = None
        settings = object()
        registry = bootstrap(settings)
        assert self.components_class.call_count == 1
        assert self.components.queryUtility.call_count == 4
        assert self.components.registerUtility.call_count == 4
        calls = self.components.registerUtility.mock_calls
        calls = [call[1][0] for call in calls]
        default_components = self.default_components
        assert default_components.ConcurrencyUtils.return_value in calls
        assert default_components.ServerConstructor in calls
        assert default_components.RequestSerializer.return_value in calls
        assert default_components.QueueConstructor.return_value in calls
        queue_cons = self.default_components.QueueConstructor
        assert queue_cons.mock_calls[0][1] == (registry, )

    def test_get_concurrency_utils(self):
        utils = object()
        registry = bootstrap(object())
        self.components.queryUtility.return_value = utils
        assert registry.get_concurrency_utils() == utils

    def test_get_request_serializer(self):
        serializer = object()
        registry = bootstrap(object())
        self.components.queryUtility.return_value = serializer
        assert registry.get_request_serializer() == serializer

    def test_construct_server(self):
        constructor = mock.Mock()
        app = object()
        registry = bootstrap(object())
        self.components.queryUtility.return_value = constructor
        server = registry.construct_server(app, 'host', 1234)
        assert server == constructor.return_value
        assert constructor.call_count == 1
        assert constructor.mock_calls[0][1] == (app, 'host', 1234)

    def test_construct_request_queue(self):
        constructor = mock.Mock()
        registry = bootstrap(object())
        self.components.queryUtility.return_value = constructor
        server = registry.construct_request_queue('name')
        assert server == constructor.return_value
        assert constructor.call_count == 1
        assert constructor.mock_calls[0][1] == ('name', )
