# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import unittest

from basyx.aas.examples.data import example_aas
from basyx.aas import model


class ConceptDescriptionTest(unittest.TestCase):
    def test_concept_description(self):
        concept_description = example_aas.create_example_concept_description()

        concept_description._set_category(category=None)
        concept_description_category = concept_description.__dict__.get("_category")
        self.assertEqual(concept_description_category, "PROPERTY")

        concept_description._set_category(category="VALUE")
        concept_description_category = concept_description.__dict__.get("_category")
        self.assertEqual(concept_description_category, "VALUE")

        with self.assertRaises(model.base.AASConstraintViolation):
            concept_description._set_category(category="FORBIDDEN_CONCEPT_DESCRIPTION")
