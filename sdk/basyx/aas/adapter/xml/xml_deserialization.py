# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.xml.xml_deserialization:

Module for deserializing Asset Administration Shell data from the official XML format

This module provides the following functions for parsing XML documents:

- :func:`read_aas_xml_element` constructs a single object from an XML document containing a single element
- :func:`read_aas_xml_file_into` constructs all elements of an XML document and stores them in a given
  :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>`
- :func:`read_aas_xml_file` constructs all elements of an XML document and returns them in a
  :class:`~basyx.aas.model.provider.DictObjectStore`

These functions take a decoder class as keyword argument, which allows parsing in failsafe (default) or non-failsafe
mode. Parsing stripped elements - used in the HTTP adapter - is also possible. It is also possible to subclass the
default decoder class and provide an own decoder.

In failsafe mode errors regarding missing attributes and elements or invalid values are caught and logged.
In non-failsafe mode any error would abort parsing.
Error handling is done only by ``_failsafe_construct()`` in this module. Nearly all constructor functions are called
by other constructor functions via ``_failsafe_construct()``, so an error chain is constructed in the error case,
which allows printing stacktrace-like error messages like the following in the error case (in failsafe mode of course):


.. code-block::

    KeyError: aas:id on line 252 has no attribute with name idType!
        -> Failed to construct aas:id on line 252 using construct_identifier!
        -> Failed to construct aas:conceptDescription on line 247 using construct_concept_description!


Unlike the JSON deserialization, parsing is done top-down. Elements with a specific tag are searched on the level
directly below the level of the current xml element (in terms of parent and child relation) and parsed when
found. Constructor functions of these elements will then again search for mandatory and optional child elements
and construct them if available, and so on.
"""

from ... import model
from lxml import etree
import logging
import base64
import enum

from typing import Any, Callable, Dict, Iterable, Optional, Set, Tuple, Type, TypeVar
from .._generic import XML_NS_MAP, XML_NS_AAS, MODELLING_KIND_INVERSE, ASSET_KIND_INVERSE, KEY_TYPES_INVERSE, \
    ENTITY_TYPES_INVERSE, IEC61360_DATA_TYPES_INVERSE, IEC61360_LEVEL_TYPES_INVERSE, KEY_TYPES_CLASSES_INVERSE, \
    REFERENCE_TYPES_INVERSE, DIRECTION_INVERSE, STATE_OF_EVENT_INVERSE, QUALIFIER_KIND_INVERSE, PathOrIO

NS_AAS = XML_NS_AAS
REQUIRED_NAMESPACES: Set[str] = {XML_NS_MAP["aas"]}

logger = logging.getLogger(__name__)

T = TypeVar("T")
RE = TypeVar("RE", bound=model.RelationshipElement)
LSS = TypeVar("LSS", bound=model.LangStringSet)


def _str_to_bool(string: str) -> bool:
    """
    XML only allows ``false`` and ``true`` (case-sensitive) as valid values for a boolean.

    This function checks the string and raises a ValueError if the string is neither ``true`` nor ``false``.

    :param string: String representation of a boolean. (``true`` or ``false``)
    :return: The respective boolean value.
    :raises ValueError: If string is neither ``true`` nor ``false``.
    """
    if string not in ("true", "false"):
        raise ValueError(f"{string} is not a valid boolean! Only true and false are allowed.")
    return string == "true"


def _tag_replace_namespace(tag: str, nsmap: Dict[Optional[str], str]) -> str:
    """
    Attempts to replace the namespace in front of a tag with the prefix used in the xml document.

    :param tag: The tag of an xml element.
    :param nsmap: A dict mapping prefixes to namespaces.
    :return: The modified element tag. If the namespace wasn't found in nsmap, the unmodified tag is returned.
    """
    split = tag.split("}")
    for prefix, namespace in nsmap.items():
        if prefix and namespace == split[0][1:]:
            return prefix + ":" + split[1]
    return tag


def _element_pretty_identifier(element: etree._Element) -> str:
    """
    Returns a pretty element identifier for a given XML element.

    If the prefix is known, the namespace in the element tag is replaced by the prefix.
    If additionally also the sourceline is known, it is added as a suffix to name.
    For example, instead of "{https://admin-shell.io/aas/3/0}assetAdministrationShell" this function would return
    "aas:assetAdministrationShell on line $line", if both, prefix and sourceline, are known.

    :param element: The xml element.
    :return: The pretty element identifier.
    """
    identifier = element.tag
    if element.prefix is not None:
        # Only replace the namespace by the prefix if it matches our known namespaces,
        # so the replacement by the prefix doesn't mask errors such as incorrect namespaces.
        namespace, tag = element.tag.split("}", 1)
        if namespace[1:] in XML_NS_MAP.values():
            identifier = element.prefix + ":" + tag
    if element.sourceline is not None:
        identifier += f" on line {element.sourceline}"
    return identifier


def _exception_to_str(exception: BaseException) -> str:
    """
    A helper function used to stringify exceptions.

    It removes the quotation marks '' that are put around str(KeyError), otherwise it's just calls str(exception).

    :param exception: The exception to stringify.
    :return: The stringified exception.
    """
    string = str(exception)
    return string[1:-1] if isinstance(exception, KeyError) else string


def _get_child_mandatory(parent: etree._Element, child_tag: str) -> etree._Element:
    """
    A helper function for getting a mandatory child element.

    :param parent: The parent element.
    :param child_tag: The tag of the child element to return.
    :return: The child element.
    :raises KeyError: If the parent element has no child element with the given tag.
    """
    child = parent.find(child_tag)
    if child is None:
        raise KeyError(_element_pretty_identifier(parent)
                       + f" has no child {_tag_replace_namespace(child_tag, parent.nsmap)}!")
    return child


def _get_all_children_expect_tag(parent: etree._Element, expected_tag: str, failsafe: bool) -> Iterable[etree._Element]:
    """
    Iterates over all children, matching the tag.

    not failsafe: Throws an error if a child element doesn't match.
    failsafe: Logs a warning if a child element doesn't match.

    :param parent: The parent element.
    :param expected_tag: The tag of the children.
    :return: An iterator over all child elements that match child_tag.
    :raises KeyError: If the tag of a child element doesn't match and failsafe is true.
    """
    for child in parent:
        if child.tag != expected_tag:
            error_message = f"{_element_pretty_identifier(child)}, child of {_element_pretty_identifier(parent)}, " \
                            f"doesn't match the expected tag {_tag_replace_namespace(expected_tag, child.nsmap)}!"
            if not failsafe:
                raise KeyError(error_message)
            logger.warning(error_message)
            continue
        yield child


def _get_attrib_mandatory(element: etree._Element, attrib: str) -> str:
    """
    A helper function for getting a mandatory attribute of an element.

    :param element: The xml element.
    :param attrib: The name of the attribute.
    :return: The value of the attribute.
    :raises KeyError: If the attribute does not exist.
    """
    if attrib not in element.attrib:
        raise KeyError(f"{_element_pretty_identifier(element)} has no attribute with name {attrib}!")
    return element.attrib[attrib]  # type: ignore[return-value]


def _get_attrib_mandatory_mapped(element: etree._Element, attrib: str, dct: Dict[str, T]) -> T:
    """
    A helper function for getting a mapped mandatory attribute of an xml element.

    It first gets the attribute value using _get_attrib_mandatory(), which raises a KeyError if the attribute
    does not exist.
    Then it returns dct[<attribute value>] and raises a ValueError, if the attribute value does not exist in the dict.

    :param element: The xml element.
    :param attrib: The name of the attribute.
    :param dct: The dictionary that is used to map the attribute value.
    :return: The mapped value of the attribute.
    :raises ValueError: If the value of the attribute does not exist in dct.
    """
    attrib_value = _get_attrib_mandatory(element, attrib)
    if attrib_value not in dct:
        raise ValueError(f"Attribute {attrib} of {_element_pretty_identifier(element)} "
                         f"has invalid value: {attrib_value}")
    return dct[attrib_value]


def _get_text_or_none(element: Optional[etree._Element]) -> Optional[str]:
    """
    A helper function for getting the text of an element, when it's not clear whether the element exists or not.

    This function is useful whenever the text of an optional child element is needed.
    Then the text can be gotten with: text = _get_text_or_none(element.find("childElement")
    element.find() returns either the element or None, if it doesn't exist. This is why this function accepts
    an optional element, to reduce the amount of code in the constructor functions below.

    :param element: The xml element or None.
    :return: The text of the xml element if the xml element is not None and if the xml element has a text.
             None otherwise.
    """
    return element.text if element is not None else None


def _get_text_or_empty_string_or_none(element: Optional[etree._Element]) -> Optional[str]:
    """
    Returns element.text or "" if the element has no text
    or None, if the element is None.

    :param element: The xml element or None.
    :return: The text of the xml element if the xml element is not None and if the xml element has a text.
             Empty string if the xml element has no text.
             None otherwise.
    """
    if element is None:
        return None
    return element.text if element.text is not None else ""


def _get_text_mapped_or_none(element: Optional[etree._Element], dct: Dict[str, T]) -> Optional[T]:
    """
    Returns dct[element.text] or None, if the element is None, has no text or the text is not in dct.

    :param element: The xml element or None.
    :param dct: The dictionary that is used to map the text.
    :return: The mapped text or None.
    """
    text = _get_text_or_none(element)
    if text is None or text not in dct:
        return None
    return dct[text]


def _get_text_mandatory(element: etree._Element) -> str:
    """
    A helper function for getting the mandatory text of an element.

    :param element: The xml element.
    :return: The text of the xml element.
    :raises KeyError: If the xml element has no text.
    """
    text = element.text
    if text is None:
        raise KeyError(_element_pretty_identifier(element) + " has no text!")
    return text


def _get_text_mandatory_mapped(element: etree._Element, dct: Dict[str, T]) -> T:
    """
    A helper function for getting the mapped mandatory text of an element.

    It first gets the text of the element using _get_text_mandatory(),
    which raises a KeyError if the element has no text.
    Then it returns dct[<element text>] and raises a ValueError, if the text of the element does not exist in the dict.

    :param element: The xml element.
    :param dct: The dictionary that is used to map the text.
    :return: The mapped text of the element.
    :raises ValueError: If the text of the xml element does not exist in dct.
    """
    text = _get_text_mandatory(element)
    if text not in dct:
        raise ValueError(_element_pretty_identifier(element) + f" has invalid text: {text}")
    return dct[text]


def _failsafe_construct(element: Optional[etree._Element], constructor: Callable[..., T], failsafe: bool,
                        **kwargs: Any) -> Optional[T]:
    """
    A wrapper function that is used to handle exceptions raised in constructor functions.

    This is the only function of this module where exceptions are caught.
    This is why constructor functions should (in almost all cases) call other constructor functions using this function,
    so errors can be caught and logged in failsafe mode.
    The function accepts None as a valid value for element for the same reason _get_text_or_none() does, so it can be
    called like _failsafe_construct(element.find("childElement"), ...), since element.find() can return None.
    This function will also return None in this case.

    :param element: The xml element or None.
    :param constructor: The constructor function to apply on the element.
    :param failsafe: Indicates whether errors should be caught or re-raised.
    :param kwargs: Optional keyword arguments that are passed to the constructor function.
    :return: The constructed class instance, if construction was successful.
             None if the element was None or if the construction failed.
    """
    if element is None:
        return None
    try:
        return constructor(element, **kwargs)
    except (KeyError, ValueError, model.AASConstraintViolation) as e:
        error_message = f"Failed to construct {_element_pretty_identifier(element)} using {constructor.__name__}!"
        if not failsafe:
            raise (type(e) if isinstance(e, (KeyError, ValueError)) else ValueError)(error_message) from e
        error_type = type(e).__name__
        cause: Optional[BaseException] = e
        while cause is not None:
            error_message = _exception_to_str(cause) + "\n -> " + error_message
            cause = cause.__cause__
        logger.error(error_type + ": " + error_message)
        return None


def _failsafe_construct_mandatory(element: etree._Element, constructor: Callable[..., T], **kwargs: Any) -> T:
    """
    _failsafe_construct() but not failsafe and it returns T instead of Optional[T]

    :param element: The xml element.
    :param constructor: The constructor function to apply on the xml element.
    :param kwargs: Optional keyword arguments that are passed to the constructor function.
    :return: The constructed child element.
    :raises TypeError: If the result of _failsafe_construct() in non-failsafe mode was None.
                       This shouldn't be possible and if it happens, indicates a bug in _failsafe_construct().
    """
    constructed = _failsafe_construct(element, constructor, False, **kwargs)
    if constructed is None:
        raise AssertionError("The result of a non-failsafe _failsafe_construct() call was None! "
                             "This is a bug in the Eclipse BaSyx Python SDK XML deserialization, please report it!")
    return constructed


def _failsafe_construct_multiple(elements: Iterable[etree._Element], constructor: Callable[..., T], failsafe: bool,
                                 **kwargs: Any) -> Iterable[T]:
    """
    A generator function that applies _failsafe_construct() to multiple elements.

    :param elements: Any iterable containing any number of xml elements.
    :param constructor: The constructor function to apply on the xml elements.
    :param failsafe: Indicates whether errors should be caught or re-raised.
    :param kwargs: Optional keyword arguments that are passed to the constructor function.
    :return: An iterator over the successfully constructed elements.
             If an error occurred while constructing an element and while in failsafe mode,
             the respective element will be skipped.
    """
    for element in elements:
        parsed = _failsafe_construct(element, constructor, failsafe, **kwargs)
        if parsed is not None:
            yield parsed


def _child_construct_mandatory(parent: etree._Element, child_tag: str, constructor: Callable[..., T], **kwargs: Any) \
        -> T:
    """
    Shorthand for _failsafe_construct_mandatory() in combination with _get_child_mandatory().

    :param parent: The xml element where the child element is searched.
    :param child_tag: The tag of the child element to construct.
    :param constructor: The constructor function for the child element.
    :param kwargs: Optional keyword arguments that are passed to the constructor function.
    :return: The constructed child element.
    """
    return _failsafe_construct_mandatory(_get_child_mandatory(parent, child_tag), constructor, **kwargs)


def _child_construct_multiple(parent: etree._Element, expected_tag: str, constructor: Callable[..., T],
                              failsafe: bool, **kwargs: Any) -> Iterable[T]:
    """
    Shorthand for _failsafe_construct_multiple() in combination with _get_child_multiple().

    :param parent: The xml element where child elements are searched.
    :param expected_tag: The expected tag of the child elements.
    :param constructor: The constructor function for the child element.
    :param kwargs: Optional keyword arguments that are passed to the constructor function.
    :return: An iterator over successfully constructed child elements.
             If an error occurred while constructing an element and while in failsafe mode,
             the respective element will be skipped.
    """
    return _failsafe_construct_multiple(_get_all_children_expect_tag(parent, expected_tag, failsafe), constructor,
                                        failsafe, **kwargs)


def _child_text_mandatory(parent: etree._Element, child_tag: str) -> str:
    """
    Shorthand for _get_text_mandatory() in combination with _get_child_mandatory().

    :param parent: The xml element where the child element is searched.
    :param child_tag: The tag of the child element to get the text from.
    :return: The text of the child element.
    """
    return _get_text_mandatory(_get_child_mandatory(parent, child_tag))


def _child_text_mandatory_mapped(parent: etree._Element, child_tag: str, dct: Dict[str, T]) -> T:
    """
    Shorthand for _get_text_mandatory_mapped() in combination with _get_child_mandatory().

    :param parent: The xml element where the child element is searched.
    :param child_tag: The tag of the child element to get the text from.
    :param dct: The dictionary that is used to map the text of the child element.
    :return: The mapped text of the child element.
    """
    return _get_text_mandatory_mapped(_get_child_mandatory(parent, child_tag), dct)


def _get_kind(element: etree._Element) -> model.ModellingKind:
    """
    Returns the modelling kind of an element with the default value INSTANCE, if none specified.

    :param element: The xml element.
    :return: The modelling kind of the element.
    """
    modelling_kind = _get_text_mapped_or_none(element.find(NS_AAS + "kind"), MODELLING_KIND_INVERSE)
    return modelling_kind if modelling_kind is not None else model.ModellingKind.INSTANCE


def _expect_reference_type(element: etree._Element, expected_type: Type[model.Reference]) -> None:
    """
    Validates the type attribute of a Reference.

    :param element: The xml element.
    :param expected_type: The expected type of the Reference.
    :return: None
    """
    actual_type = _child_text_mandatory_mapped(element, NS_AAS + "type", REFERENCE_TYPES_INVERSE)
    if actual_type is not expected_type:
        raise ValueError(f"{_element_pretty_identifier(element)} is of type {actual_type}, expected {expected_type}!")


class AASFromXmlDecoder:
    """
    The default XML decoder class.

    It parses XML documents in a failsafe manner, meaning any errors encountered will be logged and invalid XML elements
    will be skipped.
    Most member functions support the ``object_class`` parameter. It was introduced, so they can be overwritten
    in subclasses, which allows constructing instances of subtypes.
    """
    failsafe = True
    stripped = False

    @classmethod
    def _amend_abstract_attributes(cls, obj: object, element: etree._Element) -> None:
        """
        A helper function that amends optional attributes to already constructed class instances, if they inherit
        from an abstract class like Referable, Identifiable, HasSemantics or Qualifiable.

        :param obj: The constructed class instance.
        :param element: The respective xml element.
        :return: None
        """
        if isinstance(obj, model.Referable):
            id_short = _get_text_or_none(element.find(NS_AAS + "idShort"))
            if id_short is not None:
                obj.id_short = id_short
            category = _get_text_or_none(element.find(NS_AAS + "category"))
            display_name = _failsafe_construct(element.find(NS_AAS + "displayName"),
                                               cls.construct_multi_language_name_type, cls.failsafe)
            if display_name is not None:
                obj.display_name = display_name
            if category is not None:
                obj.category = category
            description = _failsafe_construct(element.find(NS_AAS + "description"),
                                              cls.construct_multi_language_text_type, cls.failsafe)
            if description is not None:
                obj.description = description
        if isinstance(obj, model.Identifiable):
            administration = _failsafe_construct(element.find(NS_AAS + "administration"),
                                                 cls.construct_administrative_information, cls.failsafe)
            if administration:
                obj.administration = administration
        if isinstance(obj, model.HasSemantics):
            semantic_id = _failsafe_construct(element.find(NS_AAS + "semanticId"), cls.construct_reference,
                                              cls.failsafe)
            if semantic_id is not None:
                obj.semantic_id = semantic_id
            supplemental_semantic_ids = element.find(NS_AAS + "supplementalSemanticIds")
            if supplemental_semantic_ids is not None:
                for supplemental_semantic_id in _child_construct_multiple(supplemental_semantic_ids,
                                                                          NS_AAS + "reference", cls.construct_reference,
                                                                          cls.failsafe):
                    obj.supplemental_semantic_id.append(supplemental_semantic_id)
        if isinstance(obj, model.Qualifiable) and not cls.stripped:
            qualifiers_elem = element.find(NS_AAS + "qualifiers")
            if qualifiers_elem is not None and len(qualifiers_elem) > 0:
                for qualifier in _failsafe_construct_multiple(qualifiers_elem, cls.construct_qualifier, cls.failsafe):
                    obj.qualifier.add(qualifier)
        if isinstance(obj, model.HasDataSpecification) and not cls.stripped:
            embedded_data_specifications_elem = element.find(NS_AAS + "embeddedDataSpecifications")
            if embedded_data_specifications_elem is not None:
                for eds in _failsafe_construct_multiple(embedded_data_specifications_elem,
                                                        cls.construct_embedded_data_specification, cls.failsafe):
                    obj.embedded_data_specifications.append(eds)
        if isinstance(obj, model.HasExtension) and not cls.stripped:
            extension_elem = element.find(NS_AAS + "extensions")
            if extension_elem is not None:
                for extension in _child_construct_multiple(extension_elem, NS_AAS + "extension",
                                                           cls.construct_extension, cls.failsafe):
                    obj.extension.add(extension)

    @classmethod
    def _construct_relationship_element_internal(cls, element: etree._Element, object_class: Type[RE], **_kwargs: Any) \
            -> RE:
        """
        Helper function used by construct_relationship_element() and construct_annotated_relationship_element()
        to reduce duplicate code
        """
        relationship_element = object_class(
            None,
            _child_construct_mandatory(element, NS_AAS + "first", cls.construct_reference),
            _child_construct_mandatory(element, NS_AAS + "second", cls.construct_reference)
        )
        cls._amend_abstract_attributes(relationship_element, element)
        return relationship_element

    @classmethod
    def _construct_key_tuple(cls, element: etree._Element, namespace: str = NS_AAS, **_kwargs: Any) \
            -> Tuple[model.Key, ...]:
        """
        Helper function used by construct_reference() and construct_aas_reference() to reduce duplicate code
        """
        keys = _get_child_mandatory(element, namespace + "keys")
        return tuple(_child_construct_multiple(keys, namespace + "key", cls.construct_key, cls.failsafe))

    @classmethod
    def _construct_submodel_reference(cls, element: etree._Element, **kwargs: Any) \
            -> model.ModelReference[model.Submodel]:
        """
        Helper function. Doesn't support the object_class parameter. Overwrite construct_aas_reference instead.
        """
        return cls.construct_model_reference_expect_type(element, model.Submodel, **kwargs)

    @classmethod
    def _construct_asset_administration_shell_reference(cls, element: etree._Element, **kwargs: Any) \
            -> model.ModelReference[model.AssetAdministrationShell]:
        """
        Helper function. Doesn't support the object_class parameter. Overwrite construct_aas_reference instead.
        """
        return cls.construct_model_reference_expect_type(element, model.AssetAdministrationShell, **kwargs)

    @classmethod
    def _construct_referable_reference(cls, element: etree._Element, **kwargs: Any) \
            -> model.ModelReference[model.Referable]:
        """
        Helper function. Doesn't support the object_class parameter. Overwrite construct_aas_reference instead.
        """
        # TODO: remove the following type: ignore comments when mypy supports abstract types for Type[T]
        # see https://github.com/python/mypy/issues/5374
        return cls.construct_model_reference_expect_type(element, model.Referable, **kwargs)  # type: ignore

    @classmethod
    def _construct_operation_variable(cls, element: etree._Element, **kwargs: Any) -> model.SubmodelElement:
        """
        Since we don't implement ``OperationVariable``, this constructor discards the wrapping `aas:operationVariable`
        and `aas:value` and just returns the contained :class:`~basyx.aas.model.submodel.SubmodelElement`.
        """
        value = _get_child_mandatory(element, NS_AAS + "value")
        if len(value) == 0:
            raise KeyError(f"{_element_pretty_identifier(value)} has no submodel element!")
        if len(value) > 1:
            logger.warning(f"{_element_pretty_identifier(value)} has more than one submodel element, "
                           "using the first one...")
        return cls.construct_submodel_element(value[0], **kwargs)

    @classmethod
    def construct_key(cls, element: etree._Element, object_class=model.Key, **_kwargs: Any) \
            -> model.Key:
        return object_class(
            _child_text_mandatory_mapped(element, NS_AAS + "type", KEY_TYPES_INVERSE),
            _child_text_mandatory(element, NS_AAS + "value")
        )

    @classmethod
    def construct_reference(cls, element: etree._Element, namespace: str = NS_AAS, **kwargs: Any) -> model.Reference:
        reference_type: Type[model.Reference] = _child_text_mandatory_mapped(element, NS_AAS + "type",
                                                                             REFERENCE_TYPES_INVERSE)
        references: Dict[Type[model.Reference], Callable[..., model.Reference]] = {
            model.ExternalReference: cls.construct_external_reference,
            model.ModelReference: cls.construct_model_reference
        }
        if reference_type not in references:
            raise KeyError(_element_pretty_identifier(element) + f" is of unsupported Reference type {reference_type}!")
        return references[reference_type](element, namespace=namespace, **kwargs)

    @classmethod
    def construct_external_reference(cls, element: etree._Element, namespace: str = NS_AAS,
                                     object_class=model.ExternalReference, **_kwargs: Any) \
            -> model.ExternalReference:
        _expect_reference_type(element, model.ExternalReference)
        return object_class(cls._construct_key_tuple(element, namespace=namespace),
                            _failsafe_construct(element.find(NS_AAS + "referredSemanticId"), cls.construct_reference,
                                                cls.failsafe, namespace=namespace))

    @classmethod
    def construct_model_reference(cls, element: etree._Element, object_class=model.ModelReference, **_kwargs: Any) \
            -> model.ModelReference:
        """
        This constructor for ModelReference determines the type of the ModelReference by its keys. If no keys are
        present, it will default to the type Referable. This behaviour is wanted in read_aas_xml_element().
        """
        _expect_reference_type(element, model.ModelReference)
        keys = cls._construct_key_tuple(element)
        # TODO: remove the following type: ignore comments when mypy supports abstract types for Type[T]
        # see https://github.com/python/mypy/issues/5374
        type_: Type[model.Referable] = model.Referable  # type: ignore
        if len(keys) > 0:
            type_ = KEY_TYPES_CLASSES_INVERSE.get(keys[-1].type, model.Referable)  # type: ignore
        return object_class(keys, type_, _failsafe_construct(element.find(NS_AAS + "referredSemanticId"),
                                                             cls.construct_reference, cls.failsafe))

    @classmethod
    def construct_model_reference_expect_type(cls, element: etree._Element, type_: Type[model.base._RT],
                                              object_class=model.ModelReference, **_kwargs: Any) \
            -> model.ModelReference[model.base._RT]:
        """
        This constructor for ModelReference allows passing an expected type, which is checked against the type of the
        last key of the reference. This constructor function is used by other constructor functions, since all expect a
        specific target type.
        """
        _expect_reference_type(element, model.ModelReference)
        keys = cls._construct_key_tuple(element)
        if keys and not issubclass(KEY_TYPES_CLASSES_INVERSE.get(keys[-1].type, type(None)), type_):
            logger.warning("type %s of last key of reference to %s does not match reference type %s",
                           keys[-1].type.name, " / ".join(str(k) for k in keys), type_.__name__)
        return object_class(keys, type_, _failsafe_construct(element.find(NS_AAS + "referredSemanticId"),
                                                             cls.construct_reference, cls.failsafe))

    @classmethod
    def construct_administrative_information(cls, element: etree._Element, object_class=model.AdministrativeInformation,
                                             **_kwargs: Any) -> model.AdministrativeInformation:
        administrative_information = object_class(
            revision=_get_text_or_none(element.find(NS_AAS + "revision")),
            version=_get_text_or_none(element.find(NS_AAS + "version")),
            template_id=_get_text_or_none(element.find(NS_AAS + "templateId"))
        )
        creator = _failsafe_construct(element.find(NS_AAS + "creator"), cls.construct_reference, cls.failsafe)
        if creator is not None:
            administrative_information.creator = creator
        cls._amend_abstract_attributes(administrative_information, element)
        return administrative_information

    @classmethod
    def construct_lang_string_set(cls, element: etree._Element, expected_tag: str, object_class: Type[LSS],
                                  **_kwargs: Any) -> LSS:
        collected_lang_strings: Dict[str, str] = {}
        for lang_string_elem in _get_all_children_expect_tag(element, expected_tag, cls.failsafe):
            collected_lang_strings[_child_text_mandatory(lang_string_elem, NS_AAS + "language")] = \
                _child_text_mandatory(lang_string_elem, NS_AAS + "text")
        return object_class(collected_lang_strings)

    @classmethod
    def construct_multi_language_name_type(cls, element: etree._Element, object_class=model.MultiLanguageNameType,
                                           **kwargs: Any) -> model.MultiLanguageNameType:
        return cls.construct_lang_string_set(element, NS_AAS + "langStringNameType", object_class, **kwargs)

    @classmethod
    def construct_multi_language_text_type(cls, element: etree._Element, object_class=model.MultiLanguageTextType,
                                           **kwargs: Any) -> model.MultiLanguageTextType:
        return cls.construct_lang_string_set(element, NS_AAS + "langStringTextType", object_class, **kwargs)

    @classmethod
    def construct_definition_type_iec61360(cls, element: etree._Element, object_class=model.DefinitionTypeIEC61360,
                                           **kwargs: Any) -> model.DefinitionTypeIEC61360:
        return cls.construct_lang_string_set(element, NS_AAS + "langStringDefinitionTypeIec61360", object_class,
                                             **kwargs)

    @classmethod
    def construct_preferred_name_type_iec61360(cls, element: etree._Element,
                                               object_class=model.PreferredNameTypeIEC61360,
                                               **kwargs: Any) -> model.PreferredNameTypeIEC61360:
        return cls.construct_lang_string_set(element, NS_AAS + "langStringPreferredNameTypeIec61360", object_class,
                                             **kwargs)

    @classmethod
    def construct_short_name_type_iec61360(cls, element: etree._Element, object_class=model.ShortNameTypeIEC61360,
                                           **kwargs: Any) -> model.ShortNameTypeIEC61360:
        return cls.construct_lang_string_set(element, NS_AAS + "langStringShortNameTypeIec61360", object_class,
                                             **kwargs)

    @classmethod
    def construct_qualifier(cls, element: etree._Element, object_class=model.Qualifier, **_kwargs: Any) \
            -> model.Qualifier:
        qualifier = object_class(
            _child_text_mandatory(element, NS_AAS + "type"),
            _child_text_mandatory_mapped(element, NS_AAS + "valueType", model.datatypes.XSD_TYPE_CLASSES)
        )
        kind = _get_text_mapped_or_none(element.find(NS_AAS + "kind"), QUALIFIER_KIND_INVERSE)
        if kind is not None:
            qualifier.kind = kind
        value = _get_text_or_empty_string_or_none(element.find(NS_AAS + "value"))
        if value is not None:
            qualifier.value = model.datatypes.from_xsd(value, qualifier.value_type)
        value_id = _failsafe_construct(element.find(NS_AAS + "valueId"), cls.construct_reference, cls.failsafe)
        if value_id is not None:
            qualifier.value_id = value_id
        cls._amend_abstract_attributes(qualifier, element)
        return qualifier

    @classmethod
    def construct_extension(cls, element: etree._Element, object_class=model.Extension, **_kwargs: Any) \
            -> model.Extension:
        extension = object_class(
            _child_text_mandatory(element, NS_AAS + "name"))
        value_type = _get_text_or_none(element.find(NS_AAS + "valueType"))
        if value_type is not None:
            extension.value_type = model.datatypes.XSD_TYPE_CLASSES[value_type]
        value = _get_text_or_empty_string_or_none(element.find(NS_AAS + "value"))
        if value is not None:
            extension.value = model.datatypes.from_xsd(value, extension.value_type)
        refers_to = element.find(NS_AAS + "refersTo")
        if refers_to is not None:
            for ref in _child_construct_multiple(refers_to, NS_AAS + "reference", cls._construct_referable_reference,
                                                 cls.failsafe):
                extension.refers_to.add(ref)
        cls._amend_abstract_attributes(extension, element)
        return extension

    @classmethod
    def construct_submodel_element(cls, element: etree._Element, **kwargs: Any) -> model.SubmodelElement:
        """
        This function doesn't support the object_class parameter.
        Overwrite each individual SubmodelElement/DataElement constructor function instead.
        """
        submodel_elements: Dict[str, Callable[..., model.SubmodelElement]] = {NS_AAS + k: v for k, v in {
            "annotatedRelationshipElement": cls.construct_annotated_relationship_element,
            "basicEventElement": cls.construct_basic_event_element,
            "capability": cls.construct_capability,
            "entity": cls.construct_entity,
            "operation": cls.construct_operation,
            "relationshipElement": cls.construct_relationship_element,
            "submodelElementCollection": cls.construct_submodel_element_collection,
            "submodelElementList": cls.construct_submodel_element_list
        }.items()}
        if element.tag not in submodel_elements:
            return cls.construct_data_element(element, abstract_class_name="SubmodelElement", **kwargs)
        return submodel_elements[element.tag](element, **kwargs)

    @classmethod
    def construct_data_element(cls, element: etree._Element, abstract_class_name: str = "DataElement", **kwargs: Any) \
            -> model.DataElement:
        """
        This function does not support the object_class parameter.
        Overwrite each individual DataElement constructor function instead.
        """
        data_elements: Dict[str, Callable[..., model.DataElement]] = {NS_AAS + k: v for k, v in {
            "blob": cls.construct_blob,
            "file": cls.construct_file,
            "multiLanguageProperty": cls.construct_multi_language_property,
            "property": cls.construct_property,
            "range": cls.construct_range,
            "referenceElement": cls.construct_reference_element,
        }.items()}
        if element.tag not in data_elements:
            raise KeyError(_element_pretty_identifier(element) + f" is not a valid {abstract_class_name}!")
        return data_elements[element.tag](element, **kwargs)

    @classmethod
    def construct_annotated_relationship_element(cls, element: etree._Element,
                                                 object_class=model.AnnotatedRelationshipElement, **_kwargs: Any) \
            -> model.AnnotatedRelationshipElement:
        annotated_relationship_element = cls._construct_relationship_element_internal(element, object_class)
        if not cls.stripped:
            annotations = element.find(NS_AAS + "annotations")
            if annotations is not None:
                for data_element in _failsafe_construct_multiple(annotations, cls.construct_data_element,
                                                                 cls.failsafe):
                    annotated_relationship_element.annotation.add(data_element)
        return annotated_relationship_element

    @classmethod
    def construct_basic_event_element(cls, element: etree._Element, object_class=model.BasicEventElement,
                                      **_kwargs: Any) -> model.BasicEventElement:
        basic_event_element = object_class(
            None,
            _child_construct_mandatory(element, NS_AAS + "observed", cls._construct_referable_reference),
            _child_text_mandatory_mapped(element, NS_AAS + "direction", DIRECTION_INVERSE),
            _child_text_mandatory_mapped(element, NS_AAS + "state", STATE_OF_EVENT_INVERSE)
        )
        message_topic = _get_text_or_none(element.find(NS_AAS + "messageTopic"))
        if message_topic is not None:
            basic_event_element.message_topic = message_topic
        message_broker = element.find(NS_AAS + "messageBroker")
        if message_broker is not None:
            basic_event_element.message_broker = _failsafe_construct(message_broker, cls.construct_reference,
                                                                     cls.failsafe)
        last_update = _get_text_or_none(element.find(NS_AAS + "lastUpdate"))
        if last_update is not None:
            basic_event_element.last_update = model.datatypes.from_xsd(last_update, model.datatypes.DateTime)
        min_interval = _get_text_or_none(element.find(NS_AAS + "minInterval"))
        if min_interval is not None:
            basic_event_element.min_interval = model.datatypes.from_xsd(min_interval, model.datatypes.Duration)
        max_interval = _get_text_or_none(element.find(NS_AAS + "maxInterval"))
        if max_interval is not None:
            basic_event_element.max_interval = model.datatypes.from_xsd(max_interval, model.datatypes.Duration)
        cls._amend_abstract_attributes(basic_event_element, element)
        return basic_event_element

    @classmethod
    def construct_blob(cls, element: etree._Element, object_class=model.Blob, **_kwargs: Any) -> model.Blob:
        blob = object_class(
            None,
            _child_text_mandatory(element, NS_AAS + "contentType")
        )
        value = _get_text_or_none(element.find(NS_AAS + "value"))
        if value is not None:
            blob.value = base64.b64decode(value)
        cls._amend_abstract_attributes(blob, element)
        return blob

    @classmethod
    def construct_capability(cls, element: etree._Element, object_class=model.Capability, **_kwargs: Any) \
            -> model.Capability:
        capability = object_class(None)
        cls._amend_abstract_attributes(capability, element)
        return capability

    @classmethod
    def construct_entity(cls, element: etree._Element, object_class=model.Entity, **_kwargs: Any) -> model.Entity:
        specific_asset_id = set()
        specific_asset_ids = element.find(NS_AAS + "specificAssetIds")
        if specific_asset_ids is not None:
            for id in _child_construct_multiple(specific_asset_ids, NS_AAS + "specificAssetId",
                                                cls.construct_specific_asset_id, cls.failsafe):
                specific_asset_id.add(id)

        entity = object_class(
            id_short=None,
            entity_type=_child_text_mandatory_mapped(element, NS_AAS + "entityType", ENTITY_TYPES_INVERSE),
            global_asset_id=_get_text_or_none(element.find(NS_AAS + "globalAssetId")),
            specific_asset_id=specific_asset_id)

        if not cls.stripped:
            statements = element.find(NS_AAS + "statements")
            if statements is not None:
                for submodel_element in _failsafe_construct_multiple(statements, cls.construct_submodel_element,
                                                                     cls.failsafe):
                    entity.statement.add(submodel_element)
        cls._amend_abstract_attributes(entity, element)
        return entity

    @classmethod
    def construct_file(cls, element: etree._Element, object_class=model.File, **_kwargs: Any) -> model.File:
        file = object_class(
            None,
            _child_text_mandatory(element, NS_AAS + "contentType")
        )
        value = _get_text_or_none(element.find(NS_AAS + "value"))
        if value is not None:
            file.value = value
        cls._amend_abstract_attributes(file, element)
        return file

    @classmethod
    def construct_resource(cls, element: etree._Element, object_class=model.Resource, **_kwargs: Any) -> model.Resource:
        resource = object_class(
            _child_text_mandatory(element, NS_AAS + "path")
        )
        content_type = _get_text_or_none(element.find(NS_AAS + "contentType"))
        if content_type is not None:
            resource.content_type = content_type
        cls._amend_abstract_attributes(resource, element)
        return resource

    @classmethod
    def construct_multi_language_property(cls, element: etree._Element, object_class=model.MultiLanguageProperty,
                                          **_kwargs: Any) -> model.MultiLanguageProperty:
        multi_language_property = object_class(None)
        value = _failsafe_construct(element.find(NS_AAS + "value"), cls.construct_multi_language_text_type,
                                    cls.failsafe)
        if value is not None:
            multi_language_property.value = value
        value_id = _failsafe_construct(element.find(NS_AAS + "valueId"), cls.construct_reference, cls.failsafe)
        if value_id is not None:
            multi_language_property.value_id = value_id
        cls._amend_abstract_attributes(multi_language_property, element)
        return multi_language_property

    @classmethod
    def construct_operation(cls, element: etree._Element, object_class=model.Operation, **_kwargs: Any) \
            -> model.Operation:
        operation = object_class(None)
        for tag, target in ((NS_AAS + "inputVariables", operation.input_variable),
                            (NS_AAS + "outputVariables", operation.output_variable),
                            (NS_AAS + "inoutputVariables", operation.in_output_variable)):
            variables = element.find(tag)
            if variables is not None:
                for var in _child_construct_multiple(variables, NS_AAS + "operationVariable",
                                                     cls._construct_operation_variable, cls.failsafe):
                    target.add(var)
        cls._amend_abstract_attributes(operation, element)
        return operation

    @classmethod
    def construct_property(cls, element: etree._Element, object_class=model.Property, **_kwargs: Any) -> model.Property:
        property_ = object_class(
            None,
            value_type=_child_text_mandatory_mapped(element, NS_AAS + "valueType", model.datatypes.XSD_TYPE_CLASSES)
        )
        value = _get_text_or_empty_string_or_none(element.find(NS_AAS + "value"))
        if value is not None:
            property_.value = model.datatypes.from_xsd(value, property_.value_type)
        value_id = _failsafe_construct(element.find(NS_AAS + "valueId"), cls.construct_reference, cls.failsafe)
        if value_id is not None:
            property_.value_id = value_id
        cls._amend_abstract_attributes(property_, element)
        return property_

    @classmethod
    def construct_range(cls, element: etree._Element, object_class=model.Range, **_kwargs: Any) -> model.Range:
        range_ = object_class(
            None,
            value_type=_child_text_mandatory_mapped(element, NS_AAS + "valueType", model.datatypes.XSD_TYPE_CLASSES)
        )
        max_ = _get_text_or_empty_string_or_none(element.find(NS_AAS + "max"))
        if max_ is not None:
            range_.max = model.datatypes.from_xsd(max_, range_.value_type)
        min_ = _get_text_or_empty_string_or_none(element.find(NS_AAS + "min"))
        if min_ is not None:
            range_.min = model.datatypes.from_xsd(min_, range_.value_type)
        cls._amend_abstract_attributes(range_, element)
        return range_

    @classmethod
    def construct_reference_element(cls, element: etree._Element, object_class=model.ReferenceElement, **_kwargs: Any) \
            -> model.ReferenceElement:
        reference_element = object_class(None)
        value = _failsafe_construct(element.find(NS_AAS + "value"), cls.construct_reference, cls.failsafe)
        if value is not None:
            reference_element.value = value
        cls._amend_abstract_attributes(reference_element, element)
        return reference_element

    @classmethod
    def construct_relationship_element(cls, element: etree._Element, object_class=model.RelationshipElement,
                                       **_kwargs: Any) -> model.RelationshipElement:
        return cls._construct_relationship_element_internal(element, object_class=object_class, **_kwargs)

    @classmethod
    def construct_submodel_element_collection(cls, element: etree._Element,
                                              object_class=model.SubmodelElementCollection,
                                              **_kwargs: Any) -> model.SubmodelElementCollection:
        collection = object_class(None)
        if not cls.stripped:
            value = element.find(NS_AAS + "value")
            if value is not None:
                for submodel_element in _failsafe_construct_multiple(value, cls.construct_submodel_element,
                                                                     cls.failsafe):
                    collection.value.add(submodel_element)
        cls._amend_abstract_attributes(collection, element)
        return collection

    @classmethod
    def construct_submodel_element_list(cls, element: etree._Element, object_class=model.SubmodelElementList,
                                        **_kwargs: Any) -> model.SubmodelElementList:
        type_value_list_element = KEY_TYPES_CLASSES_INVERSE[
            _child_text_mandatory_mapped(element, NS_AAS + "typeValueListElement", KEY_TYPES_INVERSE)]
        if not issubclass(type_value_list_element, model.SubmodelElement):
            raise ValueError("Expected a SubmodelElementList with a typeValueListElement that is a subclass of"
                             f"{model.SubmodelElement}, got {type_value_list_element}!")
        order_relevant = element.find(NS_AAS + "orderRelevant")
        list_ = object_class(
            None,
            type_value_list_element,
            semantic_id_list_element=_failsafe_construct(element.find(NS_AAS + "semanticIdListElement"),
                                                         cls.construct_reference, cls.failsafe),
            value_type_list_element=_get_text_mapped_or_none(element.find(NS_AAS + "valueTypeListElement"),
                                                             model.datatypes.XSD_TYPE_CLASSES),
            order_relevant=_str_to_bool(_get_text_mandatory(order_relevant))
            if order_relevant is not None else True
        )
        if not cls.stripped:
            value = element.find(NS_AAS + "value")
            if value is not None:
                list_.value.extend(_failsafe_construct_multiple(value, cls.construct_submodel_element, cls.failsafe))
        cls._amend_abstract_attributes(list_, element)
        return list_

    @classmethod
    def construct_asset_administration_shell(cls, element: etree._Element, object_class=model.AssetAdministrationShell,
                                             **_kwargs: Any) -> model.AssetAdministrationShell:
        aas = object_class(
            id_=_child_text_mandatory(element, NS_AAS + "id"),
            asset_information=_child_construct_mandatory(element, NS_AAS + "assetInformation",
                                                         cls.construct_asset_information)
        )
        if not cls.stripped:
            submodels = element.find(NS_AAS + "submodels")
            if submodels is not None:
                for ref in _child_construct_multiple(submodels, NS_AAS + "reference",
                                                     cls._construct_submodel_reference, cls.failsafe):
                    aas.submodel.add(ref)
        derived_from = _failsafe_construct(element.find(NS_AAS + "derivedFrom"),
                                           cls._construct_asset_administration_shell_reference, cls.failsafe)
        if derived_from is not None:
            aas.derived_from = derived_from
        cls._amend_abstract_attributes(aas, element)
        return aas

    @classmethod
    def construct_specific_asset_id(cls, element: etree._Element, object_class=model.SpecificAssetId,
                                    **_kwargs: Any) -> model.SpecificAssetId:
        # semantic_id can't be applied by _amend_abstract_attributes because specificAssetId is immutable
        return object_class(
            name=_get_text_or_none(element.find(NS_AAS + "name")),
            value=_get_text_or_none(element.find(NS_AAS + "value")),
            external_subject_id=_failsafe_construct(element.find(NS_AAS + "externalSubjectId"),
                                                    cls.construct_external_reference, cls.failsafe),
            semantic_id=_failsafe_construct(element.find(NS_AAS + "semanticId"), cls.construct_reference, cls.failsafe)
        )

    @classmethod
    def construct_asset_information(cls, element: etree._Element, object_class=model.AssetInformation, **_kwargs: Any) \
            -> model.AssetInformation:
        specific_asset_id = set()
        specific_asset_ids = element.find(NS_AAS + "specificAssetIds")
        if specific_asset_ids is not None:
            for id in _child_construct_multiple(specific_asset_ids, NS_AAS + "specificAssetId",
                                                cls.construct_specific_asset_id, cls.failsafe):
                specific_asset_id.add(id)

        asset_information = object_class(
            _child_text_mandatory_mapped(element, NS_AAS + "assetKind", ASSET_KIND_INVERSE),
            global_asset_id=_get_text_or_none(element.find(NS_AAS + "globalAssetId")),
            specific_asset_id=specific_asset_id,
        )

        asset_type = _get_text_or_none(element.find(NS_AAS + "assetType"))
        if asset_type is not None:
            asset_information.asset_type = asset_type
        thumbnail = _failsafe_construct(element.find(NS_AAS + "defaultThumbnail"),
                                        cls.construct_resource, cls.failsafe)
        if thumbnail is not None:
            asset_information.default_thumbnail = thumbnail

        cls._amend_abstract_attributes(asset_information, element)
        return asset_information

    @classmethod
    def construct_submodel(cls, element: etree._Element, object_class=model.Submodel, **_kwargs: Any) \
            -> model.Submodel:
        submodel = object_class(
            _child_text_mandatory(element, NS_AAS + "id"),
            kind=_get_kind(element)
        )
        if not cls.stripped:
            submodel_elements = element.find(NS_AAS + "submodelElements")
            if submodel_elements is not None:
                for submodel_element in _failsafe_construct_multiple(submodel_elements, cls.construct_submodel_element,
                                                                     cls.failsafe):
                    submodel.submodel_element.add(submodel_element)
        cls._amend_abstract_attributes(submodel, element)
        return submodel

    @classmethod
    def construct_value_reference_pair(cls, element: etree._Element, object_class=model.ValueReferencePair,
                                       **_kwargs: Any) -> model.ValueReferencePair:
        return object_class(_child_text_mandatory(element, NS_AAS + "value"),
                            _child_construct_mandatory(element, NS_AAS + "valueId", cls.construct_reference))

    @classmethod
    def construct_value_list(cls, element: etree._Element, **_kwargs: Any) -> model.ValueList:
        """
        This function doesn't support the object_class parameter, because ValueList is just a generic type alias.
        """

        return set(
            _child_construct_multiple(_get_child_mandatory(element, NS_AAS + "valueReferencePairs"),
                                      NS_AAS + "valueReferencePair", cls.construct_value_reference_pair,
                                      cls.failsafe)
        )

    @classmethod
    def construct_concept_description(cls, element: etree._Element, object_class=model.ConceptDescription,
                                      **_kwargs: Any) -> model.ConceptDescription:
        cd = object_class(_child_text_mandatory(element, NS_AAS + "id"))
        is_case_of = element.find(NS_AAS + "isCaseOf")
        if is_case_of is not None:
            for ref in _child_construct_multiple(is_case_of, NS_AAS + "reference", cls.construct_reference,
                                                 cls.failsafe):
                cd.is_case_of.add(ref)
        cls._amend_abstract_attributes(cd, element)
        return cd

    @classmethod
    def construct_embedded_data_specification(cls, element: etree._Element,
                                              object_class=model.EmbeddedDataSpecification,
                                              **_kwargs: Any) -> model.EmbeddedDataSpecification:
        data_specification_content = _get_child_mandatory(element, NS_AAS + "dataSpecificationContent")
        if len(data_specification_content) == 0:
            raise KeyError(f"{_element_pretty_identifier(data_specification_content)} has no data specification!")
        if len(data_specification_content) > 1:
            logger.warning(f"{_element_pretty_identifier(data_specification_content)} has more than one "
                           "data specification, using the first one...")
        embedded_data_specification = object_class(
            _child_construct_mandatory(element, NS_AAS + "dataSpecification", cls.construct_external_reference),
            _failsafe_construct_mandatory(data_specification_content[0], cls.construct_data_specification_content)
        )
        cls._amend_abstract_attributes(embedded_data_specification, element)
        return embedded_data_specification

    @classmethod
    def construct_data_specification_content(cls, element: etree._Element, **kwargs: Any) \
            -> model.DataSpecificationContent:
        """
        This function doesn't support the object_class parameter.
        Overwrite each individual DataSpecificationContent constructor function instead.
        """
        data_specification_contents: Dict[str, Callable[..., model.DataSpecificationContent]] = \
            {NS_AAS + k: v for k, v in {
                "dataSpecificationIec61360": cls.construct_data_specification_iec61360,
            }.items()}
        if element.tag not in data_specification_contents:
            raise KeyError(f"{_element_pretty_identifier(element)} is not a valid DataSpecificationContent!")
        return data_specification_contents[element.tag](element, **kwargs)

    @classmethod
    def construct_data_specification_iec61360(cls, element: etree._Element,
                                              object_class=model.DataSpecificationIEC61360,
                                              **_kwargs: Any) -> model.DataSpecificationIEC61360:
        ds_iec = object_class(_child_construct_mandatory(element, NS_AAS + "preferredName",
                                                         cls.construct_preferred_name_type_iec61360))
        short_name = _failsafe_construct(element.find(NS_AAS + "shortName"), cls.construct_short_name_type_iec61360,
                                         cls.failsafe)
        if short_name is not None:
            ds_iec.short_name = short_name
        unit = _get_text_or_none(element.find(NS_AAS + "unit"))
        if unit is not None:
            ds_iec.unit = unit
        unit_id = _failsafe_construct(element.find(NS_AAS + "unitId"), cls.construct_reference, cls.failsafe)
        if unit_id is not None:
            ds_iec.unit_id = unit_id
        source_of_definition = _get_text_or_none(element.find(NS_AAS + "sourceOfDefinition"))
        if source_of_definition is not None:
            ds_iec.source_of_definition = source_of_definition
        symbol = _get_text_or_none(element.find(NS_AAS + "symbol"))
        if symbol is not None:
            ds_iec.symbol = symbol
        data_type = _get_text_mapped_or_none(element.find(NS_AAS + "dataType"), IEC61360_DATA_TYPES_INVERSE)
        if data_type is not None:
            ds_iec.data_type = data_type
        definition = _failsafe_construct(element.find(NS_AAS + "definition"), cls.construct_definition_type_iec61360,
                                         cls.failsafe)
        if definition is not None:
            ds_iec.definition = definition
        value_format = _get_text_or_none(element.find(NS_AAS + "valueFormat"))
        if value_format is not None:
            ds_iec.value_format = value_format
        value_list = _failsafe_construct(element.find(NS_AAS + "valueList"), cls.construct_value_list, cls.failsafe)
        if value_list is not None:
            ds_iec.value_list = value_list
        value = _get_text_or_none(element.find(NS_AAS + "value"))
        if value is not None and value_format is not None:
            ds_iec.value = value
        level_type = element.find(NS_AAS + "levelType")
        if level_type is not None:
            for child in level_type:
                tag = child.tag.split(NS_AAS, 1)[-1]
                if tag not in IEC61360_LEVEL_TYPES_INVERSE:
                    error_message = f"{_element_pretty_identifier(element)} has invalid levelType: {tag}"
                    if not cls.failsafe:
                        raise ValueError(error_message)
                    logger.warning(error_message)
                    continue
                try:
                    if child.text is None:
                        raise ValueError
                    level_type_value = _str_to_bool(child.text)
                except ValueError:
                    error_message = f"levelType {tag} of {_element_pretty_identifier(element)} has invalid boolean: " \
                            + str(child.text)
                    if not cls.failsafe:
                        raise ValueError(error_message)
                    logger.warning(error_message)
                    continue
                if level_type_value:
                    ds_iec.level_types.add(IEC61360_LEVEL_TYPES_INVERSE[tag])
        cls._amend_abstract_attributes(ds_iec, element)
        return ds_iec


class StrictAASFromXmlDecoder(AASFromXmlDecoder):
    """
    Non-failsafe XML decoder. Encountered errors won't be caught and abort parsing.
    """
    failsafe = False


class StrippedAASFromXmlDecoder(AASFromXmlDecoder):
    """
    Decoder for stripped XML elements. Used in the HTTP adapter.
    """
    stripped = True


class StrictStrippedAASFromXmlDecoder(StrictAASFromXmlDecoder, StrippedAASFromXmlDecoder):
    """
    Non-failsafe decoder for stripped XML elements.
    """
    pass


def _parse_xml_document(file: PathOrIO, failsafe: bool = True, **parser_kwargs: Any) -> Optional[etree._Element]:
    """
    Parse an XML document into an element tree

    :param file: A filename or file-like object to read the XML-serialized data from
    :param failsafe: If True, the file is parsed in a failsafe way: Instead of raising an Exception if the document
                     is malformed, parsing is aborted, an error is logged and None is returned
    :param parser_kwargs: Keyword arguments passed to the XMLParser constructor
    :raises ~lxml.etree.XMLSyntaxError: **Non-failsafe**: If the given file(-handle) has invalid XML
    :raises KeyError: **Non-failsafe**: If a required namespace has not been declared on the XML document
    :return: The root element of the element tree
    """

    parser = etree.XMLParser(remove_blank_text=True, remove_comments=True, **parser_kwargs)

    try:
        root = etree.parse(file, parser).getroot()
    except etree.XMLSyntaxError as e:
        if failsafe:
            logger.error(e)
            return None
        raise e

    missing_namespaces: Set[str] = REQUIRED_NAMESPACES - set(root.nsmap.values())
    if missing_namespaces:
        error_message = f"The following required namespaces are not declared: {' | '.join(missing_namespaces)}" \
                        + " - Is the input document of an older version?"
        if not failsafe:
            raise KeyError(error_message)
        logger.error(error_message)
    return root


def _select_decoder(failsafe: bool, stripped: bool, decoder: Optional[Type[AASFromXmlDecoder]]) \
        -> Type[AASFromXmlDecoder]:
    """
    Returns the correct decoder based on the parameters failsafe and stripped. If a decoder class is given, failsafe
    and stripped are ignored.

    :param failsafe: If true, a failsafe decoder is selected. Ignored if a decoder class is specified.
    :param stripped: If true, a decoder for parsing stripped XML elements is selected. Ignored if a decoder class is
                     specified.
    :param decoder: Is returned, if specified.
    :return: A AASFromXmlDecoder (sub)class.
    """
    if decoder is not None:
        return decoder
    if failsafe:
        if stripped:
            return StrippedAASFromXmlDecoder
        return AASFromXmlDecoder
    else:
        if stripped:
            return StrictStrippedAASFromXmlDecoder
        return StrictAASFromXmlDecoder


@enum.unique
class XMLConstructables(enum.Enum):
    """
    This enum is used to specify which type to construct in read_aas_xml_element().
    """
    KEY = enum.auto()
    REFERENCE = enum.auto()
    MODEL_REFERENCE = enum.auto()
    EXTERNAL_REFERENCE = enum.auto()
    ADMINISTRATIVE_INFORMATION = enum.auto()
    QUALIFIER = enum.auto()
    SECURITY = enum.auto()
    ANNOTATED_RELATIONSHIP_ELEMENT = enum.auto()
    BASIC_EVENT_ELEMENT = enum.auto()
    BLOB = enum.auto()
    CAPABILITY = enum.auto()
    ENTITY = enum.auto()
    EXTENSION = enum.auto()
    FILE = enum.auto()
    RESOURCE = enum.auto()
    MULTI_LANGUAGE_PROPERTY = enum.auto()
    OPERATION = enum.auto()
    PROPERTY = enum.auto()
    RANGE = enum.auto()
    REFERENCE_ELEMENT = enum.auto()
    RELATIONSHIP_ELEMENT = enum.auto()
    SUBMODEL_ELEMENT_COLLECTION = enum.auto()
    SUBMODEL_ELEMENT_LIST = enum.auto()
    ASSET_ADMINISTRATION_SHELL = enum.auto()
    ASSET_INFORMATION = enum.auto()
    SPECIFIC_ASSET_ID = enum.auto()
    SUBMODEL = enum.auto()
    VALUE_REFERENCE_PAIR = enum.auto()
    IEC61360_CONCEPT_DESCRIPTION = enum.auto()
    CONCEPT_DESCRIPTION = enum.auto()
    DATA_ELEMENT = enum.auto()
    SUBMODEL_ELEMENT = enum.auto()
    VALUE_LIST = enum.auto()
    MULTI_LANGUAGE_NAME_TYPE = enum.auto()
    MULTI_LANGUAGE_TEXT_TYPE = enum.auto()
    DEFINITION_TYPE_IEC61360 = enum.auto()
    PREFERRED_NAME_TYPE_IEC61360 = enum.auto()
    SHORT_NAME_TYPE_IEC61360 = enum.auto()
    EMBEDDED_DATA_SPECIFICATION = enum.auto()
    DATA_SPECIFICATION_CONTENT = enum.auto()
    DATA_SPECIFICATION_IEC61360 = enum.auto()


def read_aas_xml_element(file: PathOrIO, construct: XMLConstructables, failsafe: bool = True, stripped: bool = False,
                         decoder: Optional[Type[AASFromXmlDecoder]] = None, **constructor_kwargs) -> Optional[object]:
    """
    Construct a single object from an XML string. The namespaces have to be declared on the object itself, since there
    is no surrounding environment element.

    :param file: A filename or file-like object to read the XML-serialized data from
    :param construct: A member of the enum :class:`~.XMLConstructables`, specifying which type to construct.
    :param failsafe: If true, the document is parsed in a failsafe way: missing attributes and elements are logged
                     instead of causing exceptions. Defect objects are skipped.
                     This parameter is ignored if a decoder class is specified.
    :param stripped: If true, stripped XML elements are parsed.
                     See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
                     This parameter is ignored if a decoder class is specified.
    :param decoder: The decoder class used to decode the XML elements
    :param constructor_kwargs: Keyword arguments passed to the constructor function
    :raises ~lxml.etree.XMLSyntaxError: **Non-failsafe**: If the given file(-handle) has invalid XML
    :raises KeyError: **Non-failsafe**: If a required namespace has not been declared on the XML document
    :raises (~basyx.aas.model.base.AASConstraintViolation, KeyError, ValueError): **Non-failsafe**: Errors during
                                                                                  construction of the objects
    :return: The constructed object or None, if an error occurred in failsafe mode.
    """
    decoder_ = _select_decoder(failsafe, stripped, decoder)
    constructor: Callable[..., object]

    if construct == XMLConstructables.KEY:
        constructor = decoder_.construct_key
    elif construct == XMLConstructables.REFERENCE:
        constructor = decoder_.construct_reference
    elif construct == XMLConstructables.MODEL_REFERENCE:
        constructor = decoder_.construct_model_reference
    elif construct == XMLConstructables.EXTERNAL_REFERENCE:
        constructor = decoder_.construct_external_reference
    elif construct == XMLConstructables.ADMINISTRATIVE_INFORMATION:
        constructor = decoder_.construct_administrative_information
    elif construct == XMLConstructables.QUALIFIER:
        constructor = decoder_.construct_qualifier
    elif construct == XMLConstructables.ANNOTATED_RELATIONSHIP_ELEMENT:
        constructor = decoder_.construct_annotated_relationship_element
    elif construct == XMLConstructables.BASIC_EVENT_ELEMENT:
        constructor = decoder_.construct_basic_event_element
    elif construct == XMLConstructables.BLOB:
        constructor = decoder_.construct_blob
    elif construct == XMLConstructables.CAPABILITY:
        constructor = decoder_.construct_capability
    elif construct == XMLConstructables.ENTITY:
        constructor = decoder_.construct_entity
    elif construct == XMLConstructables.EXTENSION:
        constructor = decoder_.construct_extension
    elif construct == XMLConstructables.FILE:
        constructor = decoder_.construct_file
    elif construct == XMLConstructables.RESOURCE:
        constructor = decoder_.construct_resource
    elif construct == XMLConstructables.MULTI_LANGUAGE_PROPERTY:
        constructor = decoder_.construct_multi_language_property
    elif construct == XMLConstructables.OPERATION:
        constructor = decoder_.construct_operation
    elif construct == XMLConstructables.PROPERTY:
        constructor = decoder_.construct_property
    elif construct == XMLConstructables.RANGE:
        constructor = decoder_.construct_range
    elif construct == XMLConstructables.REFERENCE_ELEMENT:
        constructor = decoder_.construct_reference_element
    elif construct == XMLConstructables.RELATIONSHIP_ELEMENT:
        constructor = decoder_.construct_relationship_element
    elif construct == XMLConstructables.SUBMODEL_ELEMENT_COLLECTION:
        constructor = decoder_.construct_submodel_element_collection
    elif construct == XMLConstructables.SUBMODEL_ELEMENT_LIST:
        constructor = decoder_.construct_submodel_element_list
    elif construct == XMLConstructables.ASSET_ADMINISTRATION_SHELL:
        constructor = decoder_.construct_asset_administration_shell
    elif construct == XMLConstructables.ASSET_INFORMATION:
        constructor = decoder_.construct_asset_information
    elif construct == XMLConstructables.SPECIFIC_ASSET_ID:
        constructor = decoder_.construct_specific_asset_id
    elif construct == XMLConstructables.SUBMODEL:
        constructor = decoder_.construct_submodel
    elif construct == XMLConstructables.VALUE_REFERENCE_PAIR:
        constructor = decoder_.construct_value_reference_pair
    elif construct == XMLConstructables.CONCEPT_DESCRIPTION:
        constructor = decoder_.construct_concept_description
    elif construct == XMLConstructables.MULTI_LANGUAGE_NAME_TYPE:
        constructor = decoder_.construct_multi_language_name_type
    elif construct == XMLConstructables.MULTI_LANGUAGE_TEXT_TYPE:
        constructor = decoder_.construct_multi_language_text_type
    elif construct == XMLConstructables.DEFINITION_TYPE_IEC61360:
        constructor = decoder_.construct_definition_type_iec61360
    elif construct == XMLConstructables.PREFERRED_NAME_TYPE_IEC61360:
        constructor = decoder_.construct_preferred_name_type_iec61360
    elif construct == XMLConstructables.SHORT_NAME_TYPE_IEC61360:
        constructor = decoder_.construct_short_name_type_iec61360
    elif construct == XMLConstructables.EMBEDDED_DATA_SPECIFICATION:
        constructor = decoder_.construct_embedded_data_specification
    elif construct == XMLConstructables.DATA_SPECIFICATION_IEC61360:
        constructor = decoder_.construct_data_specification_iec61360
    # the following constructors decide which constructor to call based on the elements tag
    elif construct == XMLConstructables.DATA_ELEMENT:
        constructor = decoder_.construct_data_element
    elif construct == XMLConstructables.SUBMODEL_ELEMENT:
        constructor = decoder_.construct_submodel_element
    elif construct == XMLConstructables.DATA_SPECIFICATION_CONTENT:
        constructor = decoder_.construct_data_specification_content
    # type aliases
    elif construct == XMLConstructables.VALUE_LIST:
        constructor = decoder_.construct_value_list
    else:
        raise ValueError(f"{construct.name} cannot be constructed!")

    element = _parse_xml_document(file, failsafe=decoder_.failsafe)
    return _failsafe_construct(element, constructor, decoder_.failsafe, **constructor_kwargs)


def read_aas_xml_file_into(object_store: model.AbstractObjectStore[model.Identifiable], file: PathOrIO,
                           replace_existing: bool = False, ignore_existing: bool = False, failsafe: bool = True,
                           stripped: bool = False, decoder: Optional[Type[AASFromXmlDecoder]] = None,
                           **parser_kwargs: Any) -> Set[model.Identifier]:
    """
    Read an Asset Administration Shell XML file according to 'Details of the Asset Administration Shell', chapter 5.4
    into a given :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>`.

    :param object_store: The :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` in which the
                         :class:`~basyx.aas.model.base.Identifiable` objects should be stored
    :param file: A filename or file-like object to read the XML-serialized data from
    :param replace_existing: Whether to replace existing objects with the same identifier in the object store or not
    :param ignore_existing: Whether to ignore existing objects (e.g. log a message) or raise an error.
                            This parameter is ignored if replace_existing is True.
    :param failsafe: If ``True``, the document is parsed in a failsafe way: missing attributes and elements are logged
                     instead of causing exceptions. Defect objects are skipped.
                     This parameter is ignored if a decoder class is specified.
    :param stripped: If ``True``, stripped XML elements are parsed.
                     See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
                     This parameter is ignored if a decoder class is specified.
    :param decoder: The decoder class used to decode the XML elements
    :param parser_kwargs: Keyword arguments passed to the XMLParser constructor
    :raises ~lxml.etree.XMLSyntaxError: **Non-failsafe**: If the given file(-handle) has invalid XML
    :raises KeyError: **Non-failsafe**: If a required namespace has not been declared on the XML document
    :raises KeyError: **Non-failsafe**: Encountered a duplicate identifier
    :raises KeyError: Encountered an identifier that already exists in the given ``object_store`` with both
                     ``replace_existing`` and ``ignore_existing`` set to ``False``
    :raises (~basyx.aas.model.base.AASConstraintViolation, KeyError, ValueError): **Non-failsafe**: Errors during
                                                                                  construction of the objects
    :raises TypeError: **Non-failsafe**: Encountered an undefined top-level list (e.g. ``<aas:submodels1>``)
    :return: A set of :class:`Identifiers <basyx.aas.model.base.Identifier>` that were added to object_store
    """
    ret: Set[model.Identifier] = set()

    decoder_ = _select_decoder(failsafe, stripped, decoder)

    element_constructors: Dict[str, Callable[..., model.Identifiable]] = {
        "assetAdministrationShell": decoder_.construct_asset_administration_shell,
        "conceptDescription": decoder_.construct_concept_description,
        "submodel": decoder_.construct_submodel
    }

    element_constructors = {NS_AAS + k: v for k, v in element_constructors.items()}

    root = _parse_xml_document(file, failsafe=decoder_.failsafe, **parser_kwargs)

    if root is None:
        return ret

    # Add AAS objects to ObjectStore
    for list_ in root:
        element_tag = list_.tag[:-1]
        if list_.tag[-1] != "s" or element_tag not in element_constructors:
            error_message = f"Unexpected top-level list {_element_pretty_identifier(list_)}!"
            if not decoder_.failsafe:
                raise TypeError(error_message)
            logger.warning(error_message)
            continue
        constructor = element_constructors[element_tag]
        for element in _child_construct_multiple(list_, element_tag, constructor, decoder_.failsafe):
            if element.id in ret:
                error_message = f"{element} has a duplicate identifier already parsed in the document!"
                if not decoder_.failsafe:
                    raise KeyError(error_message)
                logger.error(error_message + " skipping it...")
                continue
            existing_element = object_store.get(element.id)
            if existing_element is not None:
                if not replace_existing:
                    error_message = f"object with identifier {element.id} already exists " \
                                    f"in the object store: {existing_element}!"
                    if not ignore_existing:
                        raise KeyError(error_message + f" failed to insert {element}!")
                    logger.info(error_message + f" skipping insertion of {element}...")
                    continue
                object_store.discard(existing_element)
            object_store.add(element)
            ret.add(element.id)
    return ret


def read_aas_xml_file(file: PathOrIO, **kwargs: Any) -> model.DictObjectStore[model.Identifiable]:
    """
    A wrapper of :meth:`~basyx.aas.adapter.xml.xml_deserialization.read_aas_xml_file_into`, that reads all objects in an
    empty :class:`~basyx.aas.model.provider.DictObjectStore`. This function supports
    the same keyword arguments as :meth:`~basyx.aas.adapter.xml.xml_deserialization.read_aas_xml_file_into`.

    :param file: A filename or file-like object to read the XML-serialized data from
    :param kwargs: Keyword arguments passed to :meth:`~basyx.aas.adapter.xml.xml_deserialization.read_aas_xml_file_into`
    :raises ~lxml.etree.XMLSyntaxError: **Non-failsafe**: If the given file(-handle) has invalid XML
    :raises KeyError: **Non-failsafe**: If a required namespace has not been declared on the XML document
    :raises KeyError: **Non-failsafe**: Encountered a duplicate identifier
    :raises (~basyx.aas.model.base.AASConstraintViolation, KeyError, ValueError): **Non-failsafe**: Errors during
                                                                                  construction of the objects
    :raises TypeError: **Non-failsafe**: Encountered an undefined top-level list (e.g. ``<aas:submodels1>``)
    :return: A :class:`~basyx.aas.model.provider.DictObjectStore` containing all AAS objects from the XML file
    """
    object_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    read_aas_xml_file_into(object_store, file, **kwargs)
    return object_store
