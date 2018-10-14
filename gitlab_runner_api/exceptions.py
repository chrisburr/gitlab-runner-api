from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    'AlreadyFinishedExcpetion',
    'APIExcpetion',
    'AuthException',
]


class AlreadyFinishedExcpetion(Exception):
    pass


class APIExcpetion(Exception):
    pass


class AuthException(Exception):
    pass
