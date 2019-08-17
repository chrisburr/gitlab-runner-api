from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    'CURRENT_DATA_VERSION',
    'package_version',
]

import pkg_resources  # part of setuptools

CURRENT_DATA_VERSION = 1
package_version = pkg_resources.require("gitlab_runner_api")[0].version
