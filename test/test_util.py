#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from decimal import Decimal

from RecordSheet import util


ex_date = datetime(2016,5,21,10,53,45)
ex_date_json = '"2016-05-21T10:53:45"' # mind the quotes
ex_dec = Decimal('3.13131')
ex_dec_json = '3.13131'


class JsonClass:
    def __init__(self):
        self.json_obj_called = False

    def json_obj(self):
        self.json_obj_called = True
        return {k:v for k,v in self.__dict__.items() if not k.startswith('_')}


def test_json_obj():
    obj = JsonClass()
    util.jsonDumps(obj)
    assert obj.json_obj_called == True


def test_jsonDumps_datetime():
    retval = util.jsonDumps(ex_date)
    assert retval == ex_date_json


def test_jsonDumps_Decimal():
    retval = util.jsonDumps(ex_dec)
    assert retval == ex_dec_json


def test_jsonLoads_Decimal():
    assert ex_dec == util.jsonLoads(ex_dec_json)


def test_year_range():
    start, end = util.year_range(2016)
    print(repr(start), repr(end))
    assert start.year == end.year == 2016
    assert start.month == start.day == 1
    assert end.month == 12 and end.day == 31
    assert end.hour == 23
    assert end.minute == 59
    assert end.second == 59
    assert start.tzinfo
    assert end.tzinfo

