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

import datetime

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

from sqlalchemy import (Boolean, Column, DateTime, Float, Integer, LargeBinary,
                        Numeric, String, Text, Unicode)

from sqlalchemy import create_engine, ForeignKey, func, event, asc, desc, Table
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, validates
from sqlalchemy.sql import func, select, column, literal_column
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

###############################################################################

class JsonMixin:
    """Mix-in that provides a json_obj method to turn sqlalchemy objects
    into json serializable objects via util.jsonDumps.
    """
    def json_obj(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

###############################################################################

class Posting(Base, JsonMixin):
    """Represents a credit or debit, with debits being negative in the amount
    column.
    """
    #TODO: Add asset type field
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    journal_id = Column(Integer, ForeignKey('journal.id'), nullable=False)
    amount = Column(Numeric, default=0)
    seq = Column(Integer, default=0)
    fitid = Column(Unicode(length=255))
    ref = Column(Unicode(length=32))
    memo = Column(Unicode(length=1024))

    @property
    def fmt_amount(self):
        return "{:.2f}".format(self.amount)

###############################################################################

class ImportedTransaction(Base, JsonMixin):
    __tablename__ = 'imported_transactions'
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    account_hint = Column(Unicode(length=256), default="")
    datetime = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric, default=0, nullable=False)
    memo = Column(Unicode(length=1024), nullable=False)
    ref = Column(Unicode(length=32), nullable=False)
    # transaction id from the bank, only unique to bank+account
    fitid = Column(Unicode(length=255))
    posted = Column(Boolean, default=False)
    # sha1 hash of some of the data making up the transaction to ensure
    # it's unique. Eg concatenating the bank routing number, account number
    # fitid and hashing that would be acceptable. The intention is to prevent
    # the same transactions from being imported more than once.
    tid = Column(String(length=64), unique=True, nullable=True)

    @property
    def fmt_datetime(self):
        return self.datetime.strftime("%c")

    def to_post(self):
        """Return a new Posting object with some fields filled out."""
        return Posting(account_id=self.account_id, amount=self.amount,
                       memo=self.memo, ref=self.ref, fitid=self.fitid)

    def to_journal(self):
        """Return a new Journal object with some fields filled out."""
        return Journal(datatime=self.datetime, memo=self.memo)

###############################################################################

class Journal(Base, JsonMixin):
    """Represents a single transaction with debits and credits (posts)."""
    __tablename__ = 'journal'
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime(timezone=True), default=func.now())
    memo = Column(Unicode(length=1024))
    void = Column(Boolean, default=False)
    batch_id = Column(Integer, ForeignKey('batches.id'), nullable=False)
    posts = relationship('Posting', backref='journal', \
                order_by=desc(Posting.amount))

    # this exists only because the memo field was once called desc.
    @property
    def desc(self):
        return self.memo

    @property
    def fmt_datetime(self):
        return self.datetime.strftime("%c")

###############################################################################

class Batch(Base, JsonMixin):
    """A Unit of work, literally a batch of transactions."""
    __tablename__ = 'batches'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('User', backref='batches')
    datetime = Column(DateTime(timezone=True), default=func.now())
    journal = relationship('Journal', backref='batch', \
                order_by="desc(Journal.datetime)")

###############################################################################

class Account(Base, JsonMixin):
    __tablename__ = 'accounts'
    id = Column(Integer, primary_key=True)
    # Name is treated as a path with : separators
    # This affords some ease of use to the user at the expense of not
    # having a fully realized account hierarchy.
    name = Column(Unicode(length=256), unique=True, nullable=False)
    desc = Column(Unicode(length=1024), nullable=False, default='')
    closed = Column(Boolean, default=False)
    posts = relationship('Posting', backref='account')

    @hybrid_property
    def short_name(self):
        return self.name.split(':')[-1]

    @validates('name')
    def convert_upper(self, key, value):
        return value.upper()

###############################################################################

#class Asset_Type(Base): #TODO
#    __tablename__ = 'asset_types'

#    id = Column(Integer, primary_key=True)
#    name = Column(Unicode(length=256), unique=True)
#    desc = Column(Unicode(length=1024), default='')
#    places = Column(Integer, default=2)

###############################################################################

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(Unicode(length=64), unique=True, nullable=False)
    name = Column(Unicode(length=256), default='')
    last_login = Column(DateTime(timezone=True))
    last_attempt = Column(DateTime(timezone=True))
    fail_count = Column(Integer, default=0)
    password = Column(LargeBinary, nullable=False)
    locked = Column(Boolean, default=True)
    roles = relationship('Role', secondary='role_user')


    def json_obj(self):
        """Custom implementation of json_obj that leaves out the password
        field. This is for a couple of reasons a) the password column is bytes
        and isn't serializable directly and b) I don't want to leak the
        password hash accidently via json.
        """
        dic = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        del dic['password']
        return dic

###############################################################################

role_user = Table('role_user', Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('user_id', Integer, ForeignKey('users.id'))
)

class Role(Base, JsonMixin):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), unique=True)
    description = Column(Unicode(255))


###############################################################################

@event.listens_for(Posting, 'before_insert')
def posting_insert_listener(mapper, connection, target):
    target.seq = connection.scalar("SELECT (COALESCE(MAX(seq), 0) + 1) "
                                   "as max_seq FROM posts WHERE "
                                   "account_id={}".format(target.account_id))
