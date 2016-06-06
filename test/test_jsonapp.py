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

from nose.tools import with_setup
from webtest import TestApp

from sqlalchemy import event
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import Session

from RecordSheet.dbapi import Base
from RecordSheet import jsonapp, dbapi, dbmodel
app = TestApp(jsonapp.app, extra_environ={'beaker.session':{'user_id':1}})

###############################################################################

def setup_module():
    global transaction, connection, engine

    engine = create_engine('postgresql:///recordsheet_test')
    connection = engine.connect()
    transaction = connection.begin()
    Base.metadata.create_all(connection)

    #insert some data
    inner_tr = connection.begin_nested()
    ses = Session(connection)
#    ses.begin_nested()
    ses.add(dbapi.Account(name='TEST01', desc='test account 01'))
    ses.add(dbapi.Account(name='TEST02', desc='test account 02'))
    ses.add(dbapi.User(username='testuser', name='Test T. User',
                       password=dbapi.new_pw_hash('passtestword')))

    ses.commit()
    # mock a sessionmaker so all querys are in this transaction
    dbapi._session = lambda: ses
    ses.begin_nested()

    @event.listens_for(ses, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            ses.begin_nested()


def teardown_module():
    transaction.rollback()
    connection.close()
    engine.dispose()

###############################################################################

#def setupdb(func):
#    transaction = connection.begin_nested()

#def teardowndb(func):
#    transaction.rollback()

###############################################################################

def test_jsonout():
    @jsonapp.jsonout
    def tester():
        raise Exception('Testing 123')
    result = tester()
    assert result == '{"errorMsg":"Internal Server Error"}'

###############################################################################

def test_generic_collection():
    url = '/accounts?sort=name.asc&sort=id.desc&limit=5&offset=1'
    response = app.get(url)
    assert response.status_int == 200
    assert response.content_type == 'application/json'


def test_generic_collection_404():
    response = app.get('/doesnotexist', status=404)
    assert response.status_int == 404
    assert response.content_type == 'application/json'

###############################################################################

def test_generic_item():
    response = app.get('/accounts/2')
    assert response.status_int == 200
    assert response.content_type == 'application/json'
    assert 'id' in response.json


def test_generic_item_invalid_kind():
    response = app.get('/doesnotexist/2', status=404)
    assert response.status_int == 404
    assert response.content_type == 'application/json'

def test_generic_item_invalid_id():
    response = app.get('/accounts/0', status=404)
    assert response.status_int == 404
    assert response.content_type == 'application/json'

###############################################################################

data = {'name':'TEST145', 'desc':'test_145'}

def test_generic_put():
    response = app.put_json('/accounts', data)
    assert response.status_int == 200
    assert response.content_type == 'application/json'
    assert 'id' in response.json


def test_generic_put_duplicate():
    response = app.put_json('/accounts', data, status=400)
    assert response.status_int == 400
    assert response.content_type == 'application/json'


def test_generic_put_invalid_attr():
    data['__table__'] = 'fubar'
    response = app.put_json('/accounts', data, status=400)
    assert response.content_type == 'application/json'

###############################################################################

def test_generic_post():
    response = app.post_json('/accounts/1', {'desc':'hello'}, status='*')
    assert response.status_int == 200
    assert response.content_type == 'application/json'
    assert 'id' in response.json


def test_generic_post_invalid_id():
    response = app.post_json('/accounts/0', {'desc':'hello'}, status=404)
    assert response.content_type == 'application/json'


def test_generic_post_invalid_attr():
    data = {'desc':'test', 'nxattr':1234}
    response = app.post_json('/accounts/1', data, status=400)
    assert response.content_type == 'application/json'

#FIXME needs to generate a Integrity exception serverside
#def test_generic_post_invalid_attr():
#    response = app.post_json('/accounts/1', {'desc':1}, status=404)
#    assert response.content_type == 'application/json'

###############################################################################

def test_journal_put():
    posts = [{'amount':100, 'account_id':'TEST01'},
             {'amount':-100, 'account_id':'TEST02', 'memo':'testing'}]

    data = {'memo':'test journal entry',
            'datetime':'2016-06-05 14:09:00-05',
            'posts':posts}

    response = app.put_json('/journal', data, status='*')
    assert response.status_int == 200
    assert response.content_type == 'application/json'
    assert 'id' in response.json

###############################################################################

def test_imported_transactions_get():
    response = app.get('/imported_transactions?limit=10&offset=0')
    assert response.content_type == 'application/json'
    assert 'imported_transactions' in response.json

###############################################################################

