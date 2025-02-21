# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import io
import logging
import unittest

from basyx.aas import model
from basyx.aas.adapter.xml import StrictAASFromXmlDecoder, XMLConstructables, read_aas_xml_file, \
    read_aas_xml_file_into, read_aas_xml_element
from basyx.aas.adapter.xml.xml_deserialization import _tag_replace_namespace
from basyx.aas.adapter._generic import XML_NS_MAP
from lxml import etree
from typing import Iterable, Type, Union


def _xml_wrap(xml: str) -> str:
    return f'<aas:environment xmlns:aas="{XML_NS_MAP["aas"]}">{xml}</aas:environment>'


def _root_cause(exception: BaseException) -> BaseException:
    while exception.__cause__ is not None:
        exception = exception.__cause__
    return exception


class XmlDeserializationTest(unittest.TestCase):
    def _assertInExceptionAndLog(self, xml: str, strings: Union[Iterable[str], str], error_type: Type[BaseException],
                                 log_level: int) -> None:
        """
        Runs read_xml_aas_file in failsafe mode and checks if each string is contained in the first message logged.
        Then runs it in non-failsafe mode and checks if each string is contained in the first error raised.

        :param xml: The xml document to parse.
        :param strings: One or more strings to match.
        :param error_type: The expected error type.
        :param log_level: The log level on which the string is expected.
        """
        if isinstance(strings, str):
            strings = [strings]
        string_io = io.StringIO(xml)
        with self.assertLogs(logging.getLogger(), level=log_level) as log_ctx:
            read_aas_xml_file(string_io, failsafe=True)
        with self.assertRaises(error_type) as err_ctx:
            read_aas_xml_file(string_io, failsafe=False)
        cause = _root_cause(err_ctx.exception)
        for s in strings:
            self.assertIn(s, log_ctx.output[0])
            self.assertIn(s, str(cause))

    def test_malformed_xml(self) -> None:
        xml = (
            "invalid xml",
            _xml_wrap("<<>>><<<<<"),
            _xml_wrap("<aas:submodels><aas:submodel/>")
        )
        for s in xml:
            self._assertInExceptionAndLog(s, [], etree.XMLSyntaxError, logging.ERROR)

    def test_invalid_list_name(self) -> None:
        xml = _xml_wrap("<aas:invalidList></aas:invalidList>")
        self._assertInExceptionAndLog(xml, "aas:invalidList", TypeError, logging.WARNING)

    def test_invalid_element_in_list(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:invalidElement/>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, ["aas:invalidElement", "aas:submodels"], KeyError, logging.WARNING)

    def test_missing_asset_kind(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        """)
        self._assertInExceptionAndLog(xml, "aas:assetKind", KeyError, logging.ERROR)

    def test_missing_asset_kind_text(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:assetKind></aas:assetKind>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        """)
        self._assertInExceptionAndLog(xml, "aas:assetKind", KeyError, logging.ERROR)

    def test_invalid_asset_kind_text(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:assetKind>invalidKind</aas:assetKind>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        """)
        self._assertInExceptionAndLog(xml, ["aas:assetKind", "invalidKind"], ValueError, logging.ERROR)

    def test_invalid_boolean(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:submodelElements>
                    <aas:submodelElementList>
                        <aas:orderRelevant>False</aas:orderRelevant>
                        <aas:idShort>collection</aas:idShort>
                        <aas:typeValueListElement>Capability</aas:typeValueListElement>
                    </aas:submodelElementList>
                </aas:submodelElements>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, "False", ValueError, logging.ERROR)

    def test_no_modelling_kind(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
            </aas:submodel>
        </aas:submodels>
        """)
        # should get parsed successfully
        object_store = read_aas_xml_file(io.StringIO(xml), failsafe=False)
        # modelling kind should default to INSTANCE
        submodel = object_store.pop()
        self.assertIsInstance(submodel, model.Submodel)
        assert isinstance(submodel, model.Submodel)  # to make mypy happy
        self.assertEqual(submodel.kind, model.ModellingKind.INSTANCE)

    def test_reference_kind_mismatch(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:assetKind>Instance</aas:assetKind>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
                <aas:derivedFrom>
                    <aas:type>ModelReference</aas:type>
                    <aas:keys>
                        <aas:key>
                            <aas:type>Submodel</aas:type>
                            <aas:value>http://acplt.org/test_ref</aas:value>
                        </aas:key>
                    </aas:keys>
                </aas:derivedFrom>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        """)
        with self.assertLogs(logging.getLogger(), level=logging.WARNING) as context:
            read_aas_xml_file(io.StringIO(xml), failsafe=False)
        for s in ("SUBMODEL", "http://acplt.org/test_ref", "AssetAdministrationShell"):
            self.assertIn(s, context.output[0])

    def test_invalid_submodel_element(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:submodelElements>
                    <aas:invalidSubmodelElement/>
                </aas:submodelElements>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, "aas:invalidSubmodelElement", KeyError, logging.ERROR)

    def test_empty_qualifier(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:qualifiers>
                    <aas:qualifier/>
                </aas:qualifiers>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, ["aas:qualifier", "has no child aas:type"], KeyError, logging.ERROR)

    def test_operation_variable_no_submodel_element(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:submodelElements>
                    <aas:operation>
                        <aas:idShort>test_operation</aas:idShort>
                        <aas:outputVariables>
                            <aas:operationVariable>
                                <aas:value/>
                            </aas:operationVariable>
                        </aas:outputVariables>
                    </aas:operation>
                </aas:submodelElements>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, ["aas:value", "has no submodel element"], KeyError, logging.ERROR)

    def test_operation_variable_too_many_submodel_elements(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:submodelElements>
                    <aas:operation>
                        <aas:idShort>test_operation</aas:idShort>
                        <aas:outputVariables>
                            <aas:operationVariable>
                                <aas:value>
                                    <aas:file>
                                        <aas:kind>Template</aas:kind>
                                        <aas:idShort>test_file</aas:idShort>
                                        <aas:contentType>application/problem+xml</aas:contentType>
                                    </aas:file>
                                    <aas:file>
                                        <aas:idShort>test_file2</aas:idShort>
                                        <aas:contentType>application/problem+xml</aas:contentType>
                                    </aas:file>
                                </aas:value>
                            </aas:operationVariable>
                        </aas:outputVariables>
                    </aas:operation>
                </aas:submodelElements>
            </aas:submodel>
        </aas:submodels>
        """)
        with self.assertLogs(logging.getLogger(), level=logging.WARNING) as context:
            read_aas_xml_file(io.StringIO(xml), failsafe=False)
        self.assertIn("aas:value", context.output[0])
        self.assertIn("more than one submodel element", context.output[0])

    def test_duplicate_identifier(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:assetKind>Instance</aas:assetKind>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_aas</aas:id>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, "duplicate identifier", KeyError, logging.ERROR)

    def test_duplicate_identifier_object_store(self) -> None:
        sm_id = "http://acplt.org/test_submodel"

        def get_clean_store() -> model.DictObjectStore:
            store: model.DictObjectStore = model.DictObjectStore()
            submodel_ = model.Submodel(sm_id, id_short="test123")
            store.add(submodel_)
            return store

        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:idShort>test456</aas:idShort>
            </aas:submodel>
        </aas:submodels>
        """)
        string_io = io.StringIO(xml)

        object_store = get_clean_store()
        identifiers = read_aas_xml_file_into(object_store, string_io, replace_existing=True, ignore_existing=False)
        self.assertEqual(identifiers.pop(), sm_id)
        submodel = object_store.pop()
        self.assertIsInstance(submodel, model.Submodel)
        self.assertEqual(submodel.id_short, "test456")

        object_store = get_clean_store()
        with self.assertLogs(logging.getLogger(), level=logging.INFO) as log_ctx:
            identifiers = read_aas_xml_file_into(object_store, string_io, replace_existing=False, ignore_existing=True)
        self.assertEqual(len(identifiers), 0)
        self.assertIn("already exists in the object store", log_ctx.output[0])
        submodel = object_store.pop()
        self.assertIsInstance(submodel, model.Submodel)
        self.assertEqual(submodel.id_short, "test123")

        object_store = get_clean_store()
        with self.assertRaises(KeyError) as err_ctx:
            identifiers = read_aas_xml_file_into(object_store, string_io, replace_existing=False, ignore_existing=False)
        self.assertEqual(len(identifiers), 0)
        cause = _root_cause(err_ctx.exception)
        self.assertIn("already exists in the object store", str(cause))
        submodel = object_store.pop()
        self.assertIsInstance(submodel, model.Submodel)
        self.assertEqual(submodel.id_short, "test123")

    def test_read_aas_xml_element(self) -> None:
        xml = f"""
        <aas:submodel xmlns:aas="{XML_NS_MAP["aas"]}">
            <aas:id>http://acplt.org/test_submodel</aas:id>
        </aas:submodel>
        """
        string_io = io.StringIO(xml)

        submodel = read_aas_xml_element(string_io, XMLConstructables.SUBMODEL)
        self.assertIsInstance(submodel, model.Submodel)

    def test_no_namespace_prefix(self) -> None:
        def xml(id_: str) -> str:
            return f"""
            <environment xmlns="{XML_NS_MAP["aas"]}">
                <submodels>
                    <submodel>
                        <id>{id_}</id>
                    </submodel>
                </submodels>
            </environment>
            """

        self._assertInExceptionAndLog(xml(""), f'{{{XML_NS_MAP["aas"]}}}id on line 5 has no text', KeyError,
                                      logging.ERROR)
        read_aas_xml_file(io.StringIO(xml("urn:x-test:test-submodel")))


class XmlDeserializationStrippedObjectsTest(unittest.TestCase):
    def test_stripped_qualifiable(self) -> None:
        xml = f"""
        <aas:submodel xmlns:aas="{XML_NS_MAP["aas"]}">
            <aas:id>http://acplt.org/test_stripped_submodel</aas:id>
            <aas:submodelElements>
                <aas:operation>
                    <aas:idShort>test_operation</aas:idShort>
                    <aas:qualifiers>
                        <aas:qualifier>
                            <aas:type>test_qualifier</aas:type>
                            <aas:valueType>xs:string</aas:valueType>
                        </aas:qualifier>
                    </aas:qualifiers>
                </aas:operation>
            </aas:submodelElements>
            <aas:qualifiers>
                <aas:qualifier>
                    <aas:type>test_qualifier</aas:type>
                    <aas:valueType>xs:string</aas:valueType>
                </aas:qualifier>
            </aas:qualifiers>
        </aas:submodel>
        """
        string_io = io.StringIO(xml)

        # check if XML with qualifiers can be parsed successfully
        submodel = read_aas_xml_element(string_io, XMLConstructables.SUBMODEL, failsafe=False)
        self.assertIsInstance(submodel, model.Submodel)
        assert isinstance(submodel, model.Submodel)
        self.assertEqual(len(submodel.qualifier), 1)
        operation = submodel.submodel_element.pop()
        self.assertEqual(len(operation.qualifier), 1)

        # check if qualifiers are ignored in stripped mode
        submodel = read_aas_xml_element(string_io, XMLConstructables.SUBMODEL, failsafe=False, stripped=True)
        self.assertIsInstance(submodel, model.Submodel)
        assert isinstance(submodel, model.Submodel)
        self.assertEqual(len(submodel.qualifier), 0)
        self.assertEqual(len(submodel.submodel_element), 0)

    def test_stripped_asset_administration_shell(self) -> None:
        xml = f"""
        <aas:assetAdministrationShell xmlns:aas="{XML_NS_MAP["aas"]}">
            <aas:id>http://acplt.org/test_aas</aas:id>
            <aas:assetInformation>
                <aas:assetKind>Instance</aas:assetKind>
                <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
            </aas:assetInformation>
            <aas:submodels>
                <aas:reference>
                    <aas:type>ModelReference</aas:type>
                    <aas:keys>
                        <aas:key>
                            <aas:type>Submodel</aas:type>
                            <aas:value>http://acplt.org/test_ref</aas:value>
                        </aas:key>
                    </aas:keys>
                </aas:reference>
            </aas:submodels>
        </aas:assetAdministrationShell>
        """
        string_io = io.StringIO(xml)

        # check if XML with submodels can be parsed successfully
        aas = read_aas_xml_element(string_io, XMLConstructables.ASSET_ADMINISTRATION_SHELL, failsafe=False)
        self.assertIsInstance(aas, model.AssetAdministrationShell)
        assert isinstance(aas, model.AssetAdministrationShell)
        self.assertEqual(len(aas.submodel), 1)

        # check if submodels are ignored in stripped mode
        aas = read_aas_xml_element(string_io, XMLConstructables.ASSET_ADMINISTRATION_SHELL, failsafe=False,
                                   stripped=True)
        self.assertIsInstance(aas, model.AssetAdministrationShell)
        assert isinstance(aas, model.AssetAdministrationShell)
        self.assertEqual(len(aas.submodel), 0)


class XmlDeserializationDerivingTest(unittest.TestCase):
    def test_submodel_constructor_overriding(self) -> None:
        class EnhancedSubmodel(model.Submodel):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.enhanced_attribute = "fancy!"

        class EnhancedAASDecoder(StrictAASFromXmlDecoder):
            @classmethod
            def construct_submodel(cls, element: etree._Element, object_class=EnhancedSubmodel, **kwargs) \
                    -> model.Submodel:
                return super().construct_submodel(element, object_class=object_class, **kwargs)

        xml = f"""
        <aas:submodel xmlns:aas="{XML_NS_MAP["aas"]}">
            <aas:id>http://acplt.org/test_stripped_submodel</aas:id>
        </aas:submodel>
        """
        string_io = io.StringIO(xml)

        submodel = read_aas_xml_element(string_io, XMLConstructables.SUBMODEL, decoder=EnhancedAASDecoder)
        self.assertIsInstance(submodel, EnhancedSubmodel)
        assert isinstance(submodel, EnhancedSubmodel)
        self.assertEqual(submodel.enhanced_attribute, "fancy!")


class TestTagReplaceNamespace(unittest.TestCase):
    def test_known_namespace(self):
        tag = '{https://admin-shell.io/aas/3/0}tag'
        expected = 'aas:tag'
        self.assertEqual(_tag_replace_namespace(tag, XML_NS_MAP), expected)

    def test_empty_prefix(self):
        # Empty prefix should not be replaced as otherwise it would apply everywhere
        tag = '{https://admin-shell.io/aas/3/0}tag'
        nsmap = {"": "https://admin-shell.io/aas/3/0"}
        expected = '{https://admin-shell.io/aas/3/0}tag'
        self.assertEqual(_tag_replace_namespace(tag, nsmap), expected)

    def test_empty_namespace(self):
        # Empty namespaces should also have no effect
        tag = '{https://admin-shell.io/aas/3/0}tag'
        nsmap = {"aas": ""}
        expected = '{https://admin-shell.io/aas/3/0}tag'
        self.assertEqual(_tag_replace_namespace(tag, nsmap), expected)

    def test_unknown_namespace(self):
        tag = '{http://unknownnamespace.com}unknown'
        expected = '{http://unknownnamespace.com}unknown'  # Unknown namespace should remain unchanged
        self.assertEqual(_tag_replace_namespace(tag, XML_NS_MAP), expected)
