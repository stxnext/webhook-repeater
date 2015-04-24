# WebHook Repeater

*WebHook Repeater* is small web application that receives http requests 
and forwards them to remote endpoints (see bellow to find out how to configure 
what is forwarded where). If remote endpoint is temporary incapable to accept 
requests, Repeater stores them in Redis database and tries to deliver later.

## Installation

First of all you need persistent Redis database.

To install Repeater you simply do:

```

$ python setup.py install
```

Of course in development environment you should use ``virtualenv`` 
or something similar.

To run installed repeater:

```
$ webhook-repeater
```

Don't even try to run more than one Repeater process at once 
(eg. behind nginx as load balancer). Never!

## Configuration

See ``config.ini`` for documentation how to configure Repeater. 

Additionally Repeater accepts following command line options:


```
$ webhook-repeater -h
usage: webhook-repeater [-h] [-c CONFIG] [-p PORT] [-H HOST]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to config file (default: ./config.init)
  -p PORT, --port PORT  Port to listen on (default: 8100)
  -H HOST, --host HOST  Interface to bind to (default: 0.0.0.0)
```

## Notes for hackers

See above for installation instruction. 

Tests are run using ``pytest.org``:

```
$ python setup.py test
```

or using helper bash scirpt:

```
$ ./py.test
```

You can supply arguments for ``pytest.org```:

```
$ python setup.py test -a "arg1 arg2"
```

or:

```
$ ./py.test arg1 arg2
```

You can use provided helper script to simulate remote endpoints:

```
$ reqdumper -h
usage: reqdumper [-h] [-p PORT] [-H HOST] [-o OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT
  -H HOST, --host HOST
  -o OUTPUT, --output OUTPUT
```

### Code structure

Repeater is written to be easy to refactoring. It consists of few loosely 
coupled components (see ``interfaces.py`` for its specification):

1. ``IRequestQueue`` and ``IRequestQueueConstuctor`` are the persistence
   layer, which is is implemented based on Redis in ``redis_queue.py``

2. ``IConcurrencyUtils`` is a component that provides some utilities for
   concurrency (``spawn``, ``sleep``, etc.). ``ISemaphore`` 
   provides locks. They are implemented based on ``gevent`` in 
   ``gevent_concurrency.py``

3. ``IServer`` and ``IServerConstructor`` are used to serve application. 
   The implementation is based on ``gevent`` and may be found
   ``gevent_server.py``

4. ``IRequestSerializer`` provide utilities for dumping/loading 
   request to/form string. The implementation may be found 
   in ``application.py``

5. All this components was gathered together in so-called ``registry`` 
in file ``registry.py``. If you want provide other implementation for one 
of those components simply put it in separate module and change 
``registry.py`` (you can even provide configuration option, which will 
allow to choose one of the implementations at runtime)

6. The main logic is implemented in ``application.py``. It base on
   ``webob`` as simple web framework and ``paste.proxy`` as request
   forwarder

7. ``main.py`` is responsible for configuration parsing and for 
   application bootstrapping

**Happy hacking!**
