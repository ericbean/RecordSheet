#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from RecordSheet import webapp


def test_json_error():
    retval = webapp.json_error(status=418, error_msg="I'm a teapot")
    retval = json.loads(retval)
    assert retval['errorMsg'] == "I'm a teapot"
