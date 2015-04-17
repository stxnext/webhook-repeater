# Notes for hackers
# (from http://docs.zope.org/zope.interface/README.html#declaring-interfaces):
#
# 1. We say that objects provide interfaces. If an object provides
# an interface then the interface specifies the behavior of the object.
# In other words, interfaces specify the behavior of the objects that provide
# them.
#
# 2. We normally say that classes implement interfaces. If a class
# implements an interface, then the instances of the class provide the
# interface. Objects provide interfaces that their classes implement.


from zope.interface import Interface


class IServerConstructor(Interface):

    def __call__(app, host=None, port=None):
        """
        Construct the server capable to serve WSGI application.

        app - application to serve
        host - interface to bind to
        port - the port to listen on

        Returns IServer provider
        """


class IServer(Interface):

    def serve_forever():
        """
        Enter the loop and serve requests.
        """


class IConcurrencyUtils(Interface):

    def spawn(func):
        """
        Spawn the new thread that will execute given function

        func - function to execute in new thread
        """

    def semaphore():
        """
        Construct new semaphore

        Returns an implementation of ISemaphore
        """

    def sleep(sec):
        """
        Hold an execution for given time

        sec - time in seconds (as float) to wait
        """


class ISemaphore(Interface):

    def __enter__():
        """
        Lock the semaphore. If the lock can not be acquired wait.
        """

    def __exit__(exc_type, exc_value, traceback):
        """
        Unlock the semaphore.
        """


class IRequestQueueConstructor(Interface):

    def __call__(self, name):
        """
        Construct new queue with given name

        Returns newly created queue
        """


class IRequestQueue(Interface):

    """
    FIFO queue that stores requests
    """

    def append(req):
        """
        Add new request to the end of the queue

        req - request to append to queue
        """

    def pop():
        """
        Pop the request from the beginning of the queue
        """

    def first():
        """
        Returns the first request from the queues
        """

    def __nonzero__():
        """
        Returns True if and only if the queue is not empty
        """


class IRequestSerializer(Interface):

    def loads(string):
        """
        Deserialize request from string

        string - the string representation of request

        Returns request
        """

    def dumps(req):
        """
        Serialize the request to string.

        req - request to serialize

        Returns string representation of given request
        """
