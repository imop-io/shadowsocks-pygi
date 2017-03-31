#!/usr/bin/env python3
# coding: utf8

import os
import logging
import logging.config

from gettext import gettext as _

from gi.repository import Gtk, GLib, Gio  # noqa

from .pac import Pac
from .local import Local
from .notify import Notify
from .config import Config
from .handler import Handler
from .gsettings import SystemProxy

from .tasks import AsyncCall

try:
    from shadowsocks.cryptor import method_supported
except ImportError as e:
    from shadowsocks.encrypt import method_supported


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
        self.logger.info(_('Start..'))
        self.window = None
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain('shadowsocks-pygi')
        self.methods_map = {}

        self.notify = Notify()

        self.sslocal = Local()

        self.builder.add_from_file(self.ui)
        self.logger.debug(_('Load ui from {}').format(self.ui))

        self.builder.connect_signals(Handler(self))
        self.logger.debug(_('Connect signal from class<Handler>'))

        self._signal_for_pac_menu()
        self._signal_for_proxy_menu()
        self._signal_for_connection_menu()

        self.create_notification()

        self._auto_connect()

    def _logger(self):
        logging.config.dictConfig(Config.logger)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def do_activate(self):
        if not self.window:
            self.logger.debug(_('Init window..'))
            self.window = self.builder.get_object('ShadowsocksWindow')
            header = self.builder.get_object('HeaderBar')
            header.set_show_close_button(True)
            menu_button = self.builder.get_object('MenuButton')
            menu_button.set_popover(self.builder.get_object('MenuPop'))
            self.window.connect(
                'delete-event',
                lambda x, y: self.logger.debug(_('Window delete event.'))
            )
            self.window.set_titlebar(header)
            self.window.set_application(self)
            self.create_server_view()
            self.create_supported_method_view()
        self.logger.debug(_('Show window..'))
        self.window.show_all()

    def do_startup(self):
        self.logger.debug(_('Application start.'))
        Gtk.Application.do_startup(self)

    def do_destroy(self):
        self.logger.debug(_('Application stop.'))
        self.m.stop()

    def do_command_line(self, command_line):
        self.logger.debug(_('Application command line parser..'))
        self.activate()
        return 0

    def do_set_auto_connect(self, action, state):
        self.logger.debug(
            _('Auto_connect is selected. Current state is {}').format(state)
        )
        action.set_state(state)
        Config.application.auto_connect = state.print_(True)
        Config.save_application()
        self._auto_connect()

    def do_set_auto_reconnect(self, action, state):
        self.logger.debug(
            _('Auto_Reconnect is selected. Current state is {}').format(state)
        )
        action.set_state(state)
        Config.application.auto_reconnect = state.print_(True)
        Config.save_application()

    def do_update_pac(self, action, state):
        def func(*args):
            self.logger.debug(_('Ready to update pac file..'))
            pac = Pac(Config)
            pac.fetch_remote_gfwlist()
            pac.fetch_user_rules()
            if pac.generate().save():
                self.notify.show(_('Successful to update gfwlist'))
                return True
            self.notify.show(_('Failed to update gfwlist'))
        return AsyncCall(func, None)

    def do_set_proxy(self, action, state):
        action.set_state(state)
        self.logger.info(_('Now proxy type is: {}').format(state))
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
        raise TypeError(_('Unknown proxy type: {}').format(_type))

    def _auto_connect(self):
        auto_connect = Config.application.auto_connect
        auto_connect = GLib.Variant.parse(None, auto_connect, None, None)
        if auto_connect.unpack():
            self.builder.get_object('ConnectionControl').set_state(True)
            proxy_type = Config.application.proxy_type
            return self._set_proxy(
                GLib.Variant.parse(None, proxy_type, None, None).unpack()
            )
        return AsyncCall(self.sslocal.control, 'stop')

    def create_notification(self):
        self.register()
        self.notification = Gio.Notification.new(self.get_application_id())
        self.notification.set_body('Startup.')
        icon = Gio.ThemedIcon.new('network-vpn-symbolic')
        self.notification.set_icon(icon)
        self.send_notification('state', self.notification)

    def create_menu_view(self):
        self.menu = Gtk.Menu()
        quit = Gtk.MenuItem('Quit')
        quit.connect('activate', lambda item: self.quit())
        self.menu.append(quit)
        self.menu.show_all()

    def create_server_view(self):
        self.logger.debug(_('Load view of server list..'))
        server_list = Gtk.ListStore(str)
        for server in Config.servers.keys():
            server_list.append([server])
            self.logger.debug(
                _('Append server<{}> to server list.').format(server)
            )
        server_view = self.builder.get_object('ServerListView')
        server_view.set_model(server_list)
        self.builder.get_object('ServerSelection').select_path(Gtk.TreePath(0))
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_('_Server_List'), cell, text=0)
        server_view.append_column(column)
        self.logger.debug(_('Server list loaded.'))

    def create_supported_method_view(self):
        self.logger.debug(_('Loading view of crypt methods.'))
        method_list = Gtk.ListStore(str)
        for method in self.methods:
            self.methods_map[method] = method_list.append([method])
        crypt_method_combo = self.builder.get_object("CryptMethodCombo")
        crypt_method_combo.set_model(method_list)
        cell = Gtk.CellRendererText()
        crypt_method_combo.pack_start(cell, True)
        crypt_method_combo.add_attribute(cell, "text", 0)
        self.logger.debug(_('Crypt methods list loaded.'))

    def _signal_for_proxy_menu(self):
        proxy_radio = Gio.SimpleAction.new_stateful(
            'proxy_select',
            GLib.VariantType.new("s"),
            GLib.Variant("s", 'none')
        )
        proxy_radio.connect('activate', self.do_set_proxy)
        self.add_action(proxy_radio)
        proxy_type = Config.application.proxy_type \
            if Config.application.proxy_type is not None else "'none'"
        proxy_radio.set_state(GLib.Variant.parse(None, proxy_type, None, None))
        self.logger.debug(_('Proxy type from config: {}').format(proxy_type))

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
            self.logger.debug(_('{} from config: {}').format(signal, state))
            action.set_state(GLib.Variant.parse(None, state, None, None))


if __name__ == '__main__':
    import sys
    app = Shadowsocks()
    app.run(sys.argv)
