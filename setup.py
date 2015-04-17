import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


dependencies = [
    'gevent',
    'redis',
    'webob',
    'wsgiproxy',
    'zope.interface',
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
)
