# coding: utf8


import time
import socket

from functools import reduce


class Ping:

    def __init__(self, host, port=80, timeout=2):
        self._host = host
        self._port = port

        self._timeout = timeout

        self._failed = 0
        self._successed = 0

        self._conn_times = []

        self.socket = socket.socket

    def proxy(self, addr='127.0.0.1', port=1080):
        import socks
        socks.set_default_proxy(socks.SOCKS5, addr, int(port))
        self.socket = socks.socksocket

    def _create_socket(self, family, _type):
        sock = self.socket(family, _type)
        sock.settimeout(self._timeout)

    def ping(self, count=4):
        for n in range(count + 1):
            sock = self._create_socket(socket.AF_INET, socket.SOCK_STREAM)
            start = time.time()
            try:
                sock.connect((self._host, self._port))
                sock.shutdown(socket.SHUT_RD)
                stop = time.time()

                self._conn_times.append((stop - start) * 1000)
            except socket.timeout:
                self._failed -= 1

            finally:
                sock.close()

        return self

    @property
    def failed(self):
        return self._failed

    @property
    def successed(self):
        return self._successed

    @property
    def success_rate(self):
        return '{:.2f}%'.format(
            self._successed / (self._failed + self._successed) * 100
        )

    @property
    def max(self):
        return max(self._conn_times)

    @property
    def min(self):
        return min(self._conn_times)

    @property
    def avg(self):
        return self.total / len(self._conn_times)

    @property
    def total(self):
        return reduce(lambda x, y: x + y, self._conn_times)
