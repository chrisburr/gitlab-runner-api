from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse

import gitlab_runner_api

__all__ = [
    "register_runner",
]


def register_runner():
    parser = argparse.ArgumentParser()
    parser.add_argument("api_url")
    parser.add_argument("token")
    parser.add_argument("output_fn")
    parser.add_argument(
        "--locked",
        action="store_true",
        help="Lock the runner the to the current project",
    )
    parser.add_argument(
        "--maximum-timeout",
        type=int,
        help="Maximum timeout set when this Runner will handle the job (in seconds)",
    )
    args = parser.parse_args()

    if not args.output_fn.endswith(".json"):
        parser.error("Requested output filename must end in .json")

    runner = gitlab_runner_api.Runner.register(
        args.api_url,
        args.token,
        locked=args.locked,
        maximum_timeout=args.maximum_timeout,
    )
    runner.dump(args.output_fn)
