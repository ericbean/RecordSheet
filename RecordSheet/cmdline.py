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

import argparse
import getpass
import sys

import bottle
import sqlalchemy
from RecordSheet import dbapi, dbmodel, config, webapp, __version__

###############################################################################

def stats(args):
    print("RecordSheet", __version__)
    print('Nothing to do')

###############################################################################

def server(args):
    # import gevent and monkey patch here so only the gevent server is
    # affected.
    from gevent import monkey
    monkey.patch_all()
    config.OPTIONS['debug'] = args.debug
    bottle.run(app=webapp.app(), server='gevent', debug=args.debug)

###############################################################################

def adduser(args):
    try:
        ses = dbapi.init()
    except Exception:
        sys.exit("Failed to init database")

    try:
        pw = getpass.getpass()
        if pw == "":
            sys.exit("Password can not be empty")

        pw = dbapi.new_pw_hash(pw)
        user = dbmodel.User(username=args.username, password=pw, locked=False)
        user.name = getattr(args, 'fullname', args.username)
        ses.add(user)
        ses.commit()

    except sqlalchemy.exc.IntegrityError:
        ses.rollback()
        sys.exit('User "{}" already exists'.format(args.username))

    except EOFError:
        ses.rollback()
        sys.exit('adduser canceled')

    else:
        print('User "{}" added'.format(args.username))

###############################################################################

def main():
    parser = argparse.ArgumentParser(prog='RecordSheet', description=None)
    parser.set_defaults(func=stats)
    subparsers = parser.add_subparsers(help='sub commands')
    #opts for server
    serve_parser = subparsers.add_parser('server',
                    help='start a stand alone web server',
                    aliases=['serve'])
    serve_parser.add_argument('--debug', '-d', action='store_true',
                    help='turn on debuging')
    serve_parser.set_defaults(func=server)

    #opts for adduser
    adduser_parser = subparsers.add_parser('adduser',
                    help='add a user for RecordSheet',
                    aliases=['useradd'])
    adduser_parser.add_argument('username',
                    help='user\'s username')
    adduser_parser.add_argument('--fullname','-f',
                    help='user\'s full name')
    adduser_parser.set_defaults(func=adduser)

    args = parser.parse_args()
    args.func(args)

###############################################################################
