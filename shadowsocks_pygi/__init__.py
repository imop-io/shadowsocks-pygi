# coding: utf8

import sys

import gi
gi.require_versions({
    'Gtk': '3.0',
    'GLib': '2.0',
    'Gio': '2.0'
})

from .shadowsocks import Shadowsocks


def main():
    app = Shadowsocks()
    app.run(sys.argv)
