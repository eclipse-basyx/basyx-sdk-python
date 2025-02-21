# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import io
import json
import unittest

from basyx.aas import model
from basyx.aas.adapter.json import AASToJsonEncoder, write_aas_json_file, read_aas_json_file

from basyx.aas.examples.data import example_aas_missing_attributes, example_aas, \
    example_aas_mandatory_attributes, example_submodel_template, create_example
from basyx.aas.examples.data._helper import AASDataChecker

from typing import Iterable, IO


class JsonSerializationDeserializationTest(unittest.TestCase):
    def test_random_object_serialization_deserialization(self) -> None:
        aas_identifier = "AAS1"
        submodel_key = (model.Key(model.KeyTypes.SUBMODEL, "SM1"),)
        submodel_identifier = submodel_key[0].get_identifier()
        assert submodel_identifier is not None
        submodel_reference = model.ModelReference(submodel_key, model.Submodel)
        submodel = model.Submodel(submodel_identifier)
        test_aas = model.AssetAdministrationShell(model.AssetInformation(global_asset_id="test"),
                                                  aas_identifier, submodel={submodel_reference})

        # serialize object to json
        json_data = json.dumps({
                'assetAdministrationShells': [test_aas],
                'submodels': [submodel],
                'assets': [],
                'conceptDescriptions': [],
            }, cls=AASToJsonEncoder)
        json_data_new = json.loads(json_data)

        # try deserializing the json string into a DictObjectStore of AAS objects with help of the json module
        json_object_store = read_aas_json_file(io.StringIO(json_data), failsafe=False)

    def test_example_serialization_deserialization(self) -> None:
        # test with TextIO and BinaryIO, which should both be supported
        t: Iterable[IO] = (io.StringIO(), io.BytesIO())
        for file in t:
            data = example_aas.create_full_example()
            write_aas_json_file(file=file, data=data)

            # try deserializing the json string into a DictObjectStore of AAS objects with help of the json module
            file.seek(0)
            json_object_store = read_aas_json_file(file, failsafe=False)
            checker = AASDataChecker(raise_immediately=True)
            example_aas.check_full_example(checker, json_object_store)


class JsonSerializationDeserializationTest2(unittest.TestCase):
    def test_example_mandatory_attributes_serialization_deserialization(self) -> None:
        data = example_aas_mandatory_attributes.create_full_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        # try deserializing the json string into a DictObjectStore of AAS objects with help of the json module
        file.seek(0)
        json_object_store = read_aas_json_file(file, failsafe=False)
        checker = AASDataChecker(raise_immediately=True)
        example_aas_mandatory_attributes.check_full_example(checker, json_object_store)


class JsonSerializationDeserializationTest3(unittest.TestCase):
    def test_example_missing_attributes_serialization_deserialization(self) -> None:
        data = example_aas_missing_attributes.create_full_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)
        # try deserializing the json string into a DictObjectStore of AAS objects with help of the json module
        file.seek(0)
        json_object_store = read_aas_json_file(file, failsafe=False)
        checker = AASDataChecker(raise_immediately=True)
        example_aas_missing_attributes.check_full_example(checker, json_object_store)


class JsonSerializationDeserializationTest4(unittest.TestCase):
    def test_example_submodel_template_serialization_deserialization(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        data.add(example_submodel_template.create_example_submodel_template())
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)
        # try deserializing the json string into a DictObjectStore of AAS objects with help of the json module
        file.seek(0)
        json_object_store = read_aas_json_file(file, failsafe=False)
        checker = AASDataChecker(raise_immediately=True)
        example_submodel_template.check_full_example(checker, json_object_store)


class JsonSerializationDeserializationTest5(unittest.TestCase):
    def test_example_all_examples_serialization_deserialization(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = create_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)
        # try deserializing the json string into a DictObjectStore of AAS objects with help of the json module
        file.seek(0)
        json_object_store = read_aas_json_file(file, failsafe=False)
        checker = AASDataChecker(raise_immediately=True)
        checker.check_object_store(json_object_store, data)
