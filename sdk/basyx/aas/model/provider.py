# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module implements Registries for the AAS, in order to enable resolving global
:class:`Identifiers <basyx.aas.model.base.Identifier>`; and mapping
:class:`Identifiers <basyx.aas.model.base.Identifier>` to :class:`~basyx.aas.model.base.Identifiable` objects.
"""

import abc
from typing import MutableSet, Iterator, Generic, TypeVar, Dict, List, Optional, Iterable, Set

from .base import Identifier, Identifiable


class AbstractObjectProvider(metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects, that allow to retrieve :class:`~basyx.aas.model.base.Identifiable` objects
    (resp. proxy objects for remote :class:`~basyx.aas.model.base.Identifiable` objects) by their
    :class:`~basyx.aas.model.base.Identifier`.

    This includes local object stores, database clients and AAS API clients.
    """
    @abc.abstractmethod
    def get_identifiable(self, identifier: Identifier) -> Identifiable:
        """
        Find an :class:`~basyx.aas.model.base.Identifiable` by its :class:`~basyx.aas.model.base.Identifier`

        This may include looking up the object's endpoint in a registry and fetching it from an HTTP server or a
        database.

        :param identifier: :class:`~basyx.aas.model.base.Identifier` of the object to return
        :return: The :class:`~basyx.aas.model.base.Identifiable` object (or a proxy object for a remote
                 :class:`~basyx.aas.model.base.Identifiable` object)
        :raises KeyError: If no such :class:`~.basyx.aas.model.base.Identifiable` can be found
        """
        pass

    def get(self, identifier: Identifier, default: Optional[Identifiable] = None) -> Optional[Identifiable]:
        """
        Find an object in this set by its :class:`id <basyx.aas.model.base.Identifier>`, with fallback parameter

        :param identifier: :class:`~basyx.aas.model.base.Identifier` of the object to return
        :param default: An object to be returned, if no object with the given
                        :class:`id <basyx.aas.model.base.Identifier>` is found
        :return: The :class:`~basyx.aas.model.base.Identifiable` object with the given
                 :class:`id <basyx.aas.model.base.Identifier>` in the provider. Otherwise, the ``default`` object
                 or None, if none is given.
        """
        try:
            return self.get_identifiable(identifier)
        except KeyError:
            return default


_IT = TypeVar('_IT', bound=Identifiable)


class AbstractObjectStore(AbstractObjectProvider, MutableSet[_IT], Generic[_IT], metaclass=abc.ABCMeta):
    """
    Abstract baseclass of for container-like objects for storage of :class:`~basyx.aas.model.base.Identifiable` objects.

    ObjectStores are special ObjectProvides that – in addition to retrieving objects by
    :class:`~basyx.aas.model.base.Identifier` – allow to add and delete objects (i.e. behave like a Python set).
    This includes local object stores (like :class:`~.DictObjectStore`) and database
    :class:`Backends <basyx.aas.backend.backends.Backend>`.

    The AbstractObjectStore inherits from the :class:`~collections.abc.MutableSet` abstract collections class and
    therefore implements all the functions of this class.
    """
    @abc.abstractmethod
    def __init__(self):
        pass

    def update(self, other: Iterable[_IT]) -> None:
        for x in other:
            self.add(x)


class DictObjectStore(AbstractObjectStore[_IT], Generic[_IT]):
    """
    A local in-memory object store for :class:`~basyx.aas.model.base.Identifiable` objects, backed by a dict, mapping
    :class:`~basyx.aas.model.base.Identifier` → :class:`~basyx.aas.model.base.Identifiable`

    .. note::
        The `DictObjectStore` provides efficient retrieval of objects by their :class:`~basyx.aas.model.base.Identifier`
        However, since object stores are not referenced via the parent attribute, the mapping is not updated
        if the :class:`~basyx.aas.model.base.Identifier` of an :class:`~basyx.aas.model.base.Identifiable` changes.
        For more details, see [issue #216](https://github.com/eclipse-basyx/basyx-python-sdk/issues/216).
        As a result, the `DictObjectStore` is unsuitable for storing objects whose
        :class:`~basyx.aas.model.base.Identifier` may change.
        In such cases, consider using a :class:`~.SetObjectStore` instead.
    """
    def __init__(self, objects: Iterable[_IT] = ()) -> None:
        self._backend: Dict[Identifier, _IT] = {}
        for x in objects:
            self.add(x)

    def get_identifiable(self, identifier: Identifier) -> _IT:
        return self._backend[identifier]

    def add(self, x: _IT) -> None:
        if x.id in self._backend and self._backend.get(x.id) is not x:
            raise KeyError("Identifiable object with same id {} is already stored in this store"
                           .format(x.id))
        self._backend[x.id] = x

    def discard(self, x: _IT) -> None:
        if self._backend.get(x.id) is x:
            del self._backend[x.id]

    def __contains__(self, x: object) -> bool:
        if isinstance(x, Identifier):
            return x in self._backend
        if not isinstance(x, Identifiable):
            return False
        return self._backend.get(x.id) is x

    def __len__(self) -> int:
        return len(self._backend)

    def __iter__(self) -> Iterator[_IT]:
        return iter(self._backend.values())


class SetObjectStore(AbstractObjectStore[_IT], Generic[_IT]):
    """
    A local in-memory object store for :class:`~basyx.aas.model.base.Identifiable` objects, backed by a set

    .. note::
        The `SetObjectStore` is slower than the `DictObjectStore` for retrieval of objects, because it has to iterate
        over all objects to find the one with the correct :class:`~basyx.aas.model.base.Identifier`.
        On the other hand, the `SetObjectStore` is more secure, because it is less affected by changes in the
        :class:`~basyx.aas.model.base.Identifier` of an :class:`~basyx.aas.model.base.Identifiable` object.
        Therefore, the `SetObjectStore` is suitable for storing objects whose :class:`~basyx.aas.model.base.Identifier`
        may change.
    """
    def __init__(self, objects: Iterable[_IT] = ()) -> None:
        self._backend: Set[_IT] = set()
        for x in objects:
            self.add(x)

    def get_identifiable(self, identifier: Identifier) -> _IT:
        for x in self._backend:
            if x.id == identifier:
                return x
        raise KeyError(identifier)

    def add(self, x: _IT) -> None:
        if x in self:
            # Object is already in store
            return
        try:
            self.get_identifiable(x.id)
        except KeyError:
            self._backend.add(x)
        else:
            raise KeyError(f"Identifiable object with same id {x.id} is already stored in this store")

    def discard(self, x: _IT) -> None:
        self._backend.discard(x)

    def remove(self, x: _IT) -> None:
        self._backend.remove(x)

    def __contains__(self, x: object) -> bool:
        if isinstance(x, Identifier):
            try:
                self.get_identifiable(x)
                return True
            except KeyError:
                return False
        if not isinstance(x, Identifiable):
            return False
        return x in self._backend

    def __len__(self) -> int:
        return len(self._backend)

    def __iter__(self) -> Iterator[_IT]:
        return iter(self._backend)


class ObjectProviderMultiplexer(AbstractObjectProvider):
    """
    A multiplexer for Providers of :class:`~basyx.aas.model.base.Identifiable` objects.

    This class combines multiple registries of :class:`~basyx.aas.model.base.Identifiable` objects into a single one
    to allow retrieving :class:`~basyx.aas.model.base.Identifiable` objects from different sources.
    It implements the :class:`~.AbstractObjectProvider` interface to be used as registry itself.

    :param registries: A list of :class:`AbstractObjectProviders <.AbstractObjectProvider>` to query when looking up an
                      object
    """
    def __init__(self, registries: Optional[List[AbstractObjectProvider]] = None):
        self.providers: List[AbstractObjectProvider] = registries if registries is not None else []

    def get_identifiable(self, identifier: Identifier) -> Identifiable:
        for provider in self.providers:
            try:
                return provider.get_identifiable(identifier)
            except KeyError:
                pass
        raise KeyError("Identifier could not be found in any of the {} consulted registries."
                       .format(len(self.providers)))
