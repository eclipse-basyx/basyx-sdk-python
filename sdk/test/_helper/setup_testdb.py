#!/usr/bin/env python3
# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
Small helper script to setup a blank CouchDB server with a test database and a test user (e.g. for use in CI)

This script uses the ``test/test_config.ini`` and ``test/test_config.default.ini`` files to setup the CouchDB server
the way the tests will expect it. The admin user and password used to do the setup may be configured via command line:

    setup_testdb.py -u admin -p admin_password

If no CouchDB server at the configured URL, the script will exit with exit code 1. To avoid the error exit code (for use
in CI), provide the ``--failsafe`` option.
"""
import base64
import configparser
import argparse
import json
import os.path
import sys
import urllib.request
import urllib.error

# Parse test config (required to setup the CouchDB as expected)
TEST_CONFIG = configparser.ConfigParser()
TEST_CONFIG.read((os.path.join(os.path.dirname(__file__), "..", "test_config.default.ini"),
                  os.path.join(os.path.dirname(__file__), "..", "test_config.ini")))

# Parse command line arguments
parser = argparse.ArgumentParser(description='Setup CouchDB test database according to test_config.ini')
parser.add_argument('--admin-user', '-u', help='Name of the CouchDB admin user')
parser.add_argument('--admin-password', '-p', help='Password of the CouchDB admin user', default='')
parser.add_argument('--failsafe', '-f', action='store_true',
                    help='Exit with exit code 0 even if no database server could be reached or the database already '
                         'exists on the server.')
args = parser.parse_args()


# Some basic data for couchdb setup
default_headers = {
    'Accept': 'application/json',
}
if args.admin_user is not None:
    default_headers['Authorization'] = 'Basic %s' % base64.b64encode(
        ('%s:%s' % (args.admin_user, args.admin_password)).encode('ascii')).decode("ascii")


# Check if CouchDB server is available
request = urllib.request.Request(
    TEST_CONFIG['couchdb']['url'],
    headers=default_headers,
    method='HEAD')
try:
    urllib.request.urlopen(request)
except urllib.error.URLError as e:
    print("Could not reach CouchDB server at {}: {}".format(TEST_CONFIG['couchdb']['url'], e))
    sys.exit(0 if args.failsafe else 1)

# The actual work
# Check if the System databases exist and create them otherwise
request = urllib.request.Request(
    "{}/_users".format(TEST_CONFIG['couchdb']['url']),
    headers=default_headers,
    method='HEAD')
try:
    urllib.request.urlopen(request)
except urllib.error.HTTPError as e:
    if e.code != 404:
        raise
    for db in ('_global_changes', '_replicator', '_users'):
        request = urllib.request.Request(
            "{}/{}".format(TEST_CONFIG['couchdb']['url'], db),
            headers=default_headers,
            method='PUT')
        urllib.request.urlopen(request)


# Create the database if not existing
request = urllib.request.Request(
    "{}/{}".format(TEST_CONFIG['couchdb']['url'], TEST_CONFIG['couchdb']['database']),
    headers=default_headers,
    method='PUT')
try:
    urllib.request.urlopen(request)
except urllib.error.HTTPError as e:
    if e.code == 412:
        # TODO make more failsafe: Delete and recreate database if it exists already
        print("CouchDB database {} already existed. Exiting ...".format(TEST_CONFIG['couchdb']['database']))
        sys.exit(0 if args.failsafe else 1)
    else:
        raise


# Create the user if not existing
request = urllib.request.Request(
    "{}/_users/org.couchdb.user:{}".format(TEST_CONFIG['couchdb']['url'], TEST_CONFIG['couchdb']['user']),
    headers=default_headers,
    method='PUT',
    data=json.dumps({
        "name": TEST_CONFIG['couchdb']['user'],
        "password": TEST_CONFIG['couchdb']['password'],
        "roles": [],
        "type": "user"
    }).encode())
# TODO make more failsafe: Set password of user if they exist already
urllib.request.urlopen(request)


# Add user as member of database
# TODO make more failsafe: Keep existing authorizations
request = urllib.request.Request(
    "{}/{}/_security".format(TEST_CONFIG['couchdb']['url'], TEST_CONFIG['couchdb']['database']),
    headers=default_headers,
    method='PUT',
    data=json.dumps({
        "admins": {
            "names": [],
            "roles": []},
        "members": {
            "names": [TEST_CONFIG['couchdb']['user']],
            "roles": []}
    }).encode())
urllib.request.urlopen(request)
