# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module implements the basic structures of the AAS metamodel, including the abstract classes and enums needed for
the higher level classes to inherit from.
"""

import abc
import inspect
import itertools
from enum import Enum, unique
from typing import List, Optional, Set, TypeVar, MutableSet, Generic, Iterable, Dict, Iterator, Union, overload, \
    MutableSequence, Type, Any, TYPE_CHECKING, Tuple, Callable, MutableMapping
import re

from . import datatypes, _string_constraints
from ..backend import backends

if TYPE_CHECKING:
    from . import provider

DataTypeDefXsd = Type[datatypes.AnyXSDType]
ValueDataType = datatypes.AnyXSDType  # any xsd atomic type (from .datatypes)
ValueList = Set["ValueReferencePair"]
BlobType = bytes

# The following string aliases are constrained by the decorator functions defined in the string_constraints module,
# wherever they are used for an instance attributes.
ContentType = str  # any mimetype as in RFC2046
Identifier = str
LabelType = str
MessageTopicType = str
NameType = str
PathType = str
QualifierType = str
RevisionType = str
ShortNameType = str
VersionType = str
ValueTypeIEC61360 = str


@unique
class KeyTypes(Enum):
    """
    Enumeration for denoting which kind of entity is referenced. They can be categorized in ReferableElements,
    IdentifiableElements and other KeyTypes

    **IdentifiableElements starting from 0**

    :cvar ASSET_ADMINISTRATION_SHELL: :class:`~basyx.aas.model.aas.AssetAdministrationShell`
    :cvar CONCEPT_DESCRIPTION: :class:`~basyx.aas.model.concept.ConceptDescription`
    :cvar SUBMODEL: :class:`~basyx.aas.model.submodel.Submodel`

    **ReferableElements starting from 1000**

    .. note::
        DataElement is abstract, i.e. if a key uses :attr:`~.KeyTypes.DATA_ELEMENT` the reference may be
        :class:`~basyx.aas.model.submodel.Property`, :class:`~basyx.aas.model.submodel.File` etc.

    .. note::
        SubmodelElement is abstract, i.e. if a key uses :attr:`~.KeyTypes.SUBMODEL_ELEMENT` the reference may be a
        :class:`~basyx.aas.model.submodel.Property`, a :class:`~basyx.aas.model.submodel.SubmodelElementCollection`,
        an :class:`~basyx.aas.model.submodel.Operation` etc.

    :cvar ANNOTATED_RELATIONSHIP_ELEMENT: :class:`~basyx.aas.model.submodel.AnnotatedRelationshipElement`
    :cvar BASIC_EVENT_ELEMENT: :class:`~basyx.aas.model.submodel.BasicEventElement`
    :cvar BLOB: :class:`~basyx.aas.model.submodel.Blob`
    :cvar CAPABILITY: :class:`~basyx.aas.model.submodel.Capability`
    :cvar DATA_ELEMENT: :class:`~basyx.aas.model.submodel.DataElement`
    :cvar ENTITY: :class:`~basyx.aas.model.submodel.Entity`
    :cvar EVENT_ELEMENT: :class:`~basyx.aas.model.submodel.EventElement`, Note: EventElement is abstract
    :cvar FILE: :class:`~basyx.aas.model.submodel.File`
    :cvar MULTI_LANGUAGE_PROPERTY: :class:`~basyx.aas.model.submodel.MultiLanguageProperty` property with a value that
                                   can be provided in multiple languages
    :cvar OPERATION: :class:`~basyx.aas.model.submodel.Operation`
    :cvar PROPERTY: :class:`~basyx.aas.model.submodel.Property`
    :cvar RANGE: :class:`~basyx.aas.model.submodel.Range` with min and max
    :cvar REFERENCE_ELEMENT: :class:`~basyx.aas.model.submodel.ReferenceElement`
    :cvar RELATIONSHIP_ELEMENT: :class:`~basyx.aas.model.submodel.RelationshipElement`
    :cvar SUBMODEL_ELEMENT: :class:`~basyx.aas.model.submodel.SubmodelElement`
    :cvar SUBMODEL_ELEMENT_COLLECTION: :class:`~basyx.aas.model.submodel.SubmodelElementCollection`
    :cvar SUBMODEL_ELEMENT_LIST: :class:`~basyx.aas.model.submodel.SubmodelElementList`

    **KeyTypes starting from 2000**

    :cvar GLOBAL_REFERENCE: reference to an element not belonging to an asset administration shell
    :cvar FRAGMENT_REFERENCE: unique reference to an element within a file. The file itself is assumed to be part of an
                              asset administration shell.
    """

    # AasIdentifiables starting from 0
    # keep _ASSET = 0 as a protected enum member here, so 0 isn't reused by a future key type
    _ASSET = 0
    ASSET_ADMINISTRATION_SHELL = 1
    CONCEPT_DESCRIPTION = 2
    SUBMODEL = 3

    # AasSubmodelElements starting from 1000
    # keep _ACCESS_PERMISSION_RULE = 1000 as a protected enum member here, so 1000 isn't reused by a future key type
    _ACCESS_PERMISSION_RULE = 1000
    ANNOTATED_RELATIONSHIP_ELEMENT = 1001
    BASIC_EVENT_ELEMENT = 1002
    BLOB = 1003
    CAPABILITY = 1004
    # keep _CONCEPT_DICTIONARY = 1005 as a protected enum member here, so 1005 isn't reused by a future key type
    _CONCEPT_DICTIONARY = 1005
    DATA_ELEMENT = 1006
    ENTITY = 1007
    EVENT_ELEMENT = 1008
    FILE = 1009
    MULTI_LANGUAGE_PROPERTY = 1010
    OPERATION = 1011
    PROPERTY = 1012
    RANGE = 1013
    REFERENCE_ELEMENT = 1014
    RELATIONSHIP_ELEMENT = 1015
    SUBMODEL_ELEMENT = 1016
    SUBMODEL_ELEMENT_COLLECTION = 1017
    # keep _VIEW = 1018 as a protected enum member here, so 1018 isn't reused by a future key type
    _VIEW = 1018
    SUBMODEL_ELEMENT_LIST = 1019

    # GenericFragmentKeys and GenericGloballyIdentifiables starting from 2000
    GLOBAL_REFERENCE = 2000
    FRAGMENT_REFERENCE = 2001

    @property
    def is_aas_identifiable(self) -> bool:
        return self in (self.ASSET_ADMINISTRATION_SHELL, self.CONCEPT_DESCRIPTION, self.SUBMODEL)

    @property
    def is_generic_globally_identifiable(self) -> bool:
        return self == self.GLOBAL_REFERENCE

    @property
    def is_generic_fragment_key(self) -> bool:
        return self == self.FRAGMENT_REFERENCE

    @property
    def is_aas_submodel_element(self) -> bool:
        return self in (
            self.ANNOTATED_RELATIONSHIP_ELEMENT,
            self.BASIC_EVENT_ELEMENT,
            self.BLOB,
            self.CAPABILITY,
            self.DATA_ELEMENT,
            self.ENTITY,
            self.EVENT_ELEMENT,
            self.FILE,
            self.MULTI_LANGUAGE_PROPERTY,
            self.OPERATION,
            self.PROPERTY,
            self.RANGE,
            self.REFERENCE_ELEMENT,
            self.RELATIONSHIP_ELEMENT,
            self.SUBMODEL_ELEMENT,
            self.SUBMODEL_ELEMENT_COLLECTION,
            self.SUBMODEL_ELEMENT_LIST
        )

    @property
    def is_aas_referable_non_identifiable(self) -> bool:
        return self.is_aas_submodel_element

    @property
    def is_fragment_key_element(self) -> bool:
        return self.is_aas_referable_non_identifiable or self.is_generic_fragment_key

    @property
    def is_globally_identifiable(self) -> bool:
        return self.is_aas_identifiable or self.is_generic_globally_identifiable


@unique
class EntityType(Enum):
    """
    Enumeration for denoting whether an entity is a self-managed or a co-managed entity

    :cvar CO_MANAGED_ENTITY: For co-managed entities there is no separate
                             :class:`AAS <basyx.aas.model.aas.AssetAdministrationShell>`. Co-managed entities need to
                             be part of a self-managed entity
    :cvar SELF_MANAGED_ENTITY: Self-managed entities have their own
                               :class:`AAS <basyx.aas.model.aas.AssetAdministrationShell>`, but can be part of the bill
                               of material of a composite self-managed entity.
    """

    CO_MANAGED_ENTITY = 0
    SELF_MANAGED_ENTITY = 1


@unique
class ModellingKind(Enum):
    """
    Enumeration for denoting whether an element is a type or an instance.

    .. note::
        An ``INSTANCE`` becomes an individual entity of a template, for example a device model,
        by defining specific property values.

    .. note::
        In an object-oriented view, an instance denotes an object of a template (class).

    :cvar TEMPLATE: Software element which specifies the common attributes shared by all instances of the template
    :cvar INSTANCE: concrete, clearly identifiable component of a certain template.

    .. note::
        It becomes an individual entity of a template, for example a device model, by defining
        specific property values.

    .. note::
        In an object-oriented view, an instance denotes an object of a template (class).
    """

    TEMPLATE = 0
    INSTANCE = 1


@unique
class AssetKind(Enum):
    """
    Enumeration for denoting whether an asset is a type asset or an instance asset or whether this kind of
    classification is not applicable.

    .. note::
        :attr:`~.AssetKind.INSTANCE` becomes an individual entity of a type, for example a device, by defining
        specific property values.

    .. note::
        In an object-oriented view, an instance denotes an object of a class (of a type)

    :cvar TYPE: Type asset
    :cvar INSTANCE: Instance asset
    :cvar NOT_APPLICABLE: Neither a type asset nor an instance asset
    """

    TYPE = 0
    INSTANCE = 1
    NOT_APPLICABLE = 2


class QualifierKind(Enum):
    """
    Enumeration for denoting whether a Qualifier is a concept, template or value qualifier.

    :cvar CONCEPT_QUALIFIER: qualifies the semantic definition the element is referring to (HasSemantics/semanticId)
    :cvar TEMPLATE_QUALIFIER: qualifies the elements within a specific submodel on concept level. Template qualifiers
                              are only applicable to elements with kind=``Template``
    :cvar VALUE_QUALIFIER: qualifies the value of the element and can change during run-time. Value qualifiers are only
                           applicable to elements with kind=``Instance``
    """

    CONCEPT_QUALIFIER = 0
    TEMPLATE_QUALIFIER = 1
    VALUE_QUALIFIER = 2


@unique
class Direction(Enum):
    """
    Direction of an event. Used in :class:`basyx.aas.model.submodel.BasicEventElement`.
    """

    INPUT = 0
    OUTPUT = 1


@unique
class StateOfEvent(Enum):
    """
    State of an event. Used in :class:`basyx.aas.model.submodel.BasicEventElement`.
    """

    ON = 0
    OFF = 1


class LangStringSet(MutableMapping[str, str]):
    """
    A mapping of language code to string. Must be non-empty.

    langString is an RDF data type. A langString is a value tagged with a language code. RDF requires
    IETF BCP 4723 language tags, i.e. simple two-letter language tags for Locales like "de" conformant to ISO 639-1
    are allowed as well as language tags plus extension like "de-DE" for country code, dialect etc. like in "en-US" or
    "en-GB" for English (United Kingdom) and English (United States). IETF language tags are referencing ISO 639,
    ISO 3166 and ISO 15924.
    """
    def __init__(self, dict_: Dict[str, str]):
        self._dict: Dict[str, str] = {}

        if len(dict_) < 1:
            raise ValueError(f"A {self.__class__.__name__} must not be empty!")
        for ltag in dict_:
            self._check_language_tag_constraints(ltag)
            self._dict[ltag] = dict_[ltag]

    @classmethod
    def _check_language_tag_constraints(cls, ltag: str):
        split = ltag.split("-", 1)
        lang_code = split[0]
        if len(lang_code) != 2 or not lang_code.isalpha() or not lang_code.islower():
            raise ValueError(f"The language code of the language tag must consist of exactly two lower-case letters! "
                             f"Given language tag and language code: '{ltag}', '{lang_code}'")

    def __getitem__(self, item: str) -> str:
        return self._dict[item]

    def __setitem__(self, key: str, value: str) -> None:
        self._check_language_tag_constraints(key)
        self._dict[key] = value

    def __delitem__(self, key: str) -> None:
        if len(self._dict) == 1:
            raise KeyError(f"A {self.__class__.__name__} must not be empty!")
        del self._dict[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    def __repr__(self) -> str:
        return self.__class__.__name__ + "(" + ", ".join(f'{k}="{v}"' for k, v in self.items()) + ")"

    def clear(self) -> None:
        raise KeyError(f"A {self.__class__.__name__} must not be empty!")


class ConstrainedLangStringSet(LangStringSet, metaclass=abc.ABCMeta):
    """
    A :class:`LangStringSet` with constrained values.
    """
    @abc.abstractmethod
    def __init__(self, dict_: Dict[str, str], constraint_check_fn: Callable[[str, str], None]):
        super().__init__(dict_)
        self._constraint_check_fn: Callable[[str, str], None] = constraint_check_fn
        for ltag, text in self._dict.items():
            self._check_text_constraints(ltag, text)

    def _check_text_constraints(self, ltag: str, text: str) -> None:
        try:
            self._constraint_check_fn(text, self.__class__.__name__)
        except ValueError as e:
            raise ValueError(f"The text for the language tag '{ltag}' is invalid: {e}") from e

    def __setitem__(self, key: str, value: str) -> None:
        self._check_text_constraints(key, value)
        super().__setitem__(key, value)


class MultiLanguageNameType(ConstrainedLangStringSet):
    """
    A :class:`~.ConstrainedLangStringSet` where each value is a :class:`ShortNameType`.
    See also: :func:`basyx.aas.model._string_constraints.check_short_name_type`
    """
    def __init__(self, dict_: Dict[str, str]):
        super().__init__(dict_, _string_constraints.check_short_name_type)


class MultiLanguageTextType(ConstrainedLangStringSet):
    """
    A :class:`~.ConstrainedLangStringSet` where each value must have at least 1 and at most 1023 characters.
    """
    def __init__(self, dict_: Dict[str, str]):
        super().__init__(dict_, _string_constraints.create_check_function(min_length=1, max_length=1023))


class DefinitionTypeIEC61360(ConstrainedLangStringSet):
    """
    A :class:`~.ConstrainedLangStringSet` where each value must have at least 1 and at most 1023 characters.
    """
    def __init__(self, dict_: Dict[str, str]):
        super().__init__(dict_, _string_constraints.create_check_function(min_length=1, max_length=1023))


class PreferredNameTypeIEC61360(ConstrainedLangStringSet):
    """
    A :class:`~.ConstrainedLangStringSet` where each value must have at least 1 and at most 255 characters.
    """
    def __init__(self, dict_: Dict[str, str]):
        super().__init__(dict_, _string_constraints.create_check_function(min_length=1, max_length=255))


class ShortNameTypeIEC61360(ConstrainedLangStringSet):
    """
    A :class:`~.ConstrainedLangStringSet` where each value must have at least 1 and at most 18 characters.
    """
    def __init__(self, dict_: Dict[str, str]):
        super().__init__(dict_, _string_constraints.create_check_function(min_length=1, max_length=18))


class Key:
    """
    A key is a reference to an element by its id.

    :ivar type: Denote which kind of entity is referenced. In case type = :attr:`~.KeyTypes.GLOBAL_REFERENCE` then
               the element is a global unique id. In all other cases the key references a model element of the same or
               of another AAS. The name of the model element is explicitly listed.
    :ivar value: The key value, for example an IRDI or IRI
    """

    def __init__(self,
                 type_: KeyTypes,
                 value: Identifier):
        """
        TODO: Add instruction what to do after construction
        """
        _string_constraints.check_identifier(value)
        self.type: KeyTypes
        self.value: Identifier
        super().__setattr__('type', type_)
        super().__setattr__('value', value)

    def __setattr__(self, key, value):
        """Prevent modification of attributes."""
        raise AttributeError('Reference is immutable')

    def __repr__(self) -> str:
        return "Key(type={}, value={})".format(self.type.name, self.value)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Key):
            return NotImplemented
        return (self.value == other.value
                and self.type == other.type)

    def __hash__(self):
        return hash((self.value, self.type))

    def get_identifier(self) -> Optional[Identifier]:
        """
        Get an :class:`Identifier` object corresponding to this key, if it is an identifiable key.

        :return: None if this is no identifiable key, otherwise a corresponding :class:`Identifier` string.
        """
        if not self.type.is_aas_identifiable:
            return None
        return self.value

    @staticmethod
    def from_referable(referable: "Referable") -> "Key":
        """
        Construct a key for a given :class:`~.Referable` (or :class:`~.Identifiable`) object

        :param referable: :class:`~.Referable` or :class:`~.Identifiable` object
        :returns: :class:`~.Key`
        """
        # Get the `type` by finding the first class from the base classes list (via inspect.getmro), that is contained
        # in KEY_ELEMENTS_CLASSES
        from . import KEY_TYPES_CLASSES, SubmodelElementList
        try:
            key_type = next(iter(KEY_TYPES_CLASSES[t]
                                 for t in inspect.getmro(type(referable))
                                 if t in KEY_TYPES_CLASSES))
        except StopIteration:
            key_type = KeyTypes.PROPERTY

        if isinstance(referable, Identifiable):
            return Key(key_type, referable.id)
        elif isinstance(referable.parent, SubmodelElementList):
            try:
                return Key(key_type, str(referable.parent.value.index(referable)))  # type: ignore
            except ValueError as e:
                raise ValueError(f"Object {referable!r} is not contained within its parent {referable.parent!r}") from e
        else:
            if referable.id_short is None:
                raise ValueError(f"Can't create Key for {referable!r} without an id_short!")
            return Key(key_type, referable.id_short)


_NSO = TypeVar('_NSO', bound=Union["Referable", "Qualifier", "HasSemantics", "Extension"])


class Namespace(metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold  objects and resolve them by their
    specific attribute.

    <<abstract>>

    :ivar namespace_element_sets: List of :class:`NamespaceSets <basyx.aas.model.base.NamespaceSet>`
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.namespace_element_sets: List[NamespaceSet] = []

    def _get_object(self, object_type: Type[_NSO], attribute_name: str, attribute) -> _NSO:
        """
        Find an :class:`~._NSO` in this namespace by its attribute

        :raises KeyError: If no such :class:`~._NSO` can be found
        """
        for ns_set in self.namespace_element_sets:
            try:
                return ns_set.get_object_by_attribute(attribute_name, attribute)
            except KeyError:
                continue
        raise KeyError(f"{object_type.__name__} with {attribute_name} {attribute} not found in {self!r}")

    def _add_object(self, attribute_name: str, obj: _NSO) -> None:
        """
        Add an :class:`~._NSO` to this namespace by its attribute

        :raises KeyError: If no such :class:`~._NSO` can be found
        """
        for ns_set in self.namespace_element_sets:
            if attribute_name not in ns_set.get_attribute_name_list():
                continue
            ns_set.add(obj)
            return
        raise ValueError(f"{obj!r} can't be added to this namespace")

    def _remove_object(self, object_type: type, attribute_name: str, attribute) -> None:
        """
        Remove an :class:`~.NSO` from this namespace by its attribute

        :raises KeyError: If no such :class:`~.NSO` can be found
        """
        for ns_set in self.namespace_element_sets:
            if attribute_name in ns_set.get_attribute_name_list():
                try:
                    ns_set.remove_by_id(attribute_name, attribute)
                    return
                except KeyError:
                    continue
        raise KeyError(f"{object_type.__name__} with {attribute_name} {attribute} not found in {self!r}")


class HasExtension(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold Extension objects and resolve them by their
    name.

    <<abstract>>

    **Constraint AASd-077:** The name of an Extension within HasExtensions needs to be unique.

    :ivar namespace_element_sets: List of :class:`NamespaceSets <basyx.aas.model.base.NamespaceSet>`
    :ivar extension: A :class:`~.NamespaceSet` of :class:`Extensions <.Extension>` of the element.
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.namespace_element_sets: List[NamespaceSet] = []
        self.extension: NamespaceSet[Extension]

    def get_extension_by_name(self, name: str) -> "Extension":
        """
        Find an :class:`~.Extension` in this namespace by its name

        :raises KeyError: If no such :class:`~.Extension` can be found
        """
        return super()._get_object(Extension, "name", name)

    def add_extension(self, extension: "Extension") -> None:
        """
        Add a :class:`~.Extension` to this Namespace

        :param extension: The :class:`~.Extension` to add
        :raises KeyError: If a :class:`~.Extension` with the same name is already present in this namespace
        :raises ValueError: If the given :class:`~.Extension` already has a parent namespace
        """
        return super()._add_object("name", extension)

    def remove_extension_by_name(self, name: str) -> None:
        """
        Remove an :class:`~.Extension` from this namespace by its name

        :raises KeyError: If no such :class:`~.Extension` can be found
        """
        return super()._remove_object(HasExtension, "name", name)


class Referable(HasExtension, metaclass=abc.ABCMeta):
    """
    An element that is referable by its id_short. This id is not globally unique. This id is unique within
    the name space of the element.

    <<abstract>>

    **Constraint AASd-001:** In case of a referable element not being an identifiable element the
    idShort is mandatory and used for referring to the element in its name space.

    **Constraint AASd-002:** idShort shall only feature letters, digits, underscore (``_``); starting
    mandatory with a letter.

    **Constraint AASd-004:** Add parent in case of non-identifiable elements.

    **Constraint AASd-022:** idShort of non-identifiable referables shall be unique in its namespace (case-sensitive)

    :ivar _id_short: Identifying string of the element within its name space
    :ivar category: The category is a value that gives further meta information w.r.t. to the class of the element.
                      It affects the expected existence of attributes and the applicability of constraints.
    :ivar description: Description or comments on the element.
    :ivar parent: Reference (in form of a :class:`~.UniqueIdShortNamespace`) to the next referable parent element
        of the element.

    :ivar source: Source of the object, a URI, that defines where this object's data originates from.
                  This is used to specify where the Referable should be updated from and committed to.
                  Default is an empty string, making it use the source of its ancestor, if possible.
    """
    @abc.abstractmethod
    def __init__(self):
        super().__init__()
        self._id_short: Optional[NameType] = None
        self.display_name: Optional[MultiLanguageNameType] = dict()
        self._category: Optional[NameType] = None
        self.description: Optional[MultiLanguageTextType] = dict()
        # We use a Python reference to the parent Namespace instead of a Reference Object, as specified. This allows
        # simpler and faster navigation/checks and it has no effect in the serialized data formats anyway.
        self.parent: Optional[UniqueIdShortNamespace] = None
        self.source: str = ""

    def __repr__(self) -> str:
        reversed_path = []
        item = self  # type: Any
        if item.id_short is not None:
            from .submodel import SubmodelElementList
            while item is not None:
                if isinstance(item, Identifiable):
                    reversed_path.append(item.id)
                    break
                elif isinstance(item, Referable):
                    if isinstance(item.parent, SubmodelElementList):
                        reversed_path.append(f"{item.parent.id_short}[{item.parent.value.index(item)}]")
                        item = item.parent
                    else:
                        reversed_path.append(item.id_short)
                    item = item.parent
                else:
                    raise AttributeError('Referable must have an identifiable as root object and only parents that are '
                                         'referable')

        return self.__class__.__name__ + ("[{}]".format(" / ".join(reversed(reversed_path))) if reversed_path else "")

    def _get_id_short(self) -> Optional[NameType]:
        return self._id_short

    def _set_category(self, category: Optional[NameType]):
        """
        Check the input string

        :param category: The category is a value that gives further meta information w.r.t. to the class of the element.
                         It affects the expected existence of attributes and the applicability of constraints.
        :raises ValueError: if the constraint is not fulfilled
        """
        if category is not None:
            _string_constraints.check_name_type(category)
        self._category = category

    def _get_category(self) -> Optional[NameType]:
        return self._category

    @classmethod
    def validate_id_short(cls, id_short: NameType) -> None:
        """
        Validates an id_short against Constraint AASd-002 and :class:`NameType` restrictions.

        **Constraint AASd-002:** idShort of Referables shall only feature letters, digits, underscore (``_``); starting
        mandatory with a letter. I.e. ``[a-zA-Z][a-zA-Z0-9_]+``

        :param id_short: The id_short to validate
        :raises ValueError: If the id_short doesn't comply to the constraints imposed by :class:`NameType`
            (see :func:`~basyx.aas.model._string_constraints.check_name_type`).
        :raises AASConstraintViolation: If the id_short doesn't comply to Constraint AASd-002.
        """
        _string_constraints.check_name_type(id_short)
        test_id_short: NameType = str(id_short)
        if not re.fullmatch("[a-zA-Z0-9_]*", test_id_short):
            raise AASConstraintViolation(
                2,
                "The id_short must contain only letters, digits and underscore"
            )
        if not test_id_short[0].isalpha():
            raise AASConstraintViolation(
                2,
                "The id_short must start with a letter"
            )

    category = property(_get_category, _set_category)

    def _set_id_short(self, id_short: Optional[NameType]):
        """
        Check the input string

        **Constraint AASd-002:** idShort of Referables shall only feature letters, digits, underscore (``_``); starting
        mandatory with a letter. I.e. ``[a-zA-Z][a-zA-Z0-9_]+``

        **Constraint AASd-022:** idShort of non-identifiable referables shall be unique in its namespace
        (case-sensitive)

        :param id_short: Identifying string of the element within its name space
        :raises ValueError: If the id_short doesn't comply to the constraints imposed by :class:`NameType`
            (see :func:`~basyx.aas.model._string_constraints.check_name_type`).
        :raises AASConstraintViolation: If the new idShort causes a name collision in the parent Namespace or if the
            id_short doesn't comply to Constraint AASd-002.
        """

        if id_short == self.id_short:
            return
        if id_short is not None:
            self.validate_id_short(id_short)

        if self.parent is not None:
            if id_short is None:
                raise AASConstraintViolation(117, f"id_short of {self!r} cannot be unset, since it is already "
                                                  f"contained in {self.parent!r}")
            from .submodel import SubmodelElementList
            if isinstance(self.parent, SubmodelElementList):
                raise AASConstraintViolation(120, f"id_short of {self!r} cannot be set, because it is "
                                                  f"contained in a {self.parent!r}")
            for set_ in self.parent.namespace_element_sets:
                if set_.contains_id("id_short", id_short):
                    raise AASConstraintViolation(22, "Object with id_short '{}' is already present in the parent "
                                                     "Namespace".format(id_short))

            set_add_list: List[NamespaceSet] = []
            for set_ in self.parent.namespace_element_sets:
                if self in set_:
                    set_add_list.append(set_)
                    set_.discard(self)
            self._id_short = id_short
            for set_ in set_add_list:
                set_.add(self)
        # Redundant to the line above. However, this way, we make sure that we really update the _id_short
        self._id_short = id_short

    def update(self,
               max_age: float = 0,
               recursive: bool = True,
               _indirect_source: bool = True) -> None:
        """
        Update the local Referable object from any underlying external data source, using an appropriate backend

        If there is no source given, it will find its next ancestor with a source and update from this source.
        If there is no source in any ancestor, this function will do nothing

        :param max_age: Maximum age of the local data in seconds. This method may return early, if the previous update
                        of the object has been performed less than ``max_age`` seconds ago.
        :param recursive: Also call update on all children of this object. Default is True
        :param _indirect_source: Internal parameter to avoid duplicate updating.
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        # TODO consider max_age
        if not _indirect_source:
            # Update was already called on an ancestor of this Referable. Only update it, if it has its own source
            if self.source != "":
                backends.get_backend(self.source).update_object(updated_object=self,
                                                                store_object=self,
                                                                relative_path=[])

        else:
            # Try to find a valid source for this Referable
            if self.source != "":
                backends.get_backend(self.source).update_object(updated_object=self,
                                                                store_object=self,
                                                                relative_path=[])
            else:
                store_object, relative_path = self.find_source()
                if store_object and relative_path is not None:
                    backends.get_backend(store_object.source).update_object(updated_object=self,
                                                                            store_object=store_object,
                                                                            relative_path=list(relative_path))

        if recursive:
            # update all the children who have their own source
            if isinstance(self, UniqueIdShortNamespace):
                for namespace_set in self.namespace_element_sets:
                    if "id_short" not in namespace_set.get_attribute_name_list():
                        continue
                    for referable in namespace_set:
                        referable.update(max_age, recursive=True, _indirect_source=False)

    def find_source(self) -> Tuple[Optional["Referable"], Optional[List[str]]]:  # type: ignore
        """
        Finds the closest source in these objects ancestors. If there is no source, returns None

        :return: Tuple with the closest ancestor with a defined source and the relative path of id_shorts to that
                 ancestor
        """
        referable: Referable = self
        relative_path: List[NameType] = [self.id_short]
        while referable is not None:
            if referable.source != "":
                relative_path.reverse()
                return referable, relative_path
            if referable.parent:
                assert isinstance(referable.parent, Referable)
                referable = referable.parent
                relative_path.append(referable.id_short)
                continue
            break
        return None, None

    def update_from(self, other: "Referable", update_source: bool = False):
        """
        Internal function to updates the object's attributes from another object of a similar type.

        This function should not be used directly. It is typically used by backend implementations (database adapters,
        protocol clients, etc.) to update the object's data, after ``update()`` has been called.

        :param other: The object to update from
        :param update_source: Update the source attribute with the other's source attribute. This is not propagated
                              recursively
        """
        for name, var in vars(other).items():
            # do not update the parent, namespace_element_sets or source (depending on update_source parameter)
            if name in ("parent", "namespace_element_sets") or name == "source" and not update_source:
                continue
            if isinstance(var, NamespaceSet):
                # update the elements of the NameSpaceSet
                vars(self)[name].update_nss_from(var)
            else:
                vars(self)[name] = var  # that variable is not a NameSpaceSet, so it isn't Referable

    def commit(self) -> None:
        """
        Transfer local changes on this object to all underlying external data sources.

        This function commits the current state of this object to its own and each external data source of its
        ancestors. If there is no source, this function will do nothing.
        """
        current_ancestor = self.parent
        relative_path: List[NameType] = [self.id_short]
        # Commit to all ancestors with sources
        while current_ancestor:
            assert isinstance(current_ancestor, Referable)
            if current_ancestor.source != "":
                backends.get_backend(current_ancestor.source).commit_object(committed_object=self,
                                                                            store_object=current_ancestor,
                                                                            relative_path=list(relative_path))
            relative_path.insert(0, current_ancestor.id_short)
            current_ancestor = current_ancestor.parent
        # Commit to own source and check if there are children with sources to commit to
        self._direct_source_commit()

    def _direct_source_commit(self):
        """
        Commits children of an ancestor recursively, if they have a specific source given
        """
        if self.source != "":
            backends.get_backend(self.source).commit_object(committed_object=self,
                                                            store_object=self,
                                                            relative_path=[])

        if isinstance(self, UniqueIdShortNamespace):
            for namespace_set in self.namespace_element_sets:
                if "id_short" not in namespace_set.get_attribute_name_list():
                    continue
                for referable in namespace_set:
                    referable._direct_source_commit()

    id_short = property(_get_id_short, _set_id_short)


_RT = TypeVar('_RT', bound=Referable)


class UnexpectedTypeError(TypeError):
    """
    Exception to be raised by :meth:`.ModelReference.resolve` if the retrieved object has not
    the expected type.

    :ivar value: The object of unexpected type
    """
    def __init__(self, value: Referable, *args):
        super().__init__(*args)
        self.value = value


class Reference(metaclass=abc.ABCMeta):
    """
    Reference to either a model element of the same or another AAs or to an external entity.

    A reference is an ordered list of keys, each key referencing an element. The complete list of keys may for
    example be concatenated to a path that then gives unique access to an element or entity.

    This is the abstract superclass of ExternalReference and ModelReference, which implements common attributes and
    methods used in both reference types. The two reference types are implemented as separate classes in this SDK to
    allow typing and resolving of References with Reference/type=ModelReference.

    <<abstract>>

    **Constraint AASd-121:** For References the value of Key/type of the first key of Reference/keys shall be one of
    GloballyIdentifiables.

    :ivar key: Ordered list of unique reference in its name space, each key referencing an element. The complete
               list of keys may for example be concatenated to a path that then gives unique access to an element
               or entity.
    :ivar referred_semantic_id: SemanticId of the referenced model element. For external references there typically is
                                no semantic id.
    """
    @abc.abstractmethod
    def __init__(self, key: Tuple[Key, ...], referred_semantic_id: Optional["Reference"] = None):
        if len(key) < 1:
            raise ValueError("A reference must have at least one key!")

        # Constraint AASd-121 is enforced by checking AASd-122 for external references and AASd-123 for model references

        self.key: Tuple[Key, ...]
        self.referred_semantic_id: Optional["Reference"]
        super().__setattr__('key', key)
        super().__setattr__('referred_semantic_id', referred_semantic_id)

    def __setattr__(self, key, value):
        """Prevent modification of attributes."""
        raise AttributeError('Reference is immutable')

    def __hash__(self):
        return hash((self.__class__, self.key))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        if len(self.key) != len(other.key):
            return False
        return all(k1 == k2 for k1, k2 in zip(self.key, other.key)) \
            and self.referred_semantic_id == other.referred_semantic_id


class ExternalReference(Reference):
    """
    Reference to either a model element of the same or another AAs or to an external entity.

    A reference is an ordered list of keys, each key referencing an element. The complete list of keys may for
    example be concatenated to a path that then gives unique access to an element or entity.

    **Constraint AASd-122:** For external references, i.e. References with Reference/type = ExternalReference,
    the value of Key/type of the first key of Reference/keys shall be one of GenericGloballyIdentifiables.

    **Constraint AASd-124:** For external references, i.e. References with Reference/type = ExternalReference,
    the last key of Reference/keys shall be either one of GenericGloballyIdentifiables
    or one of GenericFragmentKeys.

    :ivar key: Ordered list of unique reference in its name space, each key referencing an element. The complete
               list of keys may for example be concatenated to a path that then gives unique access to an element
               or entity.
    :ivar referred_semantic_id: SemanticId of the referenced model element. For external references there typically is
                                no semantic id.
    """

    def __init__(self, key: Tuple[Key, ...], referred_semantic_id: Optional["Reference"] = None):
        super().__init__(key, referred_semantic_id)

        if not key[0].type.is_generic_globally_identifiable:
            raise AASConstraintViolation(122, "The type of the first key of an ExternalReference must be a "
                                              f"GenericGloballyIdentifiable: {key[0]!r}")
        if not key[-1].type.is_generic_globally_identifiable and not key[-1].type.is_generic_fragment_key:
            raise AASConstraintViolation(124, "The type of the last key of an ExternalReference must be a "
                                              f"GenericGloballyIdentifiable or a GenericFragmentKey: {key[-1]!r}")

    def __repr__(self) -> str:
        return "ExternalReference(key={})".format(self.key)


class ModelReference(Reference, Generic[_RT]):
    """
    Typed Reference to any referable AAS object.

    This is a special construct of the implementation to allow typed references and de-referencing.

    **Constraint AASd-123:** For model references, i.e. References with Reference/type = ModelReference,
    the value of Key/type of the first key of Reference/keys shall be one of AasIdentifiables.

    **Constraint AASd-125:** For model references, i.e. References with Reference/type = ModelReference with more than
    one key in Reference/keys, the value of Key/type of each of the keys following the first key of Reference/keys
    shall be one of FragmentKeys.

    **Constraint AASd-126:** For model references, i.e. References with Reference/type = ModelReference with more than
    one key in Reference/keys, the value of Key/type of the last Key in the reference key chain may be one of
    GenericFragmentKeys, or no key at all shall have a value out of GenericFragmentKeys.

    **Constraint AASd-127:** For model references, i.e. References with Reference/type = ModelReference with more than
    one key in Reference/keys, a key with Key/type FragmentReference shall be preceded by a key with Key/type
    File or Blob. All other AAS fragments, i.e. Key/type values out of AasSubmodelElements,
    do not support fragments.

    **Constraint AASd-128:** For model references the Key/value of a Key preceded by a Key with
    Key/type=SubmodelElementList is an integer number denoting the position in the array of the
    submodel element list.

    :ivar key: Ordered list of unique :class:`Keys <.Key>` in its name space, each key referencing an element.
               The complete list of keys may for example be concatenated to a path that then gives unique access to an
               element or entity.
    :ivar type: The type of the referenced object (additional parameter, not from the AAS Metamodel)
                  *Initialization parameter:* ``type_``
    :ivar referred_semantic_id: SemanticId of the referenced model element. For external references there typically is
                                no semantic id.
    """
    def __init__(self, key: Tuple[Key, ...], type_: Type[_RT], referred_semantic_id: Optional[Reference] = None):
        super().__init__(key, referred_semantic_id)

        if not key[0].type.is_aas_identifiable:
            raise AASConstraintViolation(123, "The type of the first key of a ModelReference must be an "
                                              f"AasIdentifiable: {key[0]!r}")
        for k in key[1:]:
            if not k.type.is_fragment_key_element:
                raise AASConstraintViolation(125, "The type of all keys following the first of a ModelReference "
                                                  f"must be one of FragmentKeyElements: {k!r}")
        if not key[-1].type.is_generic_fragment_key:
            for k in key[:-1]:
                if k.type.is_generic_fragment_key:
                    raise AASConstraintViolation(126, f"Key {k!r} is a GenericFragmentKey, "
                                                      f"but the last key of the chain is not: {key[-1]!r}")
        for pk, k in zip(key, key[1:]):
            if k.type == KeyTypes.FRAGMENT_REFERENCE and pk.type not in (KeyTypes.BLOB, KeyTypes.FILE):
                raise AASConstraintViolation(127, f"{k!r} is not preceded by a key of type File or Blob, but {pk!r}")
            if pk.type == KeyTypes.SUBMODEL_ELEMENT_LIST and not k.value.isnumeric():
                raise AASConstraintViolation(128, f"Key {pk!r} references a SubmodelElementList, "
                                                  f"but the value of the succeeding key ({k!r}) is not a non-negative "
                                                  f"integer: {k.value}")

        self.type: Type[_RT]
        object.__setattr__(self, 'type', type_)

    def resolve(self, provider_: "provider.AbstractObjectProvider") -> _RT:
        """
        Follow the :class:`~.Reference` and retrieve the :class:`~.Referable` object it points to

        :param provider_: :class:`~basyx.aas.model.provider.AbstractObjectProvider`
        :return: The referenced object (or a proxy object for it)
        :raises IndexError: If the list of keys is empty
        :raises TypeError: If one of the intermediate objects on the path is not a
                           :class:`~.UniqueIdShortNamespace`
        :raises ValueError: If a non-numeric index is given to resolve in a
                            :class:`~basyx.aas.model.submodel.SubmodelElementList`
        :raises UnexpectedTypeError: If the retrieved object is not of the expected type (or one of its subclasses). The
                                     object is stored in the ``value`` attribute of the exception
        :raises KeyError: If the reference could not be resolved
        """

        # For ModelReferences, the first key must be an AasIdentifiable. So resolve the first key via the provider.
        identifier: Optional[Identifier] = self.key[0].get_identifier()
        if identifier is None:
            raise AssertionError(f"Retrieving the identifier of the first {self.key[0]!r} failed.")

        try:
            item: Referable = provider_.get_identifiable(identifier)
        except KeyError as e:
            raise KeyError("Could not resolve identifier {}".format(identifier)) from e

        # All keys following the first must not reference identifiables (AASd-125). Thus, we can just resolve the
        # id_short path via get_referable().
        # This is cursed af, but at least it keeps the code DRY. get_referable() will check the type of self in the
        # first iteration, so we can ignore the type here.
        item = UniqueIdShortNamespace.get_referable(item,  # type: ignore[arg-type]
                                                    map(lambda k: k.value, self.key[1:]))

        # Check type
        if not isinstance(item, self.type):
            raise UnexpectedTypeError(item, "Retrieved object {} is not an instance of referenced type {}"
                                            .format(item, self.type.__name__))
        return item

    def get_identifier(self) -> Identifier:
        """
        Retrieve the :class:`Identifier` of the :class:`~.Identifiable` object, which is referenced or in which the
        referenced :class:`~.Referable` is contained.

        :returns: :class:`Identifier`
        :raises ValueError: If this :class:`~.ModelReference` does not include a Key of AasIdentifiable type
        """
        try:
            last_identifier = next(key.get_identifier()
                                   for key in reversed(self.key)
                                   if key.get_identifier())
            return last_identifier  # type: ignore  # MyPy doesn't get the generator expression above
        except StopIteration:
            raise ValueError("ModelReference cannot be represented as an Identifier, since it does not contain a Key"
                             f" of an AasIdentifiable type ({[t.name for t in KeyTypes if t.is_aas_identifiable]})")

    def __repr__(self) -> str:
        return "ModelReference<{}>(key={})".format(self.type.__name__, self.key)

    @staticmethod
    def from_referable(referable: Referable) -> "ModelReference":
        """
        Construct an :class:`~.ModelReference` to a given :class:`~.Referable` AAS object

        This requires that the :class:`~.Referable` object is :class:`~.Identifiable` itself or is a
        child-, grand-child-, etc. object of an
        :class:`~.Identifiable` object. Additionally, the object must be an instance of a known :class:`~.Referable`
        type.

        :param referable: :class:`~basyx.aas.model.base.Referable` object to construct the :class:`~.ModelReference`
                          from
        :returns: Constructed :class:`~.ModelReference`
        :raises ValueError: If no :class:`~basyx.aas.model.base.Identifiable` object is found while traversing the
                            object's ancestors
        """
        # Get the first class from the base classes list (via inspect.getmro), that is contained in KEY_ELEMENTS_CLASSES
        from . import KEY_TYPES_CLASSES
        try:
            ref_type = next(iter(t for t in inspect.getmro(type(referable)) if t in KEY_TYPES_CLASSES))
        except StopIteration:
            ref_type = Referable

        ref: Referable = referable
        keys: List[Key] = []
        while True:
            keys.append(Key.from_referable(ref))
            if isinstance(ref, Identifiable):
                keys.reverse()
                return ModelReference(tuple(keys), ref_type)
            if ref.parent is None or not isinstance(ref.parent, Referable):
                raise ValueError("The given Referable object is not embedded within an Identifiable object")
            ref = ref.parent


@_string_constraints.constrain_content_type("content_type")
@_string_constraints.constrain_path_type("path")
class Resource:
    """
    Resource represents an address to a file (a locator). The value is a URI that can represent an absolute or relative
    path.

    :ivar path: Path and name of the resource (with file extension). The path can be absolute or relative.
    :ivar content_type: Content type of the content of the file. The content type states which file extensions the file
                        can have.
    """
    def __init__(self, path: PathType, content_type: Optional[ContentType] = None):
        self.path: PathType = path
        self.content_type: Optional[ContentType] = content_type

    def __repr__(self):
        return f"Resource[{self.path}]"


class DataSpecificationContent:
    """
    Data specification content is part of a data specification template and defines
    which additional attributes shall be added to the element instance that references
    the data specification template and meta information about the template itself.

    **Constraint AASc-3a-050:** If the ``Data_specification_IEC_61360`` is used
    for an element, the value of ``HasDataSpecification.embedded_data_specifications``
    shall contain the external reference to the IRI of the corresponding data specification
    template ``https://admin-shell.io/DataSpecificationTemplates/DataSpecificationIEC61360/3/0``
    """
    @abc.abstractmethod
    def __init__(self):
        pass


class EmbeddedDataSpecification:
    """
    Embed the content of a data specification.

    :ivar data_specification: Reference to the data specification
    :ivar data_specification_content: Actual content of the data specification
    """
    def __init__(
        self,
        data_specification: Reference,
        data_specification_content: DataSpecificationContent,
    ) -> None:
        self.data_specification: Reference = data_specification
        self.data_specification_content: DataSpecificationContent = data_specification_content

    def __repr__(self):
        return f"EmbeddedDataSpecification[{self.data_specification}]"


class HasDataSpecification(metaclass=abc.ABCMeta):
    """
    Element that can be extended by using data specification templates.

    A data specification template defines a named set of additional attributes an
    element may or shall have. The data specifications used are explicitly specified
    with their global ID.

    .. warning::
        Please consider, that we do not implement the DataSpecification template class.

    :ivar embedded_data_specifications: List of :class:`~.EmbeddedDataSpecification`.
    """
    @abc.abstractmethod
    def __init__(
        self,
        embedded_data_specifications: Iterable[EmbeddedDataSpecification] = (),
    ) -> None:
        self.embedded_data_specifications = list(embedded_data_specifications)


@_string_constraints.constrain_version_type("version")
@_string_constraints.constrain_identifier("template_id")
class AdministrativeInformation(HasDataSpecification):
    """
    Administrative meta-information for an element like version information.

    **Constraint AASd-005:** If AdministrativeInformation/version is not specified then also
    AdministrativeInformation/revision shall be unspecified. This means, a revision
    requires a version. if there is no version there is no revision neither. Revision is
    optional.

    :ivar version: Version of the element.
    :ivar revision: Revision of the element.
    :ivar creator: The subject ID of the subject responsible for making the element
    :ivar template_id: Identifier of the template that guided the creation of the element
    :ivar embedded_data_specifications: List of Embedded data specification.
     used by the element.

    .. note::
        In case of a submodel, the template ID is the identifier of the submodel template that guided the
        creation of the submodel.

    .. note::
        The submodel template ID is not relevant for validation. Here, the Submodel/semanticId shall be used

    .. note::
        Usage of the template ID is not restricted to submodel instances.
        The creation of submodel templates can also be guided by another submodel template.
    """

    def __init__(self,
                 version: Optional[VersionType] = None,
                 revision: Optional[RevisionType] = None,
                 creator: Optional[Reference] = None,
                 template_id: Optional[Identifier] = None,
                 embedded_data_specifications: Iterable[EmbeddedDataSpecification] = ()):
        """
        Initializer of AdministrativeInformation

        :raises ValueError: If version is None and revision is not None

        TODO: Add instruction what to do after construction
        """
        super().__init__()
        self.version: Optional[VersionType] = version
        self._revision: Optional[RevisionType]
        self.revision = revision
        self.creator: Optional[Reference] = creator
        self.template_id: Optional[Identifier] = template_id
        self.embedded_data_specifications: List[EmbeddedDataSpecification] = list(embedded_data_specifications)

    def _get_revision(self):
        return self._revision

    def _set_revision(self, revision: Optional[RevisionType]):
        if self.version is None and revision:
            raise AASConstraintViolation(5, "A revision requires a version. This means, if there is no version "
                                            "there is no revision neither. Please set version first.")
        if revision is not None:
            _string_constraints.check_revision_type(revision)
        self._revision = revision

    revision = property(_get_revision, _set_revision)

    def __eq__(self, other) -> bool:
        if not isinstance(other, AdministrativeInformation):
            return NotImplemented
        return self.version == other.version \
            and self._revision == other._revision \
            and self.creator == other.creator \
            and self.template_id == other.template_id

    def __repr__(self) -> str:
        return "AdministrativeInformation(version={}, revision={}, creator={}, template_id={})".format(
            self.version, self.revision, self.creator, self.template_id)


@_string_constraints.constrain_identifier("id")
class Identifiable(Referable, metaclass=abc.ABCMeta):
    """
    An element that has a globally unique :class:`Identifier`.

    <<abstract>>

    :ivar administration: :class:`~.AdministrativeInformation` of an identifiable element.
    :ivar id: The globally unique id of the element.
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.administration: Optional[AdministrativeInformation] = None
        # The id attribute is set by all inheriting classes __init__ functions.
        self.id: Identifier

    def __repr__(self) -> str:
        return "{}[{}]".format(self.__class__.__name__, self.id)


_T = TypeVar("_T")


class ConstrainedList(MutableSequence[_T], Generic[_T]):
    """
    A type of list that can be constrained by hooks, useful when implementing AASd constraints. This list can be
    initialized with an ``item_add_hook``, ``item_set_hook`` and an ``item_del_hook``.

    The item_add_hook is called every time an item is added to the list. It is passed the item that is added and
    all items currently contained in the list.

    The ``item_set_hook`` is called every time one or multiple items are overwritten with one or multiple new items,
    à la ``list[i] = new_item`` or ``list[i:j] = new_items``. It is passed the item(s) about to replaced, the new
    item(s) and all items currently contained in the list.
    Note that this can also be used to clear the list, e.g. ``list[:] = []``. Thus, to ensure that a list is never
    empty, ``item_set_hook`` must be used in addition to ``item_del_hook``.

    Finally, ``item_del_hook`` is called whenever an item is removed from the list, (e.g. via ``.remove()``, ``.pop()``
    or ``del list[i]``. It is passed the item about to be deleted and the current list elements.
    """

    def __init__(self, items: Iterable[_T], item_add_hook: Optional[Callable[[_T, List[_T]], None]] = None,
                 item_set_hook: Optional[Callable[[List[_T], List[_T], List[_T]], None]] = None,
                 item_del_hook: Optional[Callable[[_T, List[_T]], None]] = None) -> None:
        super().__init__()
        self._list: List[_T] = []
        self._item_add_hook: Optional[Callable[[_T, List[_T]], None]] = item_add_hook
        self._item_set_hook: Optional[Callable[[List[_T], List[_T], List[_T]], None]] = item_set_hook
        self._item_del_hook: Optional[Callable[[_T, List[_T]], None]] = item_del_hook
        self.extend(items)

    def insert(self, index: int, value: _T) -> None:
        if self._item_add_hook is not None:
            self._item_add_hook(value, self._list)
        self._list.insert(index, value)

    def extend(self, values: Iterable[_T]) -> None:
        v_list = list(values)
        if self._item_add_hook is not None:
            for idx, v in enumerate(v_list):
                self._item_add_hook(v, self._list + v_list[:idx])
        self._list = self._list + v_list

    def clear(self) -> None:
        # clear() repeatedly deletes the last item by default, making it not atomic
        del self[:]

    @overload
    def __getitem__(self, index: int) -> _T: ...

    @overload
    def __getitem__(self, index: slice) -> MutableSequence[_T]: ...

    def __getitem__(self, index: Union[int, slice]) -> Union[_T, MutableSequence[_T]]:
        return self._list[index]

    @overload
    def __setitem__(self, index: int, value: _T) -> None: ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[_T]) -> None: ...

    def __setitem__(self, index: Union[int, slice], value: Union[_T, Iterable[_T]]) -> None:
        # TODO: remove the following type: ignore once mypy supports type narrowing using overload information
        # https://github.com/python/mypy/issues/4063
        if isinstance(index, int):
            if self._item_set_hook is not None:
                self._item_set_hook([self._list[index]], [value], self._list)  # type: ignore
            self._list[index] = value  # type: ignore
            return
        if self._item_set_hook is not None:
            self._item_set_hook(self._list[index], list(value), self._list)  # type: ignore
        self._list[index] = value  # type: ignore

    @overload
    def __delitem__(self, index: int) -> None: ...

    @overload
    def __delitem__(self, index: slice) -> None: ...

    def __delitem__(self, index: Union[int, slice]) -> None:
        if isinstance(index, int):
            if self._item_del_hook is not None:
                self._item_del_hook(self._list[index], self._list)
            del self._list[index]
            return
        if self._item_del_hook is not None:
            indices = range(len(self._list))[index]
            # To avoid partial deletions, perform a dry run first.
            dry_run_list = self._list.copy()
            # Delete high indices first to avoid conflicts by changing indices due to deletion of other objects.
            for i in sorted(indices, reverse=True):
                self._item_del_hook(dry_run_list[i], dry_run_list)
                del dry_run_list[i]
        # If all went well, we can now perform the real deletion.
        del self._list[index]

    def __len__(self) -> int:
        return len(self._list)

    def __repr__(self) -> str:
        return repr(self._list)

    def __eq__(self, other) -> bool:
        return other == self._list


class HasSemantics(metaclass=abc.ABCMeta):
    """
    Element that can have a semantic definition.

    <<abstract>>

    **Constraint AASd-118:** If a supplemental semantic ID (HasSemantics/supplementalSemanticId) is defined,
    there shall also be a main semantic ID (HasSemantics/semanticId).

    :ivar semantic_id: Identifier of the semantic definition of the element. It is called semantic id of the element.
                       The semantic id may either reference an external global id or it may reference a referable model
                       element of kind=Type that defines the semantics of the element.
    :ivar supplemental_semantic_id: Identifier of a supplemental semantic definition of the element. It is called
                                    supplemental semantic ID of the element.
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        # TODO: parent can be any `Namespace`, unfortunately this definition would be incompatible with the definition
        #  of Referable.parent as `UniqueIdShortNamespace`
        self.parent: Optional[Any] = None
        self._supplemental_semantic_id: ConstrainedList[Reference] = ConstrainedList(
            [], item_add_hook=self._check_constraint_add)
        self._semantic_id: Optional[Reference] = None

    def _check_constraint_add(self, _new: Reference, _list: List[Reference]) -> None:
        if self.semantic_id is None:
            raise AASConstraintViolation(118, "A semantic_id must be defined before adding a supplemental_semantic_id!")

    @property
    def semantic_id(self) -> Optional[Reference]:
        return self._semantic_id

    @semantic_id.setter
    def semantic_id(self, semantic_id: Optional[Reference]) -> None:
        if semantic_id is None and len(self.supplemental_semantic_id) > 0:
            raise AASConstraintViolation(118, "semantic_id can not be removed while there is at least one "
                                              f"supplemental_semantic_id: {self.supplemental_semantic_id!r}")
        if self.parent is not None:
            if semantic_id is not None:
                for set_ in self.parent.namespace_element_sets:
                    if set_.contains_id("semantic_id", semantic_id):
                        raise KeyError("Object with semantic_id is already present in the parent Namespace")
            set_add_list: List[NamespaceSet] = []
            for set_ in self.parent.namespace_element_sets:
                if self in set_:
                    set_add_list.append(set_)
                    set_.discard(self)
            self._semantic_id = semantic_id
            for set_ in set_add_list:
                set_.add(self)
        # Redundant to the line above. However, this way, we make sure that we really update the _semantic_id
        self._semantic_id = semantic_id

    @property
    def supplemental_semantic_id(self) -> ConstrainedList[Reference]:
        return self._supplemental_semantic_id

    @supplemental_semantic_id.setter
    def supplemental_semantic_id(self, supplemental_semantic_id: Iterable[Reference]):
        self._supplemental_semantic_id[:] = supplemental_semantic_id


class Extension(HasSemantics):
    """
    Single extension of an element

    :ivar name: An extension of the element.
    :ivar value_type: Type (:class:`DataTypeDefXsd`) of the value of the extension. Default: xsd:string
    :ivar value: Value (:class:`ValueDataType`) of the extension
    :ivar refers_to: An iterable of :class:`~.ModelReference` to elements the extension refers to
    :ivar semantic_id: The semantic_id defined in the :class:`~.HasSemantics` class.
    :ivar supplemental_semantic_id: Identifier of a supplemental semantic definition of the element. It is called
                                    supplemental semantic ID of the element. (inherited from
                                    :class:`~basyx.aas.model.base.HasSemantics`)
    """

    def __init__(self,
                 name: NameType,
                 value_type: Optional[DataTypeDefXsd] = None,
                 value: Optional[ValueDataType] = None,
                 refers_to: Iterable[ModelReference] = (),
                 semantic_id: Optional[Reference] = None,
                 supplemental_semantic_id: Iterable[Reference] = ()):
        super().__init__()
        self.parent: Optional[HasExtension] = None
        self._name: NameType
        self.name: NameType = name
        self.value_type: Optional[DataTypeDefXsd] = value_type
        self._value: Optional[ValueDataType]
        self.value = value
        self.refers_to: Set[ModelReference] = set(refers_to)
        self.semantic_id: Optional[Reference] = semantic_id
        self.supplemental_semantic_id: ConstrainedList[Reference] = ConstrainedList(supplemental_semantic_id)

    def __repr__(self) -> str:
        return "Extension(name={})".format(self.name)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value) -> None:
        if value is None:
            self._value = None
        else:
            if self.value_type is None:
                raise ValueError('ValueType must be set, if value is not None')
            self._value = datatypes.trivial_cast(value, self.value_type)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: NameType) -> None:
        _string_constraints.check_name_type(name)
        if self.parent is not None:
            for set_ in self.parent.namespace_element_sets:
                if set_.contains_id("name", name):
                    raise KeyError("Object with name '{}' is already present in the parent Namespace"
                                   .format(name))
            set_add_list: List[NamespaceSet] = []
            for set_ in self.parent.namespace_element_sets:
                if self in set_:
                    set_add_list.append(set_)
                    set_.discard(self)
            self._name = name
            for set_ in set_add_list:
                set_.add(self)
        # Redundant to the line above. However, this way, we make sure that we really update the _name
        self._name = name


class HasKind(metaclass=abc.ABCMeta):
    """
    An element with a kind is an element that can either represent a type or an instance.
    Default for an element is that it is representing an instance.

    <<abstract>>

    :ivar _kind: Kind of the element: either type or instance. Default = :attr:`~ModellingKind.INSTANCE`.
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self._kind: ModellingKind = ModellingKind.INSTANCE

    @property
    def kind(self):
        return self._kind

    @kind.setter
    def kind(self, value: ModellingKind):
        self._kind = value


class Qualifiable(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold :class:`Qualifier` objects and resolve them by
    their type.

    <<abstract>>

    :ivar namespace_element_sets: A list of all :class:`NamespaceSets <.NamespaceSet>` of this Namespace
    :ivar qualifier: Unordered list of :class:`Qualifiers <Qualifier>` that gives additional qualification of a
                     qualifiable element.
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.namespace_element_sets: List[NamespaceSet] = []
        self.qualifier: NamespaceSet[Qualifier]

    def get_qualifier_by_type(self, qualifier_type: QualifierType) -> "Qualifier":
        """
        Find a :class:`~.Qualifier` in this Namespace by its type

        :raises KeyError: If no such :class:`~.Qualifier` can be found
        """
        return super()._get_object(Qualifier, "type", qualifier_type)

    def add_qualifier(self, qualifier: "Qualifier") -> None:
        """
        Add a :class:`~.Qualifier` to this Namespace

        :param qualifier: The :class:`~.Qualifier` to add
        :raises KeyError: If a qualifier with the same type is already present in this namespace
        :raises ValueError: If the passed object already has a parent namespace
        """
        return super()._add_object("type", qualifier)

    def remove_qualifier_by_type(self, qualifier_type: QualifierType) -> None:
        """
        Remove a :class:`~.Qualifier` from this Namespace by its type

        :raises KeyError: If no such :class:`~.Qualifier` can be found
        """
        return super()._remove_object(Qualifiable, "type", qualifier_type)


class Qualifier(HasSemantics):
    """
    A qualifier is a type-value pair that makes additional statements w.r.t. the value of the element.

    **Constraint AASd-006:** If both, the value and the valueId of a Qualifier are present, the value needs
    to be identical to the value of the referenced coded value in Qualifier/valueId.

    **Constraint AASd-020:** The value of Qualifier/value shall be consistent with the
    data type as defined in Qualifier/valueType.

    :ivar type: The type (:class:`QualifierType`) of the qualifier that is applied to the element.
    :ivar value_type: Data type (:class:`DataTypeDefXsd`) of the qualifier value
    :ivar value: The value (:class:`ValueDataType`) of the qualifier.
    :ivar value_id: :class:`~.Reference` to the global unique id of a coded value.
    :ivar semantic_id: The semantic_id defined in :class:`~.HasSemantics`.
    :ivar supplemental_semantic_id: Identifier of a supplemental semantic definition of the element. It is called
                                    supplemental semantic ID of the element. (inherited from
                                    :class:`~basyx.aas.model.base.HasSemantics`)
    """

    def __init__(self,
                 type_: QualifierType,
                 value_type: DataTypeDefXsd,
                 value: Optional[ValueDataType] = None,
                 value_id: Optional[Reference] = None,
                 kind: QualifierKind = QualifierKind.CONCEPT_QUALIFIER,
                 semantic_id: Optional[Reference] = None,
                 supplemental_semantic_id: Iterable[Reference] = ()):
        """
        TODO: Add instruction what to do after construction
        """
        super().__init__()
        self.parent: Optional[Qualifiable] = None
        self._type: QualifierType
        self.type: QualifierType = type_
        self.value_type: DataTypeDefXsd = value_type
        self._value: Optional[ValueDataType] = datatypes.trivial_cast(value, value_type) if value is not None else None
        self.value_id: Optional[Reference] = value_id
        self.kind: QualifierKind = kind
        self.semantic_id: Optional[Reference] = semantic_id
        self.supplemental_semantic_id: ConstrainedList[Reference] = ConstrainedList(supplemental_semantic_id)

    def __repr__(self) -> str:
        return "Qualifier(type={})".format(self.type)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value) -> None:
        if value is None:
            self._value = None
        else:
            self._value = datatypes.trivial_cast(value, self.value_type)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type_: QualifierType) -> None:
        _string_constraints.check_qualifier_type(type_)
        if self.parent is not None:
            for set_ in self.parent.namespace_element_sets:
                if set_.contains_id("type", type_):
                    raise KeyError("Object with type '{}' is already present in the parent Namespace"
                                   .format(type_))
            set_add_list: List[NamespaceSet] = []
            for set_ in self.parent.namespace_element_sets:
                if self in set_:
                    set_add_list.append(set_)
                    set_.discard(self)
            self._type = type_
            for set_ in set_add_list:
                set_.add(self)
        # Redundant to the line above. However, this way, we make sure that we really update the _type
        self._type = type_


@_string_constraints.constrain_value_type_iec61360("value")
class ValueReferencePair:
    """
    A value reference pair within a value list. Each value has a global unique id defining its semantic.

    <<DataType>>

    :ivar value: The value of the referenced concept definition of the value in value_id
    :ivar value_id: Global unique id of the value.
    """

    def __init__(self,
                 value: ValueTypeIEC61360,
                 value_id: Reference):
        """


        TODO: Add instruction what to do after construction
        """
        self.value_id: Reference = value_id
        self.value: ValueTypeIEC61360 = value

    def __repr__(self) -> str:
        return "ValueReferencePair(value={}, value_id={})".format(self.value, self.value_id)


class UniqueIdShortNamespace(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold :class:`~.Referable` objects and resolve them by
    their id_short.

    A Namespace can contain multiple :class:`NamespaceSets <NamespaceSet>`, which contain :class:`~.Referable` objects
    of different types. However, the id_short of each object must be unique across all NamespaceSets of one Namespace.



    :ivar namespace_element_sets: A list of all :class:`NamespaceSets <.NamespaceSet>` of this Namespace
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.namespace_element_sets: List[NamespaceSet] = []

    def get_referable(self, id_short: Union[NameType, Iterable[NameType]]) -> Referable:
        """
        Find a :class:`~.Referable` in this Namespace by its id_short or by its id_short path.
        The id_short path may contain :class:`~basyx.aas.model.submodel.SubmodelElementList` indices.

        :param id_short: id_short or id_short path as any :class:`Iterable`
        :returns: :class:`~.Referable`
        :raises TypeError: If one of the intermediate objects on the path is not a
                           :class:`~.UniqueIdShortNamespace`
        :raises ValueError: If a non-numeric index is given to resolve in a
                            :class:`~basyx.aas.model.submodel.SubmodelElementList`
        :raises KeyError: If no such :class:`~.Referable` can be found
        """
        from .submodel import SubmodelElementList
        if isinstance(id_short, NameType):
            id_short = [id_short]
        item: Union[UniqueIdShortNamespace, Referable] = self
        for id_ in id_short:
            # This is redundant on first iteration, but it's a negligible overhead.
            # Also, ModelReference.resolve() relies on this check.
            if not isinstance(item, UniqueIdShortNamespace):
                raise TypeError(f"Cannot resolve id_short or index '{id_}' at {item!r}, "
                                f"because it is not a {UniqueIdShortNamespace.__name__}!")
            is_submodel_element_list = isinstance(item, SubmodelElementList)
            try:
                if is_submodel_element_list:
                    # item is known to be a SubmodelElementList which supports __getitem__ because we're in
                    # the `is_submodel_element_list` branch, but mypy doesn't infer types based on isinstance checks
                    # stored in boolean variables.
                    item = item.value[int(id_)]  # type: ignore
                else:
                    item = item._get_object(Referable, "id_short", id_)  # type: ignore[type-abstract]
            except ValueError as e:
                raise ValueError(f"Cannot resolve '{id_}' at {item!r}, because it is not a numeric index!") from e
            except (KeyError, IndexError) as e:
                raise KeyError("Referable with {} {} not found in {}".format(
                    "index" if is_submodel_element_list else "id_short", id_, repr(item))) from e
        # All UniqueIdShortNamespaces are Referables, and we only ever assign Referable to item.
        return item  # type: ignore[return-value]

    def add_referable(self, referable: Referable) -> None:
        """
        Add a :class:`~.Referable` to this Namespace

        :param referable: The :class:`~.Referable` to add
        :raises KeyError: If a :class:`~.Referable` with the same name is already present in this namespace
        :raises ValueError: If the given :class:`~.Referable` already has a parent namespace
        """
        return super()._add_object("id_short", referable)

    def remove_referable(self, id_short: NameType) -> None:
        """
        Remove a :class:`~.Referable` from this Namespace by its ``id_short``

        :param id_short: id_short
        :raises KeyError: If no such :class:`~.Referable` can be found
        """
        return super()._remove_object(Referable, "id_short", id_short)

    def __iter__(self) -> Iterator[Referable]:
        namespace_set_list: List[NamespaceSet] = []
        for namespace_set in self.namespace_element_sets:
            if len(namespace_set) == 0:
                namespace_set_list.append(namespace_set)
                continue
            if "id_short" in namespace_set.get_attribute_name_list():
                namespace_set_list.append(namespace_set)
        return itertools.chain.from_iterable(namespace_set_list)


class UniqueSemanticIdNamespace(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold HasSemantics objects and resolve them by
    their semantic_id.

    A Namespace can contain multiple NamespaceSets, which contain HasSemantics objects of different types. However,
    the semantic_id of each object must be unique across all NamespaceSets of one Namespace.

    :ivar namespace_element_sets: A list of all NamespaceSets of this Namespace
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.namespace_element_sets: List[NamespaceSet] = []

    def get_object_by_semantic_id(self, semantic_id: Reference) -> HasSemantics:
        """
        Find a HasSemantics in these Namespaces by its semantic_id

        :raises KeyError: If no such HasSemantics can be found
        """
        return super()._get_object(HasSemantics, "semantic_id", semantic_id)  # type: ignore

    def remove_object_by_semantic_id(self, semantic_id: Reference) -> None:
        """
        Remove an HasSemantics from this Namespace by its semantic_id

        :raises KeyError: If no such HasSemantics can be found
        """
        return super()._remove_object(HasSemantics, "semantic_id", semantic_id)


ATTRIBUTE_TYPES = Union[NameType, Reference, QualifierType]

# TODO: Find a better solution for providing constraint ids
ATTRIBUTES_CONSTRAINT_IDS = {
    "id_short": 22,  # Referable,
    "type": 21,  # Qualifier,
    "name": 77,  # Extension,
    # "id_short": 134, # model.OperationVariable
}


class NamespaceSet(MutableSet[_NSO], Generic[_NSO]):
    """
    Helper class for storing AAS objects of a given type in a Namespace and find them by their unique attribute.

    This class behaves much like a set of AAS objects of a defined type, but uses dicts internally to rapidly
    find those objects by their unique attribute. Additionally, it manages the ``parent`` attribute of the stored
    AAS objects and ensures the uniqueness of their attribute within the Namespace.

    Use ``add()``, ``remove()``, ``pop()``, ``discard()``, ``clear()``, ``len()``, ``x in`` checks and iteration  just
    like on a normal set of AAS objects. To get an AAS object by its attribute, use ``get_object()`` or ``get()``
    (the latter one allows a default argument and returns None instead of raising a KeyError). As a bonus, the ``x in``
    check supports checking for existence of attribute *or* a concrete AAS object.

    :ivar parent: The Namespace this set belongs to

    To initialize, use the following parameters:

    :param parent: The Namespace this set belongs to
    :param attribute_names: List of attribute names, for which objects should be unique in the set. The bool flag
        indicates if the attribute should be matched case-sensitive (true) or case-insensitive (false)
    :param items: A given list of AAS items to be added to the set

    :raises KeyError: When ``items`` contains multiple objects with same unique attribute
    """
    def __init__(self, parent: Union[UniqueIdShortNamespace, UniqueSemanticIdNamespace, Qualifiable, HasExtension],
                 attribute_names: List[Tuple[str, bool]], items: Iterable[_NSO] = (),
                 item_add_hook: Optional[Callable[[_NSO, Iterable[_NSO]], None]] = None,
                 item_id_set_hook: Optional[Callable[[_NSO], None]] = None,
                 item_id_del_hook: Optional[Callable[[_NSO], None]] = None) -> None:
        """
        Initialize a new NamespaceSet.

        This initializer automatically takes care of adding this set to the ``namespace_element_sets`` list of the
        Namespace.

        :param parent: The Namespace this set belongs to
        :attribute_names: List of attribute names, for which objects should be unique in the set. The bool flag
                          indicates if the attribute should be matched case-sensitive (true) or case-insensitive (false)
        :param items: A given list of AAS items to be added to the set
        :param item_add_hook: A function that is called for each item that is added to this NamespaceSet, even when
                              it is initialized. The first parameter is the item that is added while the second is
                              an iterator over all currently contained items. Useful for constraint checking.
        :param item_id_set_hook: A function called to calculate the identifying attribute (e.g. id_short) of an object
                                 on-the-fly when it is added. Used for the SubmodelElementList implementation.
        :param item_id_del_hook: A function that is called for each item removed from this NamespaceSet. Used in
                                 SubmodelElementList to unset id_shorts on removal. Should not be used for
                                 constraint checking, as the hook is called after removal.
        :raises AASConstraintViolation: When ``items`` contains multiple objects with same unique attribute or when an
                                        item doesn't have an identifying attribute
        """
        self.parent = parent
        parent.namespace_element_sets.append(self)
        self._backend: Dict[str, Tuple[Dict[ATTRIBUTE_TYPES, _NSO], bool]] = {}
        self._item_add_hook: Optional[Callable[[_NSO, Iterable[_NSO]], None]] = item_add_hook
        self._item_id_set_hook: Optional[Callable[[_NSO], None]] = item_id_set_hook
        self._item_id_del_hook: Optional[Callable[[_NSO], None]] = item_id_del_hook
        for name, case_sensitive in attribute_names:
            self._backend[name] = ({}, case_sensitive)
        try:
            for i in items:
                self.add(i)
        except Exception:
            # Do a rollback, when an exception occurs while adding items
            self.clear()
            raise

    @staticmethod
    def _get_attribute(x: object, attr_name: str, case_sensitive: bool):
        attr_value = getattr(x, attr_name)
        return attr_value if case_sensitive or not isinstance(attr_value, str) else attr_value.upper()

    def get_attribute_name_list(self) -> List[str]:
        return list(self._backend.keys())

    def contains_id(self, attribute_name: str, identifier: ATTRIBUTE_TYPES) -> bool:
        try:
            backend, case_sensitive = self._backend[attribute_name]
        except KeyError:
            return False
        # if the identifier is not a string we ignore the case sensitivity
        if case_sensitive or not isinstance(identifier, str):
            return identifier in backend
        return identifier.upper() in backend

    def __contains__(self, obj: object) -> bool:
        attr_name = next(iter(self._backend))
        try:
            attr_value = self._get_attribute(obj, attr_name, self._backend[attr_name][1])
        except AttributeError:
            return False
        return self._backend[attr_name][0].get(attr_value) is obj

    def __len__(self) -> int:
        return len(next(iter(self._backend.values()))[0])

    def __iter__(self) -> Iterator[_NSO]:
        return iter(next(iter(self._backend.values()))[0].values())

    def add(self, element: _NSO):
        if element.parent is not None and element.parent is not self.parent:
            raise ValueError("Object has already a parent; it cannot belong to two namespaces.")
            # TODO remove from current parent instead (allow moving)?

        self._execute_item_id_set_hook(element)
        self._validate_namespace_constraints(element)
        self._execute_item_add_hook(element)

        element.parent = self.parent
        for key_attr_name, (backend, case_sensitive) in self._backend.items():
            backend[self._get_attribute(element, key_attr_name, case_sensitive)] = element

    def _validate_namespace_constraints(self, element: _NSO):
        for set_ in self.parent.namespace_element_sets:
            for key_attr_name, (backend_dict, case_sensitive) in set_._backend.items():
                if hasattr(element, key_attr_name):
                    key_attr_value = self._get_attribute(element, key_attr_name, case_sensitive)
                    self._check_attr_is_not_none(element, key_attr_name, key_attr_value)
                    self._check_value_is_not_in_backend(element, key_attr_name, key_attr_value, backend_dict, set_)

    def _check_attr_is_not_none(self, element: _NSO, attr_name: str, attr):
        if attr is None:
            if attr_name == "id_short":
                raise AASConstraintViolation(117, f"{element!r} has attribute {attr_name}=None, "
                                                  f"which is not allowed within a {self.parent.__class__.__name__}!")
            else:
                raise ValueError(f"{element!r} has attribute {attr_name}=None, which is not allowed!")

    def _check_value_is_not_in_backend(self, element: _NSO, attr_name: str, attr,
                                       backend_dict: Dict[ATTRIBUTE_TYPES, _NSO], set_: "NamespaceSet"):
        if attr in backend_dict:
            if set_ is self:
                text = f"Object with attribute (name='{attr_name}', value='{getattr(element, attr_name)}') " \
                       f"is already present in this set of objects"
            else:
                text = f"Object with attribute (name='{attr_name}', value='{getattr(element, attr_name)}') " \
                       f"is already present in another set in the same namespace"
            raise AASConstraintViolation(ATTRIBUTES_CONSTRAINT_IDS.get(attr_name, 0), text)

    def _execute_item_id_set_hook(self, element: _NSO):
        if self._item_id_set_hook is not None:
            self._item_id_set_hook(element)

    def _execute_item_add_hook(self, element: _NSO):
        if self._item_add_hook is not None:
            try:
                self._item_add_hook(element, self.__iter__())
            except Exception as e:
                self._execute_item_del_hook(element)
                raise

    def _execute_item_del_hook(self, element: _NSO):
        # parent needs to be unset first, otherwise generated id_shorts cannot be unset
        # see SubmodelElementList
        if hasattr(element, "parent"):
            element.parent = None
        if self._item_id_del_hook is not None:
            self._item_id_del_hook(element)

    def remove_by_id(self, attribute_name: str, identifier: ATTRIBUTE_TYPES) -> None:
        item = self.get_object_by_attribute(attribute_name, identifier)
        self.remove(item)

    def remove(self, item: _NSO) -> None:
        item_found = False
        for key_attr_name, (backend_dict, case_sensitive) in self._backend.items():
            key_attr_value = self._get_attribute(item, key_attr_name, case_sensitive)
            if backend_dict[key_attr_value] is item:
                # item has to be removed from backend before _item_del_hook() is called,
                # as the hook may unset the id_short, as in SubmodelElementLists
                del backend_dict[key_attr_value]
                item_found = True
        if not item_found:
            raise KeyError("Object not found in NamespaceDict")
        self._execute_item_del_hook(item)

    def discard(self, x: _NSO) -> None:
        if x not in self:
            return
        self.remove(x)

    def pop(self) -> _NSO:
        _, value = next(iter(self._backend.values()))[0].popitem()
        self._execute_item_del_hook(value)
        value.parent = None
        return value

    def clear(self) -> None:
        for attr_name, (backend, case_sensitive) in self._backend.items():
            for value in backend.values():
                self._execute_item_del_hook(value)
        for attr_name, (backend, case_sensitive) in self._backend.items():
            backend.clear()

    def get_object_by_attribute(self, attribute_name: str, attribute_value: ATTRIBUTE_TYPES) -> _NSO:
        """
        Find an object in this set by its unique attribute

        :raises KeyError: If no such object can be found
        """
        backend, case_sensitive = self._backend[attribute_name]
        return backend[attribute_value if case_sensitive else attribute_value.upper()]  # type: ignore

    def get(self, attribute_name: str, attribute_value: str, default: Optional[_NSO] = None) -> Optional[_NSO]:
        """
        Find an object in this set by its attribute, with fallback parameter

        :param attribute_name: name of the attribute to search for
        :param attribute_value: value of the attribute to search for
        :param default: An object to be returned, if no object with the given attribute is found
        :return: The AAS object with the given attribute in the set. Otherwise, the ``default`` object or None, if
                 none is given.
        """
        backend, case_sensitive = self._backend[attribute_name]
        return backend.get(attribute_value if case_sensitive else attribute_value.upper(), default)

    # Todo: Implement function including tests
    def update_nss_from(self, other: "NamespaceSet"):
        """
        Update a NamespaceSet from a given NamespaceSet.

        WARNING: By updating, the "other" NamespaceSet gets destroyed.

        :param other: The NamespaceSet to update from
        """
        objects_to_add: List[_NSO] = []  # objects from the other nss to add to self
        objects_to_remove: List[_NSO] = []  # objects to remove from self
        for other_object in other:
            try:
                if isinstance(other_object, Referable):
                    backend, case_sensitive = self._backend["id_short"]
                    referable = backend[other_object.id_short if case_sensitive else other_object.id_short.upper()]
                    referable.update_from(other_object, update_source=True)  # type: ignore
                elif isinstance(other_object, Qualifier):
                    backend, case_sensitive = self._backend["type"]
                    qualifier = backend[other_object.type if case_sensitive else other_object.type.upper()]
                    # qualifier.update_from(other_object, update_source=True) # TODO: What should happen here?
                elif isinstance(other_object, Extension):
                    backend, case_sensitive = self._backend["name"]
                    extension = backend[other_object.name if case_sensitive else other_object.name.upper()]
                    # extension.update_from(other_object, update_source=True) # TODO: What should happen here?
                else:
                    raise TypeError("Type not implemented")
            except KeyError:
                # other object is not in NamespaceSet
                objects_to_add.append(other_object)
        for attr_name, (backend, case_sensitive) in self._backend.items():
            for attr_name_other, (backend_other, case_sensitive_other) in other._backend.items():
                if attr_name is attr_name_other:
                    for item in backend.values():
                        if not backend_other.get(self._get_attribute(item, attr_name, case_sensitive)):
                            # referable does not exist in the other NamespaceSet
                            objects_to_remove.append(item)
        for object_to_add in objects_to_add:
            other.remove(object_to_add)
            self.add(object_to_add)  # type: ignore
        for object_to_remove in objects_to_remove:
            self.remove(object_to_remove)  # type: ignore


class OrderedNamespaceSet(NamespaceSet[_NSO], MutableSequence[_NSO], Generic[_NSO]):
    """
    A specialized version of :class:`~.NamespaceSet`, that keeps track of the order of the stored
    :class:`~.Referable` objects.

    Additionally, to the MutableSet interface of :class:`~.NamespaceSet`, this class provides a set-like interface
    (actually it is derived from MutableSequence). However, we don't permit duplicate entries in the ordered list of
    objects.
    """
    def __init__(self, parent: Union[UniqueIdShortNamespace, UniqueSemanticIdNamespace, Qualifiable, HasExtension],
                 attribute_names: List[Tuple[str, bool]], items: Iterable[_NSO] = (),
                 item_add_hook: Optional[Callable[[_NSO, Iterable[_NSO]], None]] = None,
                 item_id_set_hook: Optional[Callable[[_NSO], None]] = None,
                 item_id_del_hook: Optional[Callable[[_NSO], None]] = None) -> None:
        """
        Initialize a new OrderedNamespaceSet.

        This initializer automatically takes care of adding this set to the ``namespace_element_sets`` list of the
        Namespace.

        :param parent: The Namespace this set belongs to
        :attribute_names: Dict of attribute names, for which objects should be unique in the set. The bool flag
                          indicates if the attribute should be matched case-sensitive (true) or case-insensitive (false)
        :param items: A given list of Referable items to be added to the set
        :param item_add_hook: A function that is called for each item that is added to this NamespaceSet, even when
                              it is initialized. The first parameter is the item that is added while the second is
                              an iterator over all currently contained items. Useful for constraint checking.
        :param item_id_set_hook: A function called to calculate the identifying attribute (e.g. id_short) of an object
                                 on-the-fly when it is added. Used for the SubmodelElementList implementation.
        :param item_id_del_hook: A function that is called for each item removed from this NamespaceSet. Used in
                                 SubmodelElementList to unset id_shorts on removal. Should not be used for
                                 constraint checking, as the hook is called after removal.
        :raises AASConstraintViolation: When ``items`` contains multiple objects with same unique attribute or when an
                                        item doesn't have an identifying attribute
        """
        self._order: List[_NSO] = []
        super().__init__(parent, attribute_names, items, item_add_hook, item_id_set_hook, item_id_del_hook)

    def __iter__(self) -> Iterator[_NSO]:
        return iter(self._order)

    def add(self, element: _NSO):
        super().add(element)
        self._order.append(element)

    def remove(self, item: Union[Tuple[str, ATTRIBUTE_TYPES], _NSO]):
        if isinstance(item, tuple):
            item = self.get_object_by_attribute(item[0], item[1])
        super().remove(item)
        self._order.remove(item)

    def pop(self, i: Optional[int] = None) -> _NSO:
        if i is None:
            value = super().pop()
            self._order.remove(value)
        else:
            value = self._order.pop(i)
            super().remove(value)
        return value

    def clear(self) -> None:
        super().clear()
        self._order.clear()

    def insert(self, index: int, object_: _NSO) -> None:
        super().add(object_)
        self._order.insert(index, object_)

    @overload
    def __getitem__(self, i: int) -> _NSO: ...

    @overload
    def __getitem__(self, s: slice) -> MutableSequence[_NSO]: ...

    def __getitem__(self, s: Union[int, slice]) -> Union[_NSO, MutableSequence[_NSO]]:
        return self._order[s]

    @overload
    def __setitem__(self, i: int, o: _NSO) -> None: ...

    @overload
    def __setitem__(self, s: slice, o: Iterable[_NSO]) -> None: ...

    def __setitem__(self, s, o) -> None:
        if isinstance(s, int):
            deleted_items = [self._order[s]]
            super().add(o)
            self._order[s] = o
        else:
            deleted_items = self._order[s]
            new_items = itertools.islice(o, len(deleted_items))
            successful_new_items = []
            try:
                for i in new_items:
                    super().add(i)
                    successful_new_items.append(i)
            except Exception:
                # Do a rollback, when an exception occurs while adding items
                for i in successful_new_items:
                    super().remove(i)
                raise
            self._order[s] = new_items
        for i in deleted_items:
            super().remove(i)

    @overload
    def __delitem__(self, i: int) -> None: ...

    @overload
    def __delitem__(self, i: slice) -> None: ...

    def __delitem__(self, i: Union[int, slice]) -> None:
        if isinstance(i, int):
            i = slice(i, i+1)
        for o in self._order[i]:
            super().remove(o)
        del self._order[i]


class SpecificAssetId(HasSemantics):
    """
    A specific asset ID describes a generic supplementary identifying attribute of the asset.
    The specific asset ID is not necessarily globally unique.

    **Constraint AASd-133:** SpecificAssetId/externalSubjectId shall be a global reference,
    i.e. Reference/type = ExternalReference

    :ivar name: Key of the identifier
    :ivar value: The value of the identifier with the corresponding key.
    :ivar external_subject_id: The (external) subject the key belongs to or has meaning to.
    :ivar semantic_id: Identifier of the semantic definition of the element. It is called semantic id of the
                       element. The semantic id may either reference an external global id or it may reference a
                       referable model element of kind=Type that defines the semantics of the element.
                       (inherited from :class:`~basyx.aas.model.base.HasSemantics`)
    :ivar supplemental_semantic_id: Identifier of a supplemental semantic definition of the element. It is called
                                    supplemental semantic ID of the element. (inherited from
                                    :class:`~basyx.aas.model.base.HasSemantics`)
    """

    def __init__(self,
                 name: LabelType,
                 value: Identifier,
                 external_subject_id: Optional[ExternalReference] = None,
                 semantic_id: Optional[Reference] = None,
                 supplemental_semantic_id: Iterable[Reference] = ()):
        super().__init__()
        if value == "":
            raise ValueError("value is not allowed to be an empty string")
        _string_constraints.check_label_type(name)
        _string_constraints.check_identifier(value)
        self.name: LabelType
        self.value: Identifier
        self.external_subject_id: ExternalReference

        super().__setattr__('name', name)
        super().__setattr__('value', value)
        super().__setattr__('external_subject_id', external_subject_id)
        super().__setattr__('semantic_id', semantic_id)
        super().__setattr__('supplemental_semantic_id', supplemental_semantic_id)

    def __setattr__(self, key, value):
        """Prevent modification of attributes."""
        # Hack to make the HasSemantics inheritance work
        # HasSemantics.__init__ sets the parent attribute to None, so that has to be possible. It needs to be set
        # because its value is checked in the semantic_id setter and since every subclass of HasSemantics is expected
        # to have this attribute. Additionally, the protected _semantic_id attribute must be settable.
        if key == '_semantic_id' or key == '_supplemental_semantic_id' or (key == 'parent' and value is None):
            return super(HasSemantics, self).__setattr__(key, value)
        raise AttributeError('SpecificAssetId is immutable')

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SpecificAssetId):
            return NotImplemented
        return (self.name == other.name
                and self.value == other.value
                and self.external_subject_id == other.external_subject_id
                and self.semantic_id == other.semantic_id
                and self.supplemental_semantic_id == other.supplemental_semantic_id)

    def __hash__(self):
        return hash((self.name, self.value, self.external_subject_id))

    def __repr__(self) -> str:
        return "SpecificAssetId(key={}, value={}, external_subject_id={}, " \
                "semantic_id={}, supplemental_semantic_id={})".format(
                    self.name, self.value, self.external_subject_id, self.semantic_id,
                    self.supplemental_semantic_id)


class AASConstraintViolation(Exception):
    """
    An Exception to be raised if an AASd-Constraint defined in the metamodel (Details of the Asset Administration Shell)
    is violated

    :ivar constraint_id: The ID of the constraint that is violated
    :ivar message: The error message of the Exception
    """
    def __init__(self, constraint_id: int, message: str):
        self.constraint_id: int = constraint_id
        self.message: str = message + " (Constraint AASd-" + str(constraint_id).zfill(3) + ")"
        super().__init__(self.message)


@unique
class DataTypeIEC61360(Enum):
    """
    Data types for data_type in :class:`DataSpecificationIEC61360`
    The data types are:

    :cvar DATE:
    :cvar STRING:
    :cvar STRING_TRANSLATABLE:
    :cvar INTEGER_MEASURE:
    :cvar INTEGER_COUNT:
    :cvar INTEGER_CURRENCY:
    :cvar REAL_MEASURE:
    :cvar REAL_COUNT:
    :cvar REAL_CURRENCY:
    :cvar BOOLEAN:
    :cvar IRI:
    :cvar IRDI:
    :cvar RATIONAL:
    :cvar RATIONAL_MEASURE:
    :cvar TIME:
    :cvar TIMESTAMP:
    :cvar HTML:
    :cvar BLOB:
    :cvar FILE:
    """
    DATE = 0
    STRING = 1
    STRING_TRANSLATABLE = 2
    INTEGER_MEASURE = 3
    INTEGER_COUNT = 4
    INTEGER_CURRENCY = 5
    REAL_MEASURE = 6
    REAL_COUNT = 7
    REAL_CURRENCY = 8
    BOOLEAN = 9
    IRI = 10
    IRDI = 11
    RATIONAL = 12
    RATIONAL_MEASURE = 13
    TIME = 14
    TIMESTAMP = 15
    HTML = 16
    BLOB = 17
    FILE = 18


@unique
class IEC61360LevelType(Enum):
    """
    Level types for the level_type in :class:`DataSpecificationIEC61360`
    The level types are:

    :cvar MIN:
    :cvar MAX:
    :cvar NOM:
    :cvar TYP:
    """
    MIN = 0
    MAX = 1
    NOM = 2
    TYP = 3


@_string_constraints.constrain_value_type_iec61360("value")
class DataSpecificationIEC61360(DataSpecificationContent):
    """
    A specialized :class:`~.DataSpecificationContent` to define specs according to IEC61360

    :ivar preferred_name: Preferred name of the data object
    :ivar short_name: Short name of the data object
    :ivar data_type: Data type of the data object
    :ivar definition: Definition of the data object
    :ivar parent: Reference to the next referable parent element of the element.
                  (inherited from :class:`~basyx.aas.model.base.Referable`)
    :ivar unit: Optional unit of the data object
    :ivar unit_id: Optional reference to a unit id
    :ivar source_of_definition: Optional source of the definition
    :ivar symbol: Optional unit symbol
    :ivar value_format: Optional format of the values
    :ivar value_list: Optional list of values
    :ivar value: Optional value data type object
    :ivar level_types: Optional set of level types of the DataSpecificationContent
    """
    def __init__(self,
                 preferred_name: PreferredNameTypeIEC61360,
                 data_type: Optional[DataTypeIEC61360] = None,
                 definition: Optional[DefinitionTypeIEC61360] = None,
                 short_name: Optional[ShortNameTypeIEC61360] = None,
                 unit: Optional[str] = None,
                 unit_id: Optional[Reference] = None,
                 source_of_definition: Optional[str] = None,
                 symbol: Optional[str] = None,
                 value_format: Optional[str] = None,
                 value_list: Optional[ValueList] = None,
                 value: Optional[ValueTypeIEC61360] = None,
                 level_types: Iterable[IEC61360LevelType] = ()):

        self.preferred_name: PreferredNameTypeIEC61360 = preferred_name
        self.short_name: Optional[ShortNameTypeIEC61360] = short_name
        self.data_type: Optional[DataTypeIEC61360] = data_type
        self.definition: Optional[DefinitionTypeIEC61360] = definition
        self._unit: Optional[str] = unit
        self.unit_id: Optional[Reference] = unit_id
        self._source_of_definition: Optional[str] = source_of_definition
        self._symbol: Optional[str] = symbol
        self.value_list: Optional[ValueList] = value_list
        self.level_types: Set[IEC61360LevelType] = set(level_types)
        self.value_format: Optional[str] = value_format
        self.value: Optional[ValueTypeIEC61360] = value

    def _set_unit(self, unit: Optional[str]):
        """
        Check the input string

        :param unit: unit of the data object (optional)
        :raises ValueError: if the constraint is not fulfilled
        """
        self._unit = unit

    def _get_unit(self):
        return self._unit

    unit = property(_get_unit, _set_unit)

    def _set_source_of_definition(self, source_of_definition: Optional[str]):
        """
        Check the input string

        :param source_of_definition: source of the definition (optional)
        :raises ValueError: if the constraint is not fulfilled
        """
        self._source_of_definition = source_of_definition

    def _get_source_of_definition(self):
        return self._source_of_definition

    source_of_definition = property(_get_source_of_definition, _set_source_of_definition)

    def _set_symbol(self, symbol: Optional[str]):
        """
        Check the input string

        :param symbol: unit symbol (optional)
        :raises ValueError: if the constraint is not fulfilled
        """
        self._symbol = symbol

    def _get_symbol(self):
        return self._symbol

    symbol = property(_get_symbol, _set_symbol)

    def __repr__(self):
        return f"DataSpecificationIEC61360[unit={self.unit}]"
