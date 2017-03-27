# coding: utf8

import sys

from .shadowsocks import Shadowsocks


def main():
    app = Shadowsocks()
    app.run(sys.argv)
