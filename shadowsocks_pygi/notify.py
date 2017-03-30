# coding: utf8


import logging

from gettext import gettext as _

import gi
gi.require_version('Notify', '0.7')
from gi.repository import GLib, Notify   # noqa

from .config import Config  # noqa

Notify.init(Config.application_name)


class Notify:
    notify = Notify.Notification().new(
        summary=Config.application_name,
        icon=Config.application.icon
    )

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def show(self, text=''):
        self.notify.update(summary=Config.application_name, body=text)
        self.logger.debug(_('Show notify message: {}').format(text))
        return self.notify.show()
