# -*- coding: utf-8 -*-
# Copyright 2012-2017 The Wazo Authors  (see AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import signal
import sys
import xivo_dao

from functools import partial
from xivo.daemonize import pidfile_context
from xivo.user_rights import change_user
from xivo.xivo_logging import setup_logging
from xivo_call_logs.config import load as load_config
from xivo_call_logs.controller import Controller

logger = logging.getLogger(__name__)


def main(argv):
    config = load_config(argv)

    user = config.get('user')
    if user:
        change_user(user)

    setup_logging(config['logfile'], config['foreground'], config['debug'], config['log_level'])
    xivo_dao.init_db_from_config(config)

    controller = Controller(config)
    signal.signal(signal.SIGTERM, partial(sigterm, controller))

    with pidfile_context(config['pidfile'], config['foreground']):
        controller.run()


def sigterm(controller, signum, frame):
    del signum
    del frame

    controller.stop(reason='SIGTERM')


if __name__ == '__main__':
    main(sys.argv[1:])
