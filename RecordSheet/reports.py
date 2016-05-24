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
import os

import bottle
from bottle import (Bottle, delete, get, post, put, redirect, request,
    response, route, view)

from sqlalchemy import asc, desc, func
from RecordSheet import dbapi, dbmodel, util
from RecordSheet.dbmodel import (Account, Batch, Journal, Posting,
                                    ImportedTransaction)

app = bottle.Bottle()

###############################################################################

@app.route('/reports', name='report_list')
@view('reports/index')
def index():
    return {}


@app.route('/reports/trial_balance', name='trial_balance')
@view('reports/trial_balance')
def trial_balance():
    dbs = dbapi.Session()
    balances = dbs.query(Account.name, func.sum(Posting.amount)) \
                .join(Account.posts) \
                .group_by(Account.name) \
                .order_by(Account.name).all()

    return {'balances':balances}

###############################################################################

@app.route('/reports/profit_and_loss', name='pl_selector')
@view('reports/pl_form')
def pl_selector():
    dbs = dbapi.Session()
    # Entities are just top-level account names
    entities = dbs.query(Account)\
                    .filter(~Account.name.like('%:%')) \
                    .all()
    return {'entities': entities}


@app.route('/reports/profit_and_loss/pl', name='pl_report')
@view('reports/pl_report')
def pl_report():
    ses = dbapi.Session()
    entity = request.GET.get('entity')
    period = util.year_range(int(request.GET.get('period')))

    # This requires all income and expenses to be in accounts with ":EXPENSES:"
    # or ":INCOME:" in the name.
    acct_bal = func.sum(Posting.amount).label('acct_bal')
    income = ses.query(Account.name, acct_bal)\
                    .filter(Account.name.like(entity+':INCOME:%')) \
                    .join(Account.posts) \
                    .group_by(Account.name) \
                    .order_by(Account.name) \
                    .join(Journal) \
                    .filter(Journal.datetime.between(*period))

    expenses = ses.query(Account.name, acct_bal)\
                    .filter(Account.name.like(entity+':EXPENSES:%')) \
                    .join(Account.posts) \
                    .group_by(Account.name) \
                    .order_by(Account.name) \
                    .join(Journal) \
                    .filter(Journal.datetime.between(*period))

    return {'entity':entity,
            'period':period,
            'income':income.all(),
            'expenses':expenses.all()}

###############################################################################

