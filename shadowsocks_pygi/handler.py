# coding: utf8

import logging

from .pac import Pac
from .config import Config, ConfigItem
from gi.repository import Gtk


class Handler:

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)

    def on_save_clicked(self, *args):
        self.logger.debug('Save button clicked.')
        print(*args)

    def on_cancel_btn_clicked(self, dialog):
        self.logger.debug('Cancel button clicked.')
        self.logger.debug('Hide dialog<{}>.'.format(dialog.get_title()))
        return dialog.hide()

    def on_server_save_btn_clicked(self, dialog):
        self.logger.debug('Server_Save button clicked.')
        builder = self.app.builder
        name = builder.get_object('NameEntry').get_text()
        port = builder.get_object('PortEntry').get_text()
        addr = builder.get_object('AddressEntry').get_text()
        passwd = builder.get_object('PasswordEntry').get_text()
        timeout = builder.get_object('TimeoutEntry').get_text()
        crypt_method_combo = builder.get_object('CryptMethodCombo')

        if not port:
            pass  # TODO: alart Port can't be empty
        if not addr:
            pass  # TODO: alart Addr can't be empty
        if not passwd:
            pass  # TODO: alart Passwd can't be empty
        if not timeout:
            timeout = 600
        if not name:
            name = addr

        tree_iter = crypt_method_combo.get_active_iter()
        method_model = crypt_method_combo.get_model()
        method = method_model[tree_iter][0]
        Config.servers[name] = ConfigItem(
            server=addr,
            server_port=int(port),
            timeout=int(timeout),
            method=method,
            password=passwd,
            fast_open=False
        )

        title = dialog.get_title()
        Config.save_server(name)
        if title != name:
            server_list = self.app.builder.get_object('ServerListView')
            if title == 'Add Server...':
                tree_iter = server_list.get_model().append([name])
                self.logger.debug(
                    'Append to new server <{}> to server_list'.format(name)
                )
                server_list.get_selection().select_iter(tree_iter)
            else:
                Config.delete_server(title)
                self.logger.debug(
                    'Delete old server <{}> from config'.format(title)
                )
                selection = server_list.get_selection()
                model, tree_iter = selection.get_selected()
                edited_iter = model.insert_after(
                    model[tree_iter].get_previous(),
                    [name]
                )
                self.logger.debug(
                    'Append to new server <{}> to server_list'.format(name)
                )
                selection.select_iter(edited_iter)
                model.remove(tree_iter)
                self.logger.debug(
                    'Delete old server <{}> from server_list'.format(title)
                )

        return dialog.hide()

    def on_create_btn_clicked(self, button):
        self.logger.debug('Create button clicked.')
        dialog = self.app.builder.get_object('ServerSettingDialog')
        dialog.set_title('Add Server...')
        dialog.show()
        dialog.run()
        dialog.hide()
        self.logger.debug('Hide dialog<Add Server...>.')
        return True

    def on_delete_btn_clicked(self, server_view):
        self.logger.debug('Delete button clicked.')
        selection = server_view.get_selection()
        model, tree_iter = selection.get_selected()
        server_name = model[tree_iter][0]
        Config.delete_server(server_name)
        prev = model[tree_iter].get_previous()
        next = model[tree_iter].get_next()
        model.remove(tree_iter)
        if next:
            return selection.select_iter(next.iter)
        elif prev:
            return selection.select_iter(prev.iter)
        return True

    def on_advance_btn_clicked(self, selection):
        self.logger.debug('Advance button clicked.')
        server_list, tree_iter = selection.get_selected()
        server_name = server_list[tree_iter][0]
        self.logger.debug('Selected server is: {}.'.format(server_name))

        builder = self.app.builder
        config = Config.servers[server_name]

        setting_dialog = builder.get_object('ServerSettingDialog')

        setting_dialog.set_title(server_name)

        addr = config.get('server', '')
        builder.get_object('NameEntry').set_text(server_name)
        builder.get_object('AddressEntry').set_text(addr)
        builder.get_object('PortEntry').set_text(config.get('server_port', ''))
        builder.get_object('PasswordEntry').set_text(config.get('password', ''))
        builder.get_object('PasswordDisplay').set_active(False)
        builder.get_object('TimeoutEntry').set_text(str(config.get('timeout')))

        method = config.get('method')
        builder.get_object('CryptMethodCombo') \
            .set_active_iter(self.app.methods_map[method])

        setting_dialog.show_all()
        setting_dialog.run()
        setting_dialog.hide()
        self.logger.debug('Hide dialog<{}>.'.format(server_name))
        return True

    def on_connection_switch_changed(self, switch, state):
        self.logger.debug(
            'Connection_Switch button clicked. state to be {}'.format(state)
        )
        if state is True:
            self.app.sslocal.control('start')
            # ping
            # generate config
            # sslocal.start()
            # TODO: start failed
            switch.set_state(True)
        else:
            # get config
            # sslocal.stop()
            self.app.sslocal.control('stop')
            switch.set_state(False)
        self.logger.debug(
            'Successed to change Connection_Switch\'s state to {}'.format(state)
        )
        return True

    def on_server_switch_changed(self, selection, state):
        self.logger.debug(
            'Server_Switch button clicked, State must to be {}'.format(state)
        )
        server_list, tree_iter = selection.get_selected()
        server_name = server_list[tree_iter][0]
        self.logger.debug('Selected server is: {}'.format(server_name))
        Config.servers[server_name].enabled = state
        Config.save_server(server_name)
        self.logger.debug(
            'Successed to change state<{}> of server<{}>'.format(
                server_name, state
            )
        )
        return True

    def on_selected_server_changed(self, selection, *args):
        server_list, tree_iter = selection.get_selected()
        builder = self.app.builder
        if not tree_iter:
            server_name = ''
            return True
        server_name = server_list[tree_iter][0]
        self.logger.debug('Server<{}> is selected.'.format(server_name))
        server = Config.servers.get(server_name)
        builder.get_object('ServerNameLabel').set_label(server_name)
        builder.get_object('ConnectStateLabel').set_label('Not')
        builder.get_object('Gateway').set_label(server_name + ':1080')
        builder.get_object('ServerControl') \
            .set_state(server.get('enabled', False))
        return True

    def on_gfwlist_update_clicked(self, *args):
        self.logger.debug('Gfwlist_Update is clicked.')
        pac = Pac(Config)
        if Config.application.connected:
            proxy = 'socks5://{}:{}'.format(
                Config.local.address,
                Config.local.port
            )
            pac.set_proxy(http=proxy, https=proxy)
        pac.fetch_remote_gfwlist()
        if pac.gfwlist_modified == '':
            self.logger.error(
                'Failed to update gfwlist: {}'.format(Config.pac.gfwlist_url)
            )
            raise Exception()  # TODO: add notify -- Update failed
        if Config.pac.gfwlist_modified == pac.gfwlist_modified:
            self.logger.error('Gfwlist is already up to date.')
            raise Exception()  # TODO: add notify -- Almost new
        pac.fetch_user_rules()
        self.logger.debug('Fetch user roles: {}'.format(''))
        pac.save(pac.generate())
        self.logger.info('Success to generate pac file.')
        return True

    def on_user_rules_saved(self, *args):
        self.logger.debug('User rules is changed.')
        # TODO: monitor for user_rules
        pac = Pac(Config)
        pac.fetch_user_rules()
        pac.save(pac.generate())
        self.logger.info('Success to generate pac file.')
        return True

    def on_menu_btn_clicked(self, *args):
        self.logger.debug('Menu btn clicked.')
        menu = self.app.builder.get_object('MenuPop')
        menu.show_all()
        print(args)

    def on_server_dialog_close(self, dialog):
        self.logger.debug(
            'Close button of dialog<{}> is clicked'.format(dialog.get_title())
        )
        return True

    def on_server_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.DELETE_EVENT:
            self.logger.debug(
                'Dialog<{}> receive DELETE_EVENT response.'.format(
                    dialog.get_title()
                )
            )
            return True
        self.logger.debug(
            'Dialog<{}> receive response signal: {}'.format(
                dialog.get_title(), response
            )
        )
        dialog.hide()
        self.do_clean_on_dialog_hide(dialog)
        self.logger.debug('Dialog<{}> is hidden.'.format(dialog.get_title()))
        return True

    def do_clean_on_dialog_hide(self, dialog):
        self.logger.debug(
            'Dialog<{}> receive hide signal'.format(dialog.get_title())
        )
        builder = self.app.builder
        builder.get_object('NameEntry').set_text('')
        builder.get_object('NameEntry').set_text('')
        builder.get_object('AddressEntry').set_text('')
        builder.get_object('PortEntry').set_text('')
        builder.get_object('PasswordEntry').set_text('')
        builder.get_object('PasswordDisplay').set_active(False)
        builder.get_object('TimeoutEntry').set_text('600')
        return True

    def on_passwd_display_toggled(self, check_button):
        self.logger.debug('Show password check button is clicked')
        self.app.builder.get_object('PasswordEntry') \
            .set_visibility(check_button.get_active())
        self.logger.debug(
            'Is show password set to: {}'.format(check_button.get_active())
        )
        return True
