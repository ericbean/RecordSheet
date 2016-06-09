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

"""This contains the bottle application that handles the json api."""

import functools
import html
import os
import traceback

import bottle
from bottle import abort, Bottle, HTTPError, redirect, request, response

from sqlalchemy import asc, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import label
from RecordSheet import dbapi, dbmodel, plugins, util
from RecordSheet.dbmodel import (Account, Batch, Journal, Posting,
                                    ImportedTransaction, User, Role)
from RecordSheet.config import OPTIONS


app = bottle.Bottle(autojson=False)
app.install(plugins.CsrfPlugin())
app.install(plugins.AuthPlugin())

sorte = {'accounts':Account,
         'batches':Batch,
         'imported_transactions':ImportedTransaction,
         'journal':Journal,
         'posts':Posting,
         'roles':Role}

###############################################################################

def jsonout(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        status = 500
        try:
            result = func(*args, **kwargs)
            status = 200
        except HTTPError as exc:
            print(exc)
            status = exc.status
            result = {'errorMsg':exc.args[1]}
        except Exception as exc:
            if OPTIONS['debug']:
                traceback.print_exc()
            result = {'errorMsg':'Internal Server Error'}

        response.status = status
        response.content_type = 'application/json'

        return util.jsonDumps(result)

    return wrapper

###############################################################################

@app.route('/<kind>')
@jsonout
def generic_collection(kind):
    """Generic GET handler.

    The allowed query parameters are:

     - sort: SQL column name, can be sufixed with ".asc" or ".desc" to \
     control order.
     - limit: LIMIT to apply to the results.
     - offset: OFFSET to apply to the results. Must be accompanied by a limit.

    Example: https://example.com/XYZ?sort=name.desc&limit=100&offset=100
    """
    ses = dbapi.Session()
    cls = sorte.get(kind)
    if cls is None:
        abort(404, 'Not Found')

    qry = ses.query(cls)

    sortcols = request.GET.getall('sort')
    for col in sortcols:
        colname = col
        sortfunc = lambda x: x
        if col.endswith('.desc'):
            colname = col[:-5] # remove trailing ".desc"
            sortfunc = desc
        elif col.endswith('.asc'):
            colname = col[:-4]
            sortfunc = asc

        if colname in cls.__table__.columns:
            qry = qry.order_by(sortfunc(colname))

    if 'limit' in request.GET:
        limit = request.GET.get('limit', default=0, type=int)
        qry = qry.limit(abs(limit))

    if 'offset' in request.GET and 'limit' in request.GET:
        offset = request.GET.get('offset', default=0, type=int)
        qry = qry.offset(abs(offset))

    return {kind:qry.all()}



@app.route('/<kind>/<id:int>')
@jsonout
def generic_item(kind, id):
    ses = dbapi.Session()
    cls = sorte.get(kind)
    if cls is None:
        abort(404, 'Not Found')

    obj = ses.query(cls).get(id)
    if not obj:
        abort(404, 'Not Found')

    return obj

###############################################################################

@app.put('/<kind>')
@jsonout
def generic_collection_put(kind):
    try:
        ses = dbapi.Session()
        cls = sorte.get(kind)
        obj = cls()
        for key, val in request.json.items():
            if key in cls.__table__.columns:
                setattr(obj, key, val)
            else:
                abort(400, 'Bad Request')

        ses.add(obj)
        ses.commit()

    except IntegrityError:
        ses.rollback()
        abort(400, 'Bad Request')

    return obj


@app.post('/<kind>/<id:int>')
@jsonout
def generic_item_post(kind, id):
    try:
        ses = dbapi.Session()
        cls = sorte.get(kind)
        obj = ses.query(cls).get(id)
        if not obj:
            abort(404, 'Not Found')

        for key, val in request.json.items():
            if key in cls.__table__.columns:
                setattr(obj, key, val)
            else:
                abort(400, 'Bad Request')

        ses.commit()

    except IntegrityError:
        ses.rollback()
        abort(400, 'Bad Request')

    return obj

###############################################################################

@app.put('/journal')
@jsonout
def journal_put():
    try:
        ws = request.environ.get('beaker.session')
        batch = ws.setdefault('batch', Batch(user_id=ws['user_id']))
        # allow sending datetime as sending empty string or not at all
        data = request.json
        data['datetime'] = data.get('datetime', None) or None
        journal = dbapi.new_transaction(batch, **data)

        return journal

    except dbapi.DBException as exc:
        abort(400, 'Bad Request')

###############################################################################

@app.get('/imported_transactions')
@jsonout
def imported_transactions_get():
    ses = dbapi.Session()
    qry = ses.query(dbapi.ImportedTransaction) \
            .filter(dbapi.ImportedTransaction.posted != True) \
            .order_by(desc(dbapi.ImportedTransaction.datetime)) \

    if 'limit' in request.GET:
        limit = request.GET.get('limit', default=0, type=int)
        qry = qry.limit(abs(limit))

    if 'offset' in request.GET and 'limit' in request.GET:
        offset = request.GET.get('offset', default=0, type=int)
        qry = qry.offset(abs(offset))

    return {'imported_transactions':qry.all()}

###############################################################################
