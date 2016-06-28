#!/usr/bin/env python3
import os
from setuptools import setup
import RecordSheet

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="RecordSheet",
    version=RecordSheet.__version__,
    author=RecordSheet.__author__,
    author_email="eric.beanland@gmail.com",
    description=("Double entry accounting application for small business."),
    license="GPLv3+",
    keywords="double entry accounting",
    packages=['RecordSheet'],
    include_package_data=True,
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Topic :: Office/Business :: Financial :: Accounting",
        ("License :: OSI Approved :: GNU General Public License v3 or later"
            " (GPLv3+)"),
        "Programming Language :: Python :: 3.4"
    ],
    entry_points={'console_scripts': ['recordsheet=RecordSheet.cmdline:main']},
    install_requires=['Beaker==1.8.0',
                      'bottle==0.12.9',
                      'gevent==1.1.1',
                      'greenlet==0.4.9',
                      'psycopg2==2.6.1',
                      'SQLAlchemy==1.0.12'],
    test_suite='nose.collector',
    tests_require=['nose', 'webtest']
)
