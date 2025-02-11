# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
Module for the creation of an :class:`ObjectStore <basyx.aas.model.provider.DictObjectStore>` with an example
:class:`~basyx.aas.model.aas.AssetAdministrationShell`, example :class:`Submodels <basyx.aas.model.submodel.Submodel>`
and an example :class:`~basyx.aas.model.concept.ConceptDescription`. All objects only contain mandatory attributes.

To get this object store use the function
:meth:`~basyx.aas.examples.data.example_aas_mandatory_attributes.create_full_example`. If you want to get single example
objects or want to get more information use the other functions.
"""
import logging

from ... import model
from ._helper import AASDataChecker

logger = logging.getLogger(__name__)


def create_full_example() -> model.DictObjectStore:
    """
    Creates an :class:`~.basyx.aas.model.provider.DictObjectStore` which is filled with an example
    :class:`~basyx.aas.model.submodel.Submodel`, :class:`~basyx.aas.model.concept.ConceptDescription`
    and :class:`~basyx.aas.model.aas.AssetAdministrationShell` using the functions of this module

    :return: :class:`~basyx.aas.model.provider.DictObjectStore`
    """
    obj_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    obj_store.add(create_example_submodel())
    obj_store.add(create_example_empty_submodel())
    obj_store.add(create_example_concept_description())
    obj_store.add(create_example_asset_administration_shell())
    obj_store.add(create_example_empty_asset_administration_shell())
    return obj_store


def create_example_submodel() -> model.Submodel:
    """
    Creates an example :class:`~basyx.aas.model.submodel.Submodel` containing all kind of
    :class:`~basyx.aas.model.submodel.SubmodelElement` objects where only mandatory attributes are set

    :return: example submodel
    """
    submodel_element_property = model.Property(
        id_short='ExampleProperty',
        category="PARAMETER",
        value_type=model.datatypes.String)

    submodel_element_multi_language_property = model.MultiLanguageProperty(
        category="PARAMETER",
        id_short='ExampleMultiLanguageProperty')

    submodel_element_range = model.Range(
        id_short='ExampleRange',
        category="PARAMETER",
        value_type=model.datatypes.Int)

    submodel_element_blob = model.Blob(
        id_short='ExampleBlob',
        content_type='application/pdf')

    submodel_element_file = model.File(
        id_short='ExampleFile',
        content_type='application/pdf')

    submodel_element_reference_element = model.ReferenceElement(
        category="PARAMETER",
        id_short='ExampleReferenceElement')

    submodel_element_relationship_element = model.RelationshipElement(
        id_short='ExampleRelationshipElement',
        first=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                              value='http://acplt.org/Test_Submodel'),
                                    model.Key(type_=model.KeyTypes.PROPERTY,
                                              value='ExampleProperty'),),
                                   model.Property),
        second=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                               value='http://acplt.org/Test_Submodel'),
                                     model.Key(type_=model.KeyTypes.PROPERTY,
                                               value='ExampleProperty'),),
                                    model.Property))

    submodel_element_annotated_relationship_element = model.AnnotatedRelationshipElement(
        id_short='ExampleAnnotatedRelationshipElement',
        first=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                              value='http://acplt.org/Test_Submodel'),
                                    model.Key(type_=model.KeyTypes.PROPERTY,
                                              value='ExampleProperty'),),
                                   model.Property),
        second=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                               value='http://acplt.org/Test_Submodel'),
                                     model.Key(type_=model.KeyTypes.PROPERTY,
                                               value='ExampleProperty'),),
                                    model.Property))

    submodel_element_operation = model.Operation(
        id_short='ExampleOperation')

    submodel_element_capability = model.Capability(
        id_short='ExampleCapability')

    submodel_element_basic_event_element = model.BasicEventElement(
        id_short='ExampleBasicEventElement',
        observed=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL, value='http://acplt.org/Test_Submodel'),
                                       model.Key(type_=model.KeyTypes.PROPERTY, value='ExampleProperty'),),
                                      model.Property),
        direction=model.Direction.INPUT,
        state=model.StateOfEvent.OFF)

    submodel_element_submodel_element_collection = model.SubmodelElementCollection(
        id_short=None,
        value=(submodel_element_blob,
               submodel_element_file,
               submodel_element_multi_language_property,
               submodel_element_property,
               submodel_element_range,
               submodel_element_reference_element))

    submodel_element_submodel_element_collection_2 = model.SubmodelElementCollection(
        id_short=None,
        value=())

    submodel_element_submodel_element_list = model.SubmodelElementList(
        id_short='ExampleSubmodelList',
        type_value_list_element=model.SubmodelElementCollection,
        value=(submodel_element_submodel_element_collection, submodel_element_submodel_element_collection_2))

    submodel_element_submodel_element_list_2 = model.SubmodelElementList(
        id_short='ExampleSubmodelList2',
        type_value_list_element=model.Capability,
        value=())

    submodel = model.Submodel(
        id_='https://acplt.org/Test_Submodel_Mandatory',
        submodel_element=(submodel_element_relationship_element,
                          submodel_element_annotated_relationship_element,
                          submodel_element_operation,
                          submodel_element_capability,
                          submodel_element_basic_event_element,
                          submodel_element_submodel_element_list,
                          submodel_element_submodel_element_list_2))
    return submodel


def create_example_empty_submodel() -> model.Submodel:
    """
    Creates an example empty :class:`~basyx.aas.model.submodel.Submodel` where only the id attribute is set

    :return: example submodel
    """
    return model.Submodel(
        id_='https://acplt.org/Test_Submodel2_Mandatory')


def create_example_concept_description() -> model.ConceptDescription:
    """
    Creates an example :class:`~basyx.aas.model.concept.ConceptDescription` where only the id attribute is set

    :return: example concept description
    """
    concept_description = model.ConceptDescription(
        id_='https://acplt.org/Test_ConceptDescription_Mandatory')
    return concept_description


def create_example_asset_administration_shell() -> \
        model.AssetAdministrationShell:
    """
    Creates an example :class:`~basyx.aas.model.aas.AssetAdministrationShell` containing references to the example,
    the example :class:`~Submodels <basyx.aas.model.submodel.Submodel>`.

    :return: example asset administration shell
    """
    asset_information = model.AssetInformation(
        asset_kind=model.AssetKind.INSTANCE,
        global_asset_id='http://acplt.org/Test_Asset_Mandatory/')

    asset_administration_shell = model.AssetAdministrationShell(
        asset_information=asset_information,
        id_='https://acplt.org/Test_AssetAdministrationShell_Mandatory',
        submodel={model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                  value='https://acplt.org/Test_Submodel_Mandatory'),),
                                       model.Submodel),
                  model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                  value='https://acplt.org/Test_Submodel2_Mandatory'),),
                                       model.Submodel)},)
    return asset_administration_shell


def create_example_empty_asset_administration_shell() -> model.AssetAdministrationShell:
    """
    Creates an example empty :class:`~basyx.aas.model.aas.AssetAdministrationShell` with just
    an empty :class:`~basyx.aas.model.aas.AssetInformation` and an :class:`~basyx.aas.model.base.Identifier`

    :return: example :class:`~basyx.aas.model.aas.AssetAdministrationShell`
    """
    asset_administration_shell = model.AssetAdministrationShell(
        asset_information=model.AssetInformation(
            global_asset_id='http://acplt.org/TestAsset2_Mandatory/'),
        id_='https://acplt.org/Test_AssetAdministrationShell2_Mandatory')
    return asset_administration_shell


##############################################################################
# check functions for checking if a given object is the same as the example #
##############################################################################
def check_example_concept_description(checker: AASDataChecker, concept_description: model.ConceptDescription) -> None:
    expected_concept_description = create_example_concept_description()
    checker.check_concept_description_equal(concept_description, expected_concept_description)


def check_example_asset_administration_shell(checker: AASDataChecker, shell: model.AssetAdministrationShell) -> None:
    expected_shell = create_example_asset_administration_shell()
    checker.check_asset_administration_shell_equal(shell, expected_shell)


def check_example_empty_asset_administration_shell(checker: AASDataChecker, shell: model.AssetAdministrationShell) \
        -> None:
    expected_shell = create_example_empty_asset_administration_shell()
    checker.check_asset_administration_shell_equal(shell, expected_shell)


def check_example_submodel(checker: AASDataChecker, submodel: model.Submodel) -> None:
    expected_submodel = create_example_submodel()
    checker.check_submodel_equal(submodel, expected_submodel)


def check_example_empty_submodel(checker: AASDataChecker, submodel: model.Submodel) -> None:
    expected_submodel = create_example_empty_submodel()
    checker.check_submodel_equal(submodel, expected_submodel)


def check_full_example(checker: AASDataChecker, obj_store: model.DictObjectStore) -> None:
    expected_data = create_full_example()
    checker.check_object_store(obj_store, expected_data)
