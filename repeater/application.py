import cPickle as pickle
import hmac
import StringIO as stringio
import logging

import webob
import webob.exc
import wsgiproxy.app

from zope.interface import implementer

from log import webhook_logger
from repeater.interfaces import IRequestSerializer


def sign_request(request, secret):
    body = request.body  # by purpose to compute missing content_length
    msg = request.content_type + str(request.content_length) + body
    sig = hmac.new(secret, msg).hexdigest()
    request.headers['X-REPEATER-SIG'] = sig
    return request


@implementer(IRequestSerializer)
class RequestSerializer(object):
    def loads(self, string):
        env = pickle.loads(string)
        env['wsgi.input'] = stringio.StringIO(
            env['X-REPEATER-BODY']
        )
        return webob.Request(env)

    def dumps(self, req):
        env = req.environ
        env['X-REPEATER-BODY'] = env['wsgi.input'].read()
        del env['wsgi.input']
        del env['wsgi.errors']
        if 'webob._body_file' in env:
            del env['webob._body_file']
        return pickle.dumps(env)


class QueueHandler(object):
    # This is a so-called queue handler. We got one for each remote host:port.
    # It stores requests addressed for endpoints on the host:port
    # and delivers them when possible.

    def __init__(self, host, proxies, registry):
        self.host = host
        self.proxies = proxies
        self.requests = registry.construct_request_queue(host)
        self.handler = None
        self.concurrency = registry.get_concurrency_utils()
        self.lock = self.concurrency.semaphore()
        self.backoff = registry.settings['backoff_timeout']
        self.max_backoff = registry.settings['backoff_max_timeout']
        self.timeout = registry.settings['timeout']
        if self.requests:
            self._start()

    def push(self, request):
        self.requests.append(request)
        self._start()

    def _start(self):
        with self.lock:
            if not self.handler:
                self.handler = self.concurrency.spawn(self._handle)

    def _handle(self):
        # This is executed in separate thread/coroutine
        # It tries to empty request queue. We wait self.timeout seconds
        # between to requests (we don't want to kill Intranet). In case
        # of remote endpoint failure we wait self.backoff seconds and double
        # that on each consecutive failure (until we reach self.max_backoff).
        # When queue is empty we simply exists.
        try:
            backoff = 0
            while self.requests:
                if backoff:
                    self.concurrency.sleep(backoff)
                while self.requests:
                    req = self.requests.top()
                    logging.info('Trying to forward request: '
                                 '%s' % req.path)
                    if self._forward(req):
                        self.requests.pop()
                        backoff = self.backoff
                        if self.requests:
                            self.concurrency.sleep(self.timeout)
                    else:
                        break
                backoff = 2 * backoff if backoff else self.backoff
                if backoff > self.max_backoff:
                    backoff = self.max_backoff
            with self.lock:
                self.handler = None
        except Exception as error:
            webhook_logger.exception('Greenlet failed with unexcepted '
                                     'error\n{}'.format(error))
            with self.lock:
                self.handler = None

    def _forward(self, request):
        """
        Method try to get response from proxy server. If server
        process somehow request and return any response, such request
        can be forwarded. If connection errors occur such request
        should be processed once again.
        """
        try:
            proxy = self.proxies[request.path_info]
            request.get_response(proxy)
            return True
        except IOError as e:
            webhook_logger.warn('IOError: %s' % str(e))
            return False


class Repeater(object):
    # 1. Repeater verifies if incoming request comes from allowed IP
    # 2. Repeater has one queue per destination (host:port)
    # 3. Each incoming request is put in proper destination queue based
    #    on PATH_INFO
    # 4. When request is forwarded it is signed using secret

    queue_handler = QueueHandler  # for tests
    proxy = wsgiproxy.app.WSGIProxyApp  # for tests

    def __init__(self, hooks, registry):
        self.registry = registry
        self.secret = registry.settings['secret']
        self.paths = {}
        proxies = {}
        hosts = {}
        for hook_name, hook_spec in hooks.items():

            dst_host = hook_spec['dst_host']
            dst_path = hook_spec['dst_path']
            proxies[hook_name] = self.proxy('%s%s' % (dst_host, dst_path))

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
                src_host = hooks[hook_name]['src_host']
                self.paths[src_path] = (src_host, queue)

    def __call__(self, environ, start_response):
        req = webob.Request(environ)
        resp = self._handle(req)
        return resp(environ, start_response)

    def _handle(self, request):
        host, queue = self.paths.get(request.path_info, (None, None))
        if not host:
            webhook_logger.error("host: {} not found ! Request path info "
                                 "was: {}. Please check webhook settings "
                                 "in Jira.".format(host, request.path_info))
            return webob.exc.HTTPNotFound()
        remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
        if remote_addr != host:
            webhook_logger.error("access denied, remote_address:{} but "
                                 "expected: {}".format(remote_addr, host))
            return webob.exc.HTTPForbidden()
        request = sign_request(request.copy(), self.secret)
        queue.push(request)
        response = webob.Response()
        response.status = '200 OK'
        response.content_type = 'text/plain'
        response.body = 'OK'
        return response
