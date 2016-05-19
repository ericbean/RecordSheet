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

import fnmatch
import functools
import os

###############################################################################

def pathasm(*parts):
    """Assemble an absolute path from a list of parts."""
    parts = (p.strip('/') for p in parts if p)
    return '/' + '/'.join(parts)

###############################################################################

class auth_middleware:
    """Redirect non-authenticated clients to  a login url"""
    def __init__(self, app, login_url='/login', whitelist=None):
        self.app = app
        self.login_url = login_url
        if whitelist:
            self.whitelist = whitelist
        else:
            self.whitelist = ['/favicon.ico', '/static/*', '/login', '/logout']


    def __call__(self, environ, start_response):
        fullpath = functools.partial(pathasm, environ['SCRIPT_NAME'])
        session = environ['beaker.session']
        authed = session.get('authenticated', False)
        path = environ['PATH_INFO']
        # prevent clever /static/../ type paths
        path = os.path.normpath(path)

        # call app
        if authed or any(fnmatch.fnmatch(path, p) for p in self.whitelist):
            return self.app(environ, start_response)

        dest = fullpath(environ['PATH_INFO'])
        if environ['QUERY_STRING']:
            dest = dest + '?' + environ['QUERY_STRING']
        session['dest_path'] = dest
        body = [b'Redirecting to /login']
        start_response('303 See Other',[('Location', fullpath(self.login_url))])

        return body

################################################################################
