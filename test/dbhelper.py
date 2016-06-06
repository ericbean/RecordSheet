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

"""Setup database for testing and rollback after."""

from sqlalchemy import event
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import Session

from RecordSheet.dbapi import Base
from RecordSheet import dbapi, dbmodel

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
    ses.add(dbmodel.Account(name='TEST01', desc='test account 01'))
    ses.add(dbmodel.Account(name='TEST02', desc='test account 02'))
    user = dbmodel.User(username='testuser', name='Test T. User',
                       password=dbapi.new_pw_hash('passtestword'))
    ses.add(user)

    batch = dbmodel.Batch(user=user)
    ses.add(batch)
    jrnl = dbmodel.Journal(memo='test', batch=batch,
                datetime='2016-06-05 14:09:00-05')
    ses.add(jrnl)
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
