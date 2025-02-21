# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import io
import unittest

from basyx.aas import model
from basyx.aas.adapter.xml import write_aas_xml_file, read_aas_xml_file, write_aas_xml_element, read_aas_xml_element, \
    XMLConstructables

from basyx.aas.examples.data import example_aas_missing_attributes, example_aas, \
    example_aas_mandatory_attributes, example_submodel_template, create_example
from basyx.aas.examples.data._helper import AASDataChecker


def _serialize_and_deserialize(data: model.DictObjectStore) -> model.DictObjectStore:
    file = io.BytesIO()
    write_aas_xml_file(file=file, data=data)

    # try deserializing the xml document into a DictObjectStore of AAS objects with help of the xml module
    file.seek(0)
    return read_aas_xml_file(file, failsafe=False)


class XMLSerializationDeserializationTest(unittest.TestCase):
    def test_example_serialization_deserialization(self) -> None:
        object_store = _serialize_and_deserialize(example_aas.create_full_example())
        checker = AASDataChecker(raise_immediately=True)
        example_aas.check_full_example(checker, object_store)

    def test_example_mandatory_attributes_serialization_deserialization(self) -> None:
        object_store = _serialize_and_deserialize(example_aas_mandatory_attributes.create_full_example())
        checker = AASDataChecker(raise_immediately=True)
        example_aas_mandatory_attributes.check_full_example(checker, object_store)

    def test_example_missing_attributes_serialization_deserialization(self) -> None:
        object_store = _serialize_and_deserialize(example_aas_missing_attributes.create_full_example())
        checker = AASDataChecker(raise_immediately=True)
        example_aas_missing_attributes.check_full_example(checker, object_store)

    def test_example_submodel_template_serialization_deserialization(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        data.add(example_submodel_template.create_example_submodel_template())
        object_store = _serialize_and_deserialize(data)
        checker = AASDataChecker(raise_immediately=True)
        example_submodel_template.check_full_example(checker, object_store)

    def test_example_all_examples_serialization_deserialization(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = create_example()
        object_store = _serialize_and_deserialize(data)
        checker = AASDataChecker(raise_immediately=True)
        checker.check_object_store(object_store, data)


class XMLSerializationDeserializationSingleObjectTest(unittest.TestCase):
    def test_submodel_serialization_deserialization(self) -> None:
        submodel: model.Submodel = example_submodel_template.create_example_submodel_template()
        bytes_io = io.BytesIO()
        write_aas_xml_element(bytes_io, submodel)
        bytes_io.seek(0)
        submodel2: model.Submodel = read_aas_xml_element(bytes_io,  # type: ignore[assignment]
                                                         XMLConstructables.SUBMODEL, failsafe=False)
        checker = AASDataChecker(raise_immediately=True)
        checker.check_submodel_equal(submodel2, submodel)
