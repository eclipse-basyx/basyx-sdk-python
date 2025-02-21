# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module provides a registry and abstract base class for Backends. A :class:`~.Backend` is a class that allows to
synchronize Referable AAS objects or their included data with external data sources such as a remote API or a local
source for real time data. Each backend provides access to one kind of data source.

The data source of an individual object is specified as a URI in its ``source`` attribute. The schema part of that URI
defines the type of data source and, in consequence, the backend class to use for synchronizing this object.

Custom backends for additional types of data sources can be implemented by subclassing :class:`Backend` and
implementing the :meth:`~.Backend.commit_object` and :meth:`~.Backend.update_object` class methods. These are used
internally by the objects' :meth:`~basyx.aas.model.base.Referable.update` and
:meth:`~basyx.aas.model.base.Referable.commit` methods when the backend is applicable for the relevant source URI.
Then, the Backend class needs to be registered to handle update/commit requests for a specific URI schema, using
:meth:`~basyx.aas.backend.backends.register_backend`.
"""
import abc
import re
from typing import List, Dict, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from ..model import Referable


class Backend(metaclass=abc.ABCMeta):
    """
    Abstract base class for all Backend classes.

    Each Backend class is typically capable of synchronizing (updating/committing) objects with a type of external data
    source, identified by one or more source URI schemas. Custom backends for custom source URI schemas should inherit
    from this class and be registered via :meth:`~basyx.aas.backend.backends.register_backend`. to be used by Referable
    object's :meth:`~basyx.aas.model.base.Referable.update` and :meth:`~basyx.aas.model.base.Referable.commit` methods
    when required.
    """

    @classmethod
    @abc.abstractmethod
    def commit_object(cls,
                      committed_object: "Referable",
                      store_object: "Referable",
                      relative_path: List[str]) -> None:
        """
        Function (class method) to be called when an object shall be committed (local changes pushed to the external
        data source) via this backend implementation.

        It is automatically called by the :meth:`~basyx.aas.model.base.Referable.commit` implementation, when the source
        URI of the object or the source URI one of its ancestors in the AAS object containment hierarchy include a
        URI schema for which this
        backend has been registered. Both of the objects are passed to this function: the one which shall be committed
        (``committed_object``) and its ancestor with the relevant source URI (``store_object``). They may be the same,
        the committed object has a source with the relevant schema itself. Additionally, the ``relative_path`` from the
        ``store_object`` down to the ``committed_object`` is provided.

        The backend MUST ensure to commit all local changes of at least the ``committed_object`` and all objects
        contained within it (if any) to the data source. It MAY additionally commit changes to other objects (i.e. the
        ``store_object`` and any additional contained object).

        For this purpose a concrete implementation of this method would typically use the ``source`` attribute of the
        ``store_object`` to identify the data source. If the data source supports fine-grained access to contained
        objects, the ``relative_path`` may become handy to compose the committed object's address within the data
        source's interface.

        :param committed_object: The object which shall be synced to the external data source
        :param store_object: The object which originates from the relevant data source (i.e. has the relevant source
            attribute). It may be the ``committed_object`` or one of its ancestors in the AAS object hierarchy.
        :param relative_path: List of idShort strings to resolve the ``committed_object`` starting at the
            ``store_object``, such that `obj = store_object; for i in relative_path: obj = obj.get_referable(i)`
            resolves to the ``committed_object``. In case that ``store_object is committed_object``, it is an empty
            list.
        :raises BackendNotAvailableException: when the external data source cannot be reached
        """
        pass

    @classmethod
    @abc.abstractmethod
    def update_object(cls,
                      updated_object: "Referable",
                      store_object: "Referable",
                      relative_path: List[str]) -> None:
        """
        Function (class method) to be called when an object shall be updated (local object updated with changes from the
        external data source) via this backend implementation.

        It is automatically called by the :meth:`~basyx.aas.model.base.Referable.update` implementation,
        when the source URI of the object or the source URI one of its ancestors in the AAS object containment hierarchy
        include a URI schema for which this backend has been registered. Both of the objects are passed
        to this function: the one which shall be update (``updated_object``) and its ancestor with
        the relevant source URI (``store_object``). They may be the same, the updated object has a source with
        the relevant schema itself. Additionally, the ``relative_path`` from the ``store_object`` down to
        the ``updated_object`` is provided.

        The backend MUST ensure to update at least the ``updated_object`` and all objects contained within it (if any)
        with any changes from the data source. It MAY additionally update other objects (i.e. the ``store_object`` and
        any additional contained object).

        For this purpose a concrete implementation of this method would typically use the ``source`` attribute of the
        ``store_object`` to identify the data source. If the data source supports fine-grained access to contained
        objects, the ``relative_path`` may become handy to compose the updated object's address within the data source's
        interface.

        :param updated_object: The object which shall be synced from the external data source
        :param store_object: The object which originates from the relevant data source (i.e. has the relevant source
            attribute). It may be the ``committed_object`` or one of its ancestors in the AAS object hierarchy.
        :param relative_path: List of idShort strings to resolve the ``updated_object`` starting at the
            ``store_object``, such that `obj = store_object; for i in relative_path: obj = obj.get_referable(i)`
            resolves to the ``updated_object``. In case that ``store_object is updated_object``, it is an empty list.
        :raises BackendNotAvailableException: when the external data source cannot be reached
        """
        pass


# Global registry for backends by URI scheme
# TODO allow multiple backends per scheme with priority
_backends_map: Dict[str, Type[Backend]] = {}


def register_backend(scheme: str, backend_class: Type[Backend]) -> None:
    """
    Register a Backend implementation to handle update/commit operations for a specific type of external data sources,
    identified by a source URI schema.

    This method may be called multiple times for a single Backend class, to register that class as a backend
    implementation for different source URI schemas (e.g. use the same backend for 'http://' and 'https://' sources).

    :param scheme: The URI schema of source URIs to be handled with Backend class, without trailing colon and slashes.
        E.g. 'http', 'https', 'couchdb', etc.
    :param backend_class: The Backend implementation class. Should inherit from :class:`Backend`.
    """
    # TODO handle multiple backends per scheme
    _backends_map[scheme] = backend_class


RE_URI_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z+\-\.]*):")


def get_backend(url: str) -> Type[Backend]:
    """
    Internal function to retrieve the Backend implementation for the external data source identified by the given
    ``url`` via the url's schema.

    :param url: External data source URI to find an appropriate Backend implementation for
    :return: A Backend class, capable of updating/committing from/to the external data source
    :raises UnknownBackendException: When no backend is available for that url
    """
    # TODO handle multiple backends per scheme
    scheme_match = RE_URI_SCHEME.match(url)
    if not scheme_match:
        raise ValueError("{} is not a valid URL with URI scheme.".format(url))
    scheme = scheme_match[1]
    try:
        return _backends_map[scheme]
    except KeyError as e:
        raise UnknownBackendException("Could not find Backend for source '{}'".format(url)) from e


# #################################################################################################
# Custom Exception classes for reporting errors during interaction with Backends
class BackendError(Exception):
    """Base class of all exceptions raised by the backends module"""
    pass


class UnknownBackendException(BackendError):
    """Raised, if the backend is not found in the registry"""
    pass


class BackendNotAvailableException(BackendError):
    """Raised, if the backend does exist in the registry, but is not available for some reason"""
    pass
