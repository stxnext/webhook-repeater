import json
import logging
import cStringIO as stringio

import webob
import webob.exc
import wsgiproxy.app
from zope.interface import implementer

from repeater.interfaces import IRequestSerializer


@implementer(IRequestSerializer)
class RequestSerializer(object):

    def loads(self, string):
        env = json.loads(string)
        env['wsgi.input'] = stringio.StringIO(env['X-REPEATER-BODY'])
        return webob.Request(env)

    def dumps(self, req):
        env = req.environ
        env['X-REPEATER-BODY'] = env['wsgi.input'].read()
        del env['wsgi.input']
        del env['wsgi.errors']
        return json.dumps(env)


class QueueHandler(object):

    def __init__(self, host, proxies, registry):
        self.host = host
        self.proxies = proxies
        self.requests = registry.construct_request_queue(host)
        self.greenlet = None
        self.concurrency = registry.get_concurrency_utils()
        self.lock = self.concurrency.semaphore()
        self.backoff = registry.settings['backoff_timeout']
        self.timeout = registry.settings['timeout']
        if self.requests:
            self._start()

    def _start(self):
        with self.lock:
            if not self.greenlet:
                self.greenlet = self.concurrency.spawn(self.handle)

    def push(self, request):
        self.requests.append(request)
        self._start()

    def handle(self):
        backoff = 0
        while self.requests:
            self.concurrency.sleep(backoff)
            while self.requests:
                req = self.requests.top()
                logging.debug('Trying to forward request: %s' % req.path)
                if self.forward(req):
                    self.requests.pop()
                    backoff = self.backoff
                    if self.requests:
                        self.concurrency.sleep(self.timeout)
                else:
                    break
            backoff = 2 * backoff if backoff else self.backoff
        with self.lock:
            self.greenlet = None

    def forward(self, request):
        try:
            proxy = self.proxies[request.path_info]
            response = request.get_response(proxy)
            if response.status_code != 200:
                logging.warn('HTTP Error: %s' % response.status)
                return False
            return True
        except IOError as e:
            logging.warn('IOError: %s' % str(e))
            return False


class Repeater(object):

    # 1. Repeater has one queue per destination (host:port)
    # 2. Each incoming request is put in proper destination queue
    # 3. Incoming request is matched to destination queue using PATH_INFO
    #
    # Wish list:
    # 4. Repeater verifies if incoming request comes from allowed IP

    queue_handler = QueueHandler  # for tests

    def __init__(self, hooks, registry):
        self.registry = registry
        self.paths = {}
        proxies = {}
        hosts = {}
        for hook_name, hook_spec in hooks.items():

            dst_host = hook_spec['dst_host']
            dst_path = hook_spec['dst_path']
            proxies[hook_name] = wsgiproxy.app.WSGIProxyApp(
                '%s%s' % (dst_host, dst_path)
            )

            if dst_host not in hosts:
                hosts[dst_host] = [hook_name]
            else:
                hosts[dst_host].append(hook_name)

        for host_name, hook_names in hosts.items():
            queue_proxies = {
                hooks[hook_name]['src_path']: proxies[hook_name]
                for hook_name in hook_names
            }
            queue = self.queue_handler(host_name, queue_proxies, registry)
            for hook_name in hook_names:
                src_path = hooks[hook_name]['src_path']
                self.paths[src_path] = queue

    def __call__(self, environ, start_response):
        req = webob.Request(environ)
        resp = self.handle(req)
        return resp(environ, start_response)

    def handle(self, request):
        queue = self.paths.get(request.path_info)
        if queue:
            queue.push(request.copy())
            response = webob.Response()
            response.status = '200 OK'
            response.content_type = 'text/plain'
            response.body = 'OK'
            return response
        return webob.exc.HTTPNotFound()
