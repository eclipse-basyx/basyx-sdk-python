# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import io
import os
import unittest

from lxml import etree

from basyx.aas import model
from basyx.aas.adapter.xml import write_aas_xml_file, xml_serialization

from basyx.aas.examples.data import example_aas_missing_attributes, example_aas, \
    example_submodel_template, example_aas_mandatory_attributes


XML_SCHEMA_FILE = os.path.join(os.path.dirname(__file__), '../schemas/aasXMLSchema.xsd')


class XMLSerializationTest(unittest.TestCase):
    def test_serialize_object(self) -> None:
        test_object = model.Property("test_id_short",
                                     model.datatypes.String,
                                     category="PARAMETER",
                                     description=model.MultiLanguageTextType({"en-US": "Germany", "de": "Deutschland"}))
        xml_data = xml_serialization.property_to_xml(test_object,  xml_serialization.NS_AAS+"test_object")
        # todo: is this a correct way to test it?

    def test_random_object_serialization(self) -> None:
        aas_identifier = "AAS1"
        submodel_key = (model.Key(model.KeyTypes.SUBMODEL, "SM1"),)
        submodel_identifier = submodel_key[0].get_identifier()
        assert (submodel_identifier is not None)
        submodel_reference = model.ModelReference(submodel_key, model.Submodel)
        submodel = model.Submodel(submodel_identifier)
        test_aas = model.AssetAdministrationShell(model.AssetInformation(global_asset_id="Test"),
                                                  aas_identifier, submodel={submodel_reference})

        test_data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        test_data.add(test_aas)
        test_data.add(submodel)

        test_file = io.BytesIO()
        write_aas_xml_file(file=test_file, data=test_data)


class XMLSerializationSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(XML_SCHEMA_FILE):
            raise unittest.SkipTest(f"XSD schema does not exist at {XML_SCHEMA_FILE}, skipping test")

    def test_random_object_serialization(self) -> None:
        aas_identifier = "AAS1"
        submodel_key = (model.Key(model.KeyTypes.SUBMODEL, "SM1"),)
        submodel_identifier = submodel_key[0].get_identifier()
        assert submodel_identifier is not None
        submodel_reference = model.ModelReference(submodel_key, model.Submodel)
        submodel = model.Submodel(submodel_identifier,
                                  semantic_id=model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE,
                                                                                 "http://acplt.org/TestSemanticId"),)))
        test_aas = model.AssetAdministrationShell(model.AssetInformation(global_asset_id="Test"),
                                                  aas_identifier, submodel={submodel_reference})
        # serialize object to xml
        test_data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        test_data.add(test_aas)
        test_data.add(submodel)

        test_file = io.BytesIO()
        write_aas_xml_file(file=test_file, data=test_data)

        # load schema
        aas_schema = etree.XMLSchema(file=XML_SCHEMA_FILE)

        # validate serialization against schema
        parser = etree.XMLParser(schema=aas_schema)
        test_file.seek(0)
        root = etree.parse(test_file, parser=parser)

    def test_full_example_serialization(self) -> None:
        data = example_aas.create_full_example()
        file = io.BytesIO()
        write_aas_xml_file(file=file, data=data)

        # load schema
        aas_schema = etree.XMLSchema(file=XML_SCHEMA_FILE)

        # validate serialization against schema
        parser = etree.XMLParser(schema=aas_schema)
        file.seek(0)
        root = etree.parse(file, parser=parser)

    def test_submodel_template_serialization(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        data.add(example_submodel_template.create_example_submodel_template())
        file = io.BytesIO()
        write_aas_xml_file(file=file, data=data)

        # load schema
        aas_schema = etree.XMLSchema(file=XML_SCHEMA_FILE)

        # validate serialization against schema
        parser = etree.XMLParser(schema=aas_schema)
        file.seek(0)
        root = etree.parse(file, parser=parser)

    def test_full_empty_example_serialization(self) -> None:
        data = example_aas_mandatory_attributes.create_full_example()
        file = io.BytesIO()
        write_aas_xml_file(file=file, data=data)

        # load schema
        aas_schema = etree.XMLSchema(file=XML_SCHEMA_FILE)

        # validate serialization against schema
        parser = etree.XMLParser(schema=aas_schema)
        file.seek(0)
        root = etree.parse(file, parser=parser)

    def test_missing_serialization(self) -> None:
        data = example_aas_missing_attributes.create_full_example()
        file = io.BytesIO()
        write_aas_xml_file(file=file, data=data, pretty_print=True)

        # load schema
        aas_schema = etree.XMLSchema(file=XML_SCHEMA_FILE)

        # validate serialization against schema
        parser = etree.XMLParser(schema=aas_schema)
        file.seek(0)
        root = etree.parse(file, parser=parser)

    def test_concept_description(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        data.add(example_aas.create_example_concept_description())
        file = io.BytesIO()
        write_aas_xml_file(file=file, data=data)

        # load schema
        aas_schema = etree.XMLSchema(file=XML_SCHEMA_FILE)

        # validate serialization against schema
        parser = etree.XMLParser(schema=aas_schema)
        file.seek(0)
        root = etree.parse(file, parser=parser)
