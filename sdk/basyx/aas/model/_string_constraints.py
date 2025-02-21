# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module implements constraint functions for the listed constrained string types.
All types are constrained in length (min and max), RevisionType and VersionType are additionally constrained
by a regular expression.

.. warning::
    This module is intended for internal use only.

The following types aliased in the :mod:`~basyx.aas.model.base` module are constrained:

- :class:`~basyx.aas.model.base.ContentType`
- :class:`~basyx.aas.model.base.Identifier`
- :class:`~basyx.aas.model.base.LabelType`
- :class:`~basyx.aas.model.base.MessageTopicType`
- :class:`~basyx.aas.model.base.NameType`
- :class:`~basyx.aas.model.base.PathType`
- :class:`~basyx.aas.model.base.RevisionType`
- :class:`~basyx.aas.model.base.ShortNameType`
- :class:`~basyx.aas.model.base.QualifierType`
- :class:`~basyx.aas.model.base.VersionType`
- :class:`~basyx.aas.model.base.ValueTypeIEC61360`
"""

import re

from typing import Callable, Optional, Type, TypeVar


_T = TypeVar("_T")
AASD130_RE = re.compile("[\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]*")


def _unicode_escape(value: str) -> str:
    """
    Escapes unicode characters such as \uD7FF, that may be used in regular expressions, for better error messages.
    """
    return value.encode("unicode_escape").decode("utf-8")


# Functions to verify the constraints for a given value.
def check(value: str, type_name: str, min_length: int = 0, max_length: Optional[int] = None,
          pattern: Optional[re.Pattern] = None) -> None:
    if len(value) < min_length:
        raise ValueError(f"{type_name} has a minimum length of {min_length}! (length: {len(value)})")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"{type_name} has a maximum length of {max_length}! (length: {len(value)})")
    if pattern is not None and not pattern.fullmatch(value):
        raise ValueError(f"{type_name} must match the pattern '{_unicode_escape(pattern.pattern)}'! "
                         f"(value: '{_unicode_escape(value)}')")
    # Constraint AASd-130: an attribute with data type "string" shall consist of these characters only:
    if not AASD130_RE.fullmatch(value):
        # It's easier to implement this as a ValueError, because otherwise AASConstraintViolation would need to be
        # imported from `base` and the ConstrainedLangStringSet would need to except AASConstraintViolation errors
        # as well, while only re-raising ValueErrors. Thus, even if an AASConstraintViolation would be raised here,
        # in case of a ConstrainedLangStringSet it would be re-raised as a ValueError anyway.
        raise ValueError(f"Every string must match the pattern '{_unicode_escape(AASD130_RE.pattern)}'! "
                         f"(value: '{_unicode_escape(value)}')")


def check_content_type(value: str, type_name: str = "ContentType") -> None:
    return check(value, type_name, 1, 100)


def check_identifier(value: str, type_name: str = "Identifier") -> None:
    return check(value, type_name, 1, 2000)


def check_label_type(value: str, type_name: str = "LabelType") -> None:
    return check(value, type_name, 1, 64)


def check_message_topic_type(value: str, type_name: str = "MessageTopicType") -> None:
    return check(value, type_name, 1, 255)


def check_name_type(value: str, type_name: str = "NameType") -> None:
    return check(value, type_name, 1, 128)


def check_path_type(value: str, type_name: str = "PathType") -> None:
    return check(value, type_name, 1, 2000)


def check_qualifier_type(value: str, type_name: str = "QualifierType") -> None:
    return check_name_type(value, type_name)


def check_revision_type(value: str, type_name: str = "RevisionType") -> None:
    return check(value, type_name, 1, 4, re.compile(r"([0-9]|[1-9][0-9]*)"))


def check_short_name_type(value: str, type_name: str = "ShortNameType") -> None:
    return check(value, type_name, 1, 64)


def check_value_type_iec61360(value: str, type_name: str = "ValueTypeIEC61360") -> None:
    return check(value, type_name, 1, 2000)


def check_version_type(value: str, type_name: str = "VersionType") -> None:
    return check(value, type_name, 1, 4, re.compile(r"([0-9]|[1-9][0-9]*)"))


def create_check_function(min_length: int = 0, max_length: Optional[int] = None, pattern: Optional[re.Pattern] = None) \
        -> Callable[[str, str], None]:
    """
    Returns a new ``check_type`` function with mandatory ``type_name`` for the given min_length, max_length and pattern
    constraints.

    This is the type-independent alternative to :func:`~.check_content_type`, :func:`~.check_identifier`, etc. It is
    used for the definition of the :class:`ConstrainedLangStringSets <basyx.aas.model.base.ConstrainedLangStringSet>`,
    as a "Basic" constrained string type only exists for :class:`~basyx.aas.model.base.MultiLanguageNameType`, where all
    values are :class:`ShortNames <basyx.aas.model.base.ShortNameType>`. All other
    :class:`:class:`ConstrainedLangStringSets <basyx.aas.model.base.ConstrainedLangStringSet>` use custom constraints.
    """
    def check_fn(value: str, type_name: str) -> None:
        return check(value, type_name, min_length, max_length, pattern)
    return check_fn


# Decorator functions to add getter/setter to classes for verification, whenever a value is updated.
def constrain_attr(pub_attr_name: str, constraint_check_fn: Callable[[str], None]) \
        -> Callable[[Type[_T]], Type[_T]]:
    def decorator_fn(decorated_class: Type[_T]) -> Type[_T]:
        def _getter(self) -> Optional[str]:
            return getattr(self, "_" + pub_attr_name)

        def _setter(self, value: Optional[str]) -> None:
            # if value is None, skip checks. incorrect 'None' assignments are caught by the type checker anyway
            if value is not None:
                constraint_check_fn(value)
            setattr(self, "_" + pub_attr_name, value)

        if hasattr(decorated_class, pub_attr_name):
            raise AttributeError(f"{decorated_class.__name__} already has an attribute named '{pub_attr_name}'")
        setattr(decorated_class, pub_attr_name, property(_getter, _setter))
        return decorated_class

    return decorator_fn


def constrain_content_type(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_content_type)


def constrain_identifier(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_identifier)


def constrain_label_type(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_label_type)


def constrain_message_topic_type(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_message_topic_type)


def constrain_name_type(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_name_type)


def constrain_path_type(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_path_type)


def constrain_qualifier_type(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_qualifier_type)


def constrain_revision_type(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_revision_type)


def constrain_short_name_type(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_short_name_type)


def constrain_version_type(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_version_type)


def constrain_value_type_iec61360(pub_attr_name: str) -> Callable[[Type[_T]], Type[_T]]:
    return constrain_attr(pub_attr_name, check_value_type_iec61360)
