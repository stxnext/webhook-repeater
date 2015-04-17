import argparse
import ConfigParser as configparser
import sys

from repeater.application import Repeater
from repeater.registry import bootstrap


marker = object()


class ConfigError(Exception):
    pass


def parse_settings(args, config, options):
    settings = {}
    for option, default, _type in options:
        val = getattr(args, option, marker)
        if val is not marker:
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
        elif default is not marker:
            settings[option] = default
        else:
            raise ConfigError('Missing option: %s' % option)
    return settings


def main(argv=sys.argv):

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default='config.ini')
    parser.add_argument('-p', '--port', type=int, default=marker)
    parser.add_argument('-H', '--host', type=str, default=marker)

    args = parser.parse_args(argv[1:])
    parser = configparser.ConfigParser()
    parser.read([args.config])

    server_options = [
        ('host', '0.0.0.0', str),
        ('port', 8080, int),
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
        ('timeout', 1, int),
    ]
    if parser.has_section('app'):
        config = dict(parser.items('app'))
    else:
        config = {}
    app_cfg = parse_settings(args, config, app_options)

    hook_params = ['src_host', 'src_path', 'dst_host', 'dst_path']
    hooks = {}
    paths = {}
    for section in parser.sections():
        if section.startswith('hook:'):
            hook = section[5:]
            hooks[hook] = dict(parser.items(section))
            for param in hook_params:
                val = hooks[hook].get(param)
                if val is None:  # empty strings are ok
                    sys.stderr.write(
                        'Error: missing parmeter "%s" for hook "%s"\n' % (
                            hook,
                            param
                        )
                    )
                    exit(1)
            hook_spec = hooks[hook]
            src_path = hook_spec['src_path']
            if not src_path.startswith('/'):
                src_path = hook_spec['src_path'] = '/%s' % src_path
            if src_path in paths:
                sys.stderr.write(
                    'Conflict: source path redefined: %s, %s, %s\n' % (
                        src_path,
                        hook,
                        paths[src_path]
                    )
                )
                exit(1)
            else:
                paths[src_path] = hook_spec

    if not hooks:
        sys.stderr.write('Error: No hooks defined\n')
        exit(1)

    registry = bootstrap(app_cfg)
    app = Repeater(hooks, registry)
    server = registry.construct_server(
        app,
        server_cfg['host'],
        server_cfg['port']
    )
    server.serve_forever()
