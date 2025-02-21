# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

from typing import List
import unittest

from basyx.aas.backend import backends
from basyx.aas.model import Referable


class ExampleBackend(backends.Backend):
    @classmethod
    def commit_object(cls, committed_object: Referable, store_object: Referable, relative_path: List[str]) -> None:
        raise NotImplementedError("This is a mock")

    @classmethod
    def update_object(cls, updated_object: Referable, store_object: Referable, relative_path: List[str]) -> None:
        raise NotImplementedError("This is a mock")


class BackendsTest(unittest.TestCase):
    def test_backend_store(self):
        backends.register_backend("mockScheme", ExampleBackend)
        self.assertIs(backends.get_backend("mockScheme:x-test:test_backend"), ExampleBackend)

        backends.register_backend("<this is totally a valid uri>", ExampleBackend)
        with self.assertRaises(ValueError) as cm:
            backends.get_backend("<this is totally a valid uri>")
        self.assertEqual("<this is totally a valid uri> is not a valid URL with URI scheme.", str(cm.exception))

        with self.assertRaises(backends.UnknownBackendException):
            backends.get_backend("some-unkown-scheme://example.com")
