from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import random
import six
import tempfile


def random_string(characters, length):
    return "".join([random.choice(characters).lower() for i in range(length)])


def check_token(request, valid_tokens):
    if not isinstance(valid_tokens, list):
        valid_tokens = [valid_tokens]
    payload = json.loads(request.body)

    if "token" not in payload:
        return payload, (400, {}, json.dumps({"error": "token is missing"}))

    for valid_token in valid_tokens:
        if payload["token"] == valid_token:
            break
    else:
        return payload, (403, {}, json.dumps({"message": "403 Forbidden"}))

    return payload, None


def run_test_with_artifact(func):
    def new_func(*args, **kwargs):
        assert "artifact_fn" not in kwargs
        assert "artifact_hash" not in kwargs
        artifact_hash = (
            "bdc75d9231d9760df186a2888366d14c2a83247342ef99b26c45031eaeaa4c19"
        )
        with tempfile.NamedTemporaryFile(suffix=".zip") as fp:
            fp.write(
                b"PK\x03\x04\x14\x00\x00\x00\x08\x00\xcd\x92/M\x12\x83O\x97\x7f"
                b"\x02\x00\x009\x04\x00\x00\x0b\x00\x1c\x00LICENSE.txtUT\t\x00"
                b"\x03\xc21\x9d[\xbb\x05\xa1[ux\x0b\x00\x01\x04\xf5\x01\x00\x00"
                b"\x04\x14\x00\x00\x00]RKo\xdb0\x0c\xbe\xebW\x109\xb5\x80\xd1=N"
                b"\xc3n\x8a\xad4\xc2\xfc\x82\xac4\xcb\xa9pl%\xd6\xe0X\x81%7\xe8"
                b"\xbf\x1f\xe9\xa4\xed: \x80!\x92\xdf\x8bL&5\xa4\xb61\x837\x8c"
                b"\xc5\xee\xfc:\xdac\x17\xe0\xae\xb9\x87\xef_\xbf\xfd\x80c\xff<"
                b"N\xc3`\xc6\xe7\xfal\xa15/\xa6wg3z\xc6J3\x9e\xac\xf7\xd6\r`=tf"
                b"4\xfbW8\x8e\xf5\x10L\x1b\xc1a4\x06\xdc\x01\x9a\xae\x1e\x8f&"
                b"\x82\xe0\xa0\x1e^\x81\xa0\x08p\xfbP\xdb\xc1\x0eG\xa8\xa1AQ"
                b"\x86\x93\xa1C\x1a\xef\x0e\xe1R\x8f\x06\x87[\xa8\xbdw\x8d\xad"
                b"\x91\x0fZ\xd7L'3\x84:\x90\xde\xc1\xf6\xc6\xc3]\xe8\x0c,\xaa"
                b"\x1bbq?\x8b\xb4\xa6\xee\x99\x1d\x80zo-\xb8\xd8\xd0\xb9)\xc0h|"
                b"\x18mC\x1c\x11\xd8\xa1\xe9\xa7\x96<\xbc\xb5{{\xb27\x05\x82"
                b"\xcf\x9b\xf0\x0cI'\x8f\t\xc8g\x04'\xd7\xda\x03}\xcd\x1c\xeb"
                b"<\xed{\xeb\xbb\x08ZK\xd4\xfb)`\xd1Sq^iD9\xbe\xb8\x11\xbc\xe9{"
                b"\x86\x0c\x16}\xcfY?\xdc\xcd3d\xfdL\x0b\r\xb7\x15y\xaa\\:w\xfa"
                b"\x9c\xc4zv\x98\xc6\x01%\xcd\x8ci\x1d\xaelV\xfcc\x9a@\x15\x1a?"
                b"\xb8\xbew\x17\x8a\xd6\xb8\xa1\xb5\x94\xc8\xffdLc\xab\xde\xbb"
                b"\x173g\xb9\x1ezp\x01\xad^-\xd0\x01\xce\x1fW\xbd\xb5|W\xf7="
                b"\xec\xcdma\xa8\x8b\xeb\xad\xff\x893\x92\xbc\x0fxx[\xf7pv\xe3"
                b'\xac\xf7\x7f\xcc\x07\xd4_\x0b\xa8\x8a\x95\xder%@VP\xaa\xe2I&"'
                b"\x81\x05\xaf\xf0\xbd\x88`+\xf5\xba\xd8h\xc0\t\xc5s\xbd\x83b"
                b"\x05<\xdf\xc1/\x99'\x11\x88\xdf\xa5\x12U\x05\x85b2+S)\xb0&"
                b"\xf38\xdd$2\x7f\x84%\xe2\xf2\x02\xff\xcd2\x93\x1aIu\x01$x\xa3"
                b'\x92\xa2"\xb2L\xa8x\x8dO\xbe\x94\xa9\xd4\xbb\x88\xad\xa4\xce'
                b"\x89sU(\xe0Pr\xa5e\xbcI\xb9\x82r\xa3\xca\xa2\x12(\x9f m.\xf3"
                b"\x95B\x15\x91\x89\\?\xa0*\xd6@<\xe1\x03\xaa5OS\x92b|\x83\xee"
                b"\x15\xf9\x83\xb8(wJ>\xae5\xac\x8b4\x11X\\\nt\xc6\x97\xa9\xb8J"
                b"a\xa88\xe52\x8b \xe1\x19\x7f\x143\xaa@\x16\xc5h\xec\xea\x0e"
                b"\xb6kA%\xd2\xe3\xf8\x8b\xb5,r\x8a\x11\x17\xb9V\xf8\x8c0\xa5"
                b"\xd2\xef\xd0\xad\xacD\x04\\\xc9\x8a\x16\xb2RE\x161Z'\"\x8a"
                b"\x99\x04q\xb9\xb8\xb2\xd0\xaa\xe1\xd3Ep\x84\xde\x9bJ\xbc\x13B"
                b'"x\x8a\\\x15\x81)\xe2\xdb\xf0\x03\xfb\x0bPK\x01\x02\x1e\x03'
                b"\x14\x00\x00\x00\x08\x00\xcd\x92/M\x12\x83O\x97\x7f\x02\x00"
                b"\x009\x04\x00\x00\x0b\x00\x18\x00\x00\x00\x00\x00\x01\x00\x00"
                b"\x00\xa4\x81\x00\x00\x00\x00LICENSE.txtUT\x05\x00\x03\xc21"
                b"\x9d[ux\x0b\x00\x01\x04\xf5\x01\x00\x00\x04\x14\x00\x00\x00PK"
                b"\x05\x06\x00\x00\x00\x00\x01\x00\x01\x00Q\x00\x00\x00\xc4\x02"
                b"\x00\x00\x00\x00"
            )
            fp.flush()
            return func(
                *args, artifact_fn=fp.name, artifact_hash=artifact_hash, **kwargs
            )

    return new_func


def validate_runner_info(runner_info):
    if not isinstance(runner_info, dict):
        return (400, {}, json.dumps({"error": "info is invalid"}))
    runner_info = runner_info.copy()
    if "features" in runner_info:
        runner_info.update(runner_info.pop("features"))
        raise NotImplementedError()

    # Validate individual items
    expected_types = {
        "name": six.string_types,
        "version": six.string_types,
        "revision": six.string_types,
        "platform": six.string_types,
        "architecture": six.string_types,
        "executor": six.string_types,
    }
    for name, expected_type in expected_types.items():
        if name in runner_info:
            if not isinstance(runner_info[name], expected_type):
                return (400, {}, json.dumps({"error": name + " is invalid"}))
    return runner_info
