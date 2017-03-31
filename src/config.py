# -*- coding: utf-8 -*-
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

import os

import json
import yaml
import shutil

from gi.repository import GLib

GFWLIST = 'https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt'
FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class ConfigItem(dict):

    def __getattr__(self, attr):
        if attr in self:
            return self[attr]
        raise AttributeError(
            "'ConfigItem' object has no attribute '" + attr + "'"
        )

    def __setattr__(self, attr, value):
        self[attr] = value

    def dumps(self):
        return json.dumps(self, indent=2)


class Configure(ConfigItem):
    application_name = str(GLib.get_application_name())
    path = os.path.join(GLib.get_user_config_dir(), application_name)
    servers = ConfigItem()
    pac_file = os.path.join(path, 'pac.yml')
    app_file = os.path.join(path, application_name + '.yml')
    local_file = os.path.join(path, 'local.yml')
    servers_path = os.path.join(path, 'servers')
    resources_path = os.path.join(os.path.dirname(__file__), 'resources')

    def get_server_path(self, server_name):
        return os.path.join(self.servers_path, server_name)

    def save_server(self, server_name):
        filename = self.get_server_path(server_name + '.json')
        content = self.servers[server_name]
        return self._save(filename, content)

    def delete_server(self, server_name):
        filename = self.get_server_path(server_name + '.json')
        self.servers.pop(server_name)
        return os.unlink(filename)

    def save_pac(self):
        return self._save(self.pac_file, self.pac)

    def save_local(self):
        return self._save(self.local_file, self.local)

    def save_application(self):
        return self._save(self.app_file, self.application)

    def _save(self, filename, config):
        return GLib.file_set_contents(filename, config.dumps().encode('utf8'))

    def load_configures(self):
        self.update(self.default())
        self._prepare()
        for filename in os.listdir(self.servers_path):
            if not filename.endswith('.json'):
                continue
            name = filename.rsplit('.json', 1)[0]
            self.servers[name] = self._load(self.get_server_path(filename))

    def _load(self, filename):
        _, content = GLib.file_get_contents(filename)
        if filename.endswith('yml'):
            return ConfigItem(yaml.load(content.decode('utf8')))
        elif filename.endswith('json'):
            return ConfigItem(json.loads(content.decode('utf8')))
        raise TypeError(filename + ' is not an json or yaml file!')


    def _prepare(self):
        if not os.path.isdir(self.path):
            os.mkdir(self.path)
        if os.path.isfile(self.app_file):
            self.application.update(self._load(self.app_file))
        if os.path.isfile(self.local_file):
            self.local.update(self._load(self.local_file))
        if os.path.isfile(self.pac_file):
            self.pac.update(self._load(self.pac_file))
        if not os.path.isdir(self.servers_path):
            os.mkdir(self.servers_path)
        if not os.path.isdir(os.path.dirname(self.pac.path)):
            os.mkdir(os.path.dirname(self.pac.path))
        if not os.path.isfile(self.pac.user_rules):
            user_rule_sample = os.path.join(
                self.resources_path,
                'user-rules-sample.txt'
            )
            shutil.copyfile(user_rule_sample, self.pac.user_rules)
        return True

    def default(self):
        application = ConfigItem(
            last_server=None,
            auto_connect='false',
            auto_reconnect='false',
            proxy_type=None,
            icon=os.path.join(self.resources_path, 'ss24x24.png')
        )
        ss_local = ConfigItem(
            port=1080,
            address='127.0.0.1',
            verbose=3,
            one_time_auth=False,
            workers=1,
            manager_address='127.0.0.1',
            user=GLib.get_user_name(),
            forbidden_ip=[],
            daemon='daemon',
            prefer_ipv6=False,
            pid_file=os.path.join(
                GLib.get_user_runtime_dir(),
                self.application_name + '.pid'
            ),
            log_file=os.path.join(
                GLib.get_user_runtime_dir(),
                self.application_name + '-access.log'
            )
        )
        ss_server = ConfigItem(
            server=None,
            server_port=None,
            password=None,
            method=None,
            timeout=300,
            fast_open=True
        )
        pac_config = ConfigItem(
            compress=False,
            path=os.path.join(self.path, 'pac', self.application_name + '.pac'),
            gfwlist_modified='',
            gfwlist_url=GFWLIST,
            user_rules=os.path.join(self.path, 'pac', 'user-rules.txt'),
            local_gfwlist=os.path.join(self.path, 'pac', 'gfwlist.txt')
        )
        logger = ConfigItem(
            version=1,
            formatters=ConfigItem(
                default=ConfigItem(
                    format=FORMAT
                )
            ),
            handlers=ConfigItem(
                console=ConfigItem({
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    "stream": "ext://sys.stdout",
                    'formatter': 'default',
                }),
                logfile=ConfigItem({
                    'level': 'DEBUG',
                    "class": "logging.FileHandler",
                    'formatter': 'default',
                    'filename': os.path.join(
                        GLib.get_user_runtime_dir(),
                        self.application_name + '.log'
                    ),
                    'encoding': 'utf8'
                })
            ),
            logger=ConfigItem({
                self.application_name: ConfigItem(
                    level="DEBUG",
                    propagate=1,
                    handlers=['console', 'logfile']
                )
            }),
            root=ConfigItem(
                level="DEBUG",
                handlers=['console', 'logfile']
            )
        )
        return ConfigItem(
            application=application,
            server=ss_server,
            local=ss_local,
            pac=pac_config,
            logger=logger
        )

Config = Configure()
Config.load_configures()
