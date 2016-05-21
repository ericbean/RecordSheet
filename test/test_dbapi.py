#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from RecordSheet import dbapi

def test_pw_funcs():
    pwhash = dbapi.new_pw_hash("test password")
    assert dbapi.compare_pw("test password", pwhash)
