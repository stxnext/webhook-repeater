import cStringIO as stringio
import pickle
import unittest

import webob
import mock

from repeater.application import (
    RequestSerializer,
    QueueHandler,
    Repeater,
    sign_request
)


class RequestSerializerTestCase(unittest.TestCase):
    def setUp(self):
        self.serializer = RequestSerializer()
        self.body = 'body'
        self.request = mock.Mock()
        self.request.environ = {
            'wsgi.input': stringio.StringIO(self.body),
            'wsgi.errors': None,
            'key1': 'value1',
            'key2': 'value2',
            'webob._body_file': "body_file"
        }
        self.string = pickle.dumps({
            "key1": "val1",
            "key2": "val2",
            "X-REPEATER-BODY": "body"
        })

    def test_serialize(self):
        string = self.serializer.dumps(self.request)
        assert "key2" in string
        assert "value2" in string
        assert "key1" in string
        assert "value1" in string
        assert "X-REPEATER-BODY" in string
        assert "body" in string

    def test_deserialize(self):
        req = self.serializer.loads(self.string)
        assert req.environ['key1'] == 'val1'
        assert req.environ['key2'] == 'val2'
        assert req.environ['wsgi.input'].read() == 'body'


class QueueMock(object):
    def __init__(self, queue=[]):
        self.queue = queue

    def append(self, req):
        self.queue.append(req)

    def pop(self):
        self.queue.pop(0)

    def top(self):
        return self.queue[0]

    def __nonzero__(self):
        return bool(self.queue)


class QueueHandlerTestCase(unittest.TestCase):
    def setUp(self):
        self.registry = mock.Mock()
        self.registry.settings = {
            'backoff_timeout': 1,
            'backoff_max_timeout': 4,
            'timeout': 2
        }

        self.queue = []
        queue_mock = QueueMock(self.queue)
        self.registry.construct_request_queue.return_value = queue_mock
        concurrency_utils = self.registry.get_concurrency_utils.return_value
        self.semaphore = concurrency_utils.semaphore.return_value
        self.semaphore.__exit__ = mock.Mock()
        self.semaphore.__enter__ = mock.Mock()
        self.concurrency_utils = concurrency_utils
        self.path1_proxy = object()
        self.path2_proxy = object()
        self.proxies = {
            'path1': self.path1_proxy,
            'path2': self.path2_proxy
        }

    def test_push(self):
        handler = QueueHandler('name', self.proxies, self.registry)
        request = mock.Mock()
        handler.push(request)

        assert self.queue[0] == request

    def test_spawn_on_push(self):
        handler = QueueHandler('name', self.proxies, self.registry)
        request = mock.Mock()
        handler.push(request)

        sem = self.semaphore
        assert sem.__enter__.call_count == sem.__exit__.call_count
        assert self.concurrency_utils.spawn.call_count == 1

    def test_spawn_form_constructor(self):
        self.queue[:] = [object()]
        QueueHandler('name', self.proxies, self.registry)

        sem = self.semaphore
        assert sem.__enter__.call_count == sem.__exit__.call_count
        assert self.concurrency_utils.spawn.call_count == 1

    def test_forwarding(self):
        req = mock.Mock()
        req.path_info = 'path1'
        resp = mock.Mock()
        resp.status_code = 200
        req.get_response.return_value = resp
        self.queue[:] = [req]
        QueueHandler('name', self.proxies, self.registry)

        worker = self.concurrency_utils.spawn.mock_calls[0][1][0]
        worker()
        assert not self.queue
        assert req.get_response.mock_calls[0][1] == (self.path1_proxy,)
        assert self.concurrency_utils.sleep.call_count == 0

    def test_forwarding_two_requests(self):
        req1 = mock.Mock()
        req1.path_info = 'path1'
        req2 = mock.Mock()
        req2.path_info = 'path2'
        resp = mock.Mock()
        resp.status_code = 200
        req1.get_response.return_value = resp
        req2.get_response.return_value = resp
        self.queue[:] = [req1, req2]
        QueueHandler('name', self.proxies, self.registry)

        worker = self.concurrency_utils.spawn.mock_calls[0][1][0]
        worker()
        assert not self.queue
        assert req1.get_response.mock_calls[0][1] == (self.path1_proxy,)
        assert req2.get_response.mock_calls[0][1] == (self.path2_proxy,)
        assert self.concurrency_utils.sleep.call_count == 1
        assert self.concurrency_utils.sleep.mock_calls[0][1] == (2,)

    def test_forwarding_until_400(self):
        """
        Test forwarding requests until any response will came from
        remote (in this case 400).
        """
        req = mock.Mock()
        req.path_info = 'path1'
        resp1 = mock.Mock()
        resp1.status_code = 400
        req.get_response.side_effect = [IOError(), IOError(), resp1]
        self.queue[:] = [req]
        QueueHandler('name', self.proxies, self.registry)

        worker = self.concurrency_utils.spawn.mock_calls[0][1][0]
        worker()
        assert not self.queue
        assert req.get_response.mock_calls[0][1] == (self.path1_proxy,)
        assert req.get_response.mock_calls[1][1] == (self.path1_proxy,)
        assert req.get_response.mock_calls[2][1] == (self.path1_proxy,)
        assert req.get_response.call_count == 3
        assert self.concurrency_utils.sleep.mock_calls[0][1] == (1,)
        assert self.concurrency_utils.sleep.mock_calls[1][1] == (2,)
        assert self.concurrency_utils.sleep.call_count == 2

    def test_forwarding_two_requests_with_fail(self):
        """
        Test forwarding requests until any response will came from
        remote (in this case 200).
        """
        req1 = mock.Mock()
        req1.path_info = 'path1'
        req2 = mock.Mock()
        req2.path_info = 'path2'
        resp = mock.Mock()
        resp.status_code = 200
        req1.get_response.side_effect = [IOError(), resp]
        req2.get_response.return_value = resp
        self.queue[:] = [req1, req2]
        QueueHandler('name', self.proxies, self.registry)

        worker = self.concurrency_utils.spawn.mock_calls[0][1][0]
        worker()
        assert not self.queue
        assert req1.get_response.mock_calls[0][1] == (self.path1_proxy,)
        assert req1.get_response.mock_calls[1][1] == (self.path1_proxy,)
        assert req1.get_response.call_count == 2
        assert req2.get_response.mock_calls[0][1] == (self.path2_proxy,)
        assert req2.get_response.call_count == 1
        assert self.concurrency_utils.sleep.mock_calls[0][1] == (1,)
        assert self.concurrency_utils.sleep.mock_calls[1][1] == (2,)
        assert self.concurrency_utils.sleep.call_count == 2

    def test_max_backoff(self):
        req1 = mock.Mock()
        req1.path_info = 'path1'
        resp = mock.Mock()
        resp.status_code = 200
        req1.get_response.side_effect = [
            IOError(),
            IOError(),
            IOError(),
            IOError(),
            resp
        ]
        self.queue[:] = [req1]
        QueueHandler('name', self.proxies, self.registry)

        worker = self.concurrency_utils.spawn.mock_calls[0][1][0]
        worker()
        assert not self.queue
        assert self.concurrency_utils.sleep.mock_calls[0][1] == (1,)
        assert self.concurrency_utils.sleep.mock_calls[1][1] == (2,)
        assert self.concurrency_utils.sleep.mock_calls[2][1] == (4,)
        assert self.concurrency_utils.sleep.mock_calls[3][1] == (4,)
        assert self.concurrency_utils.sleep.call_count == 4

    def test_forwarding_raise_exception(self):
        """
        Test catching exception raised by forward method.
        """
        req1 = mock.Mock()
        req1.path_info = 'path1'
        req2 = mock.Mock()
        req2.path_info = 'path2'
        resp = mock.Mock()
        resp.status_code = 200
        req1.get_response.side_effect = [KeyError(), resp]
        req2.get_response.return_value = resp
        self.queue[:] = [req1, req2]
        proxies = {
            'path1': '',
        }
        QueueHandler('name', proxies, self.registry)

        worker = self.concurrency_utils.spawn.mock_calls[0][1][0]
        worker()
        assert self.queue
        assert req1.get_response.mock_calls[0][1] == ('',)
        assert req1.get_response.call_count == 1
        assert len(req2.get_response.mock_calls) == 0
        assert self.concurrency_utils.sleep.mock_calls == []


class RepeaterTestCase(unittest.TestCase):
    def setUp(self):
        self.registry = mock.Mock()
        self.registry.settings = {
            'backoff_timeout': 1,
            'timeout': 2,
            'secret': 'secret'
        }
        concurrency_utils = self.registry.get_concurrency_utils.return_value
        self.semaphore = concurrency_utils.semaphore.return_value
        self.semaphore.__exit__ = mock.Mock()
        self.semaphore.__enter__ = mock.Mock()
        self.concurrency_utils = concurrency_utils
        self.hooks = {
            'hook1': {
                'src_host': 'src_host1',
                'src_path': '/src_path1',
                'dst_host': 'dst_host1',
                'dst_path': '/dst_path1',
            },
            'hook2': {
                'src_host': 'src_host3',
                'src_path': '/src_path2',
                'dst_host': 'dst_host1',  # dst_host1 by purpose
                'dst_path': '/dst_path2',
            },
            'hook3': {
                'src_host': 'src_host3',
                'src_path': '/src_path3',
                'dst_host': 'dst_host3',
                'dst_path': '/dst_path3',
            },
        }
        self.orig_queue_handler = Repeater.queue_handler
        self.orig_proxy = Repeater.proxy
        self.handlers = [mock.Mock(), mock.Mock()]
        self.queue_handler = mock.Mock()
        self.queue_handler.side_effect = self._queue_handler_side_effect
        self.proxy = mock.Mock()
        self.proxies = [object(), object(), object()]
        self.proxy.side_effect = self._proxy_side_effect
        Repeater.queue_handler = self.queue_handler
        Repeater.proxy = self.proxy
        self.repeater = Repeater(self.hooks, self.registry)

    def tearDown(self):
        Repeater.queue_handler = self.orig_queue_handler
        Repeater.proxy = self.orig_proxy

    def _queue_handler_side_effect(self, host, *args):
        if host == 'dst_host1':
            return self.handlers[0]
        elif host == 'dst_host3':
            return self.handlers[1]

    def _proxy_side_effect(self, host_port):
        if host_port == 'dst_host1/dst_path1':
            return self.proxies[0]
        elif host_port == 'dst_host1/dst_path2':
            return self.proxies[1]
        elif host_port == 'dst_host3/dst_path3':
            return self.proxies[2]

    def _test_constructor(self, args):
        assert args[0] in ['dst_host3', 'dst_host1']
        if args[0] == 'dst_host3':
            assert len(args[1]) == 1
            assert args[1]['/src_path3'] == self.proxies[2]
        elif args[0] == 'dst_host1':
            assert len(args[1]) == 2
            assert args[1]['/src_path1'] == self.proxies[0]
            assert args[1]['/src_path2'] == self.proxies[1]
        assert args[2] == self.registry

    def test_constructor(self):
        assert self.queue_handler.call_count == 2
        args1 = self.queue_handler.mock_calls[0][1]
        self._test_constructor(args1)
        args2 = self.queue_handler.mock_calls[1][1]
        self._test_constructor(args2)
        args = [args[1][0] for args in self.proxy.mock_calls]
        assert len(args) == 3
        assert 'dst_host1/dst_path1' in args
        assert 'dst_host1/dst_path2' in args
        assert 'dst_host3/dst_path3' in args

    def test_request(self):
        req = webob.Request.blank('/src_path1')
        req.remote_addr = 'src_host1'
        req.get_response(self.repeater)
        req_copy = self.handlers[0].push.mock_calls[0][1][0]
        assert req_copy.path_info == '/src_path1'
        assert self.handlers[0].push.call_count == 1

        req = webob.Request.blank('/src_path2')
        req.remote_addr = 'src_host3'
        req.get_response(self.repeater)
        req_copy = self.handlers[0].push.mock_calls[1][1][0]
        assert req_copy.path_info == '/src_path2'
        assert self.handlers[0].push.call_count == 2

        req = webob.Request.blank('/src_path3')
        req.remote_addr = 'src_host3'
        req.get_response(self.repeater)
        req_copy = self.handlers[1].push.mock_calls[0][1][0]
        assert req_copy.path_info == '/src_path3'
        assert self.handlers[1].push.call_count == 1

    def test_request_catch_http_not_found(self):
        """
        Test catching exception when in Jira wrong path was set
        """
        self.hooks['hook1']['src_host'] = ''
        repeater = Repeater(self.hooks, self.registry)
        req = webob.Request.blank('/src_path1')
        response = req.get_response(repeater)
        assert len(self.handlers[0].push.mock_calls) == 0
        assert self.handlers[0].push.call_count == 0
        assert response.status_code == 404

    def test_request_catch_http_forbidden(self):
        """
        Test catching exception when different src_host was set in config
        file and from different remote_host send jira request.
        """
        self.hooks['hook1']['src_path'] = '/wrong_path'
        repeater = Repeater(self.hooks, self.registry)
        req = webob.Request.blank('/wrong_path')
        response = req.get_response(repeater)
        assert len(self.handlers[0].push.mock_calls) == 0
        assert self.handlers[0].push.call_count == 0
        assert response.status_code == 403


class SignRequestTestCase(unittest.TestCase):
    def test_sign_request(self):
        req = webob.Request.blank('/')
        req.body = 'ala ma kota'
        req = sign_request(req, 'secret')
        sig = req.headers['X-REPEATER-SIG']
        assert sig == '65a415c101d8103bc3866bfe9d5dc818'
