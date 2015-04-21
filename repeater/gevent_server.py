import gevent.wsgi
from zope.interface import (
    implementer,
    provider,
)

from repeater.interfaces import (
    IServerConstructor,
    IServer,
)


@provider(IServerConstructor)  # The class provides IServerProvider
@implementer(IServer)  # Instance of the class provides IServer
class GEventServer(object):

    wsgi = gevent.wsgi

    def __init__(self, app, host=None, port=None):
        self.host = host or '0.0.0.0'
        self.port = port or 8180
        self.app = app

    def serve_forever(self):
        srv = self.wsgi.WSGIServer(
            (self.host, self.port),
            self.app
        )
        srv.serve_forever()
