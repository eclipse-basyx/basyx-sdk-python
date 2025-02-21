# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import os
import io
import unittest
import json

from basyx.aas import model
from basyx.aas.adapter.json import AASToJsonEncoder, StrippedAASToJsonEncoder, write_aas_json_file
from jsonschema import validate  # type: ignore
from typing import Set, Union

from basyx.aas.examples.data import example_aas_missing_attributes, example_aas, \
    example_aas_mandatory_attributes, example_submodel_template, create_example


JSON_SCHEMA_FILE = os.path.join(os.path.dirname(__file__), '../schemas/aasJSONSchema.json')


class JsonSerializationTest(unittest.TestCase):
    def test_serialize_object(self) -> None:
        test_object = model.Property("test_id_short", model.datatypes.String, category="PARAMETER",
                                     description=model.MultiLanguageTextType({"en-US": "Germany", "de": "Deutschland"}))
        json_data = json.dumps(test_object, cls=AASToJsonEncoder)

    def test_random_object_serialization(self) -> None:
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


class JsonSerializationSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(JSON_SCHEMA_FILE):
            raise unittest.SkipTest(f"JSON Schema does not exist at {JSON_SCHEMA_FILE}, skipping test")

    def test_random_object_serialization(self) -> None:
        aas_identifier = "AAS1"
        submodel_key = (model.Key(model.KeyTypes.SUBMODEL, "SM1"),)
        submodel_identifier = submodel_key[0].get_identifier()
        assert submodel_identifier is not None
        submodel_reference = model.ModelReference(submodel_key, model.Submodel)
        # The JSONSchema expects every object with HasSemnatics (like Submodels) to have a `semanticId` Reference, which
        # must be a Reference. (This seems to be a bug in the JSONSchema.)
        submodel = model.Submodel(submodel_identifier,
                                  semantic_id=model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE,
                                                                       "http://acplt.org/TestSemanticId"),)))
        test_aas = model.AssetAdministrationShell(model.AssetInformation(global_asset_id="test"),
                                                  aas_identifier, submodel={submodel_reference})

        # serialize object to json
        json_data = json.dumps({
                'assetAdministrationShells': [test_aas],
                'submodels': [submodel]
            }, cls=AASToJsonEncoder)
        json_data_new = json.loads(json_data)

        # load schema
        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_schema = json.load(json_file)

        # validate serialization against schema
        validate(instance=json_data_new, schema=aas_schema)

    def test_aas_example_serialization(self) -> None:
        data = example_aas.create_full_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_submodel_template_serialization(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        data.add(example_submodel_template.create_example_submodel_template())
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_full_empty_example_serialization(self) -> None:
        data = example_aas_mandatory_attributes.create_full_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_missing_serialization(self) -> None:
        data = example_aas_missing_attributes.create_full_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_concept_description_serialization(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        data.add(example_aas.create_example_concept_description())
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_full_example_serialization(self) -> None:
        data = create_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)


class JsonSerializationStrippedObjectsTest(unittest.TestCase):
    def _checkNormalAndStripped(self, attributes: Union[Set[str], str], obj: object) -> None:
        if isinstance(attributes, str):
            attributes = {attributes}

        # attributes should be present when using the normal encoder,
        # but must not be present when using the stripped encoder
        for cls, assert_fn in ((AASToJsonEncoder, self.assertIn), (StrippedAASToJsonEncoder, self.assertNotIn)):
            data = json.loads(json.dumps(obj, cls=cls))
            for attr in attributes:
                assert_fn(attr, data)

    def test_stripped_qualifiable(self) -> None:
        qualifier = model.Qualifier("test_qualifier", str)
        qualifier2 = model.Qualifier("test_qualifier2", str)
        operation = model.Operation("test_operation", qualifier={qualifier})
        submodel = model.Submodel(
            "http://acplt.org/test_submodel",
            submodel_element=[operation],
            qualifier={qualifier2}
        )

        self._checkNormalAndStripped({"submodelElements", "qualifiers"}, submodel)
        self._checkNormalAndStripped("qualifiers", operation)

    def test_stripped_annotated_relationship_element(self) -> None:
        mlp = model.MultiLanguageProperty("test_multi_language_property", category="PARAMETER")
        ref = model.ModelReference(
            (model.Key(model.KeyTypes.SUBMODEL, "http://acplt.org/test_ref"),),
            model.Submodel
        )
        are = model.AnnotatedRelationshipElement(
            "test_annotated_relationship_element",
            ref,
            ref,
            annotation=[mlp]
        )

        self._checkNormalAndStripped("annotations", are)

    def test_stripped_entity(self) -> None:
        mlp = model.MultiLanguageProperty("test_multi_language_property", category="PARAMETER")
        entity = model.Entity("test_entity", model.EntityType.CO_MANAGED_ENTITY, statement=[mlp])

        self._checkNormalAndStripped("statements", entity)

    def test_stripped_submodel_element_collection(self) -> None:
        mlp = model.MultiLanguageProperty("test_multi_language_property", category="PARAMETER")
        sec = model.SubmodelElementCollection("test_submodel_element_collection", value=[mlp])

        self._checkNormalAndStripped("value", sec)

    def test_stripped_asset_administration_shell(self) -> None:
        submodel_ref = model.ModelReference(
            (model.Key(model.KeyTypes.SUBMODEL, "http://acplt.org/test_ref"),),
            model.Submodel
        )
        aas = model.AssetAdministrationShell(
            model.AssetInformation(global_asset_id="http://acplt.org/test_ref"),
            "http://acplt.org/test_aas",
            submodel={submodel_ref}
        )

        self._checkNormalAndStripped({"submodels"}, aas)
