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

import functools

from bottle import abort, response, request, template

from RecordSheet import util

###############################################################################

class AuthPlugin:
    api = 2

    def __init__(self, get_session):
        self.get_session = get_session
        self.default_roles = {'authenticated'}
        self.login_template = 'login'


    def apply(self, callback, route):
        req_roles = route.config.get('roles')
        if req_roles is None:
            req_roles = self.default_roles

        @functools.wraps(callback)
        def wrapper(*args, **kwargs):
            wses = self.get_session()
            authed = wses.get('authenticated', False)
            if not authed and req_roles is not False:
                print('not authed and roles is not False')
                wses['dest_path'] = request.url
                accept = request.headers.get('Accept', 'text/html')
                if 'html' not in accept:
                    abort(401, "Please log in")

                return template(self.login_template)

            return callback(*args, **kwargs)

        return wrapper

###############################################################################

class CsrfPlugin:
    api = 2

    def __init__(self, session_key='beaker.session'):
        self.session_key = session_key


    def apply(self, callback, route):
        @functools.wraps(callback)
        def wrapper(*args, **kwargs):
            wses = request.environ.get(self.session_key)
            if 'csrf-token' not in wses:
                wses['csrf-token'] = util.csrf_token()

            if route.method != 'GET':
                token = (request.POST.get('csrf-token') or
                            request.headers.get('X-csrf-token'))

                if token != wses['csrf-token']:
                    abort(400, "Invalid CSRF token")

            return callback(*args, **kwargs)

        return wrapper

###############################################################################
