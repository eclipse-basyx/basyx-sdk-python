# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module contains the class :class:`~.ConceptDescription` from the AAS metamodel.
"""
from typing import Optional, Set, Iterable, List

from . import base

ALLOWED_CONCEPT_DESCRIPTION_CATEGORIES: Set[str] = {
    "VALUE",
    "PROPERTY",
    "REFERENCE",
    "DOCUMENT",
    "CAPABILITY",
    "RELATIONSHIP",
    "COLLECTION",
    "FUNCTION",
    "EVENT",
    "ENTITY",
    "APPLICATION_CLASS",
    "QUALIFIER"
}


class ConceptDescription(base.Identifiable, base.HasDataSpecification):
    """
    The semantics of a :class:`~.Property` or other elements that may have a semantic description is defined by a
    concept description.

    The description of the concept should follow a standardized schema (realized as data specification template).

    .. note::
        Compare ``is_case_of`` to is-case-of relationship in ISO 13584-32 & IEC EN 61360

    :ivar id: The globally unique id of the element. (inherited from :class:`~basyx.aas.model.base.Identifiable`)
    :ivar is_case_of: Unordered list of global :class:`References <basyx.aas.model.base.Reference>` to external
                      definitions the concept is compatible to or was derived from.
    :ivar id_short: Identifying string of the element within its name space. (inherited from
                    :class:`~basyx.aas.model.base.Referable`)
    :ivar display_name: Can be provided in several languages. (inherited from :class:`~basyx.aas.model.base.Referable`)
    :ivar category: The category is a value that gives further meta information w.r.t. to the class of the element.
                    It affects the expected existence of attributes and the applicability of constraints.
                    (inherited from :class:`~basyx.aas.model.base.Referable`)
    :ivar description: Description or comments on the element. (inherited from :class:`~basyx.aas.model.base.Referable`)
    :ivar parent: Reference to the next referable parent element of the element. (inherited from
                  :class:`~basyx.aas.model.base.Referable`)
    :ivar administration: Administrative information of an identifiable element. (inherited from
                          :class:`~basyx.aas.model.base.Identifiable`)
    :ivar embedded_data_specifications: List of Embedded data specification.
    :ivar extension: An extension of the element. (from
                     :class:`~basyx.aas.model.base.HasExtension`)
"""

    def __init__(self,
                 id_: base.Identifier,
                 is_case_of: Optional[Set[base.Reference]] = None,
                 id_short: Optional[base.NameType] = None,
                 display_name: Optional[base.MultiLanguageNameType] = None,
                 category: Optional[base.NameType] = None,
                 description: Optional[base.MultiLanguageTextType] = None,
                 parent: Optional[base.UniqueIdShortNamespace] = None,
                 administration: Optional[base.AdministrativeInformation] = None,
                 embedded_data_specifications: Iterable[base.EmbeddedDataSpecification]
                 = (),
                 extension: Iterable[base.Extension] = ()):

        super().__init__()
        self.id: base.Identifier = id_
        self.is_case_of: Set[base.Reference] = set() if is_case_of is None else is_case_of
        self.id_short = id_short
        self.display_name: Optional[base.MultiLanguageNameType] = display_name
        self.category = category
        self.description: Optional[base.MultiLanguageTextType] = description
        self.parent: Optional[base.UniqueIdShortNamespace] = parent
        self.administration: Optional[base.AdministrativeInformation] = administration
        self.embedded_data_specifications: List[base.EmbeddedDataSpecification] = list(embedded_data_specifications)
        self.extension = base.NamespaceSet(self, [("name", True)], extension)

    def _set_category(self, category: Optional[str]):
        if category is None:
            self._category = "PROPERTY"
        else:
            if category not in ALLOWED_CONCEPT_DESCRIPTION_CATEGORIES:
                raise base.AASConstraintViolation(
                    51,
                    "ConceptDescription must have one of the following "
                    "categories: " + str(ALLOWED_CONCEPT_DESCRIPTION_CATEGORIES)
                )
            self._category = category
