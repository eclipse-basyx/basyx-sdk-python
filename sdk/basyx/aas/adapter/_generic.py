# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
The dicts defined in this module are used in the json and xml modules to translate enum members of our
implementation to the respective string and vice versa.
"""
import os
from typing import BinaryIO, Dict, IO, Type, Union

from basyx.aas import model

# type aliases for path-like objects and IO
# used by write_aas_xml_file, read_aas_xml_file, write_aas_json_file, read_aas_json_file
Path = Union[str, bytes, os.PathLike]
PathOrBinaryIO = Union[Path, BinaryIO]
PathOrIO = Union[Path, IO]  # IO is TextIO or BinaryIO

# XML Namespace definition
XML_NS_MAP = {"aas": "https://admin-shell.io/aas/3/0"}
XML_NS_AAS = "{" + XML_NS_MAP["aas"] + "}"

MODELLING_KIND: Dict[model.ModellingKind, str] = {
    model.ModellingKind.TEMPLATE: 'Template',
    model.ModellingKind.INSTANCE: 'Instance'}

ASSET_KIND: Dict[model.AssetKind, str] = {
    model.AssetKind.TYPE: 'Type',
    model.AssetKind.INSTANCE: 'Instance',
    model.AssetKind.NOT_APPLICABLE: 'NotApplicable'}

QUALIFIER_KIND: Dict[model.QualifierKind, str] = {
    model.QualifierKind.CONCEPT_QUALIFIER: 'ConceptQualifier',
    model.QualifierKind.TEMPLATE_QUALIFIER: 'TemplateQualifier',
    model.QualifierKind.VALUE_QUALIFIER: 'ValueQualifier'}

DIRECTION: Dict[model.Direction, str] = {
    model.Direction.INPUT: 'input',
    model.Direction.OUTPUT: 'output'}

STATE_OF_EVENT: Dict[model.StateOfEvent, str] = {
    model.StateOfEvent.ON: 'on',
    model.StateOfEvent.OFF: 'off'}

REFERENCE_TYPES: Dict[Type[model.Reference], str] = {
    model.ExternalReference: 'ExternalReference',
    model.ModelReference: 'ModelReference'}

KEY_TYPES: Dict[model.KeyTypes, str] = {
    model.KeyTypes.ASSET_ADMINISTRATION_SHELL: 'AssetAdministrationShell',
    model.KeyTypes.CONCEPT_DESCRIPTION: 'ConceptDescription',
    model.KeyTypes.SUBMODEL: 'Submodel',
    model.KeyTypes.ANNOTATED_RELATIONSHIP_ELEMENT: 'AnnotatedRelationshipElement',
    model.KeyTypes.BASIC_EVENT_ELEMENT: 'BasicEventElement',
    model.KeyTypes.BLOB: 'Blob',
    model.KeyTypes.CAPABILITY: 'Capability',
    model.KeyTypes.DATA_ELEMENT: 'DataElement',
    model.KeyTypes.ENTITY: 'Entity',
    model.KeyTypes.EVENT_ELEMENT: 'EventElement',
    model.KeyTypes.FILE: 'File',
    model.KeyTypes.MULTI_LANGUAGE_PROPERTY: 'MultiLanguageProperty',
    model.KeyTypes.OPERATION: 'Operation',
    model.KeyTypes.PROPERTY: 'Property',
    model.KeyTypes.RANGE: 'Range',
    model.KeyTypes.REFERENCE_ELEMENT: 'ReferenceElement',
    model.KeyTypes.RELATIONSHIP_ELEMENT: 'RelationshipElement',
    model.KeyTypes.SUBMODEL_ELEMENT: 'SubmodelElement',
    model.KeyTypes.SUBMODEL_ELEMENT_COLLECTION: 'SubmodelElementCollection',
    model.KeyTypes.SUBMODEL_ELEMENT_LIST: 'SubmodelElementList',
    model.KeyTypes.GLOBAL_REFERENCE: 'GlobalReference',
    model.KeyTypes.FRAGMENT_REFERENCE: 'FragmentReference'}

ENTITY_TYPES: Dict[model.EntityType, str] = {
    model.EntityType.CO_MANAGED_ENTITY: 'CoManagedEntity',
    model.EntityType.SELF_MANAGED_ENTITY: 'SelfManagedEntity'}

IEC61360_DATA_TYPES: Dict[model.base.DataTypeIEC61360, str] = {
    model.base.DataTypeIEC61360.DATE: 'DATE',
    model.base.DataTypeIEC61360.STRING: 'STRING',
    model.base.DataTypeIEC61360.STRING_TRANSLATABLE: 'STRING_TRANSLATABLE',
    model.base.DataTypeIEC61360.INTEGER_MEASURE: 'INTEGER_MEASURE',
    model.base.DataTypeIEC61360.INTEGER_COUNT: 'INTEGER_COUNT',
    model.base.DataTypeIEC61360.INTEGER_CURRENCY: 'INTEGER_CURRENCY',
    model.base.DataTypeIEC61360.REAL_MEASURE: 'REAL_MEASURE',
    model.base.DataTypeIEC61360.REAL_COUNT: 'REAL_COUNT',
    model.base.DataTypeIEC61360.REAL_CURRENCY: 'REAL_CURRENCY',
    model.base.DataTypeIEC61360.BOOLEAN: 'BOOLEAN',
    model.base.DataTypeIEC61360.IRI: 'IRI',
    model.base.DataTypeIEC61360.IRDI: 'IRDI',
    model.base.DataTypeIEC61360.RATIONAL: 'RATIONAL',
    model.base.DataTypeIEC61360.RATIONAL_MEASURE: 'RATIONAL_MEASURE',
    model.base.DataTypeIEC61360.TIME: 'TIME',
    model.base.DataTypeIEC61360.TIMESTAMP: 'TIMESTAMP',
    model.base.DataTypeIEC61360.HTML: 'HTML',
    model.base.DataTypeIEC61360.BLOB: 'BLOB',
    model.base.DataTypeIEC61360.FILE: 'FILE',
}

IEC61360_LEVEL_TYPES: Dict[model.base.IEC61360LevelType, str] = {
    model.base.IEC61360LevelType.MIN: 'min',
    model.base.IEC61360LevelType.NOM: 'nom',
    model.base.IEC61360LevelType.TYP: 'typ',
    model.base.IEC61360LevelType.MAX: 'max',
}

MODELLING_KIND_INVERSE: Dict[str, model.ModellingKind] = {v: k for k, v in MODELLING_KIND.items()}
ASSET_KIND_INVERSE: Dict[str, model.AssetKind] = {v: k for k, v in ASSET_KIND.items()}
QUALIFIER_KIND_INVERSE: Dict[str, model.QualifierKind] = {v: k for k, v in QUALIFIER_KIND.items()}
DIRECTION_INVERSE: Dict[str, model.Direction] = {v: k for k, v in DIRECTION.items()}
STATE_OF_EVENT_INVERSE: Dict[str, model.StateOfEvent] = {v: k for k, v in STATE_OF_EVENT.items()}
REFERENCE_TYPES_INVERSE: Dict[str, Type[model.Reference]] = {v: k for k, v in REFERENCE_TYPES.items()}
KEY_TYPES_INVERSE: Dict[str, model.KeyTypes] = {v: k for k, v in KEY_TYPES.items()}
ENTITY_TYPES_INVERSE: Dict[str, model.EntityType] = {v: k for k, v in ENTITY_TYPES.items()}
IEC61360_DATA_TYPES_INVERSE: Dict[str, model.base.DataTypeIEC61360] = {v: k for k, v in IEC61360_DATA_TYPES.items()}
IEC61360_LEVEL_TYPES_INVERSE: Dict[str, model.base.IEC61360LevelType] = \
    {v: k for k, v in IEC61360_LEVEL_TYPES.items()}

KEY_TYPES_CLASSES_INVERSE: Dict[model.KeyTypes, Type[model.Referable]] = \
    {v: k for k, v in model.KEY_TYPES_CLASSES.items()}
