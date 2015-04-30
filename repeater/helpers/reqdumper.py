import argparse
import datetime
import sys

import gevent.wsgi
import webob
import webob.exc


class ReqDumper(object):

    def __init__(self, **settings):
        self.settings = settings
        self.file = settings['output']

    def __call__(self, environ, start_response):
        req = webob.Request(environ)
        resp = self.handle(req)
        return resp(environ, start_response)

    def handle(self, request):
        resp = webob.Response()
        resp.content_type = 'text/plain'
        env = ['%s = %s' % (k, v) for k, v in request.environ.items()]
        body = '%s\n\n%s' % (
            '\n'.join(env),
            request.environ['wsgi.input'].read()
        )
        resp.body = body
        self.file.write('\n=== New request from %s:%s %s ===\n\n' % (
            request.environ['REMOTE_ADDR'],
            request.environ['REMOTE_PORT'],
            datetime.datetime.now()
        ))
        self.file.write(body)
        self.file.flush()
        return resp


def main(argv=sys.argv):

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8989)
    parser.add_argument('-H', '--host', type=str, default='0.0.0.0')
    parser.add_argument('-o', '--output', type=str, default=None)

    args = parser.parse_args(argv[1:])
    if args.output:
        output = open(args.output, 'w')
    else:
        output = sys.stdout

    app = ReqDumper(output=output)
    server = gevent.wsgi.WSGIServer(
        (args.host, args.port),
        app
    )
    server.serve_forever()
