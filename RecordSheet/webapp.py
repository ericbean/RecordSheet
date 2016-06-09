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

import os

import bottle
from bottle import abort, redirect, request, response, route, view

from RecordSheet import dbapi, dbmodel, jsonapp, mport, plugins, reports, util
from RecordSheet.util import www_session
from RecordSheet.config import OPTIONS
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
    acct = dbapi.get_account(id)
    if acct is None:
        abort(404, "Account {} Doesn't Exist".format(id))

    return {"account": acct}

###############################################################################

@rsapp.route('/transaction/new', name='new_transaction')
@view('new_transaction')
def new_transaction():
    return {'accounts': dbapi.get_accounts()}

###############################################################################

@rsapp.route('/batch/<id:int>', name='batch_view')
@view('batch')
def batch(id):
    batch = dbapi.get_batch(id)
    if batch is None:
        abort(404, "Batch {} Doesn't Exist".format(id))

    return {"batch": batch}

###############################################################################

@rsapp.route('/journal', name='journal_view')
@view('journal')
def journal():
    return {"journals":dbapi.get_journals()}


@rsapp.route('/journal/<id:int>', name='journal_entry_view')
@view('journal')
def journal_entry(id):
    journal = dbapi.get_journal(id)
    if journal is None:
        abort(404, "Journal Entry {} Doesn't Exist".format(id))

    return {"journals":[journal], "posts":[]}

###############################################################################

@rsapp.route('/import', name='import_tr')
@view('import')
def import_tr():
    return {'mport_formats':mport.formats}


@rsapp.post('/import', name='import_tr_post')
@view('import')
def import_tr_post():
    file_format = request.forms.get('file_format')
    upload = request.files.get('upload')
    account_name = request.forms.get('account_name')
    account_id = None
    if account_name:
        account = dbapi.get_account_by_name(account_name)
        account_id = account.id

    transactions = mport.formats[file_format](upload.file)

    def trgen(transactions):
        for tr in transactions:
            tr['account_id'] = account_id
            yield tr

    dbapi.insert_imported_transactions(trgen(transactions))

    redirect(rsapp.get_url('import_tr'))

###############################################################################

@rsapp.route('/imported_transactions', name='imported_tr')
@view('incomplete')
def incomplete_trs():
    pagesize = 10
    page = int(request.query.get('page', 0))
    offset = page * pagesize
    #TODO load all the data from xhr
    return {"posts": dbapi.get_imported_transactions(limit=pagesize,offset=offset)}

###############################################################################

@rsapp.route('/users/<username>', name='user_view')
@view('user')
def user_view(username):
    user = dbapi.get_user_by_username(username)
    if user is None:
        abort(404, "User \"{}\" Doesn't Exist".format(username))

    return {'user': user}

###############################################################################

@rsapp.route('/me', name='me')
@view('me')
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
    return {}


@rsapp.post('/login', name='login_post', roles=False)
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

@rsapp.route('/static/<filename:path>', name='static', roles=False)
def send_static(filename):
    return bottle.static_file(filename, root=STATIC_ROOT)

###############################################################################

# install plugins
rsapp.install(plugins.CsrfPlugin())
rsapp.install(plugins.AuthPlugin(www_session))

###############################################################################

def app(**kwargs):
    OPTIONS.update(kwargs)

    # merge instead of mount
    rsapp.merge(reports.app)
    rsapp.mount('/json/', jsonapp.app)
    # setup path for views
    bottle.TEMPLATE_PATH.insert(0, VIEWS_ROOT)

    #add stuff to templates
    bottle.BaseTemplate.defaults['bottle'] = bottle
    bottle.BaseTemplate.defaults['url'] = rsapp.get_url
    bottle.BaseTemplate.defaults['app'] = rsapp
    bottle.BaseTemplate.defaults['request'] = request
    bottle.BaseTemplate.defaults['jsonDumps'] = util.jsonDumps
    bottle.BaseTemplate.defaults['www_session'] = www_session

    from beaker.middleware import SessionMiddleware
    session_opts = {'session.type': 'memory',
                    'session.auto': True,
                    'session.cookie_expires': True,
                    'secret': os.urandom(64)}

    sessionapp = SessionMiddleware(rsapp, session_opts)
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
