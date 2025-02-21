# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.json.json_serialization:

Module for serializing Asset Administration Shell objects to the official JSON format

The module provides a custom JSONEncoder classes :class:`AASToJsonEncoder` and :class:`StrippedAASToJsonEncoder`
to be used with the Python standard :mod:`json` module. While the former serializes objects as defined in the
specification, the latter serializes stripped objects, excluding some attributes
(see https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91).
Each class contains a custom :meth:`~.AASToJsonEncoder.default` function which converts BaSyx Python SDK objects to
simple python types for an automatic JSON serialization.
To simplify the usage of this module, the :meth:`write_aas_json_file` and :meth:`object_store_to_json` are provided.
The former is used to serialize a given :class:`~basyx.aas.model.provider.AbstractObjectStore` to a file, while the
latter serializes the object store to a string and returns it.

The serialization is performed in an iterative approach: The :meth:`~.AASToJsonEncoder.default` function gets called for
every object and checks if an object is an BaSyx Python SDK object. In this case, it calls a special function for the
respective BaSyx Python SDK class which converts the object (but not the contained objects) into a simple Python dict,
which is serializable. Any contained  BaSyx Python SDK objects are included into the dict as they are to be converted
later on. The special helper function ``_abstract_classes_to_json`` is called by most of the
conversion functions to handle all the attributes of abstract base classes.
"""
import base64
import contextlib
import inspect
import io
from typing import ContextManager, List, Dict, Optional, TextIO, Type, Callable, get_args
import json

from basyx.aas import model
from .. import _generic


class AASToJsonEncoder(json.JSONEncoder):
    """
    Custom JSON Encoder class to use the :mod:`json` module for serializing Asset Administration Shell data into the
    official JSON format

    The class overrides the ``default()`` method to transform BaSyx Python SDK objects into dicts that may be serialized
    by the standard encode method.

    Typical usage:

    .. code-block:: python

        json_string = json.dumps(data, cls=AASToJsonEncoder)

    :cvar stripped: If True, the JSON objects will be serialized in a stripped manner, excluding some attributes.
                    Defaults to ``False``.
                    See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
    """
    stripped = False

    def default(self, obj: object) -> object:
        """
        The overwritten ``default`` method for :class:`json.JSONEncoder`

        :param obj: The object to serialize to json
        :return: The serialized object
        """
        mapping: Dict[Type, Callable] = {
            model.AdministrativeInformation: self._administrative_information_to_json,
            model.AnnotatedRelationshipElement: self._annotated_relationship_element_to_json,
            model.AssetAdministrationShell: self._asset_administration_shell_to_json,
            model.AssetInformation: self._asset_information_to_json,
            model.BasicEventElement: self._basic_event_element_to_json,
            model.Blob: self._blob_to_json,
            model.Capability: self._capability_to_json,
            model.ConceptDescription: self._concept_description_to_json,
            model.DataSpecificationIEC61360: self._data_specification_iec61360_to_json,
            model.Entity: self._entity_to_json,
            model.Extension: self._extension_to_json,
            model.File: self._file_to_json,
            model.Key: self._key_to_json,
            model.LangStringSet: self._lang_string_set_to_json,
            model.MultiLanguageProperty: self._multi_language_property_to_json,
            model.Operation: self._operation_to_json,
            model.Property: self._property_to_json,
            model.Qualifier: self._qualifier_to_json,
            model.Range: self._range_to_json,
            model.Reference: self._reference_to_json,
            model.ReferenceElement: self._reference_element_to_json,
            model.RelationshipElement: self._relationship_element_to_json,
            model.Resource: self._resource_to_json,
            model.SpecificAssetId: self._specific_asset_id_to_json,
            model.Submodel: self._submodel_to_json,
            model.SubmodelElementCollection: self._submodel_element_collection_to_json,
            model.SubmodelElementList: self._submodel_element_list_to_json,
            model.ValueReferencePair: self._value_reference_pair_to_json,
        }
        for typ in mapping:
            if isinstance(obj, typ):
                mapping_method = mapping[typ]
                return mapping_method(obj)
        return super().default(obj)

    @classmethod
    def _abstract_classes_to_json(cls, obj: object) -> Dict[str, object]:
        """
        Transformation function to serialize abstract classes from model.base which are inherited by many classes

        :param obj: object which must be serialized
        :return: dict with the serialized attributes of the abstract classes this object inherits from
        """
        data: Dict[str, object] = {}
        if isinstance(obj, model.HasExtension) and not cls.stripped:
            if obj.extension:
                data['extensions'] = list(obj.extension)
        if isinstance(obj, model.HasDataSpecification) and not cls.stripped:
            if obj.embedded_data_specifications:
                data['embeddedDataSpecifications'] = [
                    {'dataSpecification': spec.data_specification,
                     'dataSpecificationContent': spec.data_specification_content}
                    for spec in obj.embedded_data_specifications
                ]

        if isinstance(obj, model.Referable):
            if obj.id_short and not isinstance(obj.parent, model.SubmodelElementList):
                data['idShort'] = obj.id_short
            if obj.display_name:
                data['displayName'] = obj.display_name
            if obj.category:
                data['category'] = obj.category
            if obj.description:
                data['description'] = obj.description
            try:
                ref_type = next(iter(t for t in inspect.getmro(type(obj)) if t in model.KEY_TYPES_CLASSES))
            except StopIteration as e:
                raise TypeError("Object of type {} is Referable but does not inherit from a known AAS type"
                                .format(obj.__class__.__name__)) from e
            data['modelType'] = ref_type.__name__
        if isinstance(obj, model.Identifiable):
            data['id'] = obj.id
            if obj.administration:
                data['administration'] = obj.administration
        if isinstance(obj, model.HasSemantics):
            if obj.semantic_id:
                data['semanticId'] = obj.semantic_id
            if obj.supplemental_semantic_id:
                data['supplementalSemanticIds'] = list(obj.supplemental_semantic_id)
        if isinstance(obj, model.HasKind):
            if obj.kind is model.ModellingKind.TEMPLATE:
                data['kind'] = _generic.MODELLING_KIND[obj.kind]
        if isinstance(obj, model.Qualifiable) and not cls.stripped:
            if obj.qualifier:
                data['qualifiers'] = list(obj.qualifier)
        return data

    # #############################################################
    # transformation functions to serialize classes from model.base
    # #############################################################

    @classmethod
    def _lang_string_set_to_json(cls, obj: model.LangStringSet) -> List[Dict[str, object]]:
        return [{'language': k, 'text': v}
                for k, v in obj.items()]

    @classmethod
    def _key_to_json(cls, obj: model.Key) -> Dict[str, object]:
        """
        serialization of an object from class Key to json

        :param obj: object of class Key
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data.update({'type': _generic.KEY_TYPES[obj.type],
                     'value': obj.value})
        return data

    @classmethod
    def _administrative_information_to_json(cls, obj: model.AdministrativeInformation) -> Dict[str, object]:
        """
        serialization of an object from class AdministrativeInformation to json

        :param obj: object of class AdministrativeInformation
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if obj.version:
            data['version'] = obj.version
            if obj.revision:
                data['revision'] = obj.revision
        if obj.creator:
            data['creator'] = obj.creator
        if obj.template_id:
            data['templateId'] = obj.template_id
        return data

    @classmethod
    def _reference_to_json(cls, obj: model.Reference) -> Dict[str, object]:
        """
        serialization of an object from class Reference to json

        :param obj: object of class Reference
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data['type'] = _generic.REFERENCE_TYPES[obj.__class__]
        data['keys'] = list(obj.key)
        if obj.referred_semantic_id is not None:
            data['referredSemanticId'] = cls._reference_to_json(obj.referred_semantic_id)
        return data

    @classmethod
    def _namespace_to_json(cls, obj):  # not in specification yet
        """
        serialization of an object from class Namespace to json

        :param obj: object of class Namespace
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        return data

    @classmethod
    def _qualifier_to_json(cls, obj: model.Qualifier) -> Dict[str, object]:
        """
        serialization of an object from class Qualifier to json

        :param obj: object of class Qualifier
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if obj.value:
            data['value'] = model.datatypes.xsd_repr(obj.value) if obj.value is not None else None
        if obj.value_id:
            data['valueId'] = obj.value_id
        # Even though kind is optional in the schema, it's better to always serialize it instead of specifying
        # the default value in multiple locations.
        data['kind'] = _generic.QUALIFIER_KIND[obj.kind]
        data['valueType'] = model.datatypes.XSD_TYPE_NAMES[obj.value_type]
        data['type'] = obj.type
        return data

    @classmethod
    def _extension_to_json(cls, obj: model.Extension) -> Dict[str, object]:
        """
        serialization of an object from class Extension to json

        :param obj: object of class Extension
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if obj.value:
            data['value'] = model.datatypes.xsd_repr(obj.value) if obj.value is not None else None
        if obj.refers_to:
            data['refersTo'] = list(obj.refers_to)
        if obj.value_type:
            data['valueType'] = model.datatypes.XSD_TYPE_NAMES[obj.value_type]
        data['name'] = obj.name
        return data

    @classmethod
    def _value_reference_pair_to_json(cls, obj: model.ValueReferencePair) -> Dict[str, object]:
        """
        serialization of an object from class ValueReferencePair to json

        :param obj: object of class ValueReferencePair
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data.update({'value': model.datatypes.xsd_repr(obj.value),
                     'valueId': obj.value_id})
        return data

    @classmethod
    def _value_list_to_json(cls, obj: model.ValueList) -> Dict[str, object]:
        """
        serialization of an object from class ValueList to json

        :param obj: object of class ValueList
        :return: dict with the serialized attributes of this object
        """
        return {'valueReferencePairs': list(obj)}

    # ############################################################
    # transformation functions to serialize classes from model.aas
    # ############################################################

    @classmethod
    def _specific_asset_id_to_json(cls, obj: model.SpecificAssetId) -> Dict[str, object]:
        """
        serialization of an object from class SpecificAssetId to json

        :param obj: object of class SpecificAssetId
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data['name'] = obj.name
        data['value'] = obj.value
        if obj.external_subject_id:
            data['externalSubjectId'] = obj.external_subject_id
        return data

    @classmethod
    def _asset_information_to_json(cls, obj: model.AssetInformation) -> Dict[str, object]:
        """
        serialization of an object from class AssetInformation to json

        :param obj: object of class AssetInformation
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data['assetKind'] = _generic.ASSET_KIND[obj.asset_kind]
        if obj.global_asset_id:
            data['globalAssetId'] = obj.global_asset_id
        if obj.specific_asset_id:
            data['specificAssetIds'] = list(obj.specific_asset_id)
        if obj.asset_type:
            data['assetType'] = obj.asset_type
        if obj.default_thumbnail:
            data['defaultThumbnail'] = obj.default_thumbnail
        return data

    @classmethod
    def _concept_description_to_json(cls, obj: model.ConceptDescription) -> Dict[str, object]:
        """
        serialization of an object from class ConceptDescription to json

        :param obj: object of class ConceptDescription
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if obj.is_case_of:
            data['isCaseOf'] = list(obj.is_case_of)
        return data

    @classmethod
    def _data_specification_iec61360_to_json(
            cls, obj: model.base.DataSpecificationIEC61360) -> Dict[str, object]:
        """
        serialization of an object from class DataSpecificationIEC61360 to json

        :param obj: object of class DataSpecificationIEC61360
        :return: dict with the serialized attributes of this object
        """
        data_spec: Dict[str, object] = {
            'modelType': 'DataSpecificationIec61360',
            'preferredName': obj.preferred_name
        }
        if obj.data_type is not None:
            data_spec['dataType'] = _generic.IEC61360_DATA_TYPES[obj.data_type]
        if obj.definition is not None:
            data_spec['definition'] = obj.definition
        if obj.short_name is not None:
            data_spec['shortName'] = obj.short_name
        if obj.unit is not None:
            data_spec['unit'] = obj.unit
        if obj.unit_id is not None:
            data_spec['unitId'] = obj.unit_id
        if obj.source_of_definition is not None:
            data_spec['sourceOfDefinition'] = obj.source_of_definition
        if obj.symbol is not None:
            data_spec['symbol'] = obj.symbol
        if obj.value_format is not None:
            data_spec['valueFormat'] = obj.value_format
        if obj.value_list is not None:
            data_spec['valueList'] = cls._value_list_to_json(obj.value_list)
        if obj.value is not None:
            data_spec['value'] = obj.value
        if obj.level_types:
            data_spec['levelType'] = {v: k in obj.level_types for k, v in _generic.IEC61360_LEVEL_TYPES.items()}
        return data_spec

    @classmethod
    def _asset_administration_shell_to_json(cls, obj: model.AssetAdministrationShell) -> Dict[str, object]:
        """
        serialization of an object from class AssetAdministrationShell to json

        :param obj: object of class AssetAdministrationShell
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data.update(cls._namespace_to_json(obj))
        if obj.derived_from:
            data["derivedFrom"] = obj.derived_from
        if obj.asset_information:
            data["assetInformation"] = obj.asset_information
        if not cls.stripped and obj.submodel:
            data["submodels"] = list(obj.submodel)
        return data

    # #################################################################
    # transformation functions to serialize classes from model.submodel
    # #################################################################

    @classmethod
    def _submodel_to_json(cls, obj: model.Submodel) -> Dict[str, object]:  # TODO make kind optional
        """
        serialization of an object from class Submodel to json

        :param obj: object of class Submodel
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if not cls.stripped and obj.submodel_element != set():
            data['submodelElements'] = list(obj.submodel_element)
        return data

    @classmethod
    def _data_element_to_json(cls, obj: model.DataElement) -> Dict[str, object]:  # no attributes in specification yet
        """
        serialization of an object from class DataElement to json

        :param obj: object of class DataElement
        :return: dict with the serialized attributes of this object
        """
        return {}

    @classmethod
    def _property_to_json(cls, obj: model.Property) -> Dict[str, object]:
        """
        serialization of an object from class Property to json

        :param obj: object of class Property
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if obj.value is not None:
            data['value'] = model.datatypes.xsd_repr(obj.value)
        if obj.value_id:
            data['valueId'] = obj.value_id
        data['valueType'] = model.datatypes.XSD_TYPE_NAMES[obj.value_type]
        return data

    @classmethod
    def _multi_language_property_to_json(cls, obj: model.MultiLanguageProperty) -> Dict[str, object]:
        """
        serialization of an object from class MultiLanguageProperty to json

        :param obj: object of class MultiLanguageProperty
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if obj.value:
            data['value'] = obj.value
        if obj.value_id:
            data['valueId'] = obj.value_id
        return data

    @classmethod
    def _range_to_json(cls, obj: model.Range) -> Dict[str, object]:
        """
        serialization of an object from class Range to json

        :param obj: object of class Range
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data['valueType'] = model.datatypes.XSD_TYPE_NAMES[obj.value_type]
        if obj.min is not None:
            data['min'] = model.datatypes.xsd_repr(obj.min)
        if obj.max is not None:
            data['max'] = model.datatypes.xsd_repr(obj.max)
        return data

    @classmethod
    def _blob_to_json(cls, obj: model.Blob) -> Dict[str, object]:
        """
        serialization of an object from class Blob to json

        :param obj: object of class Blob
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data['contentType'] = obj.content_type
        if obj.value is not None:
            data['value'] = base64.b64encode(obj.value).decode()
        return data

    @classmethod
    def _file_to_json(cls, obj: model.File) -> Dict[str, object]:
        """
        serialization of an object from class File to json

        :param obj: object of class File
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data['contentType'] = obj.content_type
        if obj.value is not None:
            data['value'] = obj.value
        return data

    @classmethod
    def _resource_to_json(cls, obj: model.Resource) -> Dict[str, object]:
        """
        serialization of an object from class Resource to json

        :param obj: object of class Resource
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data['path'] = obj.path
        if obj.content_type is not None:
            data['contentType'] = obj.content_type
        return data

    @classmethod
    def _reference_element_to_json(cls, obj: model.ReferenceElement) -> Dict[str, object]:
        """
        serialization of an object from class Reference to json

        :param obj: object of class Reference
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if obj.value:
            data['value'] = obj.value
        return data

    @classmethod
    def _submodel_element_collection_to_json(cls, obj: model.SubmodelElementCollection) -> Dict[str, object]:
        """
        serialization of an object from class SubmodelElementCollection to json

        :param obj: object of class SubmodelElementCollection
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if not cls.stripped and len(obj.value) > 0:
            data['value'] = list(obj.value)
        return data

    @classmethod
    def _submodel_element_list_to_json(cls, obj: model.SubmodelElementList) -> Dict[str, object]:
        """
        serialization of an object from class SubmodelElementList to json

        :param obj: object of class SubmodelElementList
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        # Even though orderRelevant is optional in the schema, it's better to always serialize it instead of specifying
        # the default value in multiple locations.
        data['orderRelevant'] = obj.order_relevant
        data['typeValueListElement'] = _generic.KEY_TYPES[model.KEY_TYPES_CLASSES[obj.type_value_list_element]]
        if obj.semantic_id_list_element is not None:
            data['semanticIdListElement'] = obj.semantic_id_list_element
        if obj.value_type_list_element is not None:
            data['valueTypeListElement'] = model.datatypes.XSD_TYPE_NAMES[obj.value_type_list_element]
        if not cls.stripped and len(obj.value) > 0:
            data['value'] = list(obj.value)
        return data

    @classmethod
    def _relationship_element_to_json(cls, obj: model.RelationshipElement) -> Dict[str, object]:
        """
        serialization of an object from class RelationshipElement to json

        :param obj: object of class RelationshipElement
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data.update({'first': obj.first, 'second': obj.second})
        return data

    @classmethod
    def _annotated_relationship_element_to_json(cls, obj: model.AnnotatedRelationshipElement) -> Dict[str, object]:
        """
        serialization of an object from class AnnotatedRelationshipElement to json

        :param obj: object of class AnnotatedRelationshipElement
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data.update({'first': obj.first, 'second': obj.second})
        if not cls.stripped and obj.annotation:
            data['annotations'] = list(obj.annotation)
        return data

    @classmethod
    def _operation_variable_to_json(cls, obj: model.SubmodelElement) -> Dict[str, object]:
        """
        serialization of an object from class SubmodelElement to a json OperationVariable representation
        Since we don't implement the ``OperationVariable`` class, which is just a wrapper for a single
        :class:`~basyx.aas.model.submodel.SubmodelElement`, elements are serialized as the ``value`` attribute of an
        ``operationVariable`` object.

        :param obj: object of class :class:`~basyx.aas.model.submodel.SubmodelElement`
        :return: ``OperationVariable`` wrapper containing the serialized
                 :class:`~basyx.aas.model.submodel.SubmodelElement`
        """
        return {'value': obj}

    @classmethod
    def _operation_to_json(cls, obj: model.Operation) -> Dict[str, object]:
        """
        serialization of an object from class Operation to json

        :param obj: object of class Operation
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        for tag, nss in (('inputVariables', obj.input_variable),
                         ('outputVariables', obj.output_variable),
                         ('inoutputVariables', obj.in_output_variable)):
            if nss:
                data[tag] = [cls._operation_variable_to_json(obj) for obj in nss]
        return data

    @classmethod
    def _capability_to_json(cls, obj: model.Capability) -> Dict[str, object]:
        """
        serialization of an object from class Capability to json

        :param obj: object of class Capability
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        # no attributes in specification yet
        return data

    @classmethod
    def _entity_to_json(cls, obj: model.Entity) -> Dict[str, object]:
        """
        serialization of an object from class Entity to json

        :param obj: object of class Entity
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        if not cls.stripped and obj.statement:
            data['statements'] = list(obj.statement)
        data['entityType'] = _generic.ENTITY_TYPES[obj.entity_type]
        if obj.global_asset_id:
            data['globalAssetId'] = obj.global_asset_id
        if obj.specific_asset_id:
            data['specificAssetIds'] = list(obj.specific_asset_id)
        return data

    @classmethod
    def _event_element_to_json(cls, obj: model.EventElement) -> Dict[str, object]:  # no attributes in specification yet
        """
        serialization of an object from class EventElement to json

        :param obj: object of class EventElement
        :return: dict with the serialized attributes of this object
        """
        return {}

    @classmethod
    def _basic_event_element_to_json(cls, obj: model.BasicEventElement) -> Dict[str, object]:
        """
        serialization of an object from class BasicEventElement to json

        :param obj: object of class BasicEventElement
        :return: dict with the serialized attributes of this object
        """
        data = cls._abstract_classes_to_json(obj)
        data['observed'] = obj.observed
        data['direction'] = _generic.DIRECTION[obj.direction]
        data['state'] = _generic.STATE_OF_EVENT[obj.state]
        if obj.message_topic is not None:
            data['messageTopic'] = obj.message_topic
        if obj.message_broker is not None:
            data['messageBroker'] = cls._reference_to_json(obj.message_broker)
        if obj.last_update is not None:
            data['lastUpdate'] = model.datatypes.xsd_repr(obj.last_update)
        if obj.min_interval is not None:
            data['minInterval'] = model.datatypes.xsd_repr(obj.min_interval)
        if obj.max_interval is not None:
            data['maxInterval'] = model.datatypes.xsd_repr(obj.max_interval)
        return data


class StrippedAASToJsonEncoder(AASToJsonEncoder):
    """
    AASToJsonEncoder for stripped objects. Used in the HTTP API.
    See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
    """
    stripped = True


def _select_encoder(stripped: bool, encoder: Optional[Type[AASToJsonEncoder]] = None) -> Type[AASToJsonEncoder]:
    """
    Returns the correct encoder based on the stripped parameter. If an encoder class is given, stripped is ignored.

    :param stripped: If true, an encoder for parsing stripped JSON objects is selected. Ignored if an encoder class is
                     specified.
    :param encoder: Is returned, if specified.
    :return: A AASToJsonEncoder (sub)class.
    """
    if encoder is not None:
        return encoder
    return AASToJsonEncoder if not stripped else StrippedAASToJsonEncoder


def _create_dict(data: model.AbstractObjectStore) -> dict:
    # separate different kind of objects
    asset_administration_shells: List[model.AssetAdministrationShell] = []
    submodels: List[model.Submodel] = []
    concept_descriptions: List[model.ConceptDescription] = []
    for obj in data:
        if isinstance(obj, model.AssetAdministrationShell):
            asset_administration_shells.append(obj)
        elif isinstance(obj, model.Submodel):
            submodels.append(obj)
        elif isinstance(obj, model.ConceptDescription):
            concept_descriptions.append(obj)
    dict_: Dict[str, List] = {}
    if asset_administration_shells:
        dict_['assetAdministrationShells'] = asset_administration_shells
    if submodels:
        dict_['submodels'] = submodels
    if concept_descriptions:
        dict_['conceptDescriptions'] = concept_descriptions
    return dict_


def object_store_to_json(data: model.AbstractObjectStore, stripped: bool = False,
                         encoder: Optional[Type[AASToJsonEncoder]] = None, **kwargs) -> str:
    """
    Create a json serialization of a set of AAS objects according to 'Details of the Asset Administration Shell',
    chapter 5.5

    :param data: :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` which contains different objects of
                 the AAS metamodel which should be serialized to a JSON file
    :param stripped: If true, objects are serialized to stripped json objects.
                     See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
                     This parameter is ignored if an encoder class is specified.
    :param encoder: The encoder class used to encode the JSON objects
    :param kwargs: Additional keyword arguments to be passed to :func:`json.dumps`
    """
    encoder_ = _select_encoder(stripped, encoder)
    # serialize object to json
    return json.dumps(_create_dict(data), cls=encoder_, **kwargs)


class _DetachingTextIOWrapper(io.TextIOWrapper):
    """
    Like :class:`io.TextIOWrapper`, but detaches on context exit instead of closing the wrapped buffer.
    """
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.detach()


def write_aas_json_file(file: _generic.PathOrIO, data: model.AbstractObjectStore, stripped: bool = False,
                        encoder: Optional[Type[AASToJsonEncoder]] = None, **kwargs) -> None:
    """
    Write a set of AAS objects to an Asset Administration Shell JSON file according to 'Details of the Asset
    Administration Shell', chapter 5.5

    :param file: A filename or file-like object to write the JSON-serialized data to
    :param data: :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` which contains different objects of
                 the AAS metamodel which should be serialized to a JSON file
    :param stripped: If `True`, objects are serialized to stripped json objects.
                     See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
                     This parameter is ignored if an encoder class is specified.
    :param encoder: The encoder class used to encode the JSON objects
    :param kwargs: Additional keyword arguments to be passed to `json.dump()`
    """
    encoder_ = _select_encoder(stripped, encoder)

    # json.dump() only accepts TextIO
    cm: ContextManager[TextIO]
    if isinstance(file, get_args(_generic.Path)):
        # 'file' is a path, needs to be opened first
        cm = open(file, "w", encoding="utf-8")
    elif not hasattr(file, "encoding"):
        # only TextIO has this attribute, so this must be BinaryIO, which needs to be wrapped
        # mypy seems to have issues narrowing the type due to get_args()
        cm = _DetachingTextIOWrapper(file, "utf-8", write_through=True)  # type: ignore[arg-type]
    else:
        # we already got TextIO, nothing needs to be done
        # mypy seems to have issues narrowing the type due to get_args()
        cm = contextlib.nullcontext(file)  # type: ignore[arg-type]

    # serialize object to json
    with cm as fp:
        json.dump(_create_dict(data), fp, cls=encoder_, **kwargs)
