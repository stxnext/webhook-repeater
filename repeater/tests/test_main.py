import unittest
import cStringIO as stringio

import mock

from repeater.main import (
    ConfigError,
    main,
    nodefault,
    parse_hooks,
    parse_settings,
)


class ArgsMock(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class ParseSettingsTestCase(unittest.TestCase):

    def setUp(self):
        self.args = ArgsMock(
            bool1=True,
            bool2=False,
            int1=10,
            float1=100.,
            str1="str1",
        )

        self.config = {
            'bool3': '1',
            'bool4': 'yes',
            'bool5': 'on',
            'bool6': 'true',
            'bool7': '0',
            'bool8': 'no',
            'bool9': 'off',
            'bool10': 'false',
            'int2': '20',
            'float2': '200.',
            'str2': 'str2'
        }

        self.spec = [
            ('bool1', nodefault, bool),
            ('bool2', nodefault, bool),
            ('bool3', nodefault, bool),
            ('bool4', nodefault, bool),
            ('bool5', nodefault, bool),
            ('bool6', nodefault, bool),
            ('bool7', nodefault, bool),
            ('bool8', nodefault, bool),
            ('bool9', nodefault, bool),
            ('bool10', nodefault, bool),
            ('bool11', False, bool),
            ('int1', nodefault, int),
            ('int2', nodefault, int),
            ('int3', 30, int),
            ('float1', nodefault, float),
            ('float2', nodefault, float),
            ('float3', 300., float),
            ('str1', nodefault, str),
            ('str2', nodefault, str),
            ('str3', 'str3', str),
        ]

        self.cfg = parse_settings(self.args, self.config, self.spec)

    def test_booleans(self):
        assert self.cfg['bool1']
        assert not self.cfg['bool2']
        assert self.cfg['bool3']
        assert self.cfg['bool4']
        assert self.cfg['bool5']
        assert self.cfg['bool6']
        assert not self.cfg['bool7']
        assert not self.cfg['bool8']
        assert not self.cfg['bool9']
        assert not self.cfg['bool10']
        assert not self.cfg['bool11']

    def test_ints(self):
        assert self.cfg['int1'] == 10
        assert self.cfg['int2'] == 20
        assert self.cfg['int3'] == 30

    def test_floats(self):
        assert self.cfg['float1'] == 100.
        assert self.cfg['float2'] == 200.
        assert self.cfg['float3'] == 300.

    def test_strings(self):
        assert self.cfg['str1'] == 'str1'
        assert self.cfg['str2'] == 'str2'
        assert self.cfg['str3'] == 'str3'

    def test_bad_type(self):
        with self.assertRaises(ConfigError):
            parse_settings(
                ArgsMock(),
                {'bool': 'not-bool'},
                [('bool', nodefault, bool)]
            )

        with self.assertRaises(ConfigError):
            parse_settings(
                ArgsMock(),
                {'int': 'not-int'},
                [('int', nodefault, int)]
            )

    def test_missing_config(self):
        with self.assertRaises(ConfigError):
            parse_settings(
                ArgsMock(),
                {},
                [('int', nodefault, int)]
            )


class ParseHookTestCase(unittest.TestCase):

    def setUp(self):
        self.sections = {
            'section': [('item1', 'val1'), ('item2', 'val2')],
            'hook:name1': [
                ('src_host', 'src_host1'),
                ('src_path', 'src_path1'),
                ('dst_host', 'dst_host1'),
                ('dst_path', 'dst_path1')
            ],
            'hook:name2': [
                ('src_host', 'src_host2'),
                ('src_path', '/src_path2'),
                ('dst_host', 'dst_host2'),
                ('dst_path', 'dst_path2')
            ]
        }
        self.config_parser = mock.Mock()
        self.config_parser.sections.return_value = [
            'section',
            'hook:name1',
            'hook:name2',
        ]

        def items(name):
            return self.sections[name]

        self.config_parser.items.side_effect = items

    def _items_side_effect(self, name):
        return self.sections[name]

    def test_parsed_hooks(self):
        hooks = parse_hooks(self.config_parser)
        assert 'name1' in hooks
        assert 'name2' in hooks
        assert len(hooks) == 2
        assert hooks['name1']['src_path'] == '/src_path1'
        assert hooks['name1']['src_host'] == 'src_host1'
        assert hooks['name1']['dst_path'] == 'dst_path1'
        assert hooks['name1']['dst_host'] == 'dst_host1'
        assert hooks['name2']['src_path'] == '/src_path2'
        assert hooks['name2']['src_host'] == 'src_host2'
        assert hooks['name2']['dst_path'] == 'dst_path2'
        assert hooks['name2']['dst_host'] == 'dst_host2'

        assert self.config_parser.sections.call_count == 1
        assert self.config_parser.items.call_count == 2
        args = [args[1][0] for args in self.config_parser.items.mock_calls]
        assert 'hook:name1' in args
        assert 'hook:name2' in args

    def test_no_hooks(self):
        self.config_parser.sections.side_effect = ['section']
        with self.assertRaises(ConfigError):
            parse_hooks(self.config_parser)

    def test_duplicated_source_paths(self):
        self.sections['hook:name2'][1] = ('src_path', '/src_path1')
        with self.assertRaises(ConfigError):
            parse_hooks(self.config_parser)

    def test_missing_options(self):
        section = list(self.sections['hook:name2'])
        for i in range(len(self.sections['hook:name2'])):
            self.sections['hook:name2'].pop(i)
            with self.assertRaises(ConfigError):
                parse_hooks(self.config_parser)
            self.sections['hook:name2'] = list(section)


class MainTestCase(unittest.TestCase):

    def setUp(self):
        self.argv = ['arg1', 'arg2', 'arg3']
        self.stderr = stringio.StringIO
        self.argument_parser_constructor = mock.Mock()
        self.argument_parser = self.argument_parser_constructor.return_value
        self.config_parser_constructor = mock.Mock()
        self.config_parser = self.config_parser_constructor.return_value
        self.parse_settings = mock.Mock()
        self.parse_hooks = mock.Mock()
        self.hooks = self.parse_hooks.return_value
        self.bootstrap = mock.Mock()
        self.repeater_constructor = mock.Mock()
        self.repeater = self.repeater_constructor.return_value
        self.registry = self.bootstrap.return_value
        self.server = self.registry.construct_server.return_value
        self.logging_config = mock.Mock()

    def call_main(self, argv=None):
        return main(
            argv=argv or self.argv,
            stderr=self.stderr,
            argument_parser=self.argument_parser_constructor,
            config_parser=self.config_parser_constructor,
            parse_settings=self.parse_settings,
            parse_hooks=self.parse_hooks,
            bootstrap=self.bootstrap,
            repeater=self.repeater_constructor,
            logging_config=self.logging_config,
        )

    def test_serve_app(self):
        app_cfg = {}
        server_cfg = {'host': 'host', 'port': 1234}
        self.config_parser.has_section.return_value = False
        self.parse_settings.side_effect = [server_cfg, app_cfg]
        self.call_main()
        self.bootstrap.mock_calls[0][1] == (app_cfg, )
        self.repeater_constructor.mock_calls[0][1] == (
            self.hooks,
            self.registry
        )
        assert self.registry.construct_server.mock_calls[0][1] == (
            self.repeater,
            'host',
            1234
        )
        assert self.server.serve_forever.call_count == 1
        assert self.logging_config.fileConfig.call_count == 1
