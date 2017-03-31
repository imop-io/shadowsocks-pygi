# -*- coding: utf-8 -*-

import time
import logging
import threading

from gi.repository import GLib

from gettext import gettext as _


class AsyncCall:
    def __init__(self, func, *args, callback=None):
        self.logger = logging.getLogger(__name__)

        self._func = func
        self._args = args
        self._callback = callback

        thread = threading.Thread(target=self)
        thread.daemon = True
        thread.start()

    def __call__(self):
        result = error = None

        try:
            self.logger.info(
                _('Task<{}> with args<{}> is starting').format(
                    self._func.__name__,
                    self._args
                )
            )
            result = self._func(*self._args)
            self.logger.info(
                _('Task<{}> with args<{}> is completed').format(
                    self._func.__name__,
                    self._args
                )
            )
            self.logger.debug(
                _('Result of Task<{}> is: {}').format(
                    self._func.__name__,
                    result
                )
            )
        except Exception as e:
            self.logger.error(
                _('An error occured when Task<{}> is running.').format(
                    self._func.__name__
                )
            )
            self.logger.exception(e)
            error = e

        if self._callback:
            GLib.idle_add(self._callback, result, error)


class AsyncDaemon:

    def __init__(self, func, *args, callback=None, sleep=2):
        self._stopped = False

        self._func = func
        self._args = args
        self._sleep = sleep
        self._callback = callback

    def run(self):
        while not self._stopped:
            GLib.idle_add(self._func, *self._args)

    def stop(self):
        self._stopped = True

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
