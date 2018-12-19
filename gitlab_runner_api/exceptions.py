from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    'AlreadyFinishedExcpetion',
    'APIExcpetion',
    'AuthException',
    'ImagePullException',
]


class AlreadyFinishedExcpetion(Exception):
    pass


class APIExcpetion(Exception):
    pass


class AuthException(Exception):
    pass


class ImagePullException(Exception):
    pass


class JobTimeoutException(Exception):
    pass
