# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
Module for the creation of an :class:`ObjectStore <basyx.aas.model.provider.DictObjectStore>` with missing object
attribute combination for testing the serialization
"""
import datetime
import logging

from ... import model
from ._helper import AASDataChecker

logger = logging.getLogger(__name__)


def create_full_example() -> model.DictObjectStore:
    """
    Creates an :class:`~basyx.aas.model.provider.DictObjectStore` containing an example
    :class:`~basyx.aas.model.submodel.Submodel`, an example :class:`~basyx.aas.model.concept.ConceptDescription` and an
    example :class:`~basyx.aas.model.aas.AssetAdministrationShell`

    :return: :class:`basyx.aas.model.provider.DictObjectStore`
    """
    obj_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    obj_store.add(create_example_submodel())
    obj_store.add(create_example_concept_description())
    obj_store.add(create_example_asset_administration_shell())
    return obj_store


def create_example_submodel() -> model.Submodel:
    """
    Creates an example :class:`~basyx.aas.model.submodel.Submodel` containing all kind of
    :class:`~basyx.aas.model.submodel.SubmodelElement`  objects

    :return: example submodel
    """
    qualifier = model.Qualifier(
        type_='http://acplt.org/Qualifier/ExampleQualifier',
        value_type=model.datatypes.String)

    submodel_element_property = model.Property(
        id_short='ExampleProperty',
        value_type=model.datatypes.String,
        value='exampleValue',
        value_id=None,  # TODO
        category='CONSTANT',
        description=model.MultiLanguageTextType({'en-US': 'Example Property object',
                                                 'de': 'Beispiel Property Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Properties/ExampleProperty'),)),
        qualifier={qualifier})

    submodel_element_multi_language_property = model.MultiLanguageProperty(
        id_short='ExampleMultiLanguageProperty',
        value=model.MultiLanguageTextType({'en-US': 'Example value of a MultiLanguageProperty element',
                                           'de': 'Beispielwert für ein MultiLanguageProperty-Element'}),
        value_id=None,  # TODO
        category='CONSTANT',
        description=model.MultiLanguageTextType({'en-US': 'Example MultiLanguageProperty object',
                                                 'de': 'Beispiel MultiLanguageProperty Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/MultiLanguageProperties/'
                                                             'ExampleMultiLanguageProperty'),)),
        qualifier=())

    submodel_element_range = model.Range(
        id_short='ExampleRange',
        value_type=model.datatypes.Int,
        min=0,
        max=100,
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example Range object',
                                                 'de': 'Beispiel Range Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Ranges/ExampleRange'),)),
        qualifier=())

    submodel_element_blob = model.Blob(
        id_short='ExampleBlob',
        content_type='application/pdf',
        value=bytearray(b'\x01\x02\x03\x04\x05'),
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example Blob object',
                                                 'de': 'Beispiel Blob Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Blobs/ExampleBlob'),)),
        qualifier=())

    submodel_element_file = model.File(
        id_short='ExampleFile',
        content_type='application/pdf',
        value='/TestFile.pdf',
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example File object',
                                                 'de': 'Beispiel File Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Files/ExampleFile'),)),
        qualifier=())

    submodel_element_reference_element = model.ReferenceElement(
        id_short='ExampleReferenceElement',
        value=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                              value='http://acplt.org/Test_Submodel'),
                                    model.Key(type_=model.KeyTypes.PROPERTY,
                                              value='ExampleProperty'),), model.Submodel),
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example Reference Element object',
                                                 'de': 'Beispiel Reference Element Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(
            type_=model.KeyTypes.GLOBAL_REFERENCE,
            value='http://acplt.org/ReferenceElements/ExampleReferenceElement'
        ),)),
        qualifier=())

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
                                    model.Property),
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example RelationshipElement object',
                                                 'de': 'Beispiel RelationshipElement Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/RelationshipElements/'
                                                             'ExampleRelationshipElement'),)),
        qualifier=())

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
                                    model.Property),
        annotation={model.Property(id_short="ExampleAnnotatedProperty",
                                   value_type=model.datatypes.String,
                                   value='exampleValue',
                                   category="PARAMETER",
                                   parent=None),
                    model.Range(id_short="ExampleAnnotatedRange",
                                value_type=model.datatypes.Integer,
                                min=1,
                                max=5,
                                category="PARAMETER",
                                parent=None)
                    },
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example AnnotatedRelationshipElement object',
                                                 'de': 'Beispiel AnnotatedRelationshipElement Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/RelationshipElements/'
                                                             'ExampleAnnotatedRelationshipElement'),)),
        qualifier=())

    operation_variable_property = model.Property(
        id_short='ExampleProperty',
        value_type=model.datatypes.String,
        value='exampleValue',
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        display_name=model.MultiLanguageNameType({'en-US': 'ExampleProperty',
                                                  'de': 'BeispielProperty'}),
        category='CONSTANT',
        description=model.MultiLanguageTextType({'en-US': 'Example Property object',
                                                 'de': 'Beispiel Property Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Properties/ExampleProperty'),)),
        qualifier=())

    input_variable_property = model.Property(
        id_short='ExamplePropertyInput',
        value_type=model.datatypes.String,
        value='exampleValue',
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        display_name=model.MultiLanguageNameType({'en-US': 'ExampleProperty',
                                                  'de': 'BeispielProperty'}),
        category='CONSTANT',
        description=model.MultiLanguageTextType({'en-US': 'Example Property object',
                                                 'de': 'Beispiel Property Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Properties/ExamplePropertyInput'),)),
        qualifier=())

    output_variable_property = model.Property(
        id_short='ExamplePropertyOutput',
        value_type=model.datatypes.String,
        value='exampleValue',
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        display_name=model.MultiLanguageNameType({'en-US': 'ExampleProperty',
                                                  'de': 'BeispielProperty'}),
        category='CONSTANT',
        description=model.MultiLanguageTextType({'en-US': 'Example Property object',
                                                 'de': 'Beispiel Property Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Properties/ExamplePropertyOutput'),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=())

    in_output_variable_property = model.Property(
        id_short='ExamplePropertyInOutput',
        value_type=model.datatypes.String,
        value='exampleValue',
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        display_name=model.MultiLanguageNameType({'en-US': 'ExampleProperty',
                                                  'de': 'BeispielProperty'}),
        category='CONSTANT',
        description=model.MultiLanguageTextType({'en-US': 'Example Property object',
                                                 'de': 'Beispiel Property Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Properties/ExamplePropertyInOutput'),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=())

    submodel_element_operation = model.Operation(
        id_short='ExampleOperation',
        input_variable=[input_variable_property],
        output_variable=[output_variable_property],
        in_output_variable=[in_output_variable_property],
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example Operation object',
                                                 'de': 'Beispiel Operation Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Operations/'
                                                             'ExampleOperation'),)),
        qualifier=())

    submodel_element_capability = model.Capability(
        id_short='ExampleCapability',
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example Capability object',
                                                 'de': 'Beispiel Capability Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Capabilities/'
                                                             'ExampleCapability'),)),
        qualifier=())

    submodel_element_basic_event_element = model.BasicEventElement(
        id_short='ExampleBasicEventElement',
        observed=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                 value='http://acplt.org/Test_Submodel'),
                                       model.Key(type_=model.KeyTypes.PROPERTY,
                                                 value='ExampleProperty'),),
                                      model.Property),
        direction=model.Direction.OUTPUT,
        state=model.StateOfEvent.ON,
        message_topic='ExampleTopic',
        message_broker=model.ModelReference((model.Key(model.KeyTypes.SUBMODEL,
                                                       "http://acplt.org/ExampleMessageBroker"),),
                                            model.Submodel),
        last_update=model.datatypes.DateTime(2022, 11, 12, 23, 50, 23, 123456, datetime.timezone.utc),
        min_interval=model.datatypes.Duration(microseconds=1),
        max_interval=model.datatypes.Duration(years=1, months=2, days=3, hours=4, minutes=5, seconds=6,
                                              microseconds=123456),
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example BasicEventElement object',
                                                 'de': 'Beispiel BasicEventElement Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Events/ExampleBasicEventElement'),)),
        qualifier=())

    submodel_element_submodel_element_collection = model.SubmodelElementCollection(
        id_short='ExampleSubmodelCollection',
        value=(submodel_element_blob,
               submodel_element_file,
               submodel_element_multi_language_property,
               submodel_element_property,
               submodel_element_range,
               submodel_element_reference_element),
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example SubmodelElementCollection object',
                                                 'de': 'Beispiel SubmodelElementCollection Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/SubmodelElementCollections/'
                                                             'ExampleSubmodelElementCollection'),)),
        qualifier=())

    submodel = model.Submodel(
        id_='https://acplt.org/Test_Submodel_Missing',
        submodel_element=(submodel_element_relationship_element,
                          submodel_element_annotated_relationship_element,
                          submodel_element_operation,
                          submodel_element_capability,
                          submodel_element_basic_event_element,
                          submodel_element_submodel_element_collection),
        id_short='TestSubmodel',
        category=None,
        description=model.MultiLanguageTextType({'en-US': 'An example submodel for the test application',
                                                 'de': 'Ein Beispiel-Teilmodell für eine Test-Anwendung'}),
        parent=None,
        administration=model.AdministrativeInformation(version='9',
                                                       revision='0'),
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/SubmodelTemplates/'
                                                             'ExampleSubmodel'),)),
        qualifier=(),
        kind=model.ModellingKind.INSTANCE)
    return submodel


def create_example_concept_description() -> model.ConceptDescription:
    """
    Creates an example :class:`~basyx.aas.model.concept.ConceptDescription`

    :return: example concept description
    """
    concept_description = model.ConceptDescription(
        id_='https://acplt.org/Test_ConceptDescription_Missing',
        is_case_of=None,
        id_short='TestConceptDescription',
        category=None,
        description=model.MultiLanguageTextType({'en-US': 'An example concept description for the test application',
                                                 'de': 'Ein Beispiel-ConceptDescription für eine Test-Anwendung'}),
        parent=None,
        administration=model.AdministrativeInformation(version='9',
                                                       revision='0'))
    return concept_description


def create_example_asset_administration_shell() -> model.AssetAdministrationShell:
    """
    Creates an example :class:`~basyx.aas.model.aas.AssetAdministrationShell` containing a reference to an example
    :class:`~basyx.aas.model.submodel.Submodel`

    :return: example asset administration shell
    """

    resource = model.Resource(
        content_type='application/pdf',
        path='file:///TestFile.pdf')

    asset_information = model.AssetInformation(
        asset_kind=model.AssetKind.INSTANCE,
        global_asset_id='http://acplt.org/Test_Asset_Missing/',
        specific_asset_id={model.SpecificAssetId(name="TestKey", value="TestValue",
                                                 external_subject_id=model.ExternalReference(
                                                            (model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                                       value='http://acplt.org/SpecificAssetId/'),)))},
        default_thumbnail=resource)

    asset_administration_shell = model.AssetAdministrationShell(
        asset_information=asset_information,
        id_='https://acplt.org/Test_AssetAdministrationShell_Missing',
        id_short='TestAssetAdministrationShell',
        category=None,
        description=model.MultiLanguageTextType({'en-US': 'An Example Asset Administration Shell for the test '
                                                          'application',
                                                 'de': 'Ein Beispiel-Verwaltungsschale für eine Test-Anwendung'}),
        parent=None,
        administration=model.AdministrativeInformation(version='9',
                                                       revision='0'),
        submodel={model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                  value='https://acplt.org/Test_Submodel_Missing'),),
                                       model.Submodel)},
        derived_from=None)
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


def check_example_submodel(checker: AASDataChecker, submodel: model.Submodel) -> None:
    expected_submodel = create_example_submodel()
    checker.check_submodel_equal(submodel, expected_submodel)


def check_full_example(checker: AASDataChecker, obj_store: model.DictObjectStore) -> None:
    expected_data = create_full_example()
    checker.check_object_store(obj_store, expected_data)
