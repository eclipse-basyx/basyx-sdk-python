# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import unittest

from basyx.aas import model
from basyx.aas.model import _string_constraints


class StringConstraintsTest(unittest.TestCase):
    def test_identifier(self) -> None:
        identifier: model.Identifier = ""
        with self.assertRaises(ValueError) as cm:
            _string_constraints.check_identifier(identifier)
        self.assertEqual("Identifier has a minimum length of 1! (length: 0)", cm.exception.args[0])
        identifier = "a" * 2001
        with self.assertRaises(ValueError) as cm:
            _string_constraints.check_identifier(identifier)
        self.assertEqual("Identifier has a maximum length of 2000! (length: 2001)", cm.exception.args[0])
        identifier = "a" * 2000
        _string_constraints.check_identifier(identifier)

    def test_version_type(self) -> None:
        version: model.VersionType = ""
        with self.assertRaises(ValueError) as cm:
            _string_constraints.check_version_type(version)
        self.assertEqual("VersionType has a minimum length of 1! (length: 0)", cm.exception.args[0])
        version = "1" * 5
        with self.assertRaises(ValueError) as cm:
            _string_constraints.check_version_type(version)
        self.assertEqual("VersionType has a maximum length of 4! (length: 5)", cm.exception.args[0])
        version = "0" * 4
        with self.assertRaises(ValueError) as cm:
            _string_constraints.check_version_type(version)
        self.assertEqual("VersionType must match the pattern '([0-9]|[1-9][0-9]*)'! (value: '0000')",
                         cm.exception.args[0])
        version = "0"
        _string_constraints.check_version_type(version)

    def test_aasd_130(self) -> None:
        name: model.NameType = "\0"
        with self.assertRaises(ValueError) as cm:
            _string_constraints.check_name_type(name)
        self.assertEqual(r"Every string must match the pattern '[\t\n\r -\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]*'! "
                         r"(value: '\x00')", cm.exception.args[0])
        name = "\ud800"
        with self.assertRaises(ValueError) as cm:
            _string_constraints.check_name_type(name)
        self.assertEqual(r"Every string must match the pattern '[\t\n\r -\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]*'! "
                         r"(value: '\ud800')", cm.exception.args[0])
        name = "\ufffe"
        with self.assertRaises(ValueError) as cm:
            _string_constraints.check_name_type(name)
        self.assertEqual(r"Every string must match the pattern '[\t\n\r -\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]*'! "
                         r"(value: '\ufffe')", cm.exception.args[0])
        name = "this\ris\na\tvalid täst\uffdd\U0010ab12"
        _string_constraints.check_name_type(name)


class StringConstraintsDecoratorTest(unittest.TestCase):
    @_string_constraints.constrain_path_type("some_attr")
    class DummyClass:
        def __init__(self, path: model.PathType):
            self.some_attr: model.PathType = path

    def test_path_type_decoration(self) -> None:
        with self.assertRaises(ValueError) as cm:
            self.DummyClass("")
        self.assertEqual("PathType has a minimum length of 1! (length: 0)", cm.exception.args[0])
        dc = self.DummyClass("a")
        with self.assertRaises(ValueError) as cm:
            dc.some_attr = "a" * 2001
        self.assertEqual("PathType has a maximum length of 2000! (length: 2001)", cm.exception.args[0])
        self.assertEqual(dc.some_attr, "a")

    def test_ignore_none_values(self) -> None:
        # None values should be ignored as some decorated attributes are optional. As shown in the following,
        # such assignments are caught by the typechecker anyway.
        dc = self.DummyClass(None)  # type: ignore
        self.assertIsNone(dc.some_attr)
        dc.some_attr = None  # type: ignore

    def test_attribute_name_conflict(self) -> None:
        # We don't want to overwrite existing attributes in case of a name conflict
        with self.assertRaises(AttributeError) as cm:
            @_string_constraints.constrain_revision_type("foo")
            class DummyClass:
                foo = property()
        self.assertEqual("DummyClass already has an attribute named 'foo'", cm.exception.args[0])

        with self.assertRaises(AttributeError) as cm:
            @_string_constraints.constrain_label_type("bar")
            class DummyClass2:
                @property
                def bar(self):
                    return "baz"
        self.assertEqual("DummyClass2 already has an attribute named 'bar'", cm.exception.args[0])
