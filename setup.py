# encoding=utf-8
import os
from setuptools import setup
from setuptools.command.test import test as TestCommand
import sys


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #  import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


dependencies = [
    'gevent',
    'redis',
    'webob',
    'wsgiproxy',
    'zope.interface',
]
test_dependencies = [
    'pytest',
    'mock',
]

setup(
    name='WebHook Repeater',
    version='0.99',
    author='Radosław Kintzi',
    author_email='r.kintzi@gmail.com',
    description=('Small web app which forwards http request'),
    license='BSD',
    keywords='example documentation tutorial',
    url='',
    packages=['repeater'],
    long_description=read('README.md'),
    classifiers=[
        'Development Status :: 1 - Beta',
        'Topic :: Web App',
        'License :: OSI Approved :: BSD License',
    ],
    entry_points={
        'console_scripts': [
            'webhook-repeater=repeater.main:main',
            'reqdumper=repeater.helpers.reqdumper:main',
        ],
    },
    install_requires=dependencies,
    tests_require=test_dependencies,
    cmdclass = {'test': PyTest},
)
