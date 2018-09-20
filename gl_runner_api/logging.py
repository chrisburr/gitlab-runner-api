from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

import colorlog


__all__ = [
    'logger',
]

handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s:%(message)s'))
logger = colorlog.getLogger('gl_runner_api')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
