#!/usr/bin/env python3
# coding: utf8

import os
import logging
import logging.config

import gi
gi.require_versions({'Gtk': '3.0', 'GLib': '2.0', 'Gio': '2.0'})

from gi.repository import Gtk, GLib, Gio  # noqa

from .pac import Pac  # noqa
from .notify import Notify  # noqa

from .local import Local  # noqa

from .config import Config  # noqa
from .handler import Handler  # noqa
from .gsettings import SystemProxy # noqa

try:
    from shadowsocks.cryptor import method_supported  # noqa
except ImportError as e:
    from shadowsocks.encrypt import method_supported  # noqa


class Shadowsocks(Gtk.Application):
    ui = os.path.join(os.path.dirname(__file__), 'resources', 'shadowsocks.ui')
    methods = method_supported.keys()

    _signals = {
        'auto_connect': 'do_set_auto_connect',
        'auto_reconnect': 'do_set_auto_reconnect',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id='io.imop.shadowsocks',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs
        )
        self._logger()
        self.logger.info('Start...')
        self.window = None
        self.builder = Gtk.Builder()
        self.methods_map = {}

        self.notify = Notify()

        self.builder.add_from_file(self.ui)
        self.logger.debug('Load ui from {}'.format(self.ui))

        self.builder.connect_signals(Handler(self))
        self.logger.debug('Connect signal from class<Handler>')

        self._signal_for_pac_menu()
        self._signal_for_proxy_menu()
        self._signal_for_connection_menu()

        self._auto_connect()

        self.sslocal = Local()

    def _logger(self):
        logging.config.dictConfig(Config.logger)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def do_activate(self):
        if not self.window:
            self.logger.debug('Init window...')
            self.window = self.builder.get_object('ShadowsocksWindow')
            header = self.builder.get_object('HeaderBar')
            header.set_show_close_button(True)
            menu_button = self.builder.get_object('MenuButton')
            menu_button.set_popover(self.builder.get_object('MenuPop'))
            self.window.set_titlebar(header)
            self.window.set_application(self)
            self.create_server_view()
            self.create_supported_method_view()
        self.logger.debug('Show window...')
        self.window.show_all()

    def do_startup(self):
        self.logger.debug('Application start.')
        Gtk.Application.do_startup(self)

    def do_command_line(self, command_line):
        self.logger.debug('Application command line parser...')
        self.activate()
        return 0

    def do_set_auto_connect(self, action, state):
        self.logger.debug(
            'Auto_connect is selected. Current state is {}'.format(state)
        )
        action.set_state(state)
        Config.application.auto_connect = state.print_(True)
        Config.save_application()
        self._auto_connect()

    def do_set_auto_reconnect(self, action, state):
        self.logger.debug(
            'Auto_Reconnect is selected. Current state is {}'.format(state)
        )
        action.set_state(state)
        Config.application.auto_reconnect = state.print_(True)
        Config.save_application()

    def do_update_pac(self, *args):
        print(args)
        pac = Pac(Config)
        pac.fetch_remote_gfwlist()
        pac.fetch_user_rules()
        if pac.generate().save():
            self.notify.show('Successful to update gfwlist')
            return True
        self.notify.show('Failed to update gfwlist')
        return False

    def do_set_proxy(self, action, state):
        action.set_state(state)
        self.logger.info('Now proxy type is: {}'.format(state))
        Config.application.proxy_type = state.print_(True)
        Config.save_application()
        self._set_proxy(state.unpack())
        return True

    def _set_proxy(self, _type='auto'):
        if _type == 'auto':
            return SystemProxy().by_pac(Config.pac.path)
        elif _type == 'global':
            # TODO: get proxy setting
            return SystemProxy().global_proxy()
        elif _type == 'none':
            return SystemProxy().none_proxy()
        raise TypeError('Unknown proxy type: {}'.format(_type))

    def _auto_connect(self):
        if GLib.Variant.parse(Config.application.auto_connect).unpack():
            self.sslocal.control('start')
            return self._set_proxy(
                GLib.Variant.parse(Config.application.proxy_type).unpack()
            )
        return self.sslocal.control('stop')

    def create_server_view(self):
        self.logger.debug('Load view of server list...')
        server_list = Gtk.ListStore(str)
        for server in Config.servers.keys():
            server_list.append([server])
            self.logger.debug(
                'Append server<{}> to server list.'.format(server)
            )
        server_view = self.builder.get_object('ServerListView')
        server_view.set_model(server_list)
        self.builder.get_object('ServerSelection').select_path(Gtk.TreePath(0))
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('_Server_List', cell, text=0)
        server_view.append_column(column)
        self.logger.debug('Server list loaded.')

    def create_supported_method_view(self):
        self.logger.debug('Load view of crypt methods...')
        method_list = Gtk.ListStore(str)
        for method in self.methods:
            self.methods_map[method] = method_list.append([method])
        crypt_method_combo = self.builder.get_object("CryptMethodCombo")
        crypt_method_combo.set_model(method_list)
        cell = Gtk.CellRendererText()
        crypt_method_combo.pack_start(cell, True)
        crypt_method_combo.add_attribute(cell, "text", 0)
        self.logger.debug('Crypt methods list loaded.')

    def _signal_for_proxy_menu(self):
        proxy_radio = Gio.SimpleAction.new_stateful(
            'proxy_select',
            GLib.VariantType.new("s"),
            GLib.Variant("s", 'none')
        )
        proxy_radio.connect('activate', self.do_set_proxy)
        self.add_action(proxy_radio)
        self.logger.debug(
            'Proxy type from config: {}'.format(Config.application.proxy_type)
        )
        proxy_type = Config.application.proxy_type \
            if Config.application.proxy_type is not None else "'none'"
        proxy_radio.set_state(GLib.Variant.parse(None, proxy_type, None, None))

    def _signal_for_pac_menu(self):
        action = Gio.SimpleAction.new('update_pac', None)
        action.connect('activate', self.do_update_pac)
        self.add_action(action)

    def _signal_for_connection_menu(self):
        var_false = GLib.Variant.new_boolean(False)
        for signal, callback in self._signals.items():
            action = Gio.SimpleAction.new_stateful(signal, None, var_false)
            action.connect('change-state', getattr(self, callback))
            self.add_action(action)
            state = Config.application.get(signal, 'false')
            self.logger.debug('{} from config: {}'.format(signal, state))
            action.set_state(GLib.Variant.parse(None, state, None, None))


if __name__ == '__main__':
    import sys
    app = Shadowsocks()
    app.run(sys.argv)
