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
from decimal import Decimal
import hashlib
import os

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from RecordSheet.config import OPTIONS
from RecordSheet.dbmodel import (Account, Batch, Journal, Posting,
                                    ImportedTransaction, User, Base)

###############################################################################

class DBException(Exception):
    pass

###############################################################################

_session = None

def init():
    """Initiallize the database connection"""
    global _session
    if _session:
        return _session

    connect_str = OPTIONS['dbconnectstr']
    engine = create_engine(connect_str, echo=False)
    session_factory = sessionmaker(bind=engine)
    meta = Base.metadata.create_all(engine)
    # using thread local storage
    _session = scoped_session(session_factory)

    return _session


def Session():
    return _session()

###############################################################################

def get_accounts(limit=None, offset=0):
    ses = _session()
    return ses.query(Account).order_by(Account.name)\
            .limit(limit).offset(offset).all()


def get_account(account_id):
    ses = _session()
    return ses.query(Account).get(account_id)


def get_account_by_name(name):
    ses = _session()
    return ses.query(Account).filter(Account.name==name).one()


def new_account(name, desc):
    ses = _session()
    try:
        if len(name) == 0:
            raise DBException("Account name can not be empty")

        elif name is None:
            raise DBException("Account name can not be None")

        acct = Account(name=name, desc=desc)
        ses.add(acct)
        ses.commit()
        return acct

    except IntegrityError as exc:
        ses.rollback()
        raise DBException("Account already exists") from exc

    except SQLAlchemyError:
        ses.rollback()
        raise DBException("Failed to create account") from exc

    except Exception:
        ses.rollback()
        raise

###############################################################################

def get_batch(id):
    ses = _session()
    return ses.query(Batch).get(id)

def new_batch(user_id):
    return Batch(user_id=user_id)

###############################################################################

def get_journals(limit=None, offset=0):
    ses = _session()
    return ses.query(Journal).order_by(desc(Journal.datetime))\
        .limit(limit).offset(offset).all()


def get_journal(id):
    ses = _session()
    return ses.query(Journal).get(id)

###############################################################################

def posts(account_id):
    ses = _session()
    return ses.query(Posting).filter(Posting.account_id==account_id)\
                .join(Journal).order_by(Journal.datetime)

###############################################################################

def new_transaction(batch, posts=None, datetime=None, memo=None):
    ses = _session()
    closed = ses.query(Account.id).filter(Account.closed==True)
    closed = set(r[0] for r in closed)

    try:
        #length test
        if not posts or len(posts) < 2:
            raise DBException("Journal entries require at least two posts")

        # balance test
        if sum([Decimal(p['amount']) for p in posts]):
            raise DBException("Journal entry must sum to zero")

        # test for empty memo
        if not memo or memo == "":
            raise DBException("Journal memo field must not be empty")

        _posts = []
        for p in posts:
            if 'account_id' in p:
                acct = ses.query(Account).get(p['account_id'])

            elif 'account' in p:
                acct = ses.query(Account).filter(Account.name==p['account']) \
                        .one()

                p['account_id'] = acct.id

            else:
                raise DBException("Post must contain account id or name")

            # test for closed accounts
            if acct.closed:
                raise DBException("Can not post to a closed account")

            # check for a related pending object and copy fields from it
            if 'id' in p and p['id']:
                pend = ses.query(ImportedTransaction).get(p['id'])
                post = pend.to_post()
                pend.posted = True
                if p['memo']:
                    post.memo = p['memo']

                _posts.append(post)

            else:
                post = Posting(account_id=p['account_id'], amount=p['amount'],
                               memo=(p['memo'] or memo))

                _posts.append(post)

        # create the actual posts and add them to the session
        # this is done seperately because a query after objects have been
        # added to the session will trigger a flush. Not world ending, but
        # it causes gaps in the PKEY sequence, which annoy me.
        journal = Journal(datetime=datetime, memo=memo, batch=batch)
        for post in _posts:
            post.batch = batch
            post.journal = journal
            ses.add(post)

        ses.commit()
        return journal

    except Exception:
        ses.rollback()
        raise

###############################################################################
#ImportedTransaction
def get_imported_transactions(limit=None, offset=0):
    ses = _session()
    sortdir = asc
    if offset < 0:
        sortdir = desc
        offset = abs(offset)

    return ses.query(ImportedTransaction) \
                .filter(ImportedTransaction.posted != True) \
                .order_by(sortdir(ImportedTransaction.datetime)) \
                .limit(limit).offset(offset).all()


def insert_imported_transactions(transactions):
    """Bulk insert of imported transaction data into database."""

    try:
        ses = _session()
        # filter out dups
        tids = set([r[0] for r in ses.query(ImportedTransaction.tid)])
        trs = (trs for trs in transactions if trs['tid'] not in tids)

        # bulk insert
        ses.bulk_insert_mappings(ImportedTransaction, trs)
        ses.commit()

    except Exception:
        ses.rollback()
        raise

###############################################################################

def get_users():
    ses = _session()
    return ses.query(User).all()


def get_user(id):
    ses = _session()
    return ses.query(User).get(id)


def get_user_by_username(username):
    ses = _session()
    return ses.query(User).filter(User.username == username).one()


def login(username, password):
    """Login the user with username and password."""
    ses = _session()
    try:
        user = get_user_by_username(username)
    except SQLAlchemyError:
        ses.rollback()
        return None, 'USERPASS'

    user.last_attempt = datetime.datetime.utcnow()
    if user.locked or user.fail_count >= 3:
        user.locked = True
        user.fail_count += 1
        ses.commit()

        return user, 'LOCKED'

    if compare_pw(password, user.password):
        user.last_login = user.last_attempt
        user.fail_count = 0
        ses.commit()

        return user, 'SUCCESS'

    return user, 'USERPASS'


def authenticate(user_id, password):
    try:
        ses = _session()
        user = get_user_by_username(username)
        return compare_pw(password, user.password)

    except SQLAlchemyError:
        ses.rollback()
        return False


def set_password(user_id, password):
    """Set the password for user with user_id."""
    ses = _session()
    user = ses.query(User).get(user_id)
    user.password = new_pw_hash(password)

    ses.commit()

###############################################################################

PW_MAX = 1024 # MAX password length
SALT_LEN = 512 # size of salt in bytes
HASH = 'sha512' # the hash
HASH_ROUNDS = 100000 # the number of rounds to hash

def new_pw_hash(plaintext):
    # truncate the plaintext to PW_MAX
    plaintext = plaintext[:PW_MAX]
    if not isinstance(plaintext, bytes):
        plaintext = plaintext.encode('utf8')

    salt = os.urandom(SALT_LEN)
    dk = hashlib.pbkdf2_hmac(HASH, plaintext, salt, HASH_ROUNDS)
    return salt + dk


def compare_pw(plaintext, hashed):
    plaintext = plaintext[:PW_MAX]
    if not isinstance(plaintext, bytes):
            plaintext = plaintext.encode('utf8')

    # extract the salt from the first bytes
    salt = hashed[:SALT_LEN]
    dk = hashlib.pbkdf2_hmac(HASH, plaintext, salt, HASH_ROUNDS)

    return dk == hashed[SALT_LEN:]

###############################################################################

