# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
Module for the creation of an :class:`ObjectStore <basyx.aas.model.provider.DictObjectStore>` with an example asset
administration shell and example submodels and an example concept description

To get this object store use the function :meth:`~basyx.aas.examples.data.example_aas.create_full_example`.
If you want to get single example objects or want to get more information use the other functions.
"""
import datetime
import logging

from ._helper import AASDataChecker
from ... import model

logger = logging.getLogger(__name__)


_embedded_data_specification_iec61360 = model.EmbeddedDataSpecification(
    data_specification=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                          value='https://admin-shell.io/DataSpecificationTemplates/'
                                                                'DataSpecificationIEC61360/3/0'),)),
    data_specification_content=model.DataSpecificationIEC61360(preferred_name=model.PreferredNameTypeIEC61360({
        'de': 'Test Specification',
        'en-US': 'TestSpecification'
    }), data_type=model.DataTypeIEC61360.REAL_MEASURE,
        definition=model.DefinitionTypeIEC61360({'de': 'Dies ist eine Data Specification für Testzwecke',
                                                 'en-US': 'This is a DataSpecification for testing purposes'}),
        short_name=model.ShortNameTypeIEC61360({'de': 'Test Spec', 'en-US': 'TestSpec'}), unit='SpaceUnit',
        unit_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                   value='http://acplt.org/Units/SpaceUnit'),)),
        source_of_definition='http://acplt.org/DataSpec/ExampleDef', symbol='SU', value_format="M",
        value_list={
            model.ValueReferencePair(
                value='exampleValue',
                value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                            value='http://acplt.org/ValueId/ExampleValueId'),)), ),
            model.ValueReferencePair(
                value='exampleValue2',
                value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                            value='http://acplt.org/ValueId/ExampleValueId2'),)), )},
        value="TEST", level_types={model.IEC61360LevelType.MIN, model.IEC61360LevelType.MAX})
)


def create_full_example() -> model.DictObjectStore:
    """
    Creates an object store which is filled with an example :class:`~basyx.aas.model.submodel.Submodel`,
    :class:`~basyx.aas.model.concept.ConceptDescription` and :class:`~basyx.aas.model.aas.AssetAdministrationShell`
    using the functions of this module

    :return: :class:`~basyx.aas.model.provider.DictObjectStore`
    """
    obj_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    obj_store.add(create_example_asset_identification_submodel())
    obj_store.add(create_example_bill_of_material_submodel())
    obj_store.add(create_example_submodel())
    obj_store.add(create_example_concept_description())
    obj_store.add(create_example_asset_administration_shell())
    return obj_store


def create_example_asset_identification_submodel() -> model.Submodel:
    """
    Creates a :class:`~basyx.aas.model.submodel.Submodel` containing two :class:`~basyx.aas.model.submodel.Property`
    elements according to 'Verwaltungsschale in der Praxis'
    https://www.plattform-i40.de/PI40/Redaktion/DE/Downloads/Publikation/2019-verwaltungsschale-in-der-praxis.html

    :return: example asset identification submodel

    """
    qualifier = model.Qualifier(
        type_='http://acplt.org/Qualifier/ExampleQualifier',
        value_type=model.datatypes.Int,
        value=100,
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        kind=model.QualifierKind.CONCEPT_QUALIFIER)

    qualifier2 = model.Qualifier(
        type_='http://acplt.org/Qualifier/ExampleQualifier2',
        value_type=model.datatypes.Int,
        value=50,
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        kind=model.QualifierKind.TEMPLATE_QUALIFIER)

    qualifier3 = model.Qualifier(
        type_='http://acplt.org/Qualifier/ExampleQualifier3',
        value_type=model.datatypes.DateTime,
        value=model.datatypes.DateTime(2023, 4, 7, 16, 59, 54, 870123),
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        kind=model.QualifierKind.VALUE_QUALIFIER)

    extension = model.Extension(
        name='ExampleExtension',
        value_type=model.datatypes.String,
        value="ExampleExtensionValue",
        refers_to=[model.ModelReference((model.Key(type_=model.KeyTypes.ASSET_ADMINISTRATION_SHELL,
                                                   value='http://acplt.org/RefersTo/ExampleRefersTo'),),
                                        model.AssetAdministrationShell)],)

    # Property-Element conform to 'Verwaltungsschale in der Praxis' page 41 ManufacturerName:
    # https://www.plattform-i40.de/PI40/Redaktion/DE/Downloads/Publikation/2019-verwaltungsschale-in-der-praxis.html
    identification_submodel_element_manufacturer_name = model.Property(
        id_short='ManufacturerName',
        value_type=model.datatypes.String,
        value='ACPLT',
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        category="PARAMETER",
        description=model.MultiLanguageTextType({
            'en-US': 'Legally valid designation of the natural or judicial person which '
                     'is directly responsible for the design, production, packaging and '
                     'labeling of a product in respect to its being brought into '
                     'circulation.',
            'de': 'Bezeichnung für eine natürliche oder juristische Person, die für die '
                  'Auslegung, Herstellung und Verpackung sowie die Etikettierung eines '
                  'Produkts im Hinblick auf das \'Inverkehrbringen\' im eigenen Namen '
                  'verantwortlich ist'
        }),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='0173-1#02-AAO677#002'),)),
        qualifier={qualifier, qualifier2},
        extension={extension},
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    # Property-Element conform to 'Verwaltungsschale in der Praxis' page 44 InstanceId:
    # https://www.plattform-i40.de/PI40/Redaktion/DE/Downloads/Publikation/2019-verwaltungsschale-in-der-praxis.html
    identification_submodel_element_instance_id = model.Property(
        id_short='InstanceId',
        value_type=model.datatypes.String,
        value='978-8234-234-342',
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        category="PARAMETER",
        description=model.MultiLanguageTextType({
            'en-US': 'Legally valid designation of the natural or judicial person which '
                     'is directly responsible for the design, production, packaging and '
                     'labeling of a product in respect to its being brought into '
                     'circulation.',
            'de': 'Bezeichnung für eine natürliche oder juristische Person, die für die '
                  'Auslegung, Herstellung und Verpackung sowie die Etikettierung eines '
                  'Produkts im Hinblick auf das \'Inverkehrbringen\' im eigenen Namen '
                  'verantwortlich ist'
        }),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(
            type_=model.KeyTypes.GLOBAL_REFERENCE,
            value='http://opcfoundation.org/UA/DI/1.1/DeviceType/Serialnumber'
        ),)),
        qualifier={qualifier3},
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    # asset identification submodel which will be included in the asset object
    identification_submodel = model.Submodel(
        id_='http://acplt.org/Submodels/Assets/TestAsset/Identification',
        submodel_element=(identification_submodel_element_manufacturer_name,
                          identification_submodel_element_instance_id),
        id_short='Identification',
        category=None,
        description=model.MultiLanguageTextType({
            'en-US': 'An example asset identification submodel for the test application',
            'de': 'Ein Beispiel-Identifikations-Submodel für eine Test-Anwendung'
        }),
        parent=None,
        administration=model.AdministrativeInformation(version='9',
                                                       revision='0',
                                                       creator=model.ExternalReference((
                                                           model.Key(model.KeyTypes.GLOBAL_REFERENCE,
                                                                     'http://acplt.org/AdministrativeInformation/'
                                                                     'TestAsset/Identification'),
                                                       )),
                                                       template_id='http://acplt.org/AdministrativeInformation'
                                                                   'Templates/TestAsset/Identification'),
        semantic_id=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                    value='http://acplt.org/SubmodelTemplates/AssetIdentification'),),
                                         model.Submodel),
        qualifier=(),
        kind=model.ModellingKind.INSTANCE,
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )
    return identification_submodel


def create_example_bill_of_material_submodel() -> model.Submodel:
    """
    creates a :class:`~basyx.aas.model.submodel.Submodel` for the bill of material containing two entities one
    co-managed and one self-managed

    :return: example bill of material submodel
    """
    submodel_element_property = model.Property(
        id_short='ExampleProperty',
        value_type=model.datatypes.String,
        value='exampleValue',
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        category='CONSTANT',
        description=model.MultiLanguageTextType({'en-US': 'Example Property object',
                                                 'de': 'Beispiel Property Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Properties/ExampleProperty'),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_property2 = model.Property(
        id_short='ExampleProperty2',
        value_type=model.datatypes.String,
        value='exampleValue2',
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleValueId'),)),
        category='CONSTANT',
        description=model.MultiLanguageTextType({'en-US': 'Example Property object',
                                                 'de': 'Beispiel Property Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Properties/ExampleProperty'),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    entity = model.Entity(
        id_short='ExampleEntity',
        entity_type=model.EntityType.SELF_MANAGED_ENTITY,
        statement={submodel_element_property, submodel_element_property2},
        global_asset_id='http://acplt.org/TestAsset/',
        specific_asset_id={
            model.SpecificAssetId(name="TestKey", value="TestValue",
                                  external_subject_id=model.ExternalReference(
                                      (model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                 value='http://acplt.org/SpecificAssetId/'),))
                                  )},
        category="PARAMETER",
        description=model.MultiLanguageTextType({
            'en-US': 'Legally valid designation of the natural or judicial person which '
                     'is directly responsible for the design, production, packaging and '
                     'labeling of a product in respect to its being brought into '
                     'circulation.',
            'de': 'Bezeichnung für eine natürliche oder juristische Person, die für die '
                  'Auslegung, Herstellung und Verpackung sowie die Etikettierung eines '
                  'Produkts im Hinblick auf das \'Inverkehrbringen\' im eigenen Namen '
                  'verantwortlich ist'
        }),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(
            type_=model.KeyTypes.GLOBAL_REFERENCE,
            value='http://opcfoundation.org/UA/DI/1.1/DeviceType/Serialnumber'
        ),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    entity_2 = model.Entity(
        id_short='ExampleEntity2',
        entity_type=model.EntityType.CO_MANAGED_ENTITY,
        statement=(),
        global_asset_id=None,
        specific_asset_id=(),
        category="PARAMETER",
        description=model.MultiLanguageTextType({
            'en-US': 'Legally valid designation of the natural or judicial person which '
                     'is directly responsible for the design, production, packaging and '
                     'labeling of a product in respect to its being brought into '
                     'circulation.',
            'de': 'Bezeichnung für eine natürliche oder juristische Person, die für die '
                  'Auslegung, Herstellung und Verpackung sowie die Etikettierung eines '
                  'Produkts im Hinblick auf das \'Inverkehrbringen\' im eigenen Namen '
                  'verantwortlich ist'
        }),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(
            type_=model.KeyTypes.GLOBAL_REFERENCE,
            value='http://opcfoundation.org/UA/DI/1.1/DeviceType/Serialnumber'
        ),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    # bill of material submodel which will be included in the asset object
    bill_of_material = model.Submodel(
        id_='http://acplt.org/Submodels/Assets/TestAsset/BillOfMaterial',
        submodel_element=(entity,
                          entity_2),
        id_short='BillOfMaterial',
        category=None,
        description=model.MultiLanguageTextType({
            'en-US': 'An example bill of material submodel for the test application',
            'de': 'Ein Beispiel-BillOfMaterial-Submodel für eine Test-Anwendung'
        }),
        parent=None,
        administration=model.AdministrativeInformation(version='9',
                                                       template_id='http://acplt.org/AdministrativeInformation'
                                                                   'Templates/TestAsset/BillOfMaterial'),
        semantic_id=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                    value='http://acplt.org/SubmodelTemplates/BillOfMaterial'),),
                                         model.Submodel),
        qualifier=(),
        kind=model.ModellingKind.INSTANCE,
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )
    return bill_of_material


def create_example_submodel() -> model.Submodel:
    """
    Creates an example :class:`~basyx.aas.model.submodel.Submodel` containing all kind of
    :class:`~basyx.aas.model.submodel.SubmodelElement` objects

    :return: example submodel
    """

    submodel_element_property = model.Property(
        id_short=None,
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
                                                       value='http://acplt.org/Properties/ExampleProperty'),), ),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                                     value='http://acplt.org/Properties/'
                                                                           'ExampleProperty/SupplementalId1'),)),
                                  model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                                     value='http://acplt.org/Properties/'
                                                                           'ExampleProperty/SupplementalId2'),))),
        embedded_data_specifications=(_embedded_data_specification_iec61360,))

    submodel_element_property_2 = model.Property(
        id_short=None,
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
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                                     value='http://acplt.org/Properties/'
                                                                           'ExampleProperty2/SupplementalId'),)),),
        embedded_data_specifications=()
    )

    submodel_element_multi_language_property = model.MultiLanguageProperty(
        id_short='ExampleMultiLanguageProperty',
        value=model.MultiLanguageTextType({'en-US': 'Example value of a MultiLanguageProperty element',
                                           'de': 'Beispielwert für ein MultiLanguageProperty-Element'}),
        value_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                    value='http://acplt.org/ValueId/ExampleMultiLanguageValueId'),)),
        category='CONSTANT',
        description=model.MultiLanguageTextType({'en-US': 'Example MultiLanguageProperty object',
                                                 'de': 'Beispiel MultiLanguageProperty Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/MultiLanguageProperties/'
                                                             'ExampleMultiLanguageProperty'),),
                                            referred_semantic_id=model.ExternalReference((model.Key(
                                              type_=model.KeyTypes.GLOBAL_REFERENCE,
                                              value='http://acplt.org/Properties/ExampleProperty/Referred'),))),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

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
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_blob = model.Blob(
        id_short='ExampleBlob',
        content_type='application/pdf',
        value=bytes(b'\x01\x02\x03\x04\x05'),
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example Blob object',
                                                 'de': 'Beispiel Blob Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Blobs/ExampleBlob'),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

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
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_file_uri = model.File(
        id_short='ExampleFileURI',
        content_type='application/pdf',
        value='https://www.plattform-i40.de/PI40/Redaktion/DE/Downloads/Publikation/Details-of-the-Asset-'
              'Administration-Shell-Part1.pdf?__blob=publicationFile&v=5',
        category='CONSTANT',
        description=model.MultiLanguageTextType({
            'en-US': 'Details of the Asset Administration Shell — An example for an external file reference',
            'de': 'Details of the Asset Administration Shell – Ein Beispiel für eine extern referenzierte Datei'
        }),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Files/ExampleFile'),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_reference_element = model.ReferenceElement(
        id_short='ExampleReferenceElement',
        value=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                              value='http://acplt.org/Test_Submodel'),
                                    model.Key(type_=model.KeyTypes.PROPERTY,
                                              value='ExampleProperty'),),
                                   model.Property),
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example Reference Element object',
                                                 'de': 'Beispiel Reference Element Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(
            type_=model.KeyTypes.GLOBAL_REFERENCE,
            value='http://acplt.org/ReferenceElements/ExampleReferenceElement'
        ),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_relationship_element = model.RelationshipElement(
        id_short='ExampleRelationshipElement',
        first=model.ModelReference((
            model.Key(
                type_=model.KeyTypes.SUBMODEL,
                value='http://acplt.org/Test_Submodel'),
            model.Key(
                type_=model.KeyTypes.PROPERTY,
                value='ExampleProperty'),
        ), model.Property),
        second=model.ModelReference((
            model.Key(
                type_=model.KeyTypes.SUBMODEL,
                value='http://acplt.org/Test_Submodel'),
            model.Key(
                type_=model.KeyTypes.PROPERTY,
                value='ExampleProperty2'),
        ), model.Property),
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example RelationshipElement object',
                                                 'de': 'Beispiel RelationshipElement Element'}),
        parent=None,
        semantic_id=model.ModelReference((model.Key(type_=model.KeyTypes.CONCEPT_DESCRIPTION,
                                                    value='https://acplt.org/Test_ConceptDescription'),),
                                         model.ConceptDescription),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_annotated_relationship_element = model.AnnotatedRelationshipElement(
        id_short='ExampleAnnotatedRelationshipElement',
        first=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL, value='http://acplt.org/Test_Submodel'),
                                    model.Key(type_=model.KeyTypes.PROPERTY,
                                              value='ExampleProperty'),),
                                   model.Property),
        second=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL, value='http://acplt.org/Test_Submodel'),
                                     model.Key(type_=model.KeyTypes.PROPERTY,
                                               value='ExampleProperty2'),),
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
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

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
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

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
        embedded_data_specifications=()
    )

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
        embedded_data_specifications=()
    )

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
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_capability = model.Capability(
        id_short='ExampleCapability',
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example Capability object',
                                                 'de': 'Beispiel Capability Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/Capabilities/'
                                                             'ExampleCapability'),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_basic_event_element = model.BasicEventElement(
        id_short='ExampleBasicEventElement',
        observed=model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL, value='http://acplt.org/Test_Submodel'),
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
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_submodel_element_list = model.SubmodelElementList(
        id_short='ExampleSubmodelList',
        type_value_list_element=model.Property,
        value=(submodel_element_property, submodel_element_property_2),
        semantic_id_list_element=model.ExternalReference((model.Key(
            type_=model.KeyTypes.GLOBAL_REFERENCE,
            value='http://acplt.org/Properties/ExampleProperty'
        ),)),
        value_type_list_element=model.datatypes.String,
        order_relevant=True,
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example SubmodelElementList object',
                                                 'de': 'Beispiel SubmodelElementList Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/SubmodelElementLists/'
                                                             'ExampleSubmodelElementList'),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel_element_submodel_element_collection = model.SubmodelElementCollection(
        id_short='ExampleSubmodelCollection',
        value=(submodel_element_blob,
               submodel_element_file,
               submodel_element_file_uri,
               submodel_element_multi_language_property,
               submodel_element_range,
               submodel_element_reference_element,
               submodel_element_submodel_element_list),
        category='PARAMETER',
        description=model.MultiLanguageTextType({'en-US': 'Example SubmodelElementCollection object',
                                                 'de': 'Beispiel SubmodelElementCollection Element'}),
        parent=None,
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/SubmodelElementCollections/'
                                                             'ExampleSubmodelElementCollection'),)),
        qualifier=(),
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )

    submodel = model.Submodel(
        id_='https://acplt.org/Test_Submodel',
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
                                                       revision='0',
                                                       creator=model.ExternalReference((
                                                           model.Key(model.KeyTypes.GLOBAL_REFERENCE,
                                                                     'http://acplt.org/AdministrativeInformation/'
                                                                     'Test_Submodel'),
                                                       )),),
        semantic_id=model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/SubmodelTemplates/'
                                                             'ExampleSubmodel'),)),
        qualifier=(),
        kind=model.ModellingKind.INSTANCE,
        extension=(),
        supplemental_semantic_id=(),
        embedded_data_specifications=()
    )
    return submodel


def create_example_concept_description() -> model.ConceptDescription:
    """
    Creates an example :class:`~basyx.aas.model.concept.ConceptDescription`

    :return: example concept description
    """
    concept_description = model.ConceptDescription(
        id_='https://acplt.org/Test_ConceptDescription',
        is_case_of={model.ExternalReference((model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                       value='http://acplt.org/DataSpecifications/'
                                                             'ConceptDescriptions/TestConceptDescription'),))},
        id_short='TestConceptDescription',
        category=None,
        description=model.MultiLanguageTextType({'en-US': 'An example concept description for the test application',
                                                 'de': 'Ein Beispiel-ConceptDescription für eine Test-Anwendung'}),
        parent=None,
        administration=model.AdministrativeInformation(version='9',
                                                       revision='0',
                                                       creator=model.ExternalReference((
                                                           model.Key(model.KeyTypes.GLOBAL_REFERENCE,
                                                                     'http://acplt.org/AdministrativeInformation/'
                                                                     'Test_ConceptDescription'),
                                                       )),
                                                       template_id='http://acplt.org/AdministrativeInformation'
                                                                   'Templates/Test_ConceptDescription',
                                                       embedded_data_specifications=(
                                                           _embedded_data_specification_iec61360,
                                                       ))
    )
    return concept_description


def create_example_asset_administration_shell() -> \
        model.AssetAdministrationShell:
    """
    Creates an :class:`~basyx.aas.model.aas.AssetAdministrationShell` with references to an example
    :class:`~basyx.aas.model.submodel.Submodel`.

    :return: example :class:`~basyx.aas.model.aas.AssetAdministrationShell`
    """

    asset_information = model.AssetInformation(
        asset_kind=model.AssetKind.INSTANCE,
        global_asset_id='http://acplt.org/TestAsset/',
        specific_asset_id={model.SpecificAssetId(name="TestKey",
                                                 value="TestValue",
                                                 external_subject_id=model.ExternalReference(
                                                            (model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                                       value='http://acplt.org/SpecificAssetId/'),)),
                                                 semantic_id=model.ExternalReference((model.Key(
                                                     model.KeyTypes.GLOBAL_REFERENCE,
                                                     "http://acplt.org/SpecificAssetId/"
                                                 ),)))},
        asset_type='http://acplt.org/TestAssetType/',
        default_thumbnail=model.Resource(
            "file:///path/to/thumbnail.png",
            "image/png"
        )
    )

    asset_administration_shell = model.AssetAdministrationShell(
        asset_information=asset_information,
        id_='https://acplt.org/Test_AssetAdministrationShell',
        id_short='TestAssetAdministrationShell',
        category=None,
        description=model.MultiLanguageTextType({
            'en-US': 'An Example Asset Administration Shell for the test application',
            'de': 'Ein Beispiel-Verwaltungsschale für eine Test-Anwendung'
        }),
        parent=None,
        administration=model.AdministrativeInformation(version='9',
                                                       revision='0',
                                                       creator=model.ExternalReference((
                                                           model.Key(model.KeyTypes.GLOBAL_REFERENCE,
                                                                     'http://acplt.org/AdministrativeInformation/'
                                                                     'Test_AssetAdministrationShell'),
                                                       )),
                                                       template_id='http://acplt.org/AdministrativeInformation'
                                                                   'Templates/Test_AssetAdministrationShell'),
        submodel={model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                  value='https://acplt.org/Test_Submodel'),),
                                       model.Submodel,
                                       model.ExternalReference((
                                           model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE,
                                                     value='http://acplt.org/SubmodelTemplates/ExampleSubmodel'),
                                       ))),
                  model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                  value='http://acplt.org/Submodels/Assets/TestAsset/Identification'),),
                                       model.Submodel,
                                       model.ModelReference((
                                           model.Key(type_=model.KeyTypes.SUBMODEL,
                                                     value='http://acplt.org/SubmodelTemplates/AssetIdentification'),),
                                           model.Submodel
                                       )),
                  model.ModelReference((model.Key(type_=model.KeyTypes.SUBMODEL,
                                                  value='http://acplt.org/Submodels/Assets/TestAsset/BillOfMaterial'),),
                                       model.Submodel),
                  },
        derived_from=model.ModelReference((model.Key(type_=model.KeyTypes.ASSET_ADMINISTRATION_SHELL,
                                                     value='https://acplt.org/TestAssetAdministrationShell2'),),
                                          model.AssetAdministrationShell),
        extension=(),
        embedded_data_specifications=(_embedded_data_specification_iec61360,)
    )
    return asset_administration_shell


##############################################################################
# check functions for checking if a given object is the same as the example #
##############################################################################
def check_example_asset_identification_submodel(checker: AASDataChecker, submodel: model.Submodel) -> None:
    expected_submodel = create_example_asset_identification_submodel()
    checker.check_submodel_equal(submodel, expected_submodel)


def check_example_bill_of_material_submodel(checker: AASDataChecker, submodel: model.Submodel) -> None:
    expected_submodel = create_example_bill_of_material_submodel()
    checker.check_submodel_equal(submodel, expected_submodel)


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
