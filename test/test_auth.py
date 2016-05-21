#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from RecordSheet import auth

def test_pathasm():
    retval = auth.pathasm('foo', 'bar', 'baz')
    assert retval == '/foo/bar/baz'


class AppFixture:
    """Mock wsgi application."""
    def __init__(self):
        self.status = ''
        self.headers = []

    def __call__(self, environ, start_response):
        return [b'foo']

    def start_response(self, status, response_headers, exc_info=None):
        self.status = status
        self.headers = response_headers


def test_app_redirect():
    testserver = AppFixture()
    testapp = AppFixture()
    authapp = auth.auth_middleware(testapp)
    environ = {'beaker.session':{},
                'SCRIPT_NAME':"TEST",
                'PATH_INFO':"",
                'QUERY_STRING':"item=9000"}
    response = authapp(environ, testserver.start_response)
    assert testserver.status == "303 See Other"
    assert testserver.headers[0][0] == "Location"
    assert testserver.headers[0][1] == "/TEST/login"
    assert environ['beaker.session']['dest_path'] == "/TEST?item=9000"
