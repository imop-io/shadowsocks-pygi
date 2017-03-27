# -*- coding: utf-8 -*-

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
        if not self._server:
            srv = self.select_server()
            if not srv:
                return False
            self.set_server(srv)
            self._logger.debug('Ready to connect to {}'.format(self._server))
        self.prepare()
        pid = os.fork()
        if pid != 0:
            self._logger.debug('Control process return. child: {}'.format(pid))
            print(os.wait())
            return True

        self._logger.debug('Control sslocal...')
        main()

    def select_server(self):
        for srv in Config.servers:
            if Config.servers.get(srv).enabled:
                return srv

    def prepare(self):
        if 'pid-file' not in self._config:
            self._config['pid-file'] = self._config.pid_file

        if 'log-file' not in self._config:
            self._config['log-file'] = self._config.log_file

        if 'local_address' not in self._config:
            self._config.local_address = self._config.address

        if 'local_port' not in self._config:
            self._config.local_port = int(self._config.port)

    def is_running(self):

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
            sock.send(b'0')
            running = sock.recv(1) == b'\x00'
            sock.close()
        except ConnectionRefusedError:
            sock.close()
            return False

        return running
