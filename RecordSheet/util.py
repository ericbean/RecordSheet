#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Eric Beanland <eric.beanland@gmail.com>

# This file is part of RecordSheet
#
# RecordSheet is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RecordSheet is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

import base64
import datetime
import decimal
import functools
import json
import os

import bottle

###############################################################################

class fakeFloat(float):
    """Float subclass that returns a fixed string when __repr__ is called.
    Useful for passing decimal.Decimal objects to json.dumps
    """
    def __init__(self, number):
        self.str = str(number)

    def __repr__(self):
        return self.str


class RsJsonEncoder(json.JSONEncoder):
    """Json encoder for various classes. Objects with a json_obj method
    should return a json serializable object when it is called.
    """
    def default(self, obj):
        if hasattr(obj, 'json_obj'):
            return obj.json_obj()

        #serialize datetime objects
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()

        #serialize decimal.Decimal
        elif isinstance(obj, decimal.Decimal):
            return fakeFloat(obj)

        return json.JSONEncoder.default(self, obj)

jsonDumps = functools.partial(json.dumps, cls=RsJsonEncoder,
                separators=(',', ':')) # save a few bytes
jsonLoads = functools.partial(json.loads, parse_float=decimal.Decimal)

###############################################################################

def year_range(year):
    """Return a (datetime, datetime) tuple representing the start and end of
    year. The datetime objects will have Zulu time set as their timezone.
    """
    #Zulu time might give surprising results for a user...
    tz = datetime.timezone.utc
    datetime.datetime(year, 1, 1, tzinfo=None)
    return (datetime.datetime(year, 1, 1, tzinfo=tz),
            datetime.datetime(year, 12, 31, hour=23, minute=59, second=59,
                                microsecond=999999, tzinfo=tz))

###############################################################################

def csrf_token():
    """Create a random token suitable for csrf protection."""
    token = base64.standard_b64encode(os.urandom(20))
    return str(token, encoding='utf8')

###############################################################################

def www_session():
    """Utility function to get the web session."""
    return bottle.request.environ.get('beaker.session')

###############################################################################
