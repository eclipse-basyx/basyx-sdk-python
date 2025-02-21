# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import unittest
import dateutil.tz

from basyx.aas import model


class EntityTest(unittest.TestCase):
    def test_aasd_014_init_self_managed(self) -> None:
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.Entity("TestEntity", model.EntityType.SELF_MANAGED_ENTITY)
        self.assertEqual("A self-managed entity has to have a globalAssetId or a specificAssetId (Constraint AASd-014)",
                         str(cm.exception))
        model.Entity("TestEntity", model.EntityType.SELF_MANAGED_ENTITY, global_asset_id="https://acplt.org/TestAsset")
        model.Entity("TestEntity", model.EntityType.SELF_MANAGED_ENTITY,
                     specific_asset_id=(model.SpecificAssetId("test", "test"),))
        model.Entity("TestEntity", model.EntityType.SELF_MANAGED_ENTITY, global_asset_id="https://acplt.org/TestAsset",
                     specific_asset_id=(model.SpecificAssetId("test", "test"),))

    def test_aasd_014_init_co_managed(self) -> None:
        model.Entity("TestEntity", model.EntityType.CO_MANAGED_ENTITY)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.Entity("TestEntity", model.EntityType.CO_MANAGED_ENTITY,
                         global_asset_id="https://acplt.org/TestAsset")
        self.assertEqual("A co-managed entity has to have neither a globalAssetId nor a specificAssetId "
                         "(Constraint AASd-014)", str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.Entity("TestEntity", model.EntityType.CO_MANAGED_ENTITY,
                         specific_asset_id=(model.SpecificAssetId("test", "test"),))
        self.assertEqual("A co-managed entity has to have neither a globalAssetId nor a specificAssetId "
                         "(Constraint AASd-014)", str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.Entity("TestEntity", model.EntityType.CO_MANAGED_ENTITY,
                         global_asset_id="https://acplt.org/TestAsset",
                         specific_asset_id=(model.SpecificAssetId("test", "test"),))
        self.assertEqual("A co-managed entity has to have neither a globalAssetId nor a specificAssetId "
                         "(Constraint AASd-014)", str(cm.exception))

    def test_aasd_014_set_self_managed(self) -> None:
        entity = model.Entity("TestEntity", model.EntityType.SELF_MANAGED_ENTITY,
                              global_asset_id="https://acplt.org/TestAsset",
                              specific_asset_id=(model.SpecificAssetId("test", "test"),))
        entity.global_asset_id = None
        with self.assertRaises(model.AASConstraintViolation) as cm:
            entity.specific_asset_id = model.ConstrainedList(())
        self.assertEqual("A self-managed entity has to have a globalAssetId or a specificAssetId (Constraint AASd-014)",
                         str(cm.exception))

        entity = model.Entity("TestEntity", model.EntityType.SELF_MANAGED_ENTITY,
                              global_asset_id="https://acplt.org/TestAsset",
                              specific_asset_id=(model.SpecificAssetId("test", "test"),))
        entity.specific_asset_id = model.ConstrainedList(())
        with self.assertRaises(model.AASConstraintViolation) as cm:
            entity.global_asset_id = None
        self.assertEqual("A self-managed entity has to have a globalAssetId or a specificAssetId (Constraint AASd-014)",
                         str(cm.exception))

    def test_aasd_014_set_co_managed(self) -> None:
        entity = model.Entity("TestEntity", model.EntityType.CO_MANAGED_ENTITY)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            entity.global_asset_id = "https://acplt.org/TestAsset"
        self.assertEqual("A co-managed entity has to have neither a globalAssetId nor a specificAssetId "
                         "(Constraint AASd-014)", str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            entity.specific_asset_id = model.ConstrainedList((model.SpecificAssetId("test", "test"),))
        self.assertEqual("A co-managed entity has to have neither a globalAssetId nor a specificAssetId "
                         "(Constraint AASd-014)", str(cm.exception))

    def test_aasd_014_specific_asset_id_add_self_managed(self) -> None:
        entity = model.Entity("TestEntity", model.EntityType.SELF_MANAGED_ENTITY,
                              global_asset_id="https://acplt.org/TestAsset")
        specific_asset_id1 = model.SpecificAssetId("test", "test")
        specific_asset_id2 = model.SpecificAssetId("test", "test")
        entity.specific_asset_id.append(specific_asset_id1)
        entity.specific_asset_id.extend((specific_asset_id2,))
        self.assertIs(entity.specific_asset_id[0], specific_asset_id1)
        self.assertIs(entity.specific_asset_id[1], specific_asset_id2)

    def test_aasd_014_specific_asset_id_add_co_managed(self) -> None:
        entity = model.Entity("TestEntity", model.EntityType.CO_MANAGED_ENTITY)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            entity.specific_asset_id.append(model.SpecificAssetId("test", "test"))
        self.assertEqual("A co-managed entity has to have neither a globalAssetId nor a specificAssetId "
                         "(Constraint AASd-014)", str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            entity.specific_asset_id.extend((model.SpecificAssetId("test", "test"),))
        self.assertEqual("A co-managed entity has to have neither a globalAssetId nor a specificAssetId "
                         "(Constraint AASd-014)", str(cm.exception))

    def test_assd_014_specific_asset_id_set_self_managed(self) -> None:
        entity = model.Entity("TestEntity", model.EntityType.SELF_MANAGED_ENTITY,
                              specific_asset_id=(model.SpecificAssetId("test", "test"),))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            entity.specific_asset_id[:] = ()
        self.assertEqual("A self-managed entity has to have a globalAssetId or a specificAssetId (Constraint AASd-014)",
                         str(cm.exception))
        specific_asset_id = model.SpecificAssetId("test", "test")
        self.assertIsNot(entity.specific_asset_id[0], specific_asset_id)
        entity.specific_asset_id[:] = (specific_asset_id,)
        self.assertIs(entity.specific_asset_id[0], specific_asset_id)
        entity.specific_asset_id[0] = model.SpecificAssetId("test", "test")
        self.assertIsNot(entity.specific_asset_id[0], specific_asset_id)

    def test_assd_014_specific_asset_id_set_co_managed(self) -> None:
        entity = model.Entity("TestEntity", model.EntityType.CO_MANAGED_ENTITY)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            entity.specific_asset_id[:] = (model.SpecificAssetId("test", "test"),)
        self.assertEqual("A co-managed entity has to have neither a globalAssetId nor a specificAssetId "
                         "(Constraint AASd-014)", str(cm.exception))
        entity.specific_asset_id[:] = ()

    def test_aasd_014_specific_asset_id_del_self_managed(self) -> None:
        specific_asset_id = model.SpecificAssetId("test", "test")
        entity = model.Entity("TestEntity", model.EntityType.SELF_MANAGED_ENTITY,
                              specific_asset_id=(model.SpecificAssetId("test", "test"),
                                                 specific_asset_id))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            del entity.specific_asset_id[:]
        self.assertEqual("A self-managed entity has to have a globalAssetId or a specificAssetId (Constraint AASd-014)",
                         str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            entity.specific_asset_id.clear()
        self.assertEqual("A self-managed entity has to have a globalAssetId or a specificAssetId (Constraint AASd-014)",
                         str(cm.exception))
        self.assertIsNot(entity.specific_asset_id[0], specific_asset_id)
        del entity.specific_asset_id[0]
        self.assertIs(entity.specific_asset_id[0], specific_asset_id)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            del entity.specific_asset_id[0]
        self.assertEqual("A self-managed entity has to have a globalAssetId or a specificAssetId (Constraint AASd-014)",
                         str(cm.exception))

    def test_aasd_014_specific_asset_id_del_co_managed(self) -> None:
        entity = model.Entity("TestEntity", model.EntityType.CO_MANAGED_ENTITY)
        del entity.specific_asset_id[:]


class PropertyTest(unittest.TestCase):
    def test_set_value(self):
        property = model.Property('test', model.datatypes.Int, 2)
        self.assertEqual(property.value, 2)
        property.value = None
        self.assertIsNone(property.value)


class RangeTest(unittest.TestCase):
    def test_set_min_max(self):
        range = model.Range('test', model.datatypes.Int, 2, 5)
        self.assertEqual(range.min, 2)
        self.assertEqual(range.max, 5)
        range.min = None
        self.assertIsNone(range.min)
        range.max = None
        self.assertIsNone(range.max)


class SubmodelElementListTest(unittest.TestCase):
    def test_constraints(self):
        # AASd-107
        mlp = model.MultiLanguageProperty(None, semantic_id=model.ExternalReference(
            (model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:invalid"),)
        ))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.SubmodelElementList("test_list", model.MultiLanguageProperty, {mlp},
                                      semantic_id_list_element=model.ExternalReference((
                                          model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:test"),)))
        self.assertEqual("If semantic_id_list_element=ExternalReference(key=(Key(type=GLOBAL_REFERENCE, "
                         "value=urn:x-test:test),)) is specified all first level children must have "
                         "the same semantic_id, got MultiLanguageProperty with "
                         "semantic_id=ExternalReference(key=(Key(type=GLOBAL_REFERENCE, value=urn:x-test:invalid),)) "
                         "(Constraint AASd-107)", str(cm.exception))
        sel = model.SubmodelElementList("test_list", model.MultiLanguageProperty, {mlp},
                                        semantic_id_list_element=model.ExternalReference((
                                            model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:invalid"),)))
        sel.value.clear()
        model.SubmodelElementList("test_list", model.MultiLanguageProperty, {mlp}, semantic_id_list_element=None)
        mlp = model.MultiLanguageProperty(None)
        model.SubmodelElementList("test_list", model.MultiLanguageProperty, {mlp},
                                  semantic_id_list_element=model.ExternalReference((
                                      model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:invalid"),)))

        # AASd-108
        are = model.AnnotatedRelationshipElement(
            None,
            model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:test-first"),)),
            model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:test-second"),))
        )
        # This tests checks if subclasses of the required type are rejected in a SubmodelElementList.
        # Thus, a requirement is that AnnotatedRelationshipElement is a subclass of RelationshipElement:
        self.assertIsInstance(are, model.RelationshipElement)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.SubmodelElementList("test_list", model.RelationshipElement, {are})
        self.assertEqual("All first level elements must be of the type specified in "
                         "type_value_list_element=RelationshipElement, got AnnotatedRelationshipElement "
                         "(Constraint AASd-108)", str(cm.exception))
        model.SubmodelElementList("test_list", model.AnnotatedRelationshipElement, {are})

        # AASd-109
        # Pass an item to the constructor to assert that this constraint is checked before items are added.
        prop = model.Property(None, model.datatypes.Int, 0)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.SubmodelElementList("test_list", model.Property, [prop])
        self.assertEqual("type_value_list_element=Property, but value_type_list_element is not set! "
                         "(Constraint AASd-109)", str(cm.exception))
        model.SubmodelElementList("test_list", model.Property, [prop], value_type_list_element=model.datatypes.Int)

        prop = model.Property(None, model.datatypes.String)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.SubmodelElementList("test_list", model.Property, {prop}, value_type_list_element=model.datatypes.Int)
        self.assertEqual("All first level elements must have the value_type specified by value_type_list_element=Int, "
                         "got Property with value_type=str (Constraint AASd-109)", str(cm.exception))
        model.SubmodelElementList("test_list", model.Property, {prop}, value_type_list_element=model.datatypes.String)

        # AASd-114
        semantic_id1 = model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:test"),))
        semantic_id2 = model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE, "urn:x-test:different"),))
        mlp1 = model.MultiLanguageProperty(None, semantic_id=semantic_id1)
        mlp2 = model.MultiLanguageProperty(None, semantic_id=semantic_id2)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.SubmodelElementList("test_list", model.MultiLanguageProperty, [mlp1, mlp2])
        self.assertEqual("Element to be added MultiLanguageProperty has semantic_id "
                         "ExternalReference(key=(Key(type=GLOBAL_REFERENCE, value=urn:x-test:different),)), "
                         "while already contained element MultiLanguageProperty[test_list[0]] has semantic_id "
                         "ExternalReference(key=(Key(type=GLOBAL_REFERENCE, value=urn:x-test:test),)), "
                         "which aren't equal. (Constraint AASd-114)", str(cm.exception))
        mlp2.semantic_id = semantic_id1
        model.SubmodelElementList("test_list", model.MultiLanguageProperty, [mlp1, mlp2])

        # AASd-120
        mlp = model.MultiLanguageProperty("mlp")
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.SubmodelElementList("test_list", model.MultiLanguageProperty, [mlp])
        self.assertEqual("Objects with an id_short may not be added to a SubmodelElementList, got "
                         "MultiLanguageProperty[mlp] with id_short=mlp (Constraint AASd-120)", str(cm.exception))
        mlp.id_short = None
        model.SubmodelElementList("test_list", model.MultiLanguageProperty, [mlp])
        with self.assertRaises(model.AASConstraintViolation) as cm:
            mlp.id_short = "mlp"
        self.assertEqual("id_short of MultiLanguageProperty[test_list[0]] cannot be set, because it is "
                         "contained in a SubmodelElementList[test_list] (Constraint AASd-120)", str(cm.exception))

    def test_aasd_108_add_set(self):
        prop = model.Property(None, model.datatypes.Int)
        mlp1 = model.MultiLanguageProperty(None)
        mlp2 = model.MultiLanguageProperty(None)
        list_ = model.SubmodelElementList("test_list", model.MultiLanguageProperty)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            list_.add_referable(prop)
        self.assertEqual("All first level elements must be of the type specified in type_value_list_element="
                         "MultiLanguageProperty, got Property (Constraint AASd-108)", str(cm.exception))
        list_.add_referable(mlp1)

        with self.assertRaises(model.AASConstraintViolation) as cm:
            list_.value.add(prop)
        self.assertEqual("All first level elements must be of the type specified in type_value_list_element="
                         "MultiLanguageProperty, got Property (Constraint AASd-108)", str(cm.exception))
        list_.value.add(mlp2)

        with self.assertRaises(model.AASConstraintViolation) as cm:
            list_.value[0] = prop
        self.assertEqual("All first level elements must be of the type specified in type_value_list_element="
                         "MultiLanguageProperty, got Property (Constraint AASd-108)", str(cm.exception))
        del list_.value[1]
        list_.value[0] = mlp2

        with self.assertRaises(model.AASConstraintViolation) as cm:
            list_.value = [mlp1, prop]
        self.assertEqual("All first level elements must be of the type specified in type_value_list_element="
                         "MultiLanguageProperty, got Property (Constraint AASd-108)", str(cm.exception))
        list_.value = [mlp1, mlp2]

    def test_immutable_attributes(self):
        list_ = model.SubmodelElementList("test_list", model.File)
        with self.assertRaises(AttributeError):
            list_.type_value_list_element = model.MultiLanguageProperty
        with self.assertRaises(AttributeError):
            list_.order_relevant = False
        with self.assertRaises(AttributeError):
            list_.semantic_id_list_element = model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE, "t"),))
        with self.assertRaises(AttributeError):
            list_.value_type_list_element = model.datatypes.Int


class BasicEventElementTest(unittest.TestCase):
    def test_constraints(self):
        with self.assertRaises(ValueError) as cm:
            model.BasicEventElement("test_basic_event_element",
                                    model.ModelReference((model.Key(model.KeyTypes.ASSET_ADMINISTRATION_SHELL,
                                                                    "urn:x-test:AssetAdministrationShell"),),
                                                         model.AssetAdministrationShell),
                                    model.Direction.INPUT,
                                    model.StateOfEvent.ON,
                                    max_interval=model.datatypes.Duration(minutes=10))
        self.assertEqual("max_interval is not applicable if direction = input!", str(cm.exception))
        bee = model.BasicEventElement("test_basic_event_element",
                                      model.ModelReference((model.Key(model.KeyTypes.ASSET_ADMINISTRATION_SHELL,
                                                            "urn:x-test:AssetAdministrationShell"),),
                                                           model.AssetAdministrationShell),
                                      model.Direction.OUTPUT,
                                      model.StateOfEvent.ON,
                                      max_interval=model.datatypes.Duration(minutes=10))
        with self.assertRaises(ValueError) as cm:
            bee.direction = model.Direction.INPUT
        self.assertEqual("max_interval is not applicable if direction = input!", str(cm.exception))

        bee.max_interval = None
        bee.direction = model.Direction.INPUT

        timestamp_tzinfo = model.datatypes.DateTime(2022, 11, 13, 23, 45, 30, 123456,
                                                    dateutil.tz.gettz("Europe/Berlin"))
        with self.assertRaises(ValueError) as cm:
            bee.last_update = timestamp_tzinfo
        self.assertEqual("last_update must be specified in UTC!", str(cm.exception))

        timestamp = model.datatypes.DateTime(2022, 11, 13, 23, 45, 30, 123456)
        with self.assertRaises(ValueError) as cm:
            bee.last_update = timestamp
        self.assertEqual("last_update must be specified in UTC!", str(cm.exception))

        timestamp_tzinfo_utc = model.datatypes.DateTime(2022, 11, 13, 23, 45, 30, 123456, dateutil.tz.UTC)
        bee.last_update = timestamp_tzinfo_utc
