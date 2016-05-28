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

"""Import support for various file formats."""

import csv
import decimal
import hashlib
import html
import io

from RecordSheet.ofx import ofx


def import_ofx(fileobj):
    data = ofx(fileobj)
    for acct in data.accounts:
        transactions = acct.statement.transactions
        acct_num = acct.acount_number.lstrip('0')
        acct_num = ('X' * (len(acct_num) - 4)) + acct_num[-4:]
        pre_hash = acct.routing_number + acct.acount_number
        for tr in transactions:
            tid = hashlib.sha1((pre_hash+tr.fitid).encode('utf8'))
            yield {"account_hint": acct_num,
                   "datetime":tr.posted,
                   "amount":tr.amount,
                   "memo":html.unescape(tr.memo),
                   "ref":tr.refnum,
                   "fitid":tr.fitid,
                   "tid":tid.hexdigest()}


def import_amazon_csv(fileobj):
    #useful cols:Order Date, Order ID, Title, Item Subtotal, Shipment Date
    with io.TextIOWrapper(fileobj, encoding='utf8') as fobj:
        reader = csv.DictReader(fobj)
        for tr in reader:
            amount = decimal.Decimal(tr['Item Subtotal'].strip('$'))
            tid = hashlib.sha1((tr['Order ID']+tr['Title']).encode('utf8'))
            yield {"account_hint": "",
                   "datetime":tr['Order Date'],
                   "amount":amount,
                   "memo":html.unescape(tr['Title']),
                   "ref":tr['Order ID'],
                   "fitid":"",
                   "tid":tid.hexdigest()}


formats = {'ofx':import_ofx,
           'amazon csv': import_amazon_csv}

