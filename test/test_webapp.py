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
from nose.tools import with_setup
from webtest import TestApp

from RecordSheet import dbapi, dbmodel, webapp
full_app = webapp.app()
app = TestApp(webapp.rsapp, extra_environ={'beaker.session':{'user_id':1,
                                                     'csrf-token':'12345',
                                                     'authenticated':True}})

from test.dbhelper import setup_module, teardown_module

###############################################################################

def test_index():
    response = app.get('/')
    assert response.status_int == 200
    assert response.content_type == 'text/html'

###############################################################################

def test_account_chart():
    response = app.get('/accounts')
    assert response.status_int == 200
    assert response.content_type == 'text/html'


def test_account_view():
    response = app.get('/accounts/1')
    assert response.status_int == 200
    assert response.content_type == 'text/html'


def test_account_view_invalid_id():
    response = app.get('/accounts/100000', status='*')
    assert response.status_int == 404
    assert response.content_type == 'text/html'

###############################################################################

def test_new_transaction():
    response = app.get('/transaction/new')
    assert response.status_int == 200
    assert response.content_type == 'text/html'

###############################################################################

def test_batch():
    response = app.get('/batch/1')
    assert response.status_int == 200
    assert response.content_type == 'text/html'


def test_batch_invalid_id():
    response = app.get('/batch/1000000', status='*')
    assert response.status_int == 404
    assert response.content_type == 'text/html'

###############################################################################

def test_journal():
    response = app.get('/journal')
    assert response.status_int == 200
    assert response.content_type == 'text/html'


def test_journal_entry():
    response = app.get('/journal/1')
    assert response.status_int == 200
    assert response.content_type == 'text/html'


def test_journal_entry_invalid_id():
    response = app.get('/journal/100000', status='*')
    assert response.status_int == 404
    assert response.content_type == 'text/html'

###############################################################################

def test_import_tr():
    response = app.get('/import')
    assert response.status_int == 200
    assert response.content_type == 'text/html'

###############################################################################

def test_user_view():
    response = app.get('/users/testuser')
    assert response.status_int == 200
    assert response.content_type == 'text/html'


def test_user_view_invalid_user():
    response = app.get('/users/doesnotexist', status='*')
    assert response.status_int == 404
    assert response.content_type == 'text/html'


def test_user_self_edit():
    response = app.get('/me')
    assert response.status_int == 200
    assert response.content_type == 'text/html'

###############################################################################

def test_admin_users():
    response = app.get('/admin')
    assert response.status_int == 200
    assert response.content_type == 'text/html'

###############################################################################

def test_login():
    response = app.get('/login')
    assert response.status_int == 200
    assert response.content_type == 'text/html'


