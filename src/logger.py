# coding: utf8

import logging


def _load_logger():
    from .config import Config
    logging.config.dictConfig(Config.logger)
