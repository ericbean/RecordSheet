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

import html
import json
import os
import traceback

import bottle
# at some point I'll just import *
from bottle import (abort, delete, get, hook, post, put, redirect, request,
    response, route, view)

from RecordSheet import dbapi, dbmodel, reports, util
from RecordSheet.ofx import ofx

#monkey patch bottle json funcs
bottle.json_loads = lambda s: util.jsonLoads(s.decode('utf8', 'strict') \
    if isinstance(s, bytes) else unicode(s)) # send strings not bytes
bottle.json_dumps = util.jsonDumps

APP_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_ROOT = os.path.join(APP_DIR, 'static')
VIEWS_ROOT = os.path.join(APP_DIR, 'views')

rsapp = bottle.Bottle(autojson=False)
# re-setup autojson with util.jsonDumps
rsapp.install(bottle.JSONPlugin(json_dumps=util.jsonDumps))

###############################################################################

def www_session():
    """Utility function to get the web session."""
    session = request.environ.get('beaker.session')

    return session

def json_error(status=500, error_msg=None):
    """Helper for returning json responses indicating errors. Sets the http
    status and content-type headers of the response (side effects).
    """
    if not error_msg:
        error_msg = 'Internal Server Error'
    # set the http status code and content type
    response.status = status
    response.content_type = 'application/json'
    # a str will bypass the autojson plugin
    if bottle.DEBUG:
        traceback.print_exc()
    return util.jsonDumps({'errorMsg': str(error_msg)})

###############################################################################

@rsapp.route('/', name='index')
@view('index')
def index():
    return {}

###############################################################################

@rsapp.route('/accounts', name='account_chart')
@view('account_chart')
def account_chart():
    return {}


@rsapp.route('/accounts/<id:int>', name='account_view')
@view('account')
def account_view(id):
    return {"account": dbapi.get_account(id)}


@rsapp.route('/json/accounts', name='accounts_json')
def accounts_json_view():
    return {'accounts': dbapi.get_accounts()}


@rsapp.post('/json/accounts/new', name='new_account_json')
def json_accounts_new():
    try:
        name = request.json['name']
        desc = request.json['desc']
        acct = dbapi.new_account(name, desc)
        return {'acct':acct}

    except KeyError:
        return json_error(400, 'Missing name or desc')

    except dbapi.DBException as exc:
        return json_error(400, exc)

    except Exception as exc:
        return json_error(500, exc)

###############################################################################

@rsapp.route('/transaction/new', name='new_transaction')
@view('new_transaction')
def new_transaction():
    return {'accounts': dbapi.get_accounts()}


@rsapp.post('/json/journal/new', name='new_transaction_post')
def new_transaction_json():
    try:
        ws = www_session()
        batch = ws.setdefault('batch', dbapi.new_batch(ws['user_id']))
        # allow sending datetime as sending empty string or not at all
        data = request.json
        data['datetime'] = data.get('datetime', None) or None
        journal = dbapi.new_transaction(batch, **data)

        return {'journal_id':journal.id}

    except dbapi.DBException as exc:
        return json_error(400, exc)

    except Exception as exc:
        return json_error(500, exc)

###############################################################################

@rsapp.route('/batch/<id:int>', name='batch_view')
@view('batch')
def batch(id):
    return {"batch": dbapi.get_batch(id)}

###############################################################################

@rsapp.route('/journal', name='journal_view')
@view('journal')
def journal():
    return {"journals":dbapi.get_journals()}


@rsapp.route('/journal/<id:int>', name='journal_entry_view')
@view('journal')
def journal_entry(id):
    return {"journals":[dbapi.get_journal(id)], "posts":[]}

###############################################################################

@rsapp.route('/import', name='import_tr')
@view('import')
def import_tr():
    pagesize = 10
    page = int(request.query.get('page', 0))
    offset = page * pagesize
    return {"posts": dbapi.get_pending_posts(limit=pagesize,offset=offset),
            'accounts': dbapi.get_accounts()}


@rsapp.post('/import', name='import_tr_post')
@view('import')
def import_tr_post():
    # TODO Need to check the mime type/ext/whatever and possibly handle
    # csv files or other formats
    upload = request.files.get('upload')
    account = dbapi.get_account_by_name(request.forms.get('account_name'))
    data = ofx(upload.file)
    transactions = data.accounts[0].statement.transactions

    def tr_gen(transactions, account_id):
        for tr in transactions:
            yield {"account_id":account_id,
                   "datetime":tr.posted,
                   "amount":tr.amount,
                   "memo":html.unescape(tr.memo),
                   "ref":tr.refnum,
                   "fitid":tr.fitid}

    redirect('/import')


@rsapp.route('/json/import', name='import_tr_json')
def import_tr_json():
    pagesize = 10
    page = int(request.query.get('page', 0))
    offset = page * pagesize
    pposts = dbapi.get_pending_posts(limit=pagesize, offset=offset)

    return {"pending": pposts}

###############################################################################

@rsapp.route('/users/<username>', name='user_view')
def user_view(username):
    return {'user':dbapi.get_user_by_name(username)}


@rsapp.post('json/users/new')
def json_user_new():
    return {}

###############################################################################

@rsapp.route('/me', name='me')
@view('user_self')
def user_self_edit():
    ws = www_session()
    user = dbapi.get_user(ws['user_id'])

    return {'user':user}


@rsapp.post('/me/password', name='me_pw')
def user_self_edit():
    ws = www_session()
    pw = request.POST.get('password', None)
    new_pw = request.POST.get('new_password', None)
    confirm_pw = request.POST.get('confirm_password', None)
    if not pw:
        abort(400, "You must enter your password.")

    elif not new_pw and not confirm_pw:
        abort(400, "You must enter a new password and confirm it.")

    elif new_pw != confirm_pw:
        abort(400, "New password doesn't match confirmation.")

    user = dbapi.get_user(ws['user_id'])
    success = user.authenticate(pw)
    if success:
        dbapi.set_password(ws['user_id'], new_pw)
        redirect('/')

    abort(401, "Password or username is incorrect")


@rsapp.route('/admin', name='admin_users')
@view('admin_users')
def admin_users():
    return {'users':dbapi.get_users()}


###############################################################################

@rsapp.route('/login', name='login')
@view('login')
def login():
    # ensure csrf-token is set
    ws = www_session()
    if 'csrf-token' not in ws:
        ws['csrf-token'] = util.csrf_token()
    return {}


@rsapp.post('/login', name='login_post')
@view('login')
def login_post():
    ws = www_session()
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)
    if username and password:
        user, success = dbapi.login(username, password)
        if success == 'USERPASS':
            msg = "Invalid username or password"

        elif success == 'LOCKED':
            msg = "The account is locked"

        elif success == 'SUCCESS':
            ws['authenticated'] = True
            ws['user_id'] = user.id
            # send user back to their orginal request or /
            redirect(ws.get('dest_path', rsapp.get_url('index')))

        return {'msg':msg}

    # if we get to here something stupid is happening
    abort(400, "Password or username not submitted")


@rsapp.route('/logout', name='logout')
@view('login')
def logout():
    ws = www_session()
    ws['authenticated'] = False
    ws['csrf-token'] = util.csrf_token()
    return {'msg':'You are now logged out.'}

###############################################################################

@rsapp.route('/static/<filename:path>', name='static')
def send_static(filename):
    return bottle.static_file(filename, root=STATIC_ROOT)

###############################################################################

@rsapp.hook('before_request')
def csrf_check():
    if request.method != 'GET':
        ws = www_session()
        token = (request.POST.get('csrf-token') or
                        request.headers.get('X-csrf-token'))

        if token != ws['csrf-token']:
            abort(400, "CSRF Token Is Missing")

###############################################################################

def app():
    # merge instead of mount
    rsapp.merge(reports.app)
    # setup path for views
    bottle.TEMPLATE_PATH.insert(0, VIEWS_ROOT)

    #add stuff to templates
    bottle.BaseTemplate.defaults['bottle'] = bottle
    bottle.BaseTemplate.defaults['url'] = rsapp.get_url
    bottle.BaseTemplate.defaults['app'] = rsapp
    bottle.BaseTemplate.defaults['jsonDumps'] = util.jsonDumps
    bottle.BaseTemplate.defaults['www_session'] = www_session

    from RecordSheet.auth import auth_middleware
    from beaker.middleware import SessionMiddleware
    authapp = auth_middleware(rsapp)
    session_opts = {'session.type': 'memory',
                    'session.auto': True,
                    'session.cookie_expires': True,
                    'secret': os.urandom(64)}

    sessionapp = SessionMiddleware(authapp, session_opts)
    dbapi.init()
    return sessionapp

###############################################################################

def main():
    # import gevent and monkey patch here so only the gevent server is
    # affected.
    from gevent import monkey
    monkey.patch_all()
    bottle.run(app=app(), server='gevent', debug=True)

###############################################################################

