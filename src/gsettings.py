# coding: utf8
#
# Copyright (C) 2017 songww
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from gi.repository import Gio, GLib  # noqa


class SystemProxy:
    schema = 'org.gnome.system.proxy'
    ignore_hosts = ['localhost', '127.0.0.0/8', '::1']

    def __init__(self):
        self.gsetting = Gio.Settings(schema=self.schema)
        self.logger = logging.getLogger(__name__)

    def set_ignore_hosts(self, *hosts):
        host = []
        for _item in hosts:
            if isinstance(_item, (list, tuple)):
                host.extend(_item)
            else:
                host.append(_item)
        self.logger.info('Set hosts<{}> to be ignored'.format(hosts))
        self.ignore_hosts = hosts

    def apply_ignore_hosts(self):
        self.gsetting.set_value(
            'ignore-hosts',
            GLib.Variant('as', self.ignore_hosts)
        )
        self.logger.info('Apply ignored hosts<{}>'.format(self.ignore_hosts))

    def get_ignore_hosts(self):
        ignore_hosts = tuple(self.gsetting.get_value('ignore-hosts'))
        if ignore_hosts != self.ignore_hosts:
            self.ignore_hosts = ignore_hosts
        self.logger.debug('Get ignored hosts<{}>'.format(self.ignore_hosts))
        return self.ignore_hosts

    def global_proxy(self, proxy_type='socks5'):
        self.logger.debug('Set proxy type: global.')

    def none_proxy(self):
        self.gsetting.set_value('mode', GLib.Variant('s', 'none'))
        self.logger.debug('Set proxy type: None.')
        return True

    def by_pac(self, pac):
        self.gsetting.set_value('use-same-proxy', GLib.Variant('b', True))
        self.gsetting.set_value('mode', GLib.Variant('s', 'auto'))
        self.gsetting.set_value('autoconfig-url', GLib.Variant('s', pac))
        self.logger.debug('Set auto proxy type, with pac: {}'.format(pac))
        return True

    def by_socks(self, host, port):
        self.gsetting.set_value('mode', GLib.Variant('s', 'manual'))
        socks = self.gsetting.get_child('socks')
        socks.set_value('host', GLib.Variant('s', host))
        socks.set_value('port', GLib.Variant('i', port))
        self.apply_ignore_hosts()
        return True

    def by_http(self, host, port):
        pass

    def by_https(self, host, port):
        pass
