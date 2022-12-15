import logging

import coloredlogs

from . import Singleton


def setup_logging(name, log_level=logging.INFO):
    logger = logging.getLogger(name)

    # set log format to display the logger name to hunt down verbose logging modules
    fmt = "%(asctime)s %(name)s %(levelname)s %(message)s"

    coloredlogs.install(level=log_level, fmt=fmt, logger=logger)

    return logger


class Logging(Singleton):
    def _init_hook(self):
        self._log = setup_logging("engi-helpful-scripts")

    def __getattr__(self, name):
        return getattr(self._log, name)


log = Logging()
