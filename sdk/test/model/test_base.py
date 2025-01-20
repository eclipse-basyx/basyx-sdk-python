# Copyright (c) 2023 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import unittest
from unittest import mock
from typing import Callable, Dict, Iterable, List, Optional, Type, TypeVar
from collections import OrderedDict

from basyx.aas import model
from basyx.aas.model import Identifier, Identifiable
from basyx.aas.examples.data import example_aas


class KeyTest(unittest.TestCase):
    def test_get_identifier(self):
        key1 = model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel1")
        key2 = model.Key(model.KeyTypes.PROPERTY, "prop1")
        self.assertEqual("urn:x-test:submodel1", key1.get_identifier())
        self.assertIsNone(key2.get_identifier())

    def test_string_representation(self):
        key1 = model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel1")
        self.assertEqual("urn:x-test:submodel1", key1.__str__())

    def test_equality(self):
        key1 = model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel1")
        ident = 'test'
        self.assertEqual(key1.__eq__(ident), NotImplemented)

    def test_from_referable(self):
        mlp1 = model.MultiLanguageProperty(None)
        mlp2 = model.MultiLanguageProperty(None)
        se_list = model.SubmodelElementList("list", model.MultiLanguageProperty, [mlp1, mlp2])
        self.assertEqual(model.Key(model.KeyTypes.MULTI_LANGUAGE_PROPERTY, "0"), model.Key.from_referable(mlp1))
        self.assertEqual(model.Key(model.KeyTypes.MULTI_LANGUAGE_PROPERTY, "1"), model.Key.from_referable(mlp2))
        del se_list.value[0]
        self.assertEqual(model.Key(model.KeyTypes.MULTI_LANGUAGE_PROPERTY, "0"), model.Key.from_referable(mlp2))
        with self.assertRaises(ValueError) as cm:
            model.Key.from_referable(mlp1)
        self.assertEqual("Can't create Key for MultiLanguageProperty without an id_short!", str(cm.exception))
        mlp1.id_short = "mlp1"
        self.assertEqual(model.Key(model.KeyTypes.MULTI_LANGUAGE_PROPERTY, "mlp1"), model.Key.from_referable(mlp1))


class ExampleReferable(model.Referable):
    def __init__(self):
        super().__init__()


class ExampleRefereableWithNamespace(model.Referable, model.UniqueIdShortNamespace):
    def __init__(self):
        super().__init__()


class ExampleIdentifiable(model.Identifiable):
    def __init__(self):
        super().__init__()


def generate_example_referable_tree() -> model.Referable:
    """
    Generates an example referable tree, built like this:

        example_grandparent -> example_parent -> example_referable -> example_child -> example_grandchild

    :return: example_referable
    """

    def generate_example_referable_with_namespace(id_short: model.NameType,
                                                  child: Optional[model.Referable] = None) -> model.Referable:
        """
        Generates an example referable with a namespace.

        :param id_short: id_short of the referable created
        :param child: Child to be added to the namespace sets of the Referable
        :return: The generated Referable
        """
        referable = ExampleRefereableWithNamespace()
        referable.id_short = id_short
        if child:
            namespace_set = model.NamespaceSet(parent=referable, attribute_names=[("id_short", True)],
                                               items=[child])
        return referable

    example_grandchild = generate_example_referable_with_namespace("exampleGrandchild")
    example_child = generate_example_referable_with_namespace("exampleChild", example_grandchild)
    example_referable = generate_example_referable_with_namespace("exampleReferable", example_child)
    example_parent = generate_example_referable_with_namespace("exampleParent", example_referable)
    example_grandparent = generate_example_referable_with_namespace("exampleGrandparent", example_parent)

    return example_referable


class ReferableTest(unittest.TestCase):
    def test_id_short_constraint_aasd_002(self):
        test_object = ExampleReferable()
        test_object.id_short = "Test"
        self.assertEqual("Test", test_object.id_short)
        test_object.id_short = "asdASd123_"
        self.assertEqual("asdASd123_", test_object.id_short)
        test_object.id_short = "AAs12_"
        self.assertEqual("AAs12_", test_object.id_short)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            test_object.id_short = "98sdsfdAS"
        self.assertEqual("The id_short must start with a letter (Constraint AASd-002)", str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            test_object.id_short = "_sdsfdAS"
        self.assertEqual("The id_short must start with a letter (Constraint AASd-002)", str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            test_object.id_short = "asdlujSAD8348@S"
        self.assertEqual(
            "The id_short must contain only letters, digits and underscore (Constraint AASd-002)",
            str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            test_object.id_short = "abc\n"
        self.assertEqual(
            "The id_short must contain only letters, digits and underscore (Constraint AASd-002)",
            str(cm.exception))

    def test_representation(self):
        class DummyClass:
            def __init__(self, value: model.Referable):
                self.value: model.Referable = value

        ref = ExampleReferable()
        test_object = DummyClass(ref)
        ref.id_short = "NotNone"
        ref.parent = test_object
        with self.assertRaises(AttributeError) as cm:
            ref.__repr__()
        self.assertEqual('Referable must have an identifiable as root object and only parents that are referable',
                         str(cm.exception))

    def test_update_from(self):
        example_submodel = example_aas.create_example_submodel()
        example_relel = example_submodel.get_referable('ExampleRelationshipElement')

        other_submodel = example_aas.create_example_submodel()
        other_relel = other_submodel.get_referable('ExampleRelationshipElement')

        other_submodel.category = "NewCat"
        other_relel.category = "NewRelElCat"

        # Test basic functionality
        example_submodel.update_from(other_submodel)
        self.assertEqual("NewCat", example_submodel.category)
        self.assertEqual("NewRelElCat", example_relel.category)
        # References to Referable objects shall remain stable
        self.assertIs(example_relel, example_submodel.get_referable('ExampleRelationshipElement'))
        self.assertIs(example_relel, example_submodel.submodel_element.get("id_short", 'ExampleRelationshipElement'))
        # Check Namespace & parent consistency
        self.assertIs(example_submodel.namespace_element_sets[0], example_submodel.submodel_element)
        self.assertIs(example_relel.parent, example_submodel)

    def test_update_commit_qualifier_extension_semantic_id(self):
        submodel = model.Submodel("https://acplt.org/Test_Submodel")
        qualifier = model.Qualifier("test", model.datatypes.String)
        extension = model.Extension("test")
        collection = model.SubmodelElementCollection("test")
        property = model.MultiLanguageProperty("test")

        collection.add_referable(property)
        submodel.add_qualifier(qualifier)
        submodel.add_extension(extension)
        submodel.add_referable(collection)

        self.assertEqual(next(iter(submodel.qualifier)), qualifier)
        self.assertEqual(next(iter(submodel.extension)), extension)
        self.assertEqual(next(iter(submodel.submodel_element)), collection)
        self.assertEqual(next(iter(collection.value)), property)

        submodel.get_qualifier_by_type("test")
        submodel.get_extension_by_name("test")
        collection_ = submodel.get_referable("test")
        self.assertIsInstance(collection_, model.UniqueIdShortNamespace)
        assert isinstance(collection_, model.UniqueIdShortNamespace)
        collection_.get_referable("test")

        submodel.remove_qualifier_by_type("test")
        submodel.remove_extension_by_name("test")
        submodel.remove_referable("test")
        collection_.remove_referable("test")

        with self.assertRaises(StopIteration):
            next(iter(submodel.qualifier))
        with self.assertRaises(StopIteration):
            next(iter(submodel.extension))
        with self.assertRaises(StopIteration):
            next(iter(submodel.submodel_element))
        with self.assertRaises(StopIteration):
            next(iter(collection.value))


class ExampleNamespaceReferable(model.UniqueIdShortNamespace, model.UniqueSemanticIdNamespace, model.Identifiable):
    def __init__(self, values=()):
        super().__init__()
        # The 'id' is required by Referable.__repr__() in error messages.
        self.id = self.__class__.__name__
        self.set1 = model.NamespaceSet(self, [("id_short", False), ("semantic_id", True)])
        self.set2 = model.NamespaceSet(self, [("id_short", False)], values)
        self.set3 = model.NamespaceSet(self, [("name", True)])
        self.set4 = model.NamespaceSet(self, [("type", True)])


class ExampleNamespaceQualifier(model.Qualifiable):
    def __init__(self, values=()):
        super().__init__()
        self.set1 = model.NamespaceSet(self, [("type", False)], values)


class ModelNamespaceTest(unittest.TestCase):
    _namespace_class = ExampleNamespaceReferable
    _namespace_class_qualifier = ExampleNamespaceQualifier

    def setUp(self):
        self.propSemanticID = model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                                 value='http://acplt.org/Test1'),))
        self.propSemanticID2 = model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                                  value='http://acplt.org/Test2'),))
        self.propSemanticID3 = model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                                  value='http://acplt.org/Test3'),))
        self.prop1 = model.Property("Prop1", model.datatypes.Int, semantic_id=self.propSemanticID)
        self.prop2 = model.Property("Prop2", model.datatypes.Int, semantic_id=self.propSemanticID)
        self.prop3 = model.Property("Prop2", model.datatypes.Int, semantic_id=self.propSemanticID2)
        self.prop4 = model.Property("Prop3", model.datatypes.Int, semantic_id=self.propSemanticID)
        self.prop5 = model.Property("Prop3", model.datatypes.Int, semantic_id=self.propSemanticID2)
        self.prop6 = model.Property("Prop4", model.datatypes.Int, semantic_id=self.propSemanticID2)
        self.prop7 = model.Property("Prop2", model.datatypes.Int, semantic_id=self.propSemanticID3)
        self.prop8 = model.Property("ProP2", model.datatypes.Int, semantic_id=self.propSemanticID3)
        self.prop1alt = model.Property("Prop1", model.datatypes.Int, semantic_id=self.propSemanticID)
        self.collection1 = model.SubmodelElementCollection(None)
        self.list1 = model.SubmodelElementList("List1", model.SubmodelElementCollection,
                                               semantic_id=self.propSemanticID)
        self.qualifier1 = model.Qualifier("type1", model.datatypes.Int, 1, semantic_id=self.propSemanticID)
        self.qualifier2 = model.Qualifier("type2", model.datatypes.Int, 1, semantic_id=self.propSemanticID2)
        self.qualifier1alt = model.Qualifier("type1", model.datatypes.Int, 1, semantic_id=self.propSemanticID)
        self.extension1 = model.Extension("Ext1", model.datatypes.Int, 1, semantic_id=self.propSemanticID)
        self.extension2 = model.Extension("Ext2", model.datatypes.Int, 1, semantic_id=self.propSemanticID2)
        self.namespace = self._namespace_class()
        self.namespace3 = self._namespace_class_qualifier()

    def test_NamespaceSet(self) -> None:
        self.namespace.set1.add(self.prop1)
        self.assertEqual(1, len(self.namespace.set1))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            self.namespace.set1.add(self.prop2)
        self.assertEqual(
            "Object with attribute (name='semantic_id', value='ExternalReference(key=(Key("
            "type=GLOBAL_REFERENCE, value=http://acplt.org/Test1),))') is already present in this set of objects "
            "(Constraint AASd-000)",
            str(cm.exception))
        self.namespace.set2.add(self.prop5)
        self.namespace.set2.add(self.prop6)
        self.assertEqual(2, len(self.namespace.set2))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            self.namespace.set2.add(self.prop1)
        self.assertEqual("Object with attribute (name='id_short', value='Prop1') is already present in another "
                         "set in the same namespace (Constraint AASd-022)",
                         str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            self.namespace.set2.add(self.prop4)
        self.assertEqual(
            "Object with attribute (name='semantic_id', value='"
            "ExternalReference(key=(Key(type=GLOBAL_REFERENCE, value=http://acplt.org/Test1),))')"
            " is already present in another set in the same namespace (Constraint AASd-000)",
            str(cm.exception))

        self.assertIs(self.prop1, self.namespace.set1.get("id_short", "Prop1"))
        self.assertIn(self.prop1, self.namespace.set1)
        self.assertNotIn(self.prop1alt, self.namespace.set1)
        self.assertIs(self.namespace, self.prop1.parent)

        self.assertIs(self.prop5, self.namespace.set2.get("id_short", "Prop3"))

        with self.assertRaises(model.AASConstraintViolation) as cm:
            self.namespace.set1.add(self.prop1alt)
        self.assertEqual("Object with attribute (name='id_short', value='Prop1') is already present in this set of"
                         " objects (Constraint AASd-022)",
                         str(cm.exception))

        self.namespace.set1.add(self.prop3)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            self.namespace.set1.add(self.prop7)
        self.assertEqual("Object with attribute (name='id_short', value='Prop2') is already present in this set "
                         "of objects (Constraint AASd-022)",
                         str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            self.namespace.set1.add(self.prop8)
        self.assertEqual("Object with attribute (name='id_short', value='ProP2') is already present in this set "
                         "of objects (Constraint AASd-022)",
                         str(cm.exception))

        namespace2 = self._namespace_class()
        with self.assertRaises(ValueError) as cm2:
            namespace2.set1.add(self.prop1)
        self.assertIn('has already a parent', str(cm2.exception))

        self.assertEqual(2, len(self.namespace.set1))
        self.namespace.set1.remove(self.prop1)
        self.assertEqual(1, len(self.namespace.set1))
        self.assertIsNone(self.prop1.parent)
        self.namespace.set1.add(self.prop1)
        self.assertEqual(2, len(self.namespace.set1))
        self.namespace.set1.remove_by_id("id_short", self.prop1.id_short)
        self.assertEqual(1, len(self.namespace.set1))
        self.assertIsNone(self.prop1.parent)

        self.assertEqual(2, len(self.namespace.set2))
        self.assertIs(self.prop6, self.namespace.set2.pop())
        self.assertEqual(1, len(self.namespace.set2))
        self.namespace.set2.add(self.prop1alt)

        self.namespace.set2.clear()
        self.assertIsNone(self.prop1alt.parent)
        self.assertEqual(0, len(self.namespace.set2))

        self.assertEqual(1, len(self.namespace.set1))
        self.namespace.set1.add(self.prop1)
        self.assertEqual(2, len(self.namespace.set1))
        self.namespace.set1.discard(self.prop1)
        self.assertEqual(1, len(self.namespace.set1))
        self.assertIsNone(self.prop1.parent)
        self.namespace.set1.discard(self.prop1)

        self.namespace3.set1.add(self.qualifier1)
        self.assertEqual(1, len(self.namespace3.set1))
        self.namespace3.set1.add(self.qualifier2)
        self.assertEqual(2, len(self.namespace3.set1))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            self.namespace3.set1.add(self.qualifier1alt)
        self.assertEqual("Object with attribute (name='type', value='type1') is already present in this set "
                         "of objects (Constraint AASd-021)",
                         str(cm.exception))

    def test_namespaceset_hooks(self) -> None:
        T = TypeVar("T", bound=model.Referable)
        nss_types: List[Type[model.NamespaceSet]] = [model.NamespaceSet, model.OrderedNamespaceSet]
        for nss_type in nss_types:
            new_item = None
            old_item = None
            existing_items = []

            class DummyNamespace(model.UniqueIdShortNamespace):
                def __init__(self, items: Iterable[T], item_add_hook: Optional[Callable[[T, Iterable[T]], None]] = None,
                             item_id_set_hook: Optional[Callable[[T], None]] = None,
                             item_id_del_hook: Optional[Callable[[T], None]] = None):
                    super().__init__()
                    self.set1 = nss_type(self, [('id_short', True)], items, item_add_hook=item_add_hook,
                                         item_id_set_hook=item_id_set_hook,
                                         item_id_del_hook=item_id_del_hook)

            def add_hook(new: T, existing: Iterable[T]) -> None:
                nonlocal new_item, existing_items
                new_item = new
                # Create a new list to prevent an error when checking the assertions:
                # RuntimeError: dictionary changed size during iteration
                existing_items = list(existing)

            def id_set_hook(new: T) -> None:
                if new.id_short is not None:
                    new.id_short += "new"

            def id_del_hook(old: T) -> None:
                nonlocal old_item
                old_item = old
                if old.id_short is not None:
                    # remove "new" suffix
                    old.id_short = old.id_short[:-3]

            cap = model.Capability("test_cap")
            dummy_ns = DummyNamespace({cap}, item_add_hook=add_hook, item_id_set_hook=id_set_hook,
                                      item_id_del_hook=id_del_hook)
            self.assertEqual(cap.id_short, "test_capnew")
            self.assertIs(new_item, cap)
            self.assertEqual(len(existing_items), 0)

            mlp = model.MultiLanguageProperty("test_mlp")
            dummy_ns.add_referable(mlp)
            self.assertEqual(mlp.id_short, "test_mlpnew")
            self.assertIs(new_item, mlp)
            self.assertEqual(len(existing_items), 1)
            self.assertIn(cap, existing_items)

            prop = model.Property("test_prop", model.datatypes.Int)
            dummy_ns.set1.add(prop)
            self.assertEqual(prop.id_short, "test_propnew")
            self.assertIs(new_item, prop)
            self.assertEqual(len(existing_items), 2)
            self.assertIn(cap, existing_items)
            self.assertIn(mlp, existing_items)

            dummy_ns.remove_referable("test_capnew")
            self.assertIs(old_item, cap)
            self.assertEqual(cap.id_short, "test_cap")

            dummy_ns.set1.remove(prop)
            self.assertIs(old_item, prop)
            self.assertEqual(prop.id_short, "test_prop")

            dummy_ns.set1.remove_by_id("id_short", "test_mlpnew")
            self.assertIs(old_item, mlp)
            self.assertEqual(mlp.id_short, "test_mlp")

            self.assertEqual(len(list(dummy_ns)), 0)

            # test atomicity
            add_hook_counter: int = 0

            def add_hook_constraint(_new: T, _existing: Iterable[T]) -> None:
                nonlocal add_hook_counter
                add_hook_counter += 1
                if add_hook_counter > 1:
                    raise ValueError

            self.assertEqual(cap.id_short, "test_cap")
            self.assertEqual(mlp.id_short, "test_mlp")
            with self.assertRaises(ValueError):
                DummyNamespace([cap, mlp], item_add_hook=add_hook_constraint, item_id_set_hook=id_set_hook,
                               item_id_del_hook=id_del_hook)
            self.assertEqual(cap.id_short, "test_cap")
            self.assertIsNone(cap.parent)
            self.assertEqual(mlp.id_short, "test_mlp")
            self.assertIsNone(mlp.parent)

            dummy_ns = DummyNamespace((), item_add_hook=add_hook_constraint, item_id_set_hook=id_set_hook,
                                      item_id_del_hook=id_del_hook)
            add_hook_counter = 0
            dummy_ns.add_referable(cap)
            self.assertIs(cap.parent, dummy_ns)

            with self.assertRaises(ValueError):
                dummy_ns.set1.add(prop)
            self.assertEqual(prop.id_short, "test_prop")
            self.assertIsNone(prop.parent)

    def test_Namespace(self) -> None:
        with self.assertRaises(model.AASConstraintViolation) as cm:
            namespace_test = ExampleNamespaceReferable([self.prop1, self.prop2, self.prop1alt])
        self.assertEqual("Object with attribute (name='id_short', value='Prop1') is already present in this set "
                         "of objects (Constraint AASd-022)",
                         str(cm.exception))
        self.assertIsNone(self.prop1.parent)

        namespace = self._namespace_class([self.prop1, self.prop2])
        self.assertIs(self.prop2, namespace.get_referable("Prop2"))
        with self.assertRaises(KeyError) as cm2:
            namespace.get_referable("Prop3")
        self.assertEqual("'Referable with id_short Prop3 not found in "
                         f"{self._namespace_class.__name__}[{self.namespace.id}]'", str(cm2.exception))

        namespace.remove_referable("Prop2")
        with self.assertRaises(KeyError) as cm3:
            namespace.get_referable("Prop2")
        self.assertEqual("'Referable with id_short Prop2 not found in "
                         f"{self._namespace_class.__name__}[{self.namespace.id}]'", str(cm3.exception))

        with self.assertRaises(KeyError) as cm4:
            namespace.remove_referable("Prop2")
        self.assertEqual("'Referable with id_short Prop2 not found in "
                         f"{self._namespace_class.__name__}[{self.namespace.id}]'", str(cm4.exception))

    def test_id_short_path_resolution(self) -> None:
        self.namespace.set2.add(self.list1)
        self.list1.add_referable(self.collection1)
        self.collection1.add_referable(self.prop1)

        with self.assertRaises(ValueError) as cm:
            self.namespace.get_referable(["List1", "a"])
        self.assertEqual(f"Cannot resolve 'a' at SubmodelElementList[{self.namespace.id} / List1], "
                         "because it is not a numeric index!", str(cm.exception))

        with self.assertRaises(KeyError) as cm_2:
            self.namespace.get_referable(["List1", "0", "Prop2"])
        self.assertEqual("'Referable with id_short Prop2 not found in "
                         f"SubmodelElementCollection[{self.namespace.id} / List1[0]]'", str(cm_2.exception))

        with self.assertRaises(TypeError) as cm_3:
            self.namespace.get_referable(["List1", "0", "Prop1", "Test"])
        self.assertEqual("Cannot resolve id_short or index 'Test' at "
                         f"Property[{self.namespace.id} / List1[0] / Prop1], "
                         "because it is not a UniqueIdShortNamespace!", str(cm_3.exception))

        self.namespace.get_referable(["List1", "0", "Prop1"])

    def test_renaming(self) -> None:
        self.namespace.set2.add(self.prop1)
        self.namespace.set2.add(self.prop2)
        self.assertIs(self.prop1, self.namespace.get_referable("Prop1"))
        self.assertIs(self.prop2, self.namespace.get_referable("Prop2"))

        self.prop1.id_short = "Prop3"
        self.assertEqual("Prop3", self.prop1.id_short)
        self.assertEqual(2, len(self.namespace.set2))
        self.assertIs(self.prop1, self.namespace.get_referable("Prop3"))
        with self.assertRaises(KeyError) as cm:
            self.namespace.get_referable('Prop1')
        self.assertEqual("'Referable with id_short Prop1 not found in "
                         f"{self._namespace_class.__name__}[{self.namespace.id}]'", str(cm.exception))
        self.assertIs(self.prop2, self.namespace.get_referable("Prop2"))
        with self.assertRaises(model.AASConstraintViolation) as cm2:
            self.prop1.id_short = "Prop2"
        self.assertIn("already present", str(cm2.exception))

        self.namespace.set3.add(self.extension1)
        self.namespace.set3.add(self.extension2)
        with self.assertRaises(KeyError) as cm:
            self.extension1.name = "Ext2"
        self.assertIn("already present", str(cm.exception))
        self.extension1.name = "Ext3"
        self.assertEqual(self.extension1.name, "Ext3")

        self.namespace.set4.add(self.qualifier1)
        self.namespace.set4.add(self.qualifier2)
        with self.assertRaises(KeyError) as cm:
            self.qualifier1.type = "type2"
        self.assertIn("already present", str(cm.exception))
        self.qualifier1.type = "type3"
        self.assertEqual(self.qualifier1.type, "type3")

    def test_Namespaceset_update_from(self) -> None:
        # Prop1 is getting its value updated by namespace2.set1
        # Prop2 is getting deleted since it does not exist in namespace2.set1
        # Prop3 is getting added, since it does not exist in namespace1.set1 yet
        namespace1 = self._namespace_class()
        prop1 = model.Property("Prop1", model.datatypes.Int, 1, semantic_id=self.propSemanticID)
        prop2 = model.Property("Prop2", model.datatypes.Int, 0, semantic_id=self.propSemanticID2)
        namespace1.set2.add(prop1)
        namespace1.set2.add(prop2)
        namespace2 = self._namespace_class()
        namespace2.set2.add(model.Property("Prop1", model.datatypes.Int, 0, semantic_id=self.propSemanticID))
        namespace2.set2.add(model.Property("Prop3", model.datatypes.Int, 2, semantic_id=self.propSemanticID2))
        namespace1.set2.update_nss_from(namespace2.set2)
        # Check that Prop1 got updated correctly
        self.assertIs(namespace1.get_referable("Prop1"), prop1)
        self.assertEqual(prop1.value, 0)
        self.assertIs(namespace1.get_referable("Prop1").parent, namespace1)
        # Check that Prop3 got added correctly
        prop3_new = namespace1.set2.get_object_by_attribute("id_short", "Prop3")
        self.assertIs(prop3_new.parent, namespace1)
        assert isinstance(prop3_new, model.Property)
        self.assertEqual(prop3_new.value, 2)
        # Check that Prop2 got removed correctly
        self.assertFalse(namespace1.set2.contains_id("id_short", "Prop2"))
        with self.assertRaises(KeyError):
            namespace1.get_referable("Prop2")
        self.assertIsNone(prop2.parent)

    def test_qualifiable_id_short_namespace(self) -> None:
        prop1 = model.Property("Prop1", model.datatypes.Int, 1)
        qualifier1 = model.Qualifier("Qualifier1", model.datatypes.Int, 2)
        submodel_element_collection = model.SubmodelElementCollection("test_SMC", [prop1],
                                                                      qualifier=[qualifier1])
        self.assertIs(submodel_element_collection.get_referable("Prop1"), prop1)
        self.assertIs(submodel_element_collection.get_qualifier_by_type("Qualifier1"), qualifier1)

    def test_aasd_117(self) -> None:
        property = model.Property(None, model.datatypes.Int, semantic_id=self.propSemanticID)
        se_collection = model.SubmodelElementCollection("foo")
        with self.assertRaises(model.AASConstraintViolation) as cm:
            se_collection.add_referable(property)
        self.assertEqual("Property has attribute id_short=None, which is not allowed within a "
                         "SubmodelElementCollection! (Constraint AASd-117)", str(cm.exception))
        property.id_short = "property"
        se_collection.add_referable(property)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            property.id_short = None
        self.assertEqual("id_short of Property[foo / property] cannot be unset, since it is already contained in "
                         "SubmodelElementCollection[foo] (Constraint AASd-117)", str(cm.exception))
        property.id_short = "bar"


class ExampleOrderedNamespace(model.UniqueIdShortNamespace, model.UniqueSemanticIdNamespace, model.Identifiable):
    def __init__(self, values=()):
        super().__init__()
        # The 'id' is required by Referable.__repr__() in error messages.
        self.id = self.__class__.__name__
        self.set1 = model.OrderedNamespaceSet(self, [("id_short", False), ("semantic_id", True)])
        self.set2 = model.OrderedNamespaceSet(self, [("id_short", False)], values)
        self.set3 = model.NamespaceSet(self, [("name", True)])
        self.set4 = model.NamespaceSet(self, [("type", True)])


class ModelOrderedNamespaceTest(ModelNamespaceTest):
    _namespace_class = ExampleOrderedNamespace  # type: ignore

    def test_OrderedNamespace(self) -> None:
        # Tests from ModelNamespaceTest are inherited, but with ExampleOrderedNamespace instead of ExampleNamespace
        # So, we only need to test order-related things here
        self.namespace.set2.add(self.prop1)
        self.assertEqual(1, len(self.namespace.set2))
        self.namespace.set2.insert(0, self.prop2)
        self.assertEqual(2, len(self.namespace.set2))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            self.namespace.set1.insert(0, self.prop1alt)
        self.assertEqual('Object with attribute (name=\'id_short\', value=\'Prop1\') is already present in another '
                         'set in the same namespace (Constraint AASd-022)',
                         str(cm.exception))
        self.assertEqual((self.prop2, self.prop1), tuple(self.namespace.set2))
        self.assertEqual(self.prop1, self.namespace.set2[1])

        with self.assertRaises(model.AASConstraintViolation) as cm:
            self.namespace.set2[1] = self.prop2
        self.assertEqual('Object with attribute (name=\'id_short\', value=\'Prop2\') is already present in this '
                         'set of objects (Constraint AASd-022)',
                         str(cm.exception))
        prop3 = model.Property("Prop3", model.datatypes.Int, semantic_id=self.propSemanticID3)
        self.assertEqual(2, len(self.namespace.set2))
        self.namespace.set2[1] = prop3
        self.assertEqual(2, len(self.namespace.set2))
        self.assertIsNone(self.prop1.parent)
        self.assertIs(self.namespace, prop3.parent)
        self.assertEqual((self.prop2, prop3), tuple(self.namespace.set2))

        del self.namespace.set2[0]
        self.assertIsNone(self.prop2.parent)
        self.assertEqual(1, len(self.namespace.set2))

        namespace2 = ExampleOrderedNamespace()
        namespace2.set2.add(self.prop1)
        namespace2.set2.add(self.prop5)
        self.assertEqual(2, len(namespace2.set2))
        self.assertIs(self.prop1, namespace2.set2.get("id_short", "Prop1"))
        namespace2.set2.remove(("id_short", "Prop1"))
        self.assertEqual(1, len(namespace2.set2))
        with self.assertRaises(KeyError) as cm2:
            namespace2.get_referable("Prop1")
        self.assertEqual("'Referable with id_short Prop1 not found in "
                         f"{self._namespace_class.__name__}[{self.namespace.id}]'",  # type: ignore[has-type]
                         str(cm2.exception))


class ExternalReferenceTest(unittest.TestCase):
    def test_constraints(self):
        with self.assertRaises(ValueError) as cm:
            model.ExternalReference(tuple())
        self.assertEqual("A reference must have at least one key!", str(cm.exception))

        # AASd-122
        keys = (model.Key(model.KeyTypes.PROPERTY, "urn:x-test:x"),)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.ExternalReference(keys)
        self.assertEqual("The type of the first key of an ExternalReference must be a GenericGloballyIdentifiable: "
                         f"{keys[0]!r} (Constraint AASd-122)", str(cm.exception))
        model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:x"),))

        # AASd-124
        keys = (model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:x"),
                model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.ExternalReference(keys)
        self.assertEqual("The type of the last key of an ExternalReference must be a GenericGloballyIdentifiable or a"
                         f" GenericFragmentKey: {keys[-1]!r} (Constraint AASd-124)", str(cm.exception))
        keys += (model.Key(model.KeyTypes.FRAGMENT_REFERENCE, "urn:x-test:x"),)
        model.ExternalReference(keys)


class ModelReferenceTest(unittest.TestCase):
    def test_constraints(self):
        with self.assertRaises(ValueError) as cm:
            model.ExternalReference(tuple())
        self.assertEqual("A reference must have at least one key!", str(cm.exception))

        # AASd-123
        keys = (model.Key(model.KeyTypes.PROPERTY, "urn:x-test:x"),)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.ModelReference(keys, model.Property)
        self.assertEqual(f"The type of the first key of a ModelReference must be an AasIdentifiable: {keys[0]!r}"
                         " (Constraint AASd-123)", str(cm.exception))
        keys = (model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),) + keys
        model.ModelReference(keys, model.Property)

        # AASd-125
        keys = (model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),
                model.Key(model.KeyTypes.ASSET_ADMINISTRATION_SHELL, "urn:x-test:x"),
                model.Key(model.KeyTypes.CONCEPT_DESCRIPTION, "urn:x-test:x"))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.ModelReference(keys, model.ConceptDescription)
        self.assertEqual("The type of all keys following the first of a ModelReference "
                         f"must be one of FragmentKeyElements: {keys[1]!r} (Constraint AASd-125)", str(cm.exception))
        keys = (keys[0], model.Key(model.KeyTypes.FILE, "urn:x-test:x"), keys[2])
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.ModelReference(keys, model.ConceptDescription)
        self.assertEqual("The type of all keys following the first of a ModelReference "
                         f"must be one of FragmentKeyElements: {keys[2]!r} (Constraint AASd-125)", str(cm.exception))
        keys = tuple(keys[:2]) + (model.Key(model.KeyTypes.FRAGMENT_REFERENCE, "urn:x-test:x"),)
        model.ModelReference(keys, model.ConceptDescription)

        # AASd-126
        keys = (model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),
                model.Key(model.KeyTypes.FILE, "urn:x-test:x"),
                model.Key(model.KeyTypes.FRAGMENT_REFERENCE, "urn:x-test:x"),
                model.Key(model.KeyTypes.PROPERTY, "urn:x-test:x"))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.ModelReference(keys, model.Property)
        self.assertEqual(f"Key {keys[2]!r} is a GenericFragmentKey, but the last key of the chain is not: {keys[-1]!r}"
                         " (Constraint AASd-126)", str(cm.exception))
        keys = tuple(keys[:3])
        model.ModelReference(keys, model.File)

        # AASd-127
        keys = (model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),
                model.Key(model.KeyTypes.PROPERTY, "urn:x-test:x"),
                model.Key(model.KeyTypes.FRAGMENT_REFERENCE, "urn:x-test:x"))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.ModelReference(keys, model.Property)
        self.assertEqual(f"{keys[-1]!r} is not preceded by a key of type File or Blob, but {keys[1]!r}"
                         f" (Constraint AASd-127)", str(cm.exception))
        keys = (keys[0], model.Key(model.KeyTypes.BLOB, "urn:x-test:x"), keys[2])
        model.ModelReference(keys, model.Blob)

        # AASd-128
        keys = (model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),
                model.Key(model.KeyTypes.SUBMODEL_ELEMENT_LIST, "urn:x-test:x"))
        for invalid_key_value in ("string", "-5", "5.5", "5,5", "+5"):
            invalid_key = model.Key(model.KeyTypes.PROPERTY, invalid_key_value)
            with self.assertRaises(model.AASConstraintViolation) as cm:
                model.ModelReference(keys + (invalid_key,), model.Property)
            self.assertEqual(f"Key {keys[1]!r} references a SubmodelElementList, but the value of the succeeding key "
                             f"({invalid_key!r}) is not a non-negative integer: {invalid_key.value} "
                             "(Constraint AASd-128)",
                             str(cm.exception))
        keys = keys[:1] + (model.Key(model.KeyTypes.PROPERTY, "5"),)
        model.ModelReference(keys, model.Property)

    def test_set_reference(self):
        ref = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),), model.Submodel)
        with self.assertRaises(AttributeError) as cm:
            ref.type = model.Property
        self.assertEqual('Reference is immutable', str(cm.exception))
        with self.assertRaises(AttributeError) as cm:
            ref.key = model.Key(model.KeyTypes.PROPERTY, "urn:x-test:x")
        self.assertEqual('Reference is immutable', str(cm.exception))
        with self.assertRaises(AttributeError) as cm:
            ref.key = ()
        self.assertEqual('Reference is immutable', str(cm.exception))
        with self.assertRaises(AttributeError) as cm:
            ref.referred_semantic_id = model.ExternalReference(
                (model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:x"),))
        self.assertEqual('Reference is immutable', str(cm.exception))

    def test_equality(self):
        ref = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),),
                                   model.Submodel)
        ident = 'test'
        self.assertEqual(ref.__eq__(ident), NotImplemented)
        ref_2 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),
                                      model.Key(model.KeyTypes.PROPERTY, "test")),
                                     model.Submodel)
        self.assertNotEqual(ref, ref_2)
        ref_3 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),
                                      model.Key(model.KeyTypes.PROPERTY, "test")),
                                     model.Submodel)
        self.assertEqual(ref_2, ref_3)
        referred_semantic_id = model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:x"),))
        object.__setattr__(ref_2, 'referred_semantic_id', referred_semantic_id)
        self.assertNotEqual(ref_2, ref_3)
        object.__setattr__(ref_3, 'referred_semantic_id', referred_semantic_id)
        self.assertEqual(ref_2, ref_3)

    def test_reference_typing(self) -> None:
        dummy_submodel = model.Submodel("urn:x-test:x")

        class DummyObjectProvider(model.AbstractObjectProvider):
            def get_identifiable(self, identifier: Identifier) -> Identifiable:
                return dummy_submodel

        x = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),), model.Submodel)
        submodel: model.Submodel = x.resolve(DummyObjectProvider())
        self.assertIs(submodel, submodel)

    def test_resolve(self) -> None:
        prop = model.Property("prop", model.datatypes.Int)
        collection = model.SubmodelElementCollection(None, {prop})
        list_ = model.SubmodelElementList("list", model.SubmodelElementCollection, {collection})
        submodel = model.Submodel("urn:x-test:submodel", {list_})

        class DummyObjectProvider(model.AbstractObjectProvider):
            def get_identifiable(self, identifier: Identifier) -> Identifiable:
                if identifier == submodel.id:
                    return submodel
                else:
                    raise KeyError()

        ref1 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_LIST, "lst"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_COLLECTION, "99"),
                                     model.Key(model.KeyTypes.PROPERTY, "prop")),
                                    model.Property)
        with self.assertRaises(KeyError) as cm:
            ref1.resolve(DummyObjectProvider())
        self.assertEqual("'Referable with id_short lst not found in Submodel[urn:x-test:submodel]'", str(cm.exception))

        ref2 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_LIST, "list"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_COLLECTION, "99"),
                                     model.Key(model.KeyTypes.PROPERTY, "prop")),
                                    model.Property)
        with self.assertRaises(KeyError) as cm_2:
            ref2.resolve(DummyObjectProvider())
        self.assertEqual("'Referable with index 99 not found in SubmodelElementList[urn:x-test:submodel / list]'",
                         str(cm_2.exception))

        ref3 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_LIST, "list"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_COLLECTION, "0"),
                                     model.Key(model.KeyTypes.PROPERTY, "prop")),
                                    model.Property)
        self.assertIs(prop, ref3.resolve(DummyObjectProvider()))

        ref4 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_LIST, "list"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_COLLECTION, "0"),
                                     model.Key(model.KeyTypes.PROPERTY, "prop"),
                                     model.Key(model.KeyTypes.PROPERTY, "prop")),
                                    model.Property)
        with self.assertRaises(TypeError) as cm_3:
            ref4.resolve(DummyObjectProvider())
        self.assertEqual("Cannot resolve id_short or index 'prop' at Property[urn:x-test:submodel / list[0] / prop], "
                         "because it is not a UniqueIdShortNamespace!", str(cm_3.exception))

        with self.assertRaises(AttributeError) as cm_4:
            ref1.key[2].value = "prop1"
        self.assertEqual("Reference is immutable", str(cm_4.exception))

        ref5 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:sub"),), model.Property)
        # Oh no, yet another typo!
        with self.assertRaises(KeyError) as cm_5:
            ref5.resolve(DummyObjectProvider())
        self.assertEqual("'Could not resolve identifier urn:x-test:sub'", str(cm_5.exception))

        ref6 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel"),), model.Property)
        # Okay, typo is fixed, but the type is not what we expect. However, we should get the submodel via the
        # exception's value attribute
        with self.assertRaises(model.UnexpectedTypeError) as cm_6:
            ref6.resolve(DummyObjectProvider())
        self.assertIs(submodel, cm_6.exception.value)

        with self.assertRaises(ValueError) as cm_7:
            ref7 = model.ModelReference((), model.Submodel)
        self.assertEqual('A reference must have at least one key!', str(cm_7.exception))

        ref8 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_LIST, "list"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_COLLECTION, "0"),
                                     model.Key(model.KeyTypes.PROPERTY, "prop_false")), model.Property)

        with self.assertRaises(KeyError) as cm_8:
            ref8.resolve(DummyObjectProvider())
        self.assertEqual("'Referable with id_short prop_false not found in "
                         "SubmodelElementCollection[urn:x-test:submodel / list[0]]'", str(cm_8.exception))

        ref9 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:submodel"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_COLLECTION, "list"),
                                     model.Key(model.KeyTypes.SUBMODEL_ELEMENT_COLLECTION, "collection")),
                                    model.SubmodelElementCollection)

        with self.assertRaises(ValueError) as cm_9:
            ref9.resolve(DummyObjectProvider())
        self.assertEqual("Cannot resolve 'collection' at SubmodelElementList[urn:x-test:submodel / list], "
                         "because it is not a numeric index!", str(cm_9.exception))

    def test_get_identifier(self) -> None:
        ref = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),), model.Submodel)
        self.assertEqual("urn:x-test:x", ref.get_identifier())

        ref2 = model.ModelReference((model.Key(model.KeyTypes.SUBMODEL, "urn:x-test:x"),
                                     model.Key(model.KeyTypes.PROPERTY, "myProperty"),), model.Submodel)
        self.assertEqual("urn:x-test:x", ref2.get_identifier())

    def test_from_referable(self) -> None:
        prop = model.Property("prop", model.datatypes.Int)
        collection = model.SubmodelElementCollection("collection", {prop})
        prop.parent = collection
        submodel = model.Submodel("urn:x-test:submodel", {collection})
        collection.parent = submodel

        # Test normal usage for Identifiable and Referable objects
        ref1 = model.ModelReference.from_referable(submodel)
        self.assertEqual(1, len(ref1.key))
        self.assertIs(ref1.type, model.Submodel)
        self.assertEqual("urn:x-test:submodel", ref1.key[0].value)
        self.assertEqual(model.KeyTypes.SUBMODEL, ref1.key[0].type)

        ref2 = model.ModelReference.from_referable(prop)
        self.assertEqual(3, len(ref2.key))
        self.assertIs(ref2.type, model.Property)
        self.assertEqual("urn:x-test:submodel", ref2.key[0].value)
        self.assertEqual("prop", ref2.key[2].value)
        self.assertEqual(model.KeyTypes.PROPERTY, ref2.key[2].type)

        # Test exception for element without identifiable ancestor
        submodel.submodel_element.remove(collection)
        with self.assertRaises(ValueError) as cm:
            ref3 = model.ModelReference.from_referable(prop)
        self.assertEqual("The given Referable object is not embedded within an Identifiable object", str(cm.exception))

        # Test creating a reference to a custom Referable class
        class DummyThing(model.Referable):
            def __init__(self, id_short: model.NameType):
                super().__init__()
                self.id_short = id_short

        class DummyIdentifyableNamespace(model.Submodel, model.UniqueIdShortNamespace):
            def __init__(self, id_: model.Identifier):
                super().__init__(id_)
                self.things: model.NamespaceSet = model.NamespaceSet(self, [("id_short", True)])

        thing = DummyThing("thing")
        identifable_thing = DummyIdentifyableNamespace("urn:x-test:thing")
        identifable_thing.things.add(thing)
        ref4 = model.ModelReference.from_referable(thing)
        self.assertIs(ref4.type, model.Referable)


class AdministrativeInformationTest(unittest.TestCase):

    def test_setting_version_revision(self) -> None:
        with self.assertRaises(model.AASConstraintViolation) as cm:
            obj = model.AdministrativeInformation(revision='9')
        self.assertEqual("A revision requires a version. This means, if there is no version there is no "
                         "revision neither. Please set version first. (Constraint AASd-005)", str(cm.exception))

    def test_setting_revision(self) -> None:
        obj = model.AdministrativeInformation()
        with self.assertRaises(model.AASConstraintViolation) as cm:
            obj.revision = '3'
        self.assertEqual("A revision requires a version. This means, if there is no version there is no revision "
                         "neither. Please set version first. (Constraint AASd-005)", str(cm.exception))


class QualifierTest(unittest.TestCase):
    def test_set_value(self):
        qualifier = model.Qualifier('test', model.datatypes.Int, 2)
        self.assertEqual(qualifier.value, 2)
        qualifier.value = None
        self.assertIsNone(qualifier.value)


class ExtensionTest(unittest.TestCase):
    def test_set_value(self):
        extension = model.Extension('test', model.datatypes.Int, 2)
        self.assertEqual(extension.value, 2)
        extension.value = None
        self.assertIsNone(extension.value)
        extension2 = model.Extension('test')
        with self.assertRaises(ValueError) as cm:
            extension2.value = 2
        self.assertEqual("ValueType must be set, if value is not None", str(cm.exception))


class ValueReferencePairTest(unittest.TestCase):
    def test_set_value(self):
        pair = model.ValueReferencePair(
            value="2",
            value_id=model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE, 'test'),)))
        self.assertEqual(pair.value, "2")
        pair.value = "3"
        self.assertEqual(pair.value, "3")


class HasSemanticsTest(unittest.TestCase):
    def test_supplemental_semantic_id_constraint(self) -> None:
        extension = model.Extension(name='test')
        key: model.Key = model.Key(model.KeyTypes.GLOBAL_REFERENCE, "global_reference")
        ref_sem_id: model.Reference = model.ExternalReference((key,))
        ref1: model.Reference = model.ExternalReference((key,))

        with self.assertRaises(model.AASConstraintViolation) as cm:
            extension.supplemental_semantic_id.append(ref1)
        self.assertEqual(cm.exception.constraint_id, 118)
        self.assertEqual('A semantic_id must be defined before adding a supplemental_semantic_id! '
                         '(Constraint AASd-118)', str(cm.exception))
        extension.semantic_id = ref_sem_id
        extension.supplemental_semantic_id.append(ref1)

        with self.assertRaises(model.AASConstraintViolation) as cm:
            extension.semantic_id = None
        self.assertEqual(cm.exception.constraint_id, 118)
        self.assertEqual('semantic_id can not be removed while there is at least one supplemental_semantic_id: '
                         '[ExternalReference(key=(Key(type=GLOBAL_REFERENCE, value=global_reference),))] '
                         '(Constraint AASd-118)', str(cm.exception))
        extension.supplemental_semantic_id.clear()
        extension.semantic_id = None


class ConstrainedListTest(unittest.TestCase):
    def test_length(self) -> None:
        c_list: model.ConstrainedList[int] = model.ConstrainedList([1, 2])
        self.assertEqual(len(c_list), 2)
        c_list.append(1)
        self.assertEqual(len(c_list), 3)
        c_list.clear()
        self.assertEqual(len(c_list), 0)

    def test_contains(self) -> None:
        c_list: model.ConstrainedList[int] = model.ConstrainedList([1, 2])
        self.assertIn(1, c_list)
        self.assertNotIn(3, c_list)
        c_list.append(3)
        self.assertIn(3, c_list)

    def test_hooks(self) -> None:
        new: Optional[int] = None
        old_items: List[int] = []
        new_items: List[int] = []
        existing_items: List[int] = []

        def add_hook(itm: int, list_: List[int]) -> None:
            nonlocal new, existing_items
            new = itm
            # Copy list, otherwise we just store a reference to the same lists and the tests are meaningless.
            existing_items = list_.copy()

        def set_hook(old: List[int], new: List[int], list_: List[int]) -> None:
            nonlocal old_items, new_items, existing_items
            # Copy list, otherwise we just store a reference to the same lists and the tests are meaningless.
            old_items = old.copy()
            new_items = new.copy()
            existing_items = list_.copy()

        def del_hook(itm: int, list_: List[int]) -> None:
            nonlocal new, existing_items
            new = itm
            # Copy list, otherwise we just store a reference to the same lists and the tests are meaningless.
            existing_items = list_.copy()

        self.assertIsNone(new)
        self.assertEqual(len(existing_items), 0)

        c_list: model.ConstrainedList[int] = model.ConstrainedList([1, 2, 3], item_add_hook=add_hook,
                                                                   item_set_hook=set_hook,
                                                                   item_del_hook=del_hook)
        check_list: List[int] = [1, 2, 3]

        self.assertEqual(new, 3)
        self.assertEqual(existing_items, [1, 2])
        self.assertEqual(c_list, check_list)

        # add hook test
        c_list.append(4)
        self.assertEqual(new, 4)
        self.assertEqual(existing_items, [1, 2, 3])
        check_list.append(4)
        self.assertEqual(c_list, check_list)

        c_list.extend([10, 11])
        self.assertEqual(new, 11)
        self.assertEqual(existing_items, [1, 2, 3, 4, 10])
        check_list.extend([10, 11])
        self.assertEqual(c_list, check_list)

        c_list.insert(2, 20)
        self.assertEqual(new, 20)
        self.assertEqual(existing_items, [1, 2, 3, 4, 10, 11])
        check_list.insert(2, 20)
        self.assertEqual(c_list, check_list)

        # set hook test
        c_list[2] = 40
        self.assertEqual(old_items, [20])
        self.assertEqual(new_items, [40])
        self.assertEqual(existing_items, [1, 2, 20, 3, 4, 10, 11])
        check_list[2] = 40
        self.assertEqual(c_list, check_list)

        c_list[2:4] = [2, 3]
        self.assertEqual(old_items, [40, 3])
        self.assertEqual(new_items, [2, 3])
        self.assertEqual(existing_items, [1, 2, 40, 3, 4, 10, 11])
        check_list[2:4] = [2, 3]
        self.assertEqual(c_list, check_list)

        c_list[:] = []
        self.assertEqual(old_items, [1, 2, 2, 3, 4, 10, 11])
        self.assertEqual(new_items, [])
        self.assertEqual(existing_items, [1, 2, 2, 3, 4, 10, 11])
        check_list[:] = []
        self.assertEqual(c_list, check_list)

        c_list[:] = [1, 2, 20, 3, 4, 10, 11]
        self.assertEqual(old_items, [])
        self.assertEqual(new_items, [1, 2, 20, 3, 4, 10, 11])
        self.assertEqual(existing_items, [])
        check_list[:] = [1, 2, 20, 3, 4, 10, 11]
        self.assertEqual(c_list, check_list)

        # del hook test
        c_list.remove(20)
        self.assertEqual(new, 20)
        self.assertEqual(existing_items, [1, 2, 20, 3, 4, 10, 11])
        check_list.remove(20)
        self.assertEqual(c_list, check_list)

        with self.assertRaises(ValueError):
            c_list.remove(20)

        c_list.pop()
        self.assertEqual(new, 11)
        self.assertEqual(existing_items, [1, 2, 3, 4, 10, 11])
        check_list.pop()
        self.assertEqual(c_list, check_list)

    def test_atomicity(self) -> None:
        def hook(itm: int, _list: List[int]) -> None:
            if itm > 2:
                raise ValueError

        c_list: model.ConstrainedList[int] = model.ConstrainedList([], item_add_hook=hook)
        with self.assertRaises(ValueError):
            c_list = model.ConstrainedList([1, 2, 3], item_add_hook=hook)
        self.assertEqual(c_list, [])
        with self.assertRaises(ValueError):
            c_list.extend([1, 2, 3])
        self.assertEqual(c_list, [])
        c_list.extend([1, 2])
        self.assertEqual(c_list, [1, 2])

        c_list = model.ConstrainedList([1, 2, 3], item_del_hook=hook)
        with self.assertRaises(ValueError):
            del c_list[0:3]
        self.assertEqual(c_list, [1, 2, 3])
        with self.assertRaises(ValueError):
            c_list.clear()
        # the default clear() implementation seems to repeatedly delete the last item until the list is empty
        # in this case, the last item is 3, which cannot be deleted because it is > 2, thus leaving it unclear whether
        # clear() really is atomic. to work around this, the list is reversed, making 1 the last item, and attempting
        # to clear again.
        c_list.reverse()
        with self.assertRaises(ValueError):
            c_list.clear()
        self.assertEqual(c_list, [3, 2, 1])
        c_list.reverse()
        del c_list[0:2]
        self.assertEqual(c_list, [3])


class LangStringSetTest(unittest.TestCase):
    def test_language_tag_constraints(self) -> None:
        with self.assertRaises(ValueError) as cm:
            model.LangStringSet({"foo": "bar"})
        self.assertEqual("The language code of the language tag must consist of exactly two lower-case letters! "
                         "Given language tag and language code: 'foo', 'foo'", str(cm.exception))

        lss = model.LangStringSet({"fo-OO": "bar"})
        with self.assertRaises(ValueError) as cm:
            lss["foo"] = "bar"
        self.assertEqual("The language code of the language tag must consist of exactly two lower-case letters! "
                         "Given language tag and language code: 'foo', 'foo'", str(cm.exception))
        self.assertNotIn("foo", lss)
        self.assertNotIn("fo", lss)
        lss["fo"] = "bar"
        self.assertIn("fo", lss)

    def test_empty(self) -> None:
        lss = model.LangStringSet({"fo": "bar", "fo-OO": "baz"})
        with self.assertRaises(KeyError) as cm:
            lss.clear()
        self.assertEqual("A LangStringSet must not be empty!", cm.exception.args[0])
        self.assertEqual(lss, model.LangStringSet({"fo": "bar", "fo-OO": "baz"}))
        del lss["fo"]
        self.assertNotEqual(lss, model.LangStringSet({"fo": "bar", "fo-OO": "baz"}))
        self.assertEqual(lss, model.LangStringSet({"fo-OO": "baz"}))
        with self.assertRaises(KeyError) as cm:
            del lss["fo-OO"]
        self.assertEqual("A LangStringSet must not be empty!", cm.exception.args[0])
        self.assertEqual(lss, model.LangStringSet({"fo-OO": "baz"}))

    def test_text_constraints(self) -> None:
        with self.assertRaises(ValueError) as cm:
            model.MultiLanguageNameType({"fo": "o" * 65})
        self.assertEqual("The text for the language tag 'fo' is invalid: MultiLanguageNameType has a maximum length of "
                         "64! (length: 65)", str(cm.exception))
        mlnt = model.MultiLanguageNameType({"fo": "o" * 64})
        with self.assertRaises(ValueError) as cm:
            mlnt["fo"] = ""
        self.assertEqual("The text for the language tag 'fo' is invalid: MultiLanguageNameType has a minimum length of "
                         "1! (length: 0)", str(cm.exception))
        self.assertEqual(mlnt["fo"], "o" * 64)
        mlnt["fo"] = "o"
        self.assertEqual(mlnt["fo"], "o")

    def test_repr(self) -> None:
        lss = model.LangStringSet({"fo": "bar"})
        self.assertEqual("LangStringSet(fo=\"bar\")", repr(lss))
        self.assertEqual(repr(lss), str(lss))
        mltt = model.MultiLanguageTextType({"fo": "bar"})
        self.assertEqual("MultiLanguageTextType(fo=\"bar\")", repr(mltt))
        self.assertEqual(repr(mltt), str(mltt))

    def test_len(self) -> None:
        lss = model.LangStringSet({"fo": "bar"})
        self.assertEqual(1, len(lss))
        lss["aa"] = "baz"
        self.assertEqual(2, len(lss))

    def test_iter(self) -> None:
        lss = model.LangStringSet({"fo": "bar", "aa": "baz"})
        count: int = 0
        items: Dict[str, str] = {}
        for ltag, text in lss.items():
            count += 1
            items[ltag] = text
        self.assertEqual(count, 2)
        self.assertEqual(items, {"fo": "bar", "aa": "baz"})
