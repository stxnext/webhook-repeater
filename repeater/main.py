import argparse as argparse
import ConfigParser as configparser
import logging.config
import sys

from repeater.application import Repeater as _Repeater
from repeater.registry import bootstrap as _bootstrap

nodefault = object()


class ConfigError(Exception):
    pass


def parse_settings(args, config, options):
    settings = {}
    for option, default, _type in options:
        val = getattr(args, option, nodefault)
        if val is not nodefault:
            settings[option] = val
        elif option in config:
            val = config[option]
            if _type is bool:
                if val in ['1', 'yes', 'on', 'true']:
                    val = True
                elif val in ['0', 'no', 'off', 'false']:
                    val = False
                else:
                    raise ConfigError(
                        'Expected boolean for option %s; got %s' % (
                            option,
                            val
                        )
                    )
            else:
                try:
                    val = _type(val)
                except:
                    raise ConfigError(
                        'Expected %s for option %s; got %s' % (
                            _type.__name__,
                            option,
                            val
                        )
                    )
            settings[option] = val
        elif default is not nodefault:
            settings[option] = default
        else:
            raise ConfigError('Missing option: %s' % option)
    return settings


def parse_hooks(config_parser):
    hook_params = ['src_host', 'src_path', 'dst_host', 'dst_path']
    hooks = {}
    paths = {}
    for section in config_parser.sections():
        if section.startswith('hook:'):
            hook = section[5:]
            hooks[hook] = dict(config_parser.items(section))
            for param in hook_params:
                val = hooks[hook].get(param)
                if val is None:  # empty strings are ok
                    raise ConfigError(
                        'Error: missing parmeter "%s" for hook "%s"\n' % (
                            param, hook)
                    )
            hook_spec = hooks[hook]
            src_path = hook_spec['src_path']
            if not src_path.startswith('/'):
                src_path = hook_spec['src_path'] = '/%s' % src_path
            if src_path in paths:
                raise ConfigError(
                    'Conflict: source path redefined: %s, %s, %s\n' % (
                        src_path,
                        hook,
                        paths[src_path]
                    )
                )
            else:
                paths[src_path] = hook_spec
    if not hooks:
        raise ConfigError('Error: No hooks defined\n')
    return hooks


def main(
        argv=sys.argv,
        stderr=sys.stderr,
        argument_parser=argparse.ArgumentParser,
        config_parser=configparser.ConfigParser,
        parse_settings=parse_settings,
        parse_hooks=parse_hooks,
        bootstrap=_bootstrap,
        repeater=_Repeater,
        logging_config=logging.config):
    try:
        parser = argument_parser()
        parser.add_argument(
            '-c',
            '--config',
            default='config.ini',
            help='Path to config file (default: ./config.init)'
        )
        parser.add_argument(
            '-p',
            '--port',
            type=int,
            default=nodefault,
            help='Port to listen on (default: 8100)'
        )
        parser.add_argument(
            '-H',
            '--host',
            type=str,
            default=nodefault,
            help='Interface to bind to (default: 0.0.0.0)'
        )
        args = parser.parse_args(argv[1:])

        logging_config.fileConfig(args.config)

        parser = config_parser()
        parser.read([args.config])

        server_options = [
            ('host', '0.0.0.0', str),
            ('port', 8100, int),
        ]
        config = {}
        if parser.has_section('server'):
            config = dict(parser.items('server'))
        else:
            config = {}
        server_cfg = parse_settings(args, config, server_options)

        app_options = [
            ('redis_host', 'localhost', str),
            ('redis_port', 6379, int),
            ('redis_db', 0, int),
            ('backoff_timeout', 60, int),
            ('backoff_max_timeout', 3600, int),
            ('timeout', 1, int),
            ('secret', nodefault, str)
        ]
        if parser.has_section('app'):
            config = dict(parser.items('app'))
        else:
            config = {}
        app_cfg = parse_settings(args, config, app_options)

        hooks = parse_hooks(parser)

        registry = bootstrap(app_cfg)
        app = repeater(hooks, registry)
        server = registry.construct_server(
            app,
            server_cfg['host'],
            server_cfg['port']
        )
        server.serve_forever()
    except ConfigError as e:
        stderr.write('%s\n' % str(e))
