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

__author__ = "Eric Beanland"
__copyright__ = "Copyright 2016, Eric Beanland"
__license__ = "GPLv3"
__version__ = "0.1"

import datetime
import decimal
import xml.dom.minidom


def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


def getFirstText(tag, tagname):
    nodes = tag.getElementsByTagName(tagname)
    if not nodes:
        return None

    return getText(nodes[0].childNodes)


def parse_date(date_str):
    return datetime.datetime.strptime(date_str, "%Y%m%d").date()


def parse_datetime(datetime_str):
    return datetime.datetime.strptime(datetime_str, "%Y%m%d%H%M%S")


class ofx:
    def __init__(self, fileobj):
        self.file = fileobj
        self.dom = xml.dom.minidom.parse(fileobj)
        self.accounts = [account(e) for e in self.dom.getElementsByTagName("STMTRS")]


class account:
    def __init__(self, tag):
        self.tag = tag
        self.routing_number = getFirstText(tag, "BANKID")
        self.acount_number = getFirstText(tag, "ACCTID")
        self.type = getFirstText(tag, "ACCTTYPE")
        self.statement = statement(tag.getElementsByTagName("BANKTRANLIST")[0])


class statement:
    def __init__(self, tag):
        self.start_date = getFirstText(tag, "DTSTART")
        self.end_date = getFirstText(tag, "DTEND")
        self.transactions = [transaction(e) for e in tag.getElementsByTagName("STMTTRN")]


class transaction:

    def __init__(self, tag):
        self.type = getFirstText(tag, "TRNTYPE")
        self.posted = parse_datetime(getFirstText(tag, "DTPOSTED"))
        self.date_available = parse_date(getFirstText(tag, "DTAVAIL"))
        self.amount = decimal.Decimal(getFirstText(tag, "TRNAMT"))
        self.fitid = getFirstText(tag, "FITID")
        self.refnum = getFirstText(tag, "REFNUM")
        self.name = getFirstText(tag, "NAME")
        self._payee = getFirstText(tag, "PAYEE")
        self.memo = getFirstText(tag, "MEMO")

    @property
    def payee(self):
        return self._payee or self.name

