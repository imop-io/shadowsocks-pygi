# -*- coding: utf-8 -*-

from .ping import Ping
from .config import Config

from shadowsocks import shell
from shadowsocks.local import main

import os
import socket
import logging


class Local:

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._patch()
        self._server = None
        self._config = Config.local

    def set_server(self, server):
        self._server = server
        self._config.update(Config.servers.get(server))
        self._logger.debug('Server config is updated to {}'.format(server))

    def _patch(self):
        shell.get_config = lambda _: self._config
        self._logger.debug('get_config patched successful.')

    def control(self, action):
        self._config['daemon'] = action
        self._logger.debug('Receive action<{}> for sslocal.'.format(action))
        if action == 'start':
            if not self._server:
                srv = self.select_server()
                self.set_server(srv)
                self._logger.debug('Ready to connect to {}'.format(self._server))
            self.compat_local()
        self.compat_proc()
        pid = os.fork()
        if pid != 0:
            self._logger.debug('Control process return. child: {}'.format(pid))
            os.wait()
            return True

        self._logger.debug('Control sslocal...')
        main()

    def select_server(self):
        result = {}
        for srv, cfg in Config.servers.items():
            if cfg.enabled:
                result[srv] = Ping(cfg.server, cfg.server_port).ping().avg
        if not result:
            raise Exception('No server is enabled!')
        return sorted(result, key=result.get)[-1]

    def compat_proc(self):
        if 'pid-file' not in self._config:
            self._config['pid-file'] = self._config.pid_file

        if 'log-file' not in self._config:
            self._config['log-file'] = self._config.log_file

    def compat_local(self):
        if 'local_address' not in self._config:
            self._config.local_address = self._config.address

        if 'local_port' not in self._config:
            self._config.local_port = int(self._config.port)

    @property
    def is_running(self):
        if not os.path.exists(self._config.pid_file):
            return False

        with open(self._config.pid_file) as pid_file:
            pid = int(pid_file.read().strip())

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False

        sock = socket.socket()
        sock.settimeout(0.01)
        try:
            sock.connect((self._config.address, int(self._config.port)))
            running = True
        except ConnectionRefusedError:
            running = False
        finally:
            sock.shutdown(socket.SHUT_RD)
            sock.close()

        return running
