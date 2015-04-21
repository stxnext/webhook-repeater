import unittest

import mock

from repeater.gevent_server import GEventServer


class GEventServerTestCase(unittest.TestCase):

    def setUp(self):
        self.app = object()
        self.server = GEventServer(self.app, 'host', 1234)
        self.wsgi_mod = self.server.wsgi = mock.Mock()
        self.wsgi_server = self.wsgi_mod.WSGIServer.return_value

    def test_serve_forever(self):
        self.server.serve_forever()
        assert self.wsgi_mod.WSGIServer.call_count == 1
        assert self.wsgi_mod.WSGIServer.mock_calls[0][1] == (
            ('host', 1234),
            self.app
        )
        assert self.wsgi_server.serve_forever.call_count == 1
        assert self.wsgi_server.serve_forever.mock_calls[0][1] == ()
