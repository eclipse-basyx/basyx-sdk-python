# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import unittest

from basyx.aas.examples.data._helper import DataChecker, AASDataChecker
from basyx.aas import model


class DataCheckerTest(unittest.TestCase):
    def test_check(self):
        checker = DataChecker(raise_immediately=True)
        with self.assertRaises(AssertionError) as cm:
            checker.check(2 == 3, 'Assertion test')
        self.assertEqual("('Check failed: Assertion test', {})", str(cm.exception))

    def test_kwargs(self):
        checker = DataChecker(raise_immediately=True)
        with self.assertRaises(AssertionError) as cm:
            checker.check(2 == 3, 'Assertion test 1', value='kwargs1')
        with self.assertRaises(AssertionError) as cm_2:
            checker.check(2 == 3, 'Assertion test 2', value='kwargs2')
        self.assertEqual("('Check failed: Assertion test 1', {'value': 'kwargs1'})", str(cm.exception))
        self.assertEqual("('Check failed: Assertion test 2', {'value': 'kwargs2'})", str(cm_2.exception))

    def test_raise_failed(self):
        checker = DataChecker(raise_immediately=False)
        checker.check(2 == 2, 'Assertion test')
        checker.raise_failed()  # no assertion should be occur
        self.assertEqual(1, sum(1 for _ in checker.successful_checks))
        checker.check(2 == 3, 'Assertion test')
        with self.assertRaises(AssertionError) as cm:
            checker.raise_failed()
        self.assertEqual("('1 of 2 checks failed', ['Assertion test'])", str(cm.exception))


class AASDataCheckerTest(unittest.TestCase):
    def test_qualifiable_checker(self):
        qualifier_expected = model.Qualifier(
            type_='test',
            value_type=model.datatypes.String,
            value='test value'
        )
        property_expected = model.Property(
            id_short='Prop1',
            value_type=model.datatypes.String,
            value='test',
            qualifier={qualifier_expected}
        )

        property = model.Property(
            id_short='Prop1',
            value_type=model.datatypes.String,
            value='test'
        )

        checker = AASDataChecker(raise_immediately=False)

        checker.check_property_equal(property, property_expected)
        self.assertEqual(2, sum(1 for _ in checker.failed_checks))
        self.assertEqual(14, sum(1 for _ in checker.successful_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute qualifier of Property[Prop1] must contain 1 Qualifiers (count=0)",
                         repr(next(checker_iterator)))
        self.assertEqual("FAIL: Qualifier(type=test) must exist ()", repr(next(checker_iterator)))

    def test_submodel_element_list_checker(self):

        # value
        range1 = model.Range(None, model.datatypes.Int, 42, 142857)
        range2 = model.Range(None, model.datatypes.Int, 42, 1337)
        list_ = model.SubmodelElementList(
            id_short='test_list',
            type_value_list_element=model.Range,
            value_type_list_element=model.datatypes.Int,
            order_relevant=True,
            value=(range1, range2)
        )

        range1_expected = model.Range(None, model.datatypes.Int, 42, 142857)
        range2_expected = model.Range(None, model.datatypes.Int, 42, 1337)
        list_expected = model.SubmodelElementList(
            id_short='test_list',
            type_value_list_element=model.Range,
            value_type_list_element=model.datatypes.Int,
            order_relevant=True,
            value=(range2_expected, range1_expected)
        )

        checker = AASDataChecker(raise_immediately=False)
        checker.check_submodel_element_list_equal(list_, list_expected)
        self.assertEqual(2, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute max of Range[test_list[0]] must be == 1337 (value=142857)",
                         repr(next(checker_iterator)))
        self.assertEqual("FAIL: Attribute max of Range[test_list[1]] must be == 142857 (value=1337)",
                         repr(next(checker_iterator)))

        # order_relevant
        # Don't set protected attributes like this in production code!
        list_._order_relevant = False
        checker = AASDataChecker(raise_immediately=False)
        with self.assertRaises(NotImplementedError) as cm:
            checker.check_submodel_element_list_equal(list_, list_expected)
        self.assertEqual("A SubmodelElementList with order_relevant=False cannot be compared!", str(cm.exception))
        self.assertEqual(1, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute order_relevant of SubmodelElementList[test_list] must be == True "
                         "(value=False)", repr(next(checker_iterator)))

        # value_type_list_element
        list_ = model.SubmodelElementList(
            id_short='test_list',
            type_value_list_element=model.Range,
            value_type_list_element=model.datatypes.Int,
        )
        list_expected = model.SubmodelElementList(
            id_short='test_list',
            type_value_list_element=model.Range,
            value_type_list_element=model.datatypes.String,
        )
        checker = AASDataChecker(raise_immediately=False)
        checker.check_submodel_element_list_equal(list_, list_expected)
        self.assertEqual(1, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute value_type_list_element of SubmodelElementList[test_list] must be == str "
                         "(value='Int')", repr(next(checker_iterator)))

        # Don't set protected attributes like this in production code!
        list_._value_type_list_element = model.datatypes.String
        checker = AASDataChecker(raise_immediately=False)
        checker.check_submodel_element_list_equal(list_, list_expected)
        self.assertEqual(0, sum(1 for _ in checker.failed_checks))

        # type_value_list_element
        list_ = model.SubmodelElementList(
            id_short='test_list',
            type_value_list_element=model.Range,
            value_type_list_element=model.datatypes.Int,
        )
        list_expected = model.SubmodelElementList(
            id_short='test_list',
            type_value_list_element=model.Property,
            value_type_list_element=model.datatypes.Int,
        )
        checker = AASDataChecker(raise_immediately=False)
        checker.check_submodel_element_list_equal(list_, list_expected)
        self.assertEqual(1, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute type_value_list_element of SubmodelElementList[test_list] must be == "
                         "Property (value='Range')",
                         repr(next(checker_iterator)))

        # Don't set protected attributes like this in production code!
        list_._type_value_list_element = model.Property
        checker = AASDataChecker(raise_immediately=False)
        checker.check_submodel_element_list_equal(list_, list_expected)
        self.assertEqual(0, sum(1 for _ in checker.failed_checks))

        # semantic_id_list_element
        list_ = model.SubmodelElementList(
            id_short='test_list',
            type_value_list_element=model.MultiLanguageProperty,
            semantic_id_list_element=model.ExternalReference(
                (model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:invalid"),))
        )
        list_expected = model.SubmodelElementList(
            id_short='test_list',
            type_value_list_element=model.MultiLanguageProperty,
            semantic_id_list_element=model.ExternalReference(
                (model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:test"),))
        )
        checker = AASDataChecker(raise_immediately=False)
        checker.check_submodel_element_list_equal(list_, list_expected)
        self.assertEqual(1, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute semantic_id_list_element of SubmodelElementList[test_list] must be == "
                         "ExternalReference(key=(Key(type=GLOBAL_REFERENCE, value=urn:x-test:test),)) "
                         "(value=ExternalReference(key=(Key(type=GLOBAL_REFERENCE, value=urn:x-test:invalid),)))",
                         repr(next(checker_iterator)))
        # Don't set protected attributes like this in production code!
        list_._semantic_id_list_element = model.ExternalReference(
            (model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:test"),))
        checker = AASDataChecker(raise_immediately=False)
        checker.check_submodel_element_list_equal(list_, list_expected)
        self.assertEqual(0, sum(1 for _ in checker.failed_checks))

    def test_submodel_element_collection_checker(self):
        property = model.Property(
            id_short='Prop1',
            value_type=model.datatypes.String,
            value='test'
        )
        range_ = model.Range(
            id_short='Range1',
            value_type=model.datatypes.Int,
            min=100,
            max=200
        )
        collection = model.SubmodelElementCollection(
            id_short='Collection',
            value=(range_,)
        )
        property_expected = model.Property(
            id_short='Prop1',
            value_type=model.datatypes.String,
            value='test'
        )
        range_expected = model.Range(
            id_short='Range1',
            value_type=model.datatypes.Int,
            min=100,
            max=200
        )
        collection_expected = model.SubmodelElementCollection(
            id_short='Collection',
            value=(property_expected, range_expected)
        )

        checker = AASDataChecker(raise_immediately=False)
        checker.check_submodel_element_collection_equal(collection, collection_expected)
        self.assertEqual(2, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute value of SubmodelElementCollection[Collection] must contain 2 "
                         "SubmodelElements (count=1)",
                         repr(next(checker_iterator)))
        self.assertEqual("FAIL: Submodel Element Property[Collection / Prop1] must exist ()",
                         repr(next(checker_iterator)))

        collection.add_referable(property)
        checker = AASDataChecker(raise_immediately=False)
        self.assertEqual(0, sum(1 for _ in checker.failed_checks))

    def test_not_implemented(self):
        class DummySubmodelElement(model.SubmodelElement):
            def __init__(self, id_short: model.NameType):
                super().__init__(id_short)
        dummy_submodel_element = DummySubmodelElement('test')
        submodel_collection = model.SubmodelElementCollection('test')
        submodel_collection.value.add(dummy_submodel_element)
        checker = AASDataChecker(raise_immediately=True)
        with self.assertRaises(AttributeError) as cm:
            checker.check_submodel_element_collection_equal(submodel_collection, submodel_collection)
        self.assertEqual(
            'Submodel Element class not implemented',
            str(cm.exception)
        )

    def test_annotated_relationship_element(self):
        rel1 = model.AnnotatedRelationshipElement(id_short='test',
                                                  first=model.ModelReference((
                                                      model.Key(type_=model.KeyTypes.SUBMODEL,
                                                                value='http://acplt.org/Test_Submodel'),
                                                      model.Key(
                                                          type_=model.KeyTypes.PROPERTY,
                                                          value='ExampleProperty'),),
                                                                           model.Property),
                                                  second=model.ModelReference((
                                                      model.Key(type_=model.KeyTypes.SUBMODEL,
                                                                value='http://acplt.org/Test_Submodel'),
                                                      model.Key(type_=model.KeyTypes.PROPERTY,
                                                                value='ExampleProperty'),),
                                                      model.Property),
                                                  )
        rel2 = model.AnnotatedRelationshipElement(id_short='test',
                                                  first=model.ModelReference((
                                                      model.Key(type_=model.KeyTypes.SUBMODEL,
                                                                value='http://acplt.org/Test_Submodel'),
                                                      model.Key(type_=model.KeyTypes.PROPERTY,
                                                                value='ExampleProperty'),),
                                                      model.Property),
                                                  second=model.ModelReference((
                                                      model.Key(type_=model.KeyTypes.SUBMODEL,
                                                                value='http://acplt.org/Test_Submodel'),
                                                      model.Key(type_=model.KeyTypes.PROPERTY,
                                                                value='ExampleProperty'),),
                                                      model.Property),
                                                  annotation={
                                                      model.Property(id_short="ExampleAnnotatedProperty",
                                                                     value_type=model.datatypes.String,
                                                                     value='exampleValue',
                                                                     parent=None)
                                                  })
        checker = AASDataChecker(raise_immediately=False)
        checker.check_annotated_relationship_element_equal(rel1, rel2)
        self.assertEqual(2, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute annotation of AnnotatedRelationshipElement[test] must contain 1 DataElements "
                         "(count=0)",
                         repr(next(checker_iterator)))
        self.assertEqual("FAIL: Annotation Property[test / ExampleAnnotatedProperty] must exist ()",
                         repr(next(checker_iterator)))

    def test_submodel_checker(self):
        submodel = model.Submodel(id_='test')
        property_expected = model.Property(
            id_short='Prop1',
            value_type=model.datatypes.String,
            value='test'
        )
        submodel_expected = model.Submodel(id_='test',
                                           submodel_element=(property_expected,)
                                           )

        checker = AASDataChecker(raise_immediately=False)
        checker.check_submodel_equal(submodel, submodel_expected)
        self.assertEqual(2, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute submodel_element of Submodel[test] must contain 1 "
                         "SubmodelElements (count=0)",
                         repr(next(checker_iterator)))
        self.assertEqual("FAIL: Submodel Element Property[test / Prop1] must exist ()",
                         repr(next(checker_iterator)))

    def test_asset_administration_shell_checker(self):
        shell = model.AssetAdministrationShell(asset_information=model.AssetInformation(
            global_asset_id='test'),
            id_='test')
        shell_expected = model.AssetAdministrationShell(
            asset_information=model.AssetInformation(
                global_asset_id='test'),
            id_='test',
            submodel={model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                      value='test'),),
                                           model.Submodel)}
            )
        checker = AASDataChecker(raise_immediately=False)
        checker.check_asset_administration_shell_equal(shell, shell_expected)
        self.assertEqual(2, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute submodel of AssetAdministrationShell[test] must contain 1 "
                         "ModelReferences (count=0)",
                         repr(next(checker_iterator)))
        self.assertEqual("FAIL: Submodel Reference ModelReference<Submodel>(key=(Key(type=SUBMODEL,"
                         " value=test),)) must exist ()",
                         repr(next(checker_iterator)))

    def test_concept_description_checker(self):
        cd = model.ConceptDescription(id_='test')
        cd_expected = model.ConceptDescription(id_='test',
                                               is_case_of={
                                                   model.ExternalReference((model.Key(
                                                       type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='test'),))}
                                               )
        checker = AASDataChecker(raise_immediately=False)
        checker.check_concept_description_equal(cd, cd_expected)
        self.assertEqual(2, sum(1 for _ in checker.failed_checks))
        checker_iterator = checker.failed_checks
        self.assertEqual("FAIL: Attribute is_case_of of ConceptDescription[test] must contain "
                         "1 References (count=0)",
                         repr(next(checker_iterator)))
        self.assertEqual("FAIL: Concept Description Reference ExternalReference(key=(Key("
                         "type=GLOBAL_REFERENCE, value=test),)) must exist ()",
                         repr(next(checker_iterator)))
