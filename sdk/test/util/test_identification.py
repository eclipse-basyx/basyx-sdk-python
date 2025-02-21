# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import unittest

from basyx.aas.util.identification import *
from basyx.aas import model


class IdentifierGeneratorTest(unittest.TestCase):
    def test_generate_uuid_identifier(self):
        generator = UUIDGenerator()
        identification = generator.generate_id()
        self.assertRegex(identification,
                         r"urn:uuid:[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}")
        ids = set()
        for i in range(100):
            identification = generator.generate_id()
            self.assertNotIn(identification, ids)
            ids.add(identification)

    def test_generate_iri_identifier(self):
        provider = model.DictObjectStore()

        # Check expected Errors when Namespaces are not valid
        with self.assertRaises(ValueError) as cm:
            generator = NamespaceIRIGenerator("", provider)
        self.assertEqual('Namespace must be a valid IRI, ending with #, / or =', str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            generator = NamespaceIRIGenerator("http", provider)
        self.assertEqual('Namespace must be a valid IRI, ending with #, / or =', str(cm.exception))

        generator = NamespaceIRIGenerator("http://acplt.org/AAS/", provider)
        self.assertEqual("http://acplt.org/AAS/", generator.namespace)

        identification = generator.generate_id()
        self.assertEqual(identification, "http://acplt.org/AAS/0000")
        provider.add(model.Submodel(identification))

        for i in range(10):
            identification = generator.generate_id()
            self.assertNotIn(identification, provider)
            provider.add(model.Submodel(identification))
        self.assertEqual(identification, "http://acplt.org/AAS/0010")

        identification = generator.generate_id("Spülmaschine")
        self.assertEqual(identification, "http://acplt.org/AAS/Spülmaschine")
        provider.add(model.Submodel(identification))

        for i in range(10):
            identification = generator.generate_id("Spülmaschine")
            self.assertNotIn(identification, provider)
            self.assertNotEqual(identification, "http://acplt.org/AAS/Spülmaschine")
