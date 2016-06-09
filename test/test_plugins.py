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

import bottle
bottle.DEBUG = True
#from nose.tools import with_setup
from webtest import TestApp

from RecordSheet import plugins, webapp

mockapp = bottle.Bottle()

CSRF_TOKEN = '12345'
ses_data = {'user_id':1, 'csrf-token':CSRF_TOKEN, 'authenticated':True}
app = TestApp(mockapp, extra_environ={'beaker.session': ses_data})

###############################################################################
INDEX_TPL = "<!DOCTYPE html>\n<html>Hello, World!</html>"

@mockapp.route('/', roles=False)
def mock_index():
    return INDEX_TPL


@mockapp.post('/')
def mock_post():
    bottle.redirect('/')


@mockapp.route('/protected')
def mock_post():
    return INDEX_TPL

###############################################################################

class testAuthPlugin:
    @classmethod
    def setUpClass(cls):
        cls.plugin = plugins.AuthPlugin(webapp.www_session)
        mockapp.install(cls.plugin)


    @classmethod
    def tearDownClass(cls):
        mockapp.uninstall(cls.plugin)


    def test_auth(self):
        response = app.get('/')
        assert response.status_int == 200
        assert response.content_type == 'text/html'
        response.mustcontain('Hello, World!')


    def test_auth_authed(self):
        ses_data['authenticated'] = True
        response = app.get('/protected')
        assert response.status_int == 200
        assert response.content_type == 'text/html'
        response.mustcontain('Hello, World!')


    def test_auth_unauthed(self):
        ses_data['authenticated'] = False
        response = app.get('/protected')
        assert response.status_int == 200
        assert response.content_type == 'text/html'
        response.mustcontain('login-form')


    def test_auth_unauthed_json(self):
        ses_data['authenticated'] = False
        headers = {'Accept':'application/json'}
        response = app.get('/protected', headers=headers, status='*', xhr=True)
        assert response.status_int == 401

###############################################################################

class testCSRF:
    @classmethod
    def setUpClass(cls):
        cls.plugin = plugins.CsrfPlugin()
        mockapp.install(cls.plugin)


    @classmethod
    def tearDownClass(cls):
        mockapp.uninstall(cls.plugin)


    def test_csrf_no_token_sent(self):
        response = app.post('/', {'foo':'bar'}, status='*')
        assert response.status_int == 400
        assert response.content_type == 'text/html'


    def test_csrf_token(self):
        ses_data['csrf-token'] = CSRF_TOKEN
        postdata = {'foo':'bar','csrf-token':CSRF_TOKEN}
        response = app.post('/', postdata, status='*')
        assert response.status_int == 302
        assert response.content_type == 'text/html'


    def test_csrf_missing_token(self):
        del ses_data['csrf-token']
        postdata = {'foo':'bar','csrf-token':CSRF_TOKEN}
        response = app.post('/', postdata, status='*')
        assert response.status_int == 400
        assert response.content_type == 'text/html'


    def test_csrf_token_not_set(self):
        del ses_data['csrf-token']
        response = app.get('/', status='*')
        assert response.status_int == 200
        assert response.content_type == 'text/html'
        assert 'csrf-token' in ses_data

###############################################################################














