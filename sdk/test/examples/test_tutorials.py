# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
Tests for the tutorials

Functions to test if a tutorial is executable
"""
import os
import tempfile
import unittest
from contextlib import contextmanager

from basyx.aas import model
from .._helper.test_helpers import COUCHDB_OKAY, TEST_CONFIG, COUCHDB_ERROR


class TutorialTest(unittest.TestCase):
    def test_tutorial_create_simple_aas(self):
        from basyx.aas.examples import tutorial_create_simple_aas
        self.assertEqual(tutorial_create_simple_aas.submodel.get_referable('ExampleProperty').value, 'exampleValue')
        store = model.DictObjectStore({tutorial_create_simple_aas.submodel})
        next(iter(tutorial_create_simple_aas.aas.submodel)).resolve(store)

    def test_tutorial_storage(self):
        from basyx.aas.examples import tutorial_storage
        # The tutorial already includes assert statements for the relevant points. So no further checks are required.

    @unittest.skipUnless(COUCHDB_OKAY, "No CouchDB is reachable at {}/{}: {}".format(TEST_CONFIG['couchdb']['url'],
                                                                                     TEST_CONFIG['couchdb']['database'],
                                                                                     COUCHDB_ERROR))
    def test_tutorial_backend_couchdb(self):
        from basyx.aas.examples import tutorial_backend_couchdb

    def test_tutorial_serialization_deserialization_json(self):
        with temporary_workingdirectory():
            from basyx.aas.examples import tutorial_serialization_deserialization
            pass
        # The tutorial already includes assert statements for the relevant points. So no further checks are required.

    def test_tutorial_aasx(self):
        with temporary_workingdirectory():
            from basyx.aas.examples import tutorial_aasx
            pass
        # The tutorial already includes assert statements for the relevant points. So no further checks are required.


@contextmanager
def temporary_workingdirectory():
    """
    A helper contextmanager to temporarily change the current working directory of the Python process to a temporary
    directory.

    The temp directory is deleted with all its contents when leaving the with-context. This can be used to test Python
    scripts, which write files to the current working directory.
    """
    cwd = os.getcwd()
    tempdir = tempfile.TemporaryDirectory()
    os.chdir(tempdir.name)
    try:
        yield None
    finally:
        os.chdir(cwd)
        tempdir.cleanup()
