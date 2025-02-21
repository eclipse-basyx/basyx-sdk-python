# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.xml.xml_serialization:

Module for serializing Asset Administration Shell data to the official XML format

How to use:

- For generating an XML-File from a :class:`~basyx.aas.model.provider.AbstractObjectStore`, check out the function
  :func:`write_aas_xml_file`.
- For serializing any object to an XML fragment, that fits the XML specification from 'Details of the
  Asset Administration Shell', chapter 5.4, you can either use :func:`object_to_xml_element`, which serializes a given
  object and returns it as :class:`~lxml.etree._Element`, **or** :func:`write_aas_xml_element`, which does the same
  thing, but writes the :class:`~lxml.etree._Element` to a file instead of returning it.
  As a third alternative, you can also use the functions ``<class_name>_to_xml()`` directly.

.. attention::
    Unlike the XML deserialization and the JSON (de-)serialization, the XML serialization only supports
    :class:`~typing.BinaryIO` and not :class:`~typing.TextIO`. Thus, if you open files by yourself, you have to open
    them in binary mode, see the mode table of :func:`open`.

    .. code:: python

        # wb = open for writing + binary mode
        with open("example.xml", "wb") as fp:
            write_aas_xml_file(fp, object_store)
"""

from lxml import etree
from typing import Callable, Dict, Optional, Type
import base64

from basyx.aas import model
from .. import _generic

NS_AAS = _generic.XML_NS_AAS


# ##############################################################
# functions to manipulate etree.Elements more effectively
# ##############################################################

def _generate_element(name: str,
                      text: Optional[str] = None,
                      attributes: Optional[Dict] = None) -> etree._Element:
    """
    generate an :class:`~lxml.etree._Element` object

    :param name: namespace+tag_name of the element
    :param text: Text of the element. Default is None
    :param attributes: Attributes of the elements in form of a dict ``{"attribute_name": "attribute_content"}``
    :return: :class:`~lxml.etree._Element` object
    """
    et_element = etree.Element(name)
    if text:
        et_element.text = text
    if attributes:
        for key, value in attributes.items():
            et_element.set(key, value)
    return et_element


def boolean_to_xml(obj: bool) -> str:
    """
    Serialize a boolean to XML

    :param obj: Boolean (``True``, ``False``)
    :return: String in the XML accepted form (``true``, ``false``)
    """
    if obj:
        return "true"
    else:
        return "false"


# ##############################################################
# transformation functions to serialize abstract classes from model.base
# ##############################################################


def abstract_classes_to_xml(tag: str, obj: object) -> etree._Element:
    """
    Generates an XML element and adds attributes of abstract base classes of ``obj``.

    If the object obj is inheriting from any abstract AAS class, this function adds all the serialized information of
    those abstract classes to the generated element.

    :param tag: Tag of the element
    :param obj: An object of the AAS
    :return: Parent element with the serialized information from the abstract classes
    """
    elm = _generate_element(tag)
    if isinstance(obj, model.HasExtension):
        if obj.extension:
            et_extension = _generate_element(NS_AAS + "extensions")
            for extension in obj.extension:
                if isinstance(extension, model.Extension):
                    et_extension.append(extension_to_xml(extension, tag=NS_AAS + "extension"))
            elm.append(et_extension)
    if isinstance(obj, model.Referable):
        if obj.category:
            elm.append(_generate_element(name=NS_AAS + "category", text=obj.category))
        if obj.id_short and not isinstance(obj.parent, model.SubmodelElementList):
            elm.append(_generate_element(name=NS_AAS + "idShort", text=obj.id_short))
        if obj.display_name:
            elm.append(lang_string_set_to_xml(obj.display_name, tag=NS_AAS + "displayName"))
        if obj.description:
            elm.append(lang_string_set_to_xml(obj.description, tag=NS_AAS + "description"))
    if isinstance(obj, model.Identifiable):
        if obj.administration:
            elm.append(administrative_information_to_xml(obj.administration))
        elm.append(_generate_element(name=NS_AAS + "id", text=obj.id))
    if isinstance(obj, model.HasKind):
        if obj.kind is model.ModellingKind.TEMPLATE:
            elm.append(_generate_element(name=NS_AAS + "kind", text="Template"))
        else:
            # then modelling-kind is Instance
            elm.append(_generate_element(name=NS_AAS + "kind", text="Instance"))
    if isinstance(obj, model.HasSemantics):
        if obj.semantic_id:
            elm.append(reference_to_xml(obj.semantic_id, tag=NS_AAS+"semanticId"))
        if obj.supplemental_semantic_id:
            et_supplemental_semantic_ids = _generate_element(NS_AAS + "supplementalSemanticIds")
            for supplemental_semantic_id in obj.supplemental_semantic_id:
                et_supplemental_semantic_ids.append(reference_to_xml(supplemental_semantic_id, NS_AAS+"reference"))
            elm.append(et_supplemental_semantic_ids)
    if isinstance(obj, model.Qualifiable):
        if obj.qualifier:
            et_qualifier = _generate_element(NS_AAS + "qualifiers")
            for qualifier in obj.qualifier:
                et_qualifier.append(qualifier_to_xml(qualifier, tag=NS_AAS+"qualifier"))
            elm.append(et_qualifier)
    if isinstance(obj, model.HasDataSpecification):
        if obj.embedded_data_specifications:
            et_embedded_data_specifications = _generate_element(NS_AAS + "embeddedDataSpecifications")
            for eds in obj.embedded_data_specifications:
                et_embedded_data_specifications.append(embedded_data_specification_to_xml(eds))
            elm.append(et_embedded_data_specifications)
    return elm


# ##############################################################
# transformation functions to serialize classes from model.base
# ##############################################################


def _value_to_xml(value: model.ValueDataType,
                  value_type: model.DataTypeDefXsd,
                  tag: str = NS_AAS+"value") -> etree._Element:
    """
    Serialization of objects of :class:`~basyx.aas.model.base.ValueDataType` to XML

    :param value: :class:`~basyx.aas.model.base.ValueDataType` object
    :param value_type: Corresponding :class:`~basyx.aas.model.base.DataTypeDefXsd`
    :param tag: tag of the serialized :class:`~basyx.aas.model.base.ValueDataType` object
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    # todo: add "{NS_XSI+"type": "xs:"+model.datatypes.XSD_TYPE_NAMES[value_type]}" as attribute, if the schema allows
    #  it
    # TODO: if this is ever changed, check value_reference_pair_to_xml()
    return _generate_element(tag,
                             text=model.datatypes.xsd_repr(value))


def lang_string_set_to_xml(obj: model.LangStringSet, tag: str) -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.LangStringSet` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.LangStringSet`
    :param tag: Namespace+Tag name of the returned XML element.
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    LANG_STRING_SET_TAGS: Dict[Type[model.LangStringSet], str] = {k: NS_AAS + v for k, v in {
        model.MultiLanguageNameType: "langStringNameType",
        model.MultiLanguageTextType: "langStringTextType",
        model.DefinitionTypeIEC61360: "langStringDefinitionTypeIec61360",
        model.PreferredNameTypeIEC61360: "langStringPreferredNameTypeIec61360",
        model.ShortNameTypeIEC61360: "langStringShortNameTypeIec61360"
    }.items()}
    et_lss = _generate_element(name=tag)
    for language, text in obj.items():
        et_ls = _generate_element(name=LANG_STRING_SET_TAGS[type(obj)])
        et_ls.append(_generate_element(name=NS_AAS + "language", text=language))
        et_ls.append(_generate_element(name=NS_AAS + "text", text=text))
        et_lss.append(et_ls)
    return et_lss


def administrative_information_to_xml(obj: model.AdministrativeInformation,
                                      tag: str = NS_AAS+"administration") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.AdministrativeInformation` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.AdministrativeInformation`
    :param tag: Namespace+Tag of the serialized element. Default is ``aas:administration``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_administration = abstract_classes_to_xml(tag, obj)
    if obj.version:
        et_administration.append(_generate_element(name=NS_AAS + "version", text=obj.version))
    if obj.revision:
        et_administration.append(_generate_element(name=NS_AAS + "revision", text=obj.revision))
    if obj.creator:
        et_administration.append(reference_to_xml(obj.creator, tag=NS_AAS + "creator"))
    if obj.template_id:
        et_administration.append(_generate_element(name=NS_AAS + "templateId", text=obj.template_id))
    return et_administration


def data_element_to_xml(obj: model.DataElement) -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.DataElement` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.DataElement`
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    if isinstance(obj, model.MultiLanguageProperty):
        return multi_language_property_to_xml(obj)
    if isinstance(obj, model.Property):
        return property_to_xml(obj)
    if isinstance(obj, model.Range):
        return range_to_xml(obj)
    if isinstance(obj, model.Blob):
        return blob_to_xml(obj)
    if isinstance(obj, model.File):
        return file_to_xml(obj)
    if isinstance(obj, model.ReferenceElement):
        return reference_element_to_xml(obj)
    raise AssertionError(f"Type {obj.__class__.__name__} is not yet supported by the XML serialization!")


def key_to_xml(obj: model.Key, tag: str = NS_AAS+"key") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.Key` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.Key`
    :param tag: Namespace+Tag of the returned element. Default is ``aas:key``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_key = _generate_element(tag)
    et_key.append(_generate_element(name=NS_AAS + "type", text=_generic.KEY_TYPES[obj.type]))
    et_key.append(_generate_element(name=NS_AAS + "value", text=obj.value))
    return et_key


def reference_to_xml(obj: model.Reference, tag: str = NS_AAS+"reference") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.Reference` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.Reference`
    :param tag: Namespace+Tag of the returned element. Default is ``aas:reference``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_reference = _generate_element(tag)
    et_reference.append(_generate_element(NS_AAS + "type", text=_generic.REFERENCE_TYPES[obj.__class__]))
    if obj.referred_semantic_id is not None:
        et_reference.append(reference_to_xml(obj.referred_semantic_id, NS_AAS + "referredSemanticId"))
    et_keys = _generate_element(name=NS_AAS + "keys")
    for aas_key in obj.key:
        et_keys.append(key_to_xml(aas_key))
    et_reference.append(et_keys)

    return et_reference


def qualifier_to_xml(obj: model.Qualifier, tag: str = NS_AAS+"qualifier") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.Qualifier` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.Qualifier`
    :param tag: Namespace+Tag of the serialized ElementTree object. Default is ``aas:qualifier``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_qualifier = abstract_classes_to_xml(tag, obj)
    et_qualifier.append(_generate_element(NS_AAS + "kind", text=_generic.QUALIFIER_KIND[obj.kind]))
    et_qualifier.append(_generate_element(NS_AAS + "type", text=obj.type))
    et_qualifier.append(_generate_element(NS_AAS + "valueType", text=model.datatypes.XSD_TYPE_NAMES[obj.value_type]))
    if obj.value:
        et_qualifier.append(_value_to_xml(obj.value, obj.value_type))
    if obj.value_id:
        et_qualifier.append(reference_to_xml(obj.value_id, NS_AAS+"valueId"))
    return et_qualifier


def extension_to_xml(obj: model.Extension, tag: str = NS_AAS+"extension") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.Extension` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.Extension`
    :param tag: Namespace+Tag of the serialized ElementTree object. Default is ``aas:extension``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_extension = abstract_classes_to_xml(tag, obj)
    et_extension.append(_generate_element(NS_AAS + "name", text=obj.name))
    if obj.value_type:
        et_extension.append(_generate_element(NS_AAS + "valueType",
                                              text=model.datatypes.XSD_TYPE_NAMES[obj.value_type]))
    if obj.value:
        et_extension.append(_value_to_xml(obj.value, obj.value_type))  # type: ignore # (value_type could be None)
    if len(obj.refers_to) > 0:
        refers_to = _generate_element(NS_AAS+"refersTo")
        for reference in obj.refers_to:
            refers_to.append(reference_to_xml(reference, NS_AAS+"reference"))
        et_extension.append(refers_to)
    return et_extension


def value_reference_pair_to_xml(obj: model.ValueReferencePair,
                                tag: str = NS_AAS+"valueReferencePair") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.ValueReferencePair` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.ValueReferencePair`
    :param tag: Namespace+Tag of the serialized element. Default is ``aas:valueReferencePair``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_vrp = _generate_element(tag)
    # TODO: value_type isn't used at all by _value_to_xml(), thus we can ignore the type here for now
    et_vrp.append(_generate_element(NS_AAS+"value", text=obj.value))  # type: ignore
    et_vrp.append(reference_to_xml(obj.value_id, NS_AAS+"valueId"))
    return et_vrp


def value_list_to_xml(obj: model.ValueList,
                      tag: str = NS_AAS+"valueList") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.ValueList` to XML

    todo: couldn't find it in the official schema, so guessing how to implement serialization

    :param obj: Object of class :class:`~basyx.aas.model.base.ValueList`
    :param tag: Namespace+Tag of the serialized element. Default is ``aas:valueList``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_value_list = _generate_element(tag)
    et_value_reference_pairs = _generate_element(NS_AAS+"valueReferencePairs")
    for aas_reference_pair in obj:
        et_value_reference_pairs.append(value_reference_pair_to_xml(aas_reference_pair, NS_AAS+"valueReferencePair"))
    et_value_list.append(et_value_reference_pairs)
    return et_value_list


# ##############################################################
# transformation functions to serialize classes from model.aas
# ##############################################################


def specific_asset_id_to_xml(obj: model.SpecificAssetId, tag: str = NS_AAS + "specificAssetId") \
        -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.SpecificAssetId` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.SpecificAssetId`
    :param tag: Namespace+Tag of the ElementTree object. Default is ``aas:identifierKeyValuePair``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_asset_information = abstract_classes_to_xml(tag, obj)
    et_asset_information.append(_generate_element(name=NS_AAS + "name", text=obj.name))
    et_asset_information.append(_generate_element(name=NS_AAS + "value", text=obj.value))
    if obj.external_subject_id:
        et_asset_information.append(reference_to_xml(obj.external_subject_id, NS_AAS + "externalSubjectId"))

    return et_asset_information


def asset_information_to_xml(obj: model.AssetInformation, tag: str = NS_AAS+"assetInformation") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.aas.AssetInformation` to XML

    :param obj: Object of class :class:`~basyx.aas.model.aas.AssetInformation`
    :param tag: Namespace+Tag of the ElementTree object. Default is ``aas:assetInformation``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_asset_information = abstract_classes_to_xml(tag, obj)
    et_asset_information.append(_generate_element(name=NS_AAS + "assetKind", text=_generic.ASSET_KIND[obj.asset_kind]))
    if obj.global_asset_id:
        et_asset_information.append(_generate_element(name=NS_AAS + "globalAssetId", text=obj.global_asset_id))
    if obj.specific_asset_id:
        et_specific_asset_id = _generate_element(name=NS_AAS + "specificAssetIds")
        for specific_asset_id in obj.specific_asset_id:
            et_specific_asset_id.append(specific_asset_id_to_xml(specific_asset_id, NS_AAS + "specificAssetId"))
        et_asset_information.append(et_specific_asset_id)
    if obj.asset_type:
        et_asset_information.append(_generate_element(name=NS_AAS + "assetType", text=obj.asset_type))
    if obj.default_thumbnail:
        et_asset_information.append(resource_to_xml(obj.default_thumbnail, NS_AAS+"defaultThumbnail"))

    return et_asset_information


def concept_description_to_xml(obj: model.ConceptDescription,
                               tag: str = NS_AAS+"conceptDescription") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.concept.ConceptDescription` to XML

    :param obj: Object of class :class:`~basyx.aas.model.concept.ConceptDescription`
    :param tag: Namespace+Tag of the ElementTree object. Default is ``aas:conceptDescription``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_concept_description = abstract_classes_to_xml(tag, obj)
    if obj.is_case_of:
        et_is_case_of = _generate_element(NS_AAS+"isCaseOf")
        for reference in obj.is_case_of:
            et_is_case_of.append(reference_to_xml(reference, NS_AAS+"reference"))
        et_concept_description.append(et_is_case_of)
    return et_concept_description


def embedded_data_specification_to_xml(obj: model.EmbeddedDataSpecification,
                                       tag: str = NS_AAS+"embeddedDataSpecification") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.EmbeddedDataSpecification` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.EmbeddedDataSpecification`
    :param tag: Namespace+Tag of the ElementTree object. Default is ``aas:embeddedDataSpecification``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_embedded_data_specification = abstract_classes_to_xml(tag, obj)
    et_embedded_data_specification.append(reference_to_xml(obj.data_specification, tag=NS_AAS + "dataSpecification"))
    et_embedded_data_specification.append(data_specification_content_to_xml(obj.data_specification_content))
    return et_embedded_data_specification


def data_specification_content_to_xml(obj: model.DataSpecificationContent,
                                      tag: str = NS_AAS+"dataSpecificationContent") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.DataSpecificationContent` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.DataSpecificationContent`
    :param tag: Namespace+Tag of the ElementTree object. Default is ``aas:dataSpecificationContent``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_data_specification_content = abstract_classes_to_xml(tag, obj)
    if isinstance(obj, model.DataSpecificationIEC61360):
        et_data_specification_content.append(data_specification_iec61360_to_xml(obj))
    else:
        raise TypeError(f"Serialization of {obj.__class__} to XML is not supported!")
    return et_data_specification_content


def data_specification_iec61360_to_xml(obj: model.DataSpecificationIEC61360,
                                       tag: str = NS_AAS+"dataSpecificationIec61360") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.DataSpecificationIEC61360` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.DataSpecificationIEC61360`
    :param tag: Namespace+Tag of the ElementTree object. Default is ``aas:dataSpecificationIec61360``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_data_specification_iec61360 = abstract_classes_to_xml(tag, obj)
    et_data_specification_iec61360.append(lang_string_set_to_xml(obj.preferred_name, NS_AAS + "preferredName"))
    if obj.short_name is not None:
        et_data_specification_iec61360.append(lang_string_set_to_xml(obj.short_name, NS_AAS + "shortName"))
    if obj.unit is not None:
        et_data_specification_iec61360.append(_generate_element(NS_AAS + "unit", text=obj.unit))
    if obj.unit_id is not None:
        et_data_specification_iec61360.append(reference_to_xml(obj.unit_id, NS_AAS + "unitId"))
    if obj.source_of_definition is not None:
        et_data_specification_iec61360.append(_generate_element(NS_AAS + "sourceOfDefinition",
                                                                text=obj.source_of_definition))
    if obj.symbol is not None:
        et_data_specification_iec61360.append(_generate_element(NS_AAS + "symbol", text=obj.symbol))
    if obj.data_type is not None:
        et_data_specification_iec61360.append(_generate_element(NS_AAS + "dataType",
                                                                text=_generic.IEC61360_DATA_TYPES[obj.data_type]))
    if obj.definition is not None:
        et_data_specification_iec61360.append(lang_string_set_to_xml(obj.definition, NS_AAS + "definition"))

    if obj.value_format is not None:
        et_data_specification_iec61360.append(_generate_element(NS_AAS + "valueFormat", text=obj.value_format))
    # this can be either None or an empty set, both of which are equivalent to the bool false
    # thus we don't check 'is not None' for this property
    if obj.value_list:
        et_data_specification_iec61360.append(value_list_to_xml(obj.value_list))
    if obj.value is not None:
        et_data_specification_iec61360.append(_generate_element(NS_AAS + "value", text=obj.value))
    if obj.level_types:
        et_level_types = _generate_element(NS_AAS + "levelType")
        for k, v in _generic.IEC61360_LEVEL_TYPES.items():
            et_level_types.append(_generate_element(NS_AAS + v, text=boolean_to_xml(k in obj.level_types)))
        et_data_specification_iec61360.append(et_level_types)
    return et_data_specification_iec61360


def asset_administration_shell_to_xml(obj: model.AssetAdministrationShell,
                                      tag: str = NS_AAS+"assetAdministrationShell") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.aas.AssetAdministrationShell` to XML

    :param obj: Object of class :class:`~basyx.aas.model.aas.AssetAdministrationShell`
    :param tag: Namespace+Tag of the ElementTree object. Default is ``aas:assetAdministrationShell``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_aas = abstract_classes_to_xml(tag, obj)
    if obj.derived_from:
        et_aas.append(reference_to_xml(obj.derived_from, tag=NS_AAS+"derivedFrom"))
    et_aas.append(asset_information_to_xml(obj.asset_information, tag=NS_AAS + "assetInformation"))
    if obj.submodel:
        et_submodels = _generate_element(NS_AAS + "submodels")
        for reference in obj.submodel:
            et_submodels.append(reference_to_xml(reference, tag=NS_AAS+"reference"))
        et_aas.append(et_submodels)
    return et_aas


# ##############################################################
# transformation functions to serialize classes from model.submodel
# ##############################################################


def submodel_element_to_xml(obj: model.SubmodelElement) -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.SubmodelElement` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.SubmodelElement`
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    if isinstance(obj, model.DataElement):
        return data_element_to_xml(obj)
    if isinstance(obj, model.BasicEventElement):
        return basic_event_element_to_xml(obj)
    if isinstance(obj, model.Capability):
        return capability_to_xml(obj)
    if isinstance(obj, model.Entity):
        return entity_to_xml(obj)
    if isinstance(obj, model.Operation):
        return operation_to_xml(obj)
    if isinstance(obj, model.AnnotatedRelationshipElement):
        return annotated_relationship_element_to_xml(obj)
    if isinstance(obj, model.RelationshipElement):
        return relationship_element_to_xml(obj)
    if isinstance(obj, model.SubmodelElementCollection):
        return submodel_element_collection_to_xml(obj)
    if isinstance(obj, model.SubmodelElementList):
        return submodel_element_list_to_xml(obj)
    raise AssertionError(f"Type {obj.__class__.__name__} is not yet supported by the XML serialization!")


def submodel_to_xml(obj: model.Submodel,
                    tag: str = NS_AAS+"submodel") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.Submodel` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.Submodel`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:submodel``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_submodel = abstract_classes_to_xml(tag, obj)
    if obj.submodel_element:
        et_submodel_elements = _generate_element(NS_AAS + "submodelElements")
        for submodel_element in obj.submodel_element:
            et_submodel_elements.append(submodel_element_to_xml(submodel_element))
        et_submodel.append(et_submodel_elements)
    return et_submodel


def property_to_xml(obj: model.Property,
                    tag: str = NS_AAS+"property") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.Property` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.Property`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:property``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_property = abstract_classes_to_xml(tag, obj)
    et_property.append(_generate_element(NS_AAS + "valueType", text=model.datatypes.XSD_TYPE_NAMES[obj.value_type]))
    if obj.value is not None:
        et_property.append(_value_to_xml(obj.value, obj.value_type))
    if obj.value_id:
        et_property.append(reference_to_xml(obj.value_id, NS_AAS + "valueId"))
    return et_property


def multi_language_property_to_xml(obj: model.MultiLanguageProperty,
                                   tag: str = NS_AAS+"multiLanguageProperty") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.MultiLanguageProperty` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.MultiLanguageProperty`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:multiLanguageProperty``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_multi_language_property = abstract_classes_to_xml(tag, obj)
    if obj.value:
        et_multi_language_property.append(lang_string_set_to_xml(obj.value, tag=NS_AAS + "value"))
    if obj.value_id:
        et_multi_language_property.append(reference_to_xml(obj.value_id, NS_AAS+"valueId"))
    return et_multi_language_property


def range_to_xml(obj: model.Range,
                 tag: str = NS_AAS+"range") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.Range` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.Range`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:range``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_range = abstract_classes_to_xml(tag, obj)
    et_range.append(_generate_element(name=NS_AAS + "valueType",
                                      text=model.datatypes.XSD_TYPE_NAMES[obj.value_type]))
    if obj.min is not None:
        et_range.append(_value_to_xml(obj.min, obj.value_type, tag=NS_AAS + "min"))
    if obj.max is not None:
        et_range.append(_value_to_xml(obj.max, obj.value_type, tag=NS_AAS + "max"))
    return et_range


def blob_to_xml(obj: model.Blob,
                tag: str = NS_AAS+"blob") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.Blob` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.Blob`
    :param tag: Namespace+Tag of the serialized element. Default is ``aas:blob``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_blob = abstract_classes_to_xml(tag, obj)
    et_value = etree.Element(NS_AAS + "value")
    if obj.value is not None:
        et_value.text = base64.b64encode(obj.value).decode()
    et_blob.append(et_value)
    et_blob.append(_generate_element(NS_AAS + "contentType", text=obj.content_type))
    return et_blob


def file_to_xml(obj: model.File,
                tag: str = NS_AAS+"file") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.File` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.File`
    :param tag: Namespace+Tag of the serialized element. Default is ``aas:file``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_file = abstract_classes_to_xml(tag, obj)
    if obj.value:
        et_file.append(_generate_element(NS_AAS + "value", text=obj.value))
    et_file.append(_generate_element(NS_AAS + "contentType", text=obj.content_type))
    return et_file


def resource_to_xml(obj: model.Resource,
                    tag: str = NS_AAS+"resource") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.base.Resource` to XML

    :param obj: Object of class :class:`~basyx.aas.model.base.Resource`
    :param tag: Namespace+Tag of the serialized element. Default is ``aas:resource``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_resource = abstract_classes_to_xml(tag, obj)
    et_resource.append(_generate_element(NS_AAS + "path", text=obj.path))
    if obj.content_type:
        et_resource.append(_generate_element(NS_AAS + "contentType", text=obj.content_type))
    return et_resource


def reference_element_to_xml(obj: model.ReferenceElement,
                             tag: str = NS_AAS+"referenceElement") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.ReferenceElement` to XMl

    :param obj: Object of class :class:`~basyx.aas.model.submodel.ReferenceElement`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:referenceElement``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_reference_element = abstract_classes_to_xml(tag, obj)
    if obj.value:
        et_reference_element.append(reference_to_xml(obj.value, NS_AAS+"value"))
    return et_reference_element


def submodel_element_collection_to_xml(obj: model.SubmodelElementCollection,
                                       tag: str = NS_AAS+"submodelElementCollection") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.SubmodelElementCollection` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.SubmodelElementCollection`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:submodelElementCollection``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_submodel_element_collection = abstract_classes_to_xml(tag, obj)
    if obj.value:
        et_value = _generate_element(NS_AAS + "value")
        for submodel_element in obj.value:
            et_value.append(submodel_element_to_xml(submodel_element))
        et_submodel_element_collection.append(et_value)
    return et_submodel_element_collection


def submodel_element_list_to_xml(obj: model.SubmodelElementList,
                                 tag: str = NS_AAS+"submodelElementList") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.SubmodelElementList` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.SubmodelElementList`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:submodelElementList``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_submodel_element_list = abstract_classes_to_xml(tag, obj)
    et_submodel_element_list.append(_generate_element(NS_AAS + "orderRelevant", boolean_to_xml(obj.order_relevant)))
    if obj.semantic_id_list_element is not None:
        et_submodel_element_list.append(reference_to_xml(obj.semantic_id_list_element,
                                                         NS_AAS + "semanticIdListElement"))
    et_submodel_element_list.append(_generate_element(NS_AAS + "typeValueListElement", _generic.KEY_TYPES[
        model.KEY_TYPES_CLASSES[obj.type_value_list_element]]))
    if obj.value_type_list_element is not None:
        et_submodel_element_list.append(_generate_element(NS_AAS + "valueTypeListElement",
                                                          model.datatypes.XSD_TYPE_NAMES[obj.value_type_list_element]))
    if len(obj.value) > 0:
        et_value = _generate_element(NS_AAS + "value")
        for se in obj.value:
            et_value.append(submodel_element_to_xml(se))
        et_submodel_element_list.append(et_value)
    return et_submodel_element_list


def relationship_element_to_xml(obj: model.RelationshipElement,
                                tag: str = NS_AAS+"relationshipElement") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.RelationshipElement` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.RelationshipElement`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:relationshipElement``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_relationship_element = abstract_classes_to_xml(tag, obj)
    et_relationship_element.append(reference_to_xml(obj.first, NS_AAS+"first"))
    et_relationship_element.append(reference_to_xml(obj.second, NS_AAS+"second"))
    return et_relationship_element


def annotated_relationship_element_to_xml(obj: model.AnnotatedRelationshipElement,
                                          tag: str = NS_AAS+"annotatedRelationshipElement") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.AnnotatedRelationshipElement` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.AnnotatedRelationshipElement`
    :param tag: Namespace+Tag of the serialized element (optional): Default is ``aas:annotatedRelationshipElement``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_annotated_relationship_element = relationship_element_to_xml(obj, tag)
    if obj.annotation:
        et_annotations = _generate_element(name=NS_AAS + "annotations")
        for data_element in obj.annotation:
            et_annotations.append(data_element_to_xml(data_element))
        et_annotated_relationship_element.append(et_annotations)
    return et_annotated_relationship_element


def operation_variable_to_xml(obj: model.SubmodelElement, tag: str = NS_AAS+"operationVariable") -> etree._Element:
    """
    Serialization of :class:`~basyx.aas.model.submodel.SubmodelElement` to the XML OperationVariable representation
    Since we don't implement the ``OperationVariable`` class, which is just a wrapper for a single
    :class:`~basyx.aas.model.submodel.SubmodelElement`, elements are serialized as the ``aas:value`` child of an
    ``aas:operationVariable`` element.

    :param obj: Object of class :class:`~basyx.aas.model.submodel.SubmodelElement`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:operationVariable``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_operation_variable = _generate_element(tag)
    et_value = _generate_element(NS_AAS+"value")
    et_value.append(submodel_element_to_xml(obj))
    et_operation_variable.append(et_value)
    return et_operation_variable


def operation_to_xml(obj: model.Operation,
                     tag: str = NS_AAS+"operation") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.Operation` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.Operation`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:operation``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_operation = abstract_classes_to_xml(tag, obj)
    for tag, nss in ((NS_AAS+"inputVariables", obj.input_variable),
                     (NS_AAS+"outputVariables", obj.output_variable),
                     (NS_AAS+"inoutputVariables", obj.in_output_variable)):
        if nss:
            et_variables = _generate_element(tag)
            for submodel_element in nss:
                et_variables.append(operation_variable_to_xml(submodel_element))
            et_operation.append(et_variables)
    return et_operation


def capability_to_xml(obj: model.Capability,
                      tag: str = NS_AAS+"capability") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.Capability` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.Capability`
    :param tag: Namespace+Tag of the serialized element, default is ``aas:capability``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    return abstract_classes_to_xml(tag, obj)


def entity_to_xml(obj: model.Entity,
                  tag: str = NS_AAS+"entity") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.Entity` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.Entity`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:entity``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_entity = abstract_classes_to_xml(tag, obj)
    if obj.statement:
        et_statements = _generate_element(NS_AAS + "statements")
        for statement in obj.statement:
            et_statements.append(submodel_element_to_xml(statement))
        et_entity.append(et_statements)
    et_entity.append(_generate_element(NS_AAS + "entityType", text=_generic.ENTITY_TYPES[obj.entity_type]))
    if obj.global_asset_id:
        et_entity.append(_generate_element(NS_AAS + "globalAssetId", text=obj.global_asset_id))
    if obj.specific_asset_id:
        et_specific_asset_id = _generate_element(name=NS_AAS + "specificAssetIds")
        for specific_asset_id in obj.specific_asset_id:
            et_specific_asset_id.append(specific_asset_id_to_xml(specific_asset_id, NS_AAS + "specificAssetId"))
        et_entity.append(et_specific_asset_id)
    return et_entity


def basic_event_element_to_xml(obj: model.BasicEventElement, tag: str = NS_AAS+"basicEventElement") -> etree._Element:
    """
    Serialization of objects of class :class:`~basyx.aas.model.submodel.BasicEventElement` to XML

    :param obj: Object of class :class:`~basyx.aas.model.submodel.BasicEventElement`
    :param tag: Namespace+Tag of the serialized element (optional). Default is ``aas:basicEventElement``
    :return: Serialized :class:`~lxml.etree._Element` object
    """
    et_basic_event_element = abstract_classes_to_xml(tag, obj)
    et_basic_event_element.append(reference_to_xml(obj.observed, NS_AAS+"observed"))
    et_basic_event_element.append(_generate_element(NS_AAS+"direction", text=_generic.DIRECTION[obj.direction]))
    et_basic_event_element.append(_generate_element(NS_AAS+"state", text=_generic.STATE_OF_EVENT[obj.state]))
    if obj.message_topic is not None:
        et_basic_event_element.append(_generate_element(NS_AAS+"messageTopic", text=obj.message_topic))
    if obj.message_broker is not None:
        et_basic_event_element.append(reference_to_xml(obj.message_broker, NS_AAS+"messageBroker"))
    if obj.last_update is not None:
        et_basic_event_element.append(_generate_element(NS_AAS+"lastUpdate",
                                                        text=model.datatypes.xsd_repr(obj.last_update)))
    if obj.min_interval is not None:
        et_basic_event_element.append(_generate_element(NS_AAS+"minInterval",
                                                        text=model.datatypes.xsd_repr(obj.min_interval)))
    if obj.max_interval is not None:
        et_basic_event_element.append(_generate_element(NS_AAS+"maxInterval",
                                                        text=model.datatypes.xsd_repr(obj.max_interval)))
    return et_basic_event_element


# ##############################################################
# general functions
# ##############################################################

def _write_element(file: _generic.PathOrBinaryIO, element: etree._Element, **kwargs) -> None:
    etree.ElementTree(element).write(file, encoding="UTF-8", xml_declaration=True, method="xml", **kwargs)


def object_to_xml_element(obj: object) -> etree._Element:
    """
    Serialize a single object to an :class:`~lxml.etree._Element`.

    :param obj: The object to serialize
    """
    serialization_func: Callable[..., etree._Element]

    if isinstance(obj, model.Key):
        serialization_func = key_to_xml
    elif isinstance(obj, model.Reference):
        serialization_func = reference_to_xml
    elif isinstance(obj, model.Reference):
        serialization_func = reference_to_xml
    elif isinstance(obj, model.AdministrativeInformation):
        serialization_func = administrative_information_to_xml
    elif isinstance(obj, model.Qualifier):
        serialization_func = qualifier_to_xml
    elif isinstance(obj, model.AnnotatedRelationshipElement):
        serialization_func = annotated_relationship_element_to_xml
    elif isinstance(obj, model.BasicEventElement):
        serialization_func = basic_event_element_to_xml
    elif isinstance(obj, model.Blob):
        serialization_func = blob_to_xml
    elif isinstance(obj, model.Capability):
        serialization_func = capability_to_xml
    elif isinstance(obj, model.Entity):
        serialization_func = entity_to_xml
    elif isinstance(obj, model.Extension):
        serialization_func = extension_to_xml
    elif isinstance(obj, model.File):
        serialization_func = file_to_xml
    elif isinstance(obj, model.Resource):
        serialization_func = resource_to_xml
    elif isinstance(obj, model.MultiLanguageProperty):
        serialization_func = multi_language_property_to_xml
    elif isinstance(obj, model.Operation):
        serialization_func = operation_to_xml
    elif isinstance(obj, model.Property):
        serialization_func = property_to_xml
    elif isinstance(obj, model.Range):
        serialization_func = range_to_xml
    elif isinstance(obj, model.ReferenceElement):
        serialization_func = reference_element_to_xml
    elif isinstance(obj, model.RelationshipElement):
        serialization_func = relationship_element_to_xml
    elif isinstance(obj, model.SubmodelElementCollection):
        serialization_func = submodel_element_collection_to_xml
    elif isinstance(obj, model.SubmodelElementList):
        serialization_func = submodel_element_list_to_xml
    elif isinstance(obj, model.AssetAdministrationShell):
        serialization_func = asset_administration_shell_to_xml
    elif isinstance(obj, model.AssetInformation):
        serialization_func = asset_information_to_xml
    elif isinstance(obj, model.SpecificAssetId):
        serialization_func = specific_asset_id_to_xml
    elif isinstance(obj, model.Submodel):
        serialization_func = submodel_to_xml
    elif isinstance(obj, model.ValueReferencePair):
        serialization_func = value_reference_pair_to_xml
    elif isinstance(obj, model.ConceptDescription):
        serialization_func = concept_description_to_xml
    elif isinstance(obj, model.LangStringSet):
        serialization_func = lang_string_set_to_xml
    elif isinstance(obj, model.EmbeddedDataSpecification):
        serialization_func = embedded_data_specification_to_xml
    elif isinstance(obj, model.DataSpecificationIEC61360):
        serialization_func = data_specification_iec61360_to_xml
    # generic serialization using the functions for abstract classes
    elif isinstance(obj, model.DataElement):
        serialization_func = data_element_to_xml
    elif isinstance(obj, model.SubmodelElement):
        serialization_func = submodel_to_xml
    elif isinstance(obj, model.DataSpecificationContent):
        serialization_func = data_specification_content_to_xml
    # type aliases
    elif isinstance(obj, model.ValueList):
        serialization_func = value_list_to_xml
    else:
        raise ValueError(f"{obj!r} cannot be serialized!")

    return serialization_func(obj)


def write_aas_xml_element(file: _generic.PathOrBinaryIO, obj: object, **kwargs) -> None:
    """
    Serialize a single object to XML. Namespace declarations are added to the object itself, as there is no surrounding
    environment element.

    :param file: A filename or file-like object to write the XML-serialized data to
    :param obj: The object to serialize
    :param kwargs: Additional keyword arguments to be passed to :meth:`~lxml.etree._ElementTree.write`
    """
    return _write_element(file, object_to_xml_element(obj), **kwargs)


def object_store_to_xml_element(data: model.AbstractObjectStore) -> etree._Element:
    """
    Serialize a set of AAS objects to an Asset Administration Shell as :class:`~lxml.etree._Element`.
    This function is used internally by :meth:`write_aas_xml_file` and shouldn't be
    called directly for most use-cases.

    :param data: :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` which contains different objects of
                 the AAS metamodel which should be serialized to an XML file
    """
    # separate different kind of objects
    asset_administration_shells = []
    submodels = []
    concept_descriptions = []
    for obj in data:
        if isinstance(obj, model.AssetAdministrationShell):
            asset_administration_shells.append(obj)
        elif isinstance(obj, model.Submodel):
            submodels.append(obj)
        elif isinstance(obj, model.ConceptDescription):
            concept_descriptions.append(obj)

    # serialize objects to XML
    root = etree.Element(NS_AAS + "environment", nsmap=_generic.XML_NS_MAP)
    if asset_administration_shells:
        et_asset_administration_shells = etree.Element(NS_AAS + "assetAdministrationShells")
        for aas_obj in asset_administration_shells:
            et_asset_administration_shells.append(asset_administration_shell_to_xml(aas_obj))
        root.append(et_asset_administration_shells)
    if submodels:
        et_submodels = etree.Element(NS_AAS + "submodels")
        for sub_obj in submodels:
            et_submodels.append(submodel_to_xml(sub_obj))
        root.append(et_submodels)
    if concept_descriptions:
        et_concept_descriptions = etree.Element(NS_AAS + "conceptDescriptions")
        for con_obj in concept_descriptions:
            et_concept_descriptions.append(concept_description_to_xml(con_obj))
        root.append(et_concept_descriptions)

    return root


def write_aas_xml_file(file: _generic.PathOrBinaryIO,
                       data: model.AbstractObjectStore,
                       **kwargs) -> None:
    """
    Write a set of AAS objects to an Asset Administration Shell XML file according to 'Details of the Asset
    Administration Shell', chapter 5.4

    :param file: A filename or file-like object to write the XML-serialized data to
    :param data: :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` which contains different objects of
                 the AAS metamodel which should be serialized to an XML file
    :param kwargs: Additional keyword arguments to be passed to :meth:`~lxml.etree._ElementTree.write`
    """
    return _write_element(file, object_store_to_xml_element(data), **kwargs)
