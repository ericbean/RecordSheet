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

from RecordSheet.dbmodel import (Account, Batch, Journal, Posting, pendingPost,
                                    User, Base)

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

###############################################################################

class DBException(Exception):
    pass

###############################################################################

#TODO load this info from a config file or env var.
DB_CONNECT_STR = 'postgresql:///recordsheet'
DB_CONNECT_STR_TESTING = 'postgresql:///recordsheet_test'

_session = None

def init(connect_str=DB_CONNECT_STR):
    """Initiallize the database connection"""
    global _session
    if _session:
        return _session
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

def new_batch(username):
    return Batch(user=username)

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
            print("sum=", sum([Decimal(p['amount']) for p in posts]))
            raise DBException("Journal entry must sum to zero")

        # test for empty memo
        if not memo or memo == "":
            raise DBException("Journal memo field must not be empty")

        for p in posts:
            # while we're at it, convert account names (if they exist) to
            # account_ids
            if 'account' in p:
                acct = get_account_by_name(session, p['account'])
                p['account_id'] = acct.id

            if not p['account_id']:
                raise DBException("Post account_id must exist.")

            acc = ses.query(Account).get(p['account_id'])

            # test for closed accounts
            if acc.closed:
                raise DBException("Can not post to a closed account")

        journal = Journal(datetime=datetime, memo=memo, batch=batch)
        for p in posts:
            if 'id' in p and p['id']:
                pend = ses.query(pendingPost).get(p['id'])
                post = pend.to_post()
                pend.posted = True
                if p['memo']:
                    post.memo = p['memo']

            else:
                post = Posting(account_id=p['account_id'], amount=p['amount'],
                               memo=(p['memo'] or memo))

            post.batch = batch
            post.journal = journal
            ses.add(post)

        ses.commit()
        return journal

    except Exception:
        ses.rollback()
        raise

###############################################################################

def get_pending_posts(limit=None, offset=0):
    ses = _session()
    sortdir = asc
    if offset < 0:
        sortdir = desc
        offset = abs(offset)

    return ses.query(pendingPost).filter(pendingPost.posted != True) \
                .order_by(sortdir(pendingPost.datetime)) \
                .limit(limit).offset(offset).all()


def pending_posts_count(session):
    """Get the number of un-posted rows in pending_posts."""
    ses = _session()
    return ses.query(func.count(pendingPost.posted))\
                .filter(pendingPost.posted == False).scalar()


def new_pending_posts(session, transactions):
    ses = _session()
    fitids = set([r[0] for r in ses.query(pendingPost.fitid)])
    dup = []
    for tr in transactions:
        pp = pendingPost(**tr)
        if pp.fitid in fitids:
            dup.append(pp)
        else:
            session.add(pp)

    try:
        ses.commit()

    except Exception:
        ses.rollback()
        raise

    return dup

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
        return None, 'USERPASS'

    user.last_attempt = datetime.datetime.utcnow()
    if user.locked or user.fail_count >= 3:
        user.locked = True
        user.fail_count += 1
        ses.commit()

        return user, 'LOCKED'

    if user.authenticate(password):
        user.last_login = user.last_attempt
        user.fail_count = 0
        ses.commit()

        return user, 'SUCCESS'

    return user, 'USERPASS'


def set_password(user_id, password):
    """Set the password for user with user_id."""
    ses = _session()
    user = ses.query(User).get(user_id)
    user.set_password(password)
    ses.commit()

###############################################################################

