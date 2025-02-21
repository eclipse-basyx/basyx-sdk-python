# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.json.json_deserialization:

Module for deserializing Asset Administration Shell data from the official JSON format

The module provides custom JSONDecoder classes :class:`~.AASFromJsonDecoder` and :class:`~.StrictAASFromJsonDecoder` to
be used with the Python standard :mod:`json` module.

Furthermore, it provides two classes :class:`~basyx.aas.adapter.json.json_deserialization.StrippedAASFromJsonDecoder`
and :class:`~basyx.aas.adapter.json.json_deserialization.StrictStrippedAASFromJsonDecoder` for parsing stripped
JSON objects, which are used in the http adapter (see https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91).
The classes contain a custom :meth:`~basyx.aas.adapter.json.json_deserialization.AASFromJsonDecoder.object_hook`
function to detect encoded AAS objects within the JSON data and convert them to BaSyx Python SDK objects while parsing.
Additionally, there's the :meth:`~basyx.aas.adapter.json.json_deserialization.read_aas_json_file_into` function, that
takes a complete AAS JSON file, reads its contents and stores the objects in the provided
:class:`~basyx.aas.model.provider.AbstractObjectStore`. :meth:`read_aas_json_file` is a wrapper for this function.
Instead of storing the objects in a given :class:`~basyx.aas.model.provider.AbstractObjectStore`,
it returns a :class:`~basyx.aas.model.provider.DictObjectStore` containing parsed objects.

The deserialization is performed in a bottom-up approach: The ``object_hook()`` method gets called for every parsed JSON
object (as dict) and checks for existence of the ``modelType`` attribute. If it is present, the ``AAS_CLASS_PARSERS``
dict defines, which of the constructor methods of the class is to be used for converting the dict into an object.
Embedded objects that should have a ``modelType`` themselves are expected to be converted already.
Other embedded objects are converted using a number of helper constructor methods.
"""
import base64
import contextlib
import json
import logging
import pprint
from typing import Dict, Callable, ContextManager, TypeVar, Type, List, IO, Optional, Set, get_args

from basyx.aas import model
from .._generic import MODELLING_KIND_INVERSE, ASSET_KIND_INVERSE, KEY_TYPES_INVERSE, ENTITY_TYPES_INVERSE, \
    IEC61360_DATA_TYPES_INVERSE, IEC61360_LEVEL_TYPES_INVERSE, KEY_TYPES_CLASSES_INVERSE, REFERENCE_TYPES_INVERSE, \
    DIRECTION_INVERSE, STATE_OF_EVENT_INVERSE, QUALIFIER_KIND_INVERSE, PathOrIO, Path

logger = logging.getLogger(__name__)


# #############################################################################
# Helper functions (for simplifying implementation of constructor functions)
# #############################################################################

T = TypeVar('T')
LSS = TypeVar('LSS', bound=model.LangStringSet)


def _get_ts(dct: Dict[str, object], key: str, type_: Type[T]) -> T:
    """
    Helper function for getting an item from a (str→object) dict in a typesafe way.

    The type of the object is checked at runtime and a TypeError is raised, if the object has not the expected type.

    :param dct: The dict
    :param key: The key of the item to retrieve
    :param type_: The expected type of the item
    :return: The item
    :raises TypeError: If the item has an unexpected type
    :raises KeyError: If the key is not found in the dict (just as usual)
    """
    val = dct[key]
    if not isinstance(val, type_):
        raise TypeError("Dict entry '{}' has unexpected type {}".format(key, type(val).__name__))
    return val


def _expect_type(object_: object, type_: Type, context: str, failsafe: bool) -> bool:
    """
    Helper function to check type of an embedded object.

    This function may be used in any constructor function for an AAS object that expects to find already constructed
    AAS objects of a certain type within its data dict. In this case, we want to ensure that the object has this kind
    and raise a TypeError if not. In failsafe mode, we want to log the error and prevent the object from being added
    to the parent object. A typical use of this function would look like this:

      if _expect_type(element, model.SubmodelElement, str(submodel), failsafe):
          submodel.submodel_element.add(element)

    :param object_: The object to be type-checked
    :param type_: The expected type
    :param context: A string to add to the exception message / log message, that describes the context in that the
                    object has been found
    :param failsafe: Log error and return false instead of raising a TypeError
    :return: True if the object is of the expected type
    :raises TypeError: If the object is not of the expected type and the failsafe mode is not active
    """
    if isinstance(object_, type_):
        return True
    if failsafe:
        logger.error("Expected a %s in %s, but found %s", type_.__name__, context, repr(object_))
    else:
        raise TypeError("Expected a %s in %s, but found %s" % (type_.__name__, context, repr(object_)))
    return False


class AASFromJsonDecoder(json.JSONDecoder):
    """
    Custom JSONDecoder class to use the :mod:`json` module for deserializing Asset Administration Shell data from the
    official JSON format

    The class contains a custom :meth:`~.AASFromJsonDecoder.object_hook` function to detect encoded AAS objects within
    the JSON data and convert them to BaSyx Python SDK objects while parsing.

    Typical usage:

    .. code-block:: python

        data = json.loads(json_string, cls=AASFromJsonDecoder)

    The ``object_hook`` function uses a set of ``_construct_*()`` methods, one for each
    AAS object type to transform the JSON objects in to BaSyx Python SDK objects. These constructor methods are divided
    into two parts: "Helper Constructor Methods", that are used to construct AAS object types without a ``modelType``
    attribute as embedded objects within other AAS objects, and "Direct Constructor Methods" for AAS object types *with*
    ``modelType`` attribute. The former are called from other constructor methods or utility methods based on the
    expected type of an attribute, the latter are called directly from the ``object_hook()`` function based on the
    ``modelType`` attribute.

    This class may be subclassed to override some of the constructor functions, e.g. to construct objects of specialized
    subclasses of the BaSyx Python SDK object classes instead of these normal classes from the ``model`` package. To
    simplify this tasks, (nearly) all the constructor methods take a parameter ``object_type`` defaulting to the normal
    BaSyx Python SDK object class, that can be overridden in a derived function:

    .. code-block:: python

    .. code-block:: python

        class EnhancedSubmodel(model.Submodel):
            pass

        class EnhancedAASDecoder(StrictAASFromJsonDecoder):
            @classmethod
            def _construct_submodel(cls, dct, object_class=EnhancedSubmodel):
                return super()._construct_submodel(dct, object_class=object_class)


    :cvar failsafe: If ``True`` (the default), don't raise Exceptions for missing attributes and wrong types, but
                    instead skip defective objects and use logger to output warnings. Use StrictAASFromJsonDecoder for a
                    non-failsafe version.
    :cvar stripped: If ``True``, the JSON objects will be parsed in a stripped manner, excluding some attributes.
                    Defaults to ``False``.
                    See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
    """
    failsafe = True
    stripped = False

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    @classmethod
    def object_hook(cls, dct: Dict[str, object]) -> object:
        # Check if JSON object seems to be a deserializable AAS object (i.e. it has a modelType). Otherwise, the JSON
        #   object is returned as is, so it's possible to mix AAS objects with other data within a JSON structure.
        if 'modelType' not in dct:
            return dct

        # The following dict specifies a constructor method for all AAS classes that may be identified using the
        # ``modelType`` attribute in their JSON representation. Each of those constructor functions takes the JSON
        # representation of an object and tries to construct a Python object from it. Embedded objects that have a
        # modelType themselves are expected to be converted to the correct PythonType already. Additionally, each
        # function takes a bool parameter ``failsafe``, which indicates weather to log errors and skip defective objects
        # instead of raising an Exception.
        AAS_CLASS_PARSERS: Dict[str, Callable[[Dict[str, object]], object]] = {
            'AssetAdministrationShell': cls._construct_asset_administration_shell,
            'AssetInformation': cls._construct_asset_information,
            'SpecificAssetId': cls._construct_specific_asset_id,
            'ConceptDescription': cls._construct_concept_description,
            'Extension': cls._construct_extension,
            'Submodel': cls._construct_submodel,
            'Capability': cls._construct_capability,
            'Entity': cls._construct_entity,
            'BasicEventElement': cls._construct_basic_event_element,
            'Operation': cls._construct_operation,
            'RelationshipElement': cls._construct_relationship_element,
            'AnnotatedRelationshipElement': cls._construct_annotated_relationship_element,
            'SubmodelElementCollection': cls._construct_submodel_element_collection,
            'SubmodelElementList': cls._construct_submodel_element_list,
            'Blob': cls._construct_blob,
            'File': cls._construct_file,
            'MultiLanguageProperty': cls._construct_multi_language_property,
            'Property': cls._construct_property,
            'Range': cls._construct_range,
            'ReferenceElement': cls._construct_reference_element,
            'DataSpecificationIec61360': cls._construct_data_specification_iec61360,
        }

        # Get modelType and constructor function
        if not isinstance(dct['modelType'], str):
            logger.warning("JSON object has unexpected format of modelType: %s", dct['modelType'])
            # Even in strict mode, we consider 'modelType' attributes of wrong type as non-AAS objects instead of
            #   raising an exception. However, the object's type will probably checked later by read_json_aas_file() or
            #   _expect_type()
            return dct
        model_type = dct['modelType']
        if model_type not in AAS_CLASS_PARSERS:
            if not cls.failsafe:
                raise TypeError("Found JSON object with modelType=\"%s\", which is not a known AAS class" % model_type)
            logger.error("Found JSON object with modelType=\"%s\", which is not a known AAS class", model_type)
            return dct

        # Use constructor function to transform JSON representation into BaSyx Python SDK model object
        try:
            return AAS_CLASS_PARSERS[model_type](dct)
        except (KeyError, TypeError, model.AASConstraintViolation) as e:
            error_message = "Error while trying to convert JSON object into {}: {} >>> {}".format(
                model_type, e, pprint.pformat(dct, depth=2, width=2**14, compact=True))
            if cls.failsafe:
                logger.error(error_message, exc_info=e)
                # In failsafe mode, we return the raw JSON object dict, if there were errors while parsing an object, so
                #   a client application is able to handle this data. The read_json_aas_file() function and all
                #   constructors for complex objects will skip those items by using _expect_type().
                return dct
            else:
                raise (type(e) if isinstance(e, (KeyError, TypeError)) else TypeError)(error_message) from e

    # ##################################################################################################
    # Utility Methods used in constructor methods to add general attributes (from abstract base classes)
    # ##################################################################################################

    @classmethod
    def _amend_abstract_attributes(cls, obj: object, dct: Dict[str, object]) -> None:
        """
        Utility method to add the optional attributes of the abstract metaclasses Referable, Identifiable,
        HasSemantics, HasKind and Qualifiable to an object inheriting from any of these classes, if present

        :param obj: The object to amend its attributes
        :param dct: The object's dict representation from JSON
        """
        if isinstance(obj, model.Referable):
            if 'idShort' in dct:
                obj.id_short = _get_ts(dct, 'idShort', str)
            if 'category' in dct:
                obj.category = _get_ts(dct, 'category', str)
            if 'displayName' in dct:
                obj.display_name = cls._construct_lang_string_set(_get_ts(dct, 'displayName', list),
                                                                  model.MultiLanguageNameType)
            if 'description' in dct:
                obj.description = cls._construct_lang_string_set(_get_ts(dct, 'description', list),
                                                                 model.MultiLanguageTextType)
        if isinstance(obj, model.Identifiable):
            if 'administration' in dct:
                obj.administration = cls._construct_administrative_information(_get_ts(dct, 'administration', dict))
        if isinstance(obj, model.HasSemantics):
            if 'semanticId' in dct:
                obj.semantic_id = cls._construct_reference(_get_ts(dct, 'semanticId', dict))
            if 'supplementalSemanticIds' in dct:
                for ref in _get_ts(dct, 'supplementalSemanticIds', list):
                    obj.supplemental_semantic_id.append(cls._construct_reference(ref))
        # `HasKind` provides only mandatory, immutable attributes; so we cannot do anything here, after object creation.
        # However, the `cls._get_kind()` function may assist by retrieving them from the JSON object
        if isinstance(obj, model.Qualifiable) and not cls.stripped:
            if 'qualifiers' in dct:
                for constraint_dct in _get_ts(dct, 'qualifiers', list):
                    constraint = cls._construct_qualifier(constraint_dct)
                    obj.qualifier.add(constraint)
        if isinstance(obj, model.HasDataSpecification) and not cls.stripped:
            if 'embeddedDataSpecifications' in dct:
                for dspec in _get_ts(dct, 'embeddedDataSpecifications', list):
                    obj.embedded_data_specifications.append(
                        # TODO: remove the following type: ignore comment when mypy supports abstract types for Type[T]
                        # see https://github.com/python/mypy/issues/5374
                        model.EmbeddedDataSpecification(
                            data_specification=cls._construct_reference(_get_ts(dspec, 'dataSpecification', dict)),
                            data_specification_content=_get_ts(dspec, 'dataSpecificationContent',
                                                               model.DataSpecificationContent)  # type: ignore
                        )
                    )
        if isinstance(obj, model.HasExtension) and not cls.stripped:
            if 'extensions' in dct:
                for extension in _get_ts(dct, 'extensions', list):
                    obj.extension.add(cls._construct_extension(extension))

    @classmethod
    def _get_kind(cls, dct: Dict[str, object]) -> model.ModellingKind:
        """
        Utility method to get the kind of an HasKind object from its JSON representation.

        :param dct: The object's dict representation from JSON
        :return: The object's ``kind`` value
        """
        return MODELLING_KIND_INVERSE[_get_ts(dct, "kind", str)] if 'kind' in dct else model.ModellingKind.INSTANCE

    # #############################################################################
    # Helper Constructor Methods starting from here
    # #############################################################################

    # These constructor methods create objects that are not identified by a 'modelType' JSON attribute, so they can not
    # be called from the object_hook() method. Instead, they are called by other constructor functions to transform
    # embedded JSON data into the expected type at their location in the outer JSON object.

    @classmethod
    def _construct_key(cls, dct: Dict[str, object], object_class=model.Key) -> model.Key:
        return object_class(type_=KEY_TYPES_INVERSE[_get_ts(dct, 'type', str)],
                            value=_get_ts(dct, 'value', str))

    @classmethod
    def _construct_specific_asset_id(cls, dct: Dict[str, object], object_class=model.SpecificAssetId) \
            -> model.SpecificAssetId:
        # semantic_id can't be applied by _amend_abstract_attributes because specificAssetId is immutable
        return object_class(name=_get_ts(dct, 'name', str),
                            value=_get_ts(dct, 'value', str),
                            external_subject_id=cls._construct_external_reference(
                                _get_ts(dct, 'externalSubjectId', dict)) if 'externalSubjectId' in dct else None,
                            semantic_id=cls._construct_reference(_get_ts(dct, 'semanticId', dict))
                            if 'semanticId' in dct else None,
                            supplemental_semantic_id=[
                                cls._construct_reference(ref) for ref in
                                _get_ts(dct, 'supplementalSemanticIds', list)]
                            if 'supplementalSemanticIds' in dct else ())

    @classmethod
    def _construct_reference(cls, dct: Dict[str, object]) -> model.Reference:
        reference_type: Type[model.Reference] = REFERENCE_TYPES_INVERSE[_get_ts(dct, 'type', str)]
        if reference_type is model.ModelReference:
            return cls._construct_model_reference(dct, model.Referable)  # type: ignore
        elif reference_type is model.ExternalReference:
            return cls._construct_external_reference(dct)
        raise ValueError(f"Unsupported reference type {reference_type}!")

    @classmethod
    def _construct_external_reference(cls, dct: Dict[str, object], object_class=model.ExternalReference)\
            -> model.ExternalReference:
        reference_type: Type[model.Reference] = REFERENCE_TYPES_INVERSE[_get_ts(dct, 'type', str)]
        if reference_type is not model.ExternalReference:
            raise ValueError(f"Expected a reference of type {model.ExternalReference}, got {reference_type}!")
        keys = [cls._construct_key(key_data) for key_data in _get_ts(dct, "keys", list)]
        return object_class(tuple(keys), cls._construct_reference(_get_ts(dct, 'referredSemanticId', dict))
                            if 'referredSemanticId' in dct else None)

    @classmethod
    def _construct_model_reference(cls, dct: Dict[str, object], type_: Type[T], object_class=model.ModelReference)\
            -> model.ModelReference:
        reference_type: Type[model.Reference] = REFERENCE_TYPES_INVERSE[_get_ts(dct, 'type', str)]
        if reference_type is not model.ModelReference:
            raise ValueError(f"Expected a reference of type {model.ModelReference}, got {reference_type}!")
        keys = [cls._construct_key(key_data) for key_data in _get_ts(dct, "keys", list)]
        last_key_type = KEY_TYPES_CLASSES_INVERSE.get(keys[-1].type, type(None))
        if keys and not issubclass(last_key_type, type_):
            logger.warning("type %s of last key of reference to %s does not match reference type %s",
                           keys[-1].type.name, " / ".join(str(k) for k in keys), type_.__name__)
        # Infer type the model refence points to using `last_key_type` instead of `type_`.
        # `type_` is often a `model.Referable`, which is more abstract than e.g. a `model.ConceptDescription`,
        # leading to information loss while deserializing.
        # TODO Remove this fix, when this function is called with correct `type_`
        return object_class(tuple(keys), last_key_type,
                            cls._construct_reference(_get_ts(dct, 'referredSemanticId', dict))
                            if 'referredSemanticId' in dct else None)

    @classmethod
    def _construct_administrative_information(
            cls, dct: Dict[str, object], object_class=model.AdministrativeInformation)\
            -> model.AdministrativeInformation:
        ret = object_class()
        cls._amend_abstract_attributes(ret, dct)
        if 'version' in dct:
            ret.version = _get_ts(dct, 'version', str)
            if 'revision' in dct:
                ret.revision = _get_ts(dct, 'revision', str)
        elif 'revision' in dct:
            logger.warning("Ignoring 'revision' attribute of AdministrativeInformation object due to missing 'version'")
        if 'creator' in dct:
            ret.creator = cls._construct_reference(_get_ts(dct, 'creator', dict))
        if 'templateId' in dct:
            ret.template_id = _get_ts(dct, 'templateId', str)
        return ret

    @classmethod
    def _construct_operation_variable(cls, dct: Dict[str, object]) -> model.SubmodelElement:
        """
        Since we don't implement ``OperationVariable``, this constructor discards the wrapping ``OperationVariable``
        object and just returns the contained :class:`~basyx.aas.model.submodel.SubmodelElement`.
        """
        # TODO: remove the following type: ignore comments when mypy supports abstract types for Type[T]
        # see https://github.com/python/mypy/issues/5374
        return _get_ts(dct, 'value', model.SubmodelElement)  # type: ignore

    @classmethod
    def _construct_lang_string_set(cls, lst: List[Dict[str, object]], object_class: Type[LSS]) -> LSS:
        ret = {}
        for desc in lst:
            try:
                ret[_get_ts(desc, 'language', str)] = _get_ts(desc, 'text', str)
            except (KeyError, TypeError) as e:
                error_message = "Error while trying to convert JSON object into {}: {} >>> {}".format(
                    object_class.__name__, e, pprint.pformat(desc, depth=2, width=2 ** 14, compact=True))
                if cls.failsafe:
                    logger.error(error_message, exc_info=e)
                else:
                    raise type(e)(error_message) from e
        return object_class(ret)

    @classmethod
    def _construct_value_list(cls, dct: Dict[str, object]) -> model.ValueList:
        ret: model.ValueList = set()
        for element in _get_ts(dct, 'valueReferencePairs', list):
            try:
                ret.add(cls._construct_value_reference_pair(element))
            except (KeyError, TypeError) as e:
                error_message = "Error while trying to convert JSON object into ValueReferencePair: {} >>> {}".format(
                    e, pprint.pformat(element, depth=2, width=2 ** 14, compact=True))
                if cls.failsafe:
                    logger.error(error_message, exc_info=e)
                else:
                    raise type(e)(error_message) from e
        return ret

    @classmethod
    def _construct_value_reference_pair(cls, dct: Dict[str, object],
                                        object_class=model.ValueReferencePair) -> model.ValueReferencePair:
        return object_class(value=_get_ts(dct, 'value', str),
                            value_id=cls._construct_reference(_get_ts(dct, 'valueId', dict)))

    # #############################################################################
    # Direct Constructor Methods (for classes with `modelType`) starting from here
    # #############################################################################

    # These constructor methods create objects that *are* identified by a 'modelType' JSON attribute, so they can
    # be called from the object_hook() method directly.

    @classmethod
    def _construct_asset_information(cls, dct: Dict[str, object], object_class=model.AssetInformation)\
            -> model.AssetInformation:
        global_asset_id = None
        if 'globalAssetId' in dct:
            global_asset_id = _get_ts(dct, 'globalAssetId', str)
        specific_asset_id = set()
        if 'specificAssetIds' in dct:
            for desc_data in _get_ts(dct, "specificAssetIds", list):
                specific_asset_id.add(cls._construct_specific_asset_id(desc_data, model.SpecificAssetId))

        ret = object_class(asset_kind=ASSET_KIND_INVERSE[_get_ts(dct, 'assetKind', str)],
                           global_asset_id=global_asset_id,
                           specific_asset_id=specific_asset_id)
        cls._amend_abstract_attributes(ret, dct)

        if 'assetType' in dct:
            ret.asset_type = _get_ts(dct, 'assetType', str)
        if 'defaultThumbnail' in dct:
            ret.default_thumbnail = cls._construct_resource(_get_ts(dct, 'defaultThumbnail', dict))
        return ret

    @classmethod
    def _construct_asset_administration_shell(
            cls, dct: Dict[str, object], object_class=model.AssetAdministrationShell) -> model.AssetAdministrationShell:
        ret = object_class(
            asset_information=cls._construct_asset_information(_get_ts(dct, 'assetInformation', dict),
                                                               model.AssetInformation),
            id_=_get_ts(dct, 'id', str))
        cls._amend_abstract_attributes(ret, dct)
        if not cls.stripped and 'submodels' in dct:
            for sm_data in _get_ts(dct, 'submodels', list):
                ret.submodel.add(cls._construct_model_reference(sm_data, model.Submodel))
        if 'derivedFrom' in dct:
            ret.derived_from = cls._construct_model_reference(_get_ts(dct, 'derivedFrom', dict),
                                                              model.AssetAdministrationShell)
        return ret

    @classmethod
    def _construct_concept_description(cls, dct: Dict[str, object], object_class=model.ConceptDescription)\
            -> model.ConceptDescription:
        ret = object_class(id_=_get_ts(dct, 'id', str))
        cls._amend_abstract_attributes(ret, dct)
        if 'isCaseOf' in dct:
            for case_data in _get_ts(dct, "isCaseOf", list):
                ret.is_case_of.add(cls._construct_reference(case_data))
        return ret

    @classmethod
    def _construct_data_specification_iec61360(cls, dct: Dict[str, object],
                                               object_class=model.base.DataSpecificationIEC61360)\
            -> model.base.DataSpecificationIEC61360:
        ret = object_class(preferred_name=cls._construct_lang_string_set(_get_ts(dct, 'preferredName', list),
                                                                         model.PreferredNameTypeIEC61360))
        if 'dataType' in dct:
            ret.data_type = IEC61360_DATA_TYPES_INVERSE[_get_ts(dct, 'dataType', str)]
        if 'definition' in dct:
            ret.definition = cls._construct_lang_string_set(_get_ts(dct, 'definition', list),
                                                            model.DefinitionTypeIEC61360)
        if 'shortName' in dct:
            ret.short_name = cls._construct_lang_string_set(_get_ts(dct, 'shortName', list),
                                                            model.ShortNameTypeIEC61360)
        if 'unit' in dct:
            ret.unit = _get_ts(dct, 'unit', str)
        if 'unitId' in dct:
            ret.unit_id = cls._construct_reference(_get_ts(dct, 'unitId', dict))
        if 'sourceOfDefinition' in dct:
            ret.source_of_definition = _get_ts(dct, 'sourceOfDefinition', str)
        if 'symbol' in dct:
            ret.symbol = _get_ts(dct, 'symbol', str)
        if 'valueFormat' in dct:
            ret.value_format = _get_ts(dct, 'valueFormat', str)
        if 'valueList' in dct:
            ret.value_list = cls._construct_value_list(_get_ts(dct, 'valueList', dict))
        if 'value' in dct:
            ret.value = _get_ts(dct, 'value', str)
        if 'valueId' in dct:
            ret.value_id = cls._construct_reference(_get_ts(dct, 'valueId', dict))
        if 'levelType' in dct:
            for k, v in _get_ts(dct, 'levelType', dict).items():
                if v:
                    ret.level_types.add(IEC61360_LEVEL_TYPES_INVERSE[k])
        return ret

    @classmethod
    def _construct_entity(cls, dct: Dict[str, object], object_class=model.Entity) -> model.Entity:
        global_asset_id = None
        if 'globalAssetId' in dct:
            global_asset_id = _get_ts(dct, 'globalAssetId', str)
        specific_asset_id = set()
        if 'specificAssetIds' in dct:
            for desc_data in _get_ts(dct, "specificAssetIds", list):
                specific_asset_id.add(cls._construct_specific_asset_id(desc_data, model.SpecificAssetId))

        ret = object_class(id_short=None,
                           entity_type=ENTITY_TYPES_INVERSE[_get_ts(dct, "entityType", str)],
                           global_asset_id=global_asset_id,
                           specific_asset_id=specific_asset_id)
        cls._amend_abstract_attributes(ret, dct)
        if not cls.stripped and 'statements' in dct:
            for element in _get_ts(dct, "statements", list):
                if _expect_type(element, model.SubmodelElement, str(ret), cls.failsafe):
                    ret.statement.add(element)
        return ret

    @classmethod
    def _construct_qualifier(cls, dct: Dict[str, object], object_class=model.Qualifier) -> model.Qualifier:
        ret = object_class(type_=_get_ts(dct, 'type', str),
                           value_type=model.datatypes.XSD_TYPE_CLASSES[_get_ts(dct, 'valueType', str)])
        cls._amend_abstract_attributes(ret, dct)
        if 'value' in dct:
            ret.value = model.datatypes.from_xsd(_get_ts(dct, 'value', str), ret.value_type)
        if 'valueId' in dct:
            ret.value_id = cls._construct_reference(_get_ts(dct, 'valueId', dict))
        if 'kind' in dct:
            ret.kind = QUALIFIER_KIND_INVERSE[_get_ts(dct, 'kind', str)]
        return ret

    @classmethod
    def _construct_extension(cls, dct: Dict[str, object], object_class=model.Extension) -> model.Extension:
        ret = object_class(name=_get_ts(dct, 'name', str))
        cls._amend_abstract_attributes(ret, dct)
        if 'valueType' in dct:
            ret.value_type = model.datatypes.XSD_TYPE_CLASSES[_get_ts(dct, 'valueType', str)]
        if 'value' in dct:
            ret.value = model.datatypes.from_xsd(_get_ts(dct, 'value', str), ret.value_type)
        if 'refersTo' in dct:
            ret.refers_to = {cls._construct_model_reference(refers_to, model.Referable)  # type: ignore
                             for refers_to in _get_ts(dct, 'refersTo', list)}
        return ret

    @classmethod
    def _construct_submodel(cls, dct: Dict[str, object], object_class=model.Submodel) -> model.Submodel:
        ret = object_class(id_=_get_ts(dct, 'id', str),
                           kind=cls._get_kind(dct))
        cls._amend_abstract_attributes(ret, dct)
        if not cls.stripped and 'submodelElements' in dct:
            for element in _get_ts(dct, "submodelElements", list):
                if _expect_type(element, model.SubmodelElement, str(ret), cls.failsafe):
                    ret.submodel_element.add(element)
        return ret

    @classmethod
    def _construct_capability(cls, dct: Dict[str, object], object_class=model.Capability) -> model.Capability:
        ret = object_class(id_short=None)
        cls._amend_abstract_attributes(ret, dct)
        return ret

    @classmethod
    def _construct_basic_event_element(cls, dct: Dict[str, object], object_class=model.BasicEventElement) \
            -> model.BasicEventElement:
        # TODO: remove the following type: ignore comments when mypy supports abstract types for Type[T]
        # see https://github.com/python/mypy/issues/5374
        ret = object_class(id_short=None,
                           observed=cls._construct_model_reference(_get_ts(dct, 'observed', dict),
                                                                   model.Referable),  # type: ignore
                           direction=DIRECTION_INVERSE[_get_ts(dct, "direction", str)],
                           state=STATE_OF_EVENT_INVERSE[_get_ts(dct, "state", str)])
        cls._amend_abstract_attributes(ret, dct)
        if 'messageTopic' in dct:
            ret.message_topic = _get_ts(dct, 'messageTopic', str)
        if 'messageBroker' in dct:
            ret.message_broker = cls._construct_reference(_get_ts(dct, 'messageBroker', dict))
        if 'lastUpdate' in dct:
            ret.last_update = model.datatypes.from_xsd(_get_ts(dct, 'lastUpdate', str), model.datatypes.DateTime)
        if 'minInterval' in dct:
            ret.min_interval = model.datatypes.from_xsd(_get_ts(dct, 'minInterval', str), model.datatypes.Duration)
        if 'maxInterval' in dct:
            ret.max_interval = model.datatypes.from_xsd(_get_ts(dct, 'maxInterval', str), model.datatypes.Duration)
        return ret

    @classmethod
    def _construct_operation(cls, dct: Dict[str, object], object_class=model.Operation) -> model.Operation:
        ret = object_class(None)
        cls._amend_abstract_attributes(ret, dct)

        # Deserialize variables (they are not Referable, thus we don't
        for json_name, target in (('inputVariables', ret.input_variable),
                                  ('outputVariables', ret.output_variable),
                                  ('inoutputVariables', ret.in_output_variable)):
            if json_name in dct:
                for variable_data in _get_ts(dct, json_name, list):
                    try:
                        target.add(cls._construct_operation_variable(variable_data))
                    except (KeyError, TypeError) as e:
                        error_message = "Error while trying to convert JSON object into {} of {}: {}".format(
                            json_name, ret, pprint.pformat(variable_data, depth=2, width=2 ** 14, compact=True))
                        if cls.failsafe:
                            logger.error(error_message, exc_info=e)
                        else:
                            raise type(e)(error_message) from e
        return ret

    @classmethod
    def _construct_relationship_element(
            cls, dct: Dict[str, object], object_class=model.RelationshipElement) -> model.RelationshipElement:
        ret = object_class(id_short=None,
                           first=cls._construct_reference(_get_ts(dct, 'first', dict)),
                           second=cls._construct_reference(_get_ts(dct, 'second', dict)))
        cls._amend_abstract_attributes(ret, dct)
        return ret

    @classmethod
    def _construct_annotated_relationship_element(
            cls, dct: Dict[str, object], object_class=model.AnnotatedRelationshipElement)\
            -> model.AnnotatedRelationshipElement:
        ret = object_class(
            id_short=None,
            first=cls._construct_reference(_get_ts(dct, 'first', dict)),
            second=cls._construct_reference(_get_ts(dct, 'second', dict)))
        cls._amend_abstract_attributes(ret, dct)
        if not cls.stripped and 'annotations' in dct:
            for element in _get_ts(dct, 'annotations', list):
                if _expect_type(element, model.DataElement, str(ret), cls.failsafe):
                    ret.annotation.add(element)
        return ret

    @classmethod
    def _construct_submodel_element_collection(cls, dct: Dict[str, object],
                                               object_class=model.SubmodelElementCollection)\
            -> model.SubmodelElementCollection:
        ret = object_class(id_short=None)
        cls._amend_abstract_attributes(ret, dct)
        if not cls.stripped and 'value' in dct:
            for element in _get_ts(dct, "value", list):
                if _expect_type(element, model.SubmodelElement, str(ret), cls.failsafe):
                    ret.value.add(element)
        return ret

    @classmethod
    def _construct_submodel_element_list(cls, dct: Dict[str, object], object_class=model.SubmodelElementList)\
            -> model.SubmodelElementList:
        type_value_list_element = KEY_TYPES_CLASSES_INVERSE[
            KEY_TYPES_INVERSE[_get_ts(dct, 'typeValueListElement', str)]]
        if not issubclass(type_value_list_element, model.SubmodelElement):
            raise ValueError("Expected a SubmodelElementList with a typeValueListElement that is a subclass of"
                             f"{model.SubmodelElement}, got {type_value_list_element}!")
        order_relevant = _get_ts(dct, 'orderRelevant', bool) if 'orderRelevant' in dct else True
        semantic_id_list_element = cls._construct_reference(_get_ts(dct, 'semanticIdListElement', dict))\
            if 'semanticIdListElement' in dct else None
        value_type_list_element = model.datatypes.XSD_TYPE_CLASSES[_get_ts(dct, 'valueTypeListElement', str)]\
            if 'valueTypeListElement' in dct else None
        ret = object_class(id_short=None,
                           type_value_list_element=type_value_list_element,
                           order_relevant=order_relevant,
                           semantic_id_list_element=semantic_id_list_element,
                           value_type_list_element=value_type_list_element)
        cls._amend_abstract_attributes(ret, dct)
        if not cls.stripped and 'value' in dct:
            for element in _get_ts(dct, 'value', list):
                if _expect_type(element, type_value_list_element, str(ret), cls.failsafe):
                    ret.value.add(element)
        return ret

    @classmethod
    def _construct_blob(cls, dct: Dict[str, object], object_class=model.Blob) -> model.Blob:
        ret = object_class(id_short=None,
                           content_type=_get_ts(dct, "contentType", str))
        cls._amend_abstract_attributes(ret, dct)
        if 'value' in dct:
            ret.value = base64.b64decode(_get_ts(dct, 'value', str))
        return ret

    @classmethod
    def _construct_file(cls, dct: Dict[str, object], object_class=model.File) -> model.File:
        ret = object_class(id_short=None,
                           value=None,
                           content_type=_get_ts(dct, "contentType", str))
        cls._amend_abstract_attributes(ret, dct)
        if 'value' in dct and dct['value'] is not None:
            ret.value = _get_ts(dct, 'value', str)
        return ret

    @classmethod
    def _construct_resource(cls, dct: Dict[str, object], object_class=model.Resource) -> model.Resource:
        ret = object_class(path=_get_ts(dct, "path", str))
        cls._amend_abstract_attributes(ret, dct)
        if 'contentType' in dct and dct['contentType'] is not None:
            ret.content_type = _get_ts(dct, 'contentType', str)
        return ret

    @classmethod
    def _construct_multi_language_property(
            cls, dct: Dict[str, object], object_class=model.MultiLanguageProperty) -> model.MultiLanguageProperty:
        ret = object_class(id_short=None)
        cls._amend_abstract_attributes(ret, dct)
        if 'value' in dct and dct['value'] is not None:
            ret.value = cls._construct_lang_string_set(_get_ts(dct, 'value', list), model.MultiLanguageTextType)
        if 'valueId' in dct:
            ret.value_id = cls._construct_reference(_get_ts(dct, 'valueId', dict))
        return ret

    @classmethod
    def _construct_property(cls, dct: Dict[str, object], object_class=model.Property) -> model.Property:
        ret = object_class(id_short=None,
                           value_type=model.datatypes.XSD_TYPE_CLASSES[_get_ts(dct, 'valueType', str)],)
        cls._amend_abstract_attributes(ret, dct)
        if 'value' in dct and dct['value'] is not None:
            ret.value = model.datatypes.from_xsd(_get_ts(dct, 'value', str), ret.value_type)
        if 'valueId' in dct:
            ret.value_id = cls._construct_reference(_get_ts(dct, 'valueId', dict))
        return ret

    @classmethod
    def _construct_range(cls, dct: Dict[str, object], object_class=model.Range) -> model.Range:
        ret = object_class(id_short=None,
                           value_type=model.datatypes.XSD_TYPE_CLASSES[_get_ts(dct, 'valueType', str)],)
        cls._amend_abstract_attributes(ret, dct)
        if 'min' in dct and dct['min'] is not None:
            ret.min = model.datatypes.from_xsd(_get_ts(dct, 'min', str), ret.value_type)
        if 'max' in dct and dct['max'] is not None:
            ret.max = model.datatypes.from_xsd(_get_ts(dct, 'max', str), ret.value_type)
        return ret

    @classmethod
    def _construct_reference_element(
            cls, dct: Dict[str, object], object_class=model.ReferenceElement) -> model.ReferenceElement:
        ret = object_class(id_short=None,
                           value=None)
        cls._amend_abstract_attributes(ret, dct)
        if 'value' in dct and dct['value'] is not None:
            ret.value = cls._construct_reference(_get_ts(dct, 'value', dict))
        return ret


class StrictAASFromJsonDecoder(AASFromJsonDecoder):
    """
    A strict version of the AASFromJsonDecoder class for deserializing Asset Administration Shell data from the
    official JSON format

    This version has set ``failsafe = False``, which will lead to Exceptions raised for every missing attribute or wrong
    object type.
    """
    failsafe = False


class StrippedAASFromJsonDecoder(AASFromJsonDecoder):
    """
    Decoder for stripped JSON objects. Used in the HTTP adapter.
    """
    stripped = True


class StrictStrippedAASFromJsonDecoder(StrictAASFromJsonDecoder, StrippedAASFromJsonDecoder):
    """
    Non-failsafe decoder for stripped JSON objects.
    """
    pass


def _select_decoder(failsafe: bool, stripped: bool, decoder: Optional[Type[AASFromJsonDecoder]]) \
        -> Type[AASFromJsonDecoder]:
    """
    Returns the correct decoder based on the parameters failsafe and stripped. If a decoder class is given, failsafe
    and stripped are ignored.

    :param failsafe: If ``True``, a failsafe decoder is selected. Ignored if a decoder class is specified.
    :param stripped: If ``True``, a decoder for parsing stripped JSON objects is selected. Ignored if a decoder class is
                     specified.
    :param decoder: Is returned, if specified.
    :return: An :class:`~.AASFromJsonDecoder` (sub)class.
    """
    if decoder is not None:
        return decoder
    if failsafe:
        if stripped:
            return StrippedAASFromJsonDecoder
        return AASFromJsonDecoder
    else:
        if stripped:
            return StrictStrippedAASFromJsonDecoder
        return StrictAASFromJsonDecoder


def read_aas_json_file_into(object_store: model.AbstractObjectStore, file: PathOrIO, replace_existing: bool = False,
                            ignore_existing: bool = False, failsafe: bool = True, stripped: bool = False,
                            decoder: Optional[Type[AASFromJsonDecoder]] = None) -> Set[model.Identifier]:
    """
    Read an Asset Administration Shell JSON file according to 'Details of the Asset Administration Shell', chapter 5.5
    into a given object store.

    :param object_store: The :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` in which the
                         identifiable objects should be stored
    :param file: A filename or file-like object to read the JSON-serialized data from
    :param replace_existing: Whether to replace existing objects with the same identifier in the object store or not
    :param ignore_existing: Whether to ignore existing objects (e.g. log a message) or raise an error.
                            This parameter is ignored if replace_existing is ``True``.
    :param failsafe: If ``True``, the document is parsed in a failsafe way: Missing attributes and elements are logged
                     instead of causing exceptions. Defect objects are skipped.
                     This parameter is ignored if a decoder class is specified.
    :param stripped: If ``True``, stripped JSON objects are parsed.
                     See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
                     This parameter is ignored if a decoder class is specified.
    :param decoder: The decoder class used to decode the JSON objects
    :raises KeyError: **Non-failsafe**: Encountered a duplicate identifier
    :raises KeyError: Encountered an identifier that already exists in the given ``object_store`` with both
                     ``replace_existing`` and ``ignore_existing`` set to ``False``
    :raises (~basyx.aas.model.base.AASConstraintViolation, KeyError, ValueError, TypeError): **Non-failsafe**:
        Errors during construction of the objects
    :raises TypeError: **Non-failsafe**: Encountered an element in the wrong list
                                         (e.g. an AssetAdministrationShell in ``submodels``)
    :return: A set of :class:`Identifiers <basyx.aas.model.base.Identifier>` that were added to object_store
    """
    ret: Set[model.Identifier] = set()
    decoder_ = _select_decoder(failsafe, stripped, decoder)

    # json.load() accepts TextIO and BinaryIO
    cm: ContextManager[IO]
    if isinstance(file, get_args(Path)):
        # 'file' is a path, needs to be opened first
        cm = open(file, "r", encoding="utf-8-sig")
    else:
        # 'file' is not a path, thus it must already be IO
        # mypy seems to have issues narrowing the type due to get_args()
        cm = contextlib.nullcontext(file)  # type: ignore[arg-type]

    # read, parse and convert JSON file
    with cm as fp:
        data = json.load(fp, cls=decoder_)

    for name, expected_type in (('assetAdministrationShells', model.AssetAdministrationShell),
                                ('submodels', model.Submodel),
                                ('conceptDescriptions', model.ConceptDescription)):
        try:
            lst = _get_ts(data, name, list)
        except (KeyError, TypeError):
            continue

        for item in lst:
            error_message = "Expected a {} in list '{}', but found {}".format(
                expected_type.__name__, name, repr(item))
            if isinstance(item, model.Identifiable):
                if not isinstance(item, expected_type):
                    if decoder_.failsafe:
                        logger.warning("{} was in wrong list '{}'; nevertheless, we'll use it".format(item, name))
                    else:
                        raise TypeError(error_message)
                if item.id in ret:
                    error_message = f"{item} has a duplicate identifier already parsed in the document!"
                    if not decoder_.failsafe:
                        raise KeyError(error_message)
                    logger.error(error_message + " skipping it...")
                    continue
                existing_element = object_store.get(item.id)
                if existing_element is not None:
                    if not replace_existing:
                        error_message = f"object with identifier {item.id} already exists " \
                                        f"in the object store: {existing_element}!"
                        if not ignore_existing:
                            raise KeyError(error_message + f" failed to insert {item}!")
                        logger.info(error_message + f" skipping insertion of {item}...")
                        continue
                    object_store.discard(existing_element)
                object_store.add(item)
                ret.add(item.id)
            elif decoder_.failsafe:
                logger.error(error_message)
            else:
                raise TypeError(error_message)
    return ret


def read_aas_json_file(file: PathOrIO, **kwargs) -> model.DictObjectStore[model.Identifiable]:
    """
    A wrapper of :meth:`~basyx.aas.adapter.json.json_deserialization.read_aas_json_file_into`, that reads all objects
    in an empty :class:`~basyx.aas.model.provider.DictObjectStore`. This function supports the same keyword arguments as
    :meth:`~basyx.aas.adapter.json.json_deserialization.read_aas_json_file_into`.

    :param file: A filename or file-like object to read the JSON-serialized data from
    :param kwargs: Keyword arguments passed to :meth:`read_aas_json_file_into`
    :raises KeyError: **Non-failsafe**: Encountered a duplicate identifier
    :raises (~basyx.aas.model.base.AASConstraintViolation, KeyError, ValueError, TypeError): **Non-failsafe**:
        Errors during construction of the objects
    :raises TypeError: **Non-failsafe**: Encountered an element in the wrong list
                                         (e.g. an AssetAdministrationShell in ``submodels``)
    :return: A :class:`~basyx.aas.model.provider.DictObjectStore` containing all AAS objects from the JSON file
    """
    object_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    read_aas_json_file_into(object_store, file, **kwargs)
    return object_store
