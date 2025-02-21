# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module adds the functionality of storing and retrieving :class:`~basyx.aas.model.base.Identifiable` objects
in local files.

The :class:`~.LocalFileBackend` takes care of updating and committing objects from and to the files, while the
:class:`~LocalFileObjectStore` handles adding, deleting and otherwise managing the AAS objects in a specific Directory.
"""
from typing import List, Iterator, Iterable, Union
import logging
import json
import os
import hashlib
import threading
import weakref

from . import backends
from ..adapter.json import json_serialization, json_deserialization
from basyx.aas import model


logger = logging.getLogger(__name__)


class LocalFileBackend(backends.Backend):
    """
    This Backend stores each Identifiable object as a single JSON document as a local file in a directory.
    Each document's id is build from the object's identifier using a SHA256 sum of its identifiable; the document's
    contents comprise a single property ``data``, containing the JSON serialization of the BaSyx Python SDK object. The
    :ref:`adapter.json <adapter.json.__init__>` package is used for serialization and deserialization of objects.
    """

    @classmethod
    def update_object(cls,
                      updated_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str]) -> None:

        if not isinstance(store_object, model.Identifiable):
            raise FileBackendSourceError("The given store_object is not Identifiable, therefore cannot be found "
                                         "in the FileBackend")
        file_name: str = store_object.source.replace("file://localhost/", "")
        with open(file_name, "r") as file:
            data = json.load(file, cls=json_deserialization.AASFromJsonDecoder)
            updated_store_object = data["data"]
            store_object.update_from(updated_store_object)

    @classmethod
    def commit_object(cls,
                      committed_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str]) -> None:
        if not isinstance(store_object, model.Identifiable):
            raise FileBackendSourceError("The given store_object is not Identifiable, therefore cannot be found "
                                         "in the FileBackend")
        file_name: str = store_object.source.replace("file://localhost/", "")
        with open(file_name, "w") as file:
            json.dump({'data': store_object}, file, cls=json_serialization.AASToJsonEncoder, indent=4)


backends.register_backend("file", LocalFileBackend)


class LocalFileObjectStore(model.AbstractObjectStore):
    """
    An ObjectStore implementation for :class:`~basyx.aas.model.base.Identifiable` BaSyx Python SDK objects backed
    by a local file based local backend
    """
    def __init__(self, directory_path: str):
        """
        Initializer of class LocalFileObjectStore

        :param directory_path: Path to the local file backend (the path where you want to store your AAS JSON files)
        """
        self.directory_path: str = directory_path.rstrip("/")

        # A dictionary of weak references to local replications of stored objects. Objects are kept in this cache as
        # long as there is any other reference in the Python application to them. We use this to make sure that only one
        # local replication of each object is kept in the application and retrieving an object from the store always
        # returns the **same** (not only equal) object. Still, objects are forgotten, when they are not referenced
        # anywhere else to save memory.
        self._object_cache: weakref.WeakValueDictionary[model.Identifier, model.Identifiable] \
            = weakref.WeakValueDictionary()
        self._object_cache_lock = threading.Lock()

    def check_directory(self, create=False):
        """
        Check if the directory exists and created it if not (and requested to do so)

        :param create: If True and the database does not exist, try to create it
        """
        if not os.path.exists(self.directory_path):
            if not create:
                raise FileNotFoundError("The given directory ({}) does not exist".format(self.directory_path))
            # Create directory
            os.mkdir(self.directory_path)
            logger.info("Creating directory {}".format(self.directory_path))

    def get_identifiable_by_hash(self, hash_: str) -> model.Identifiable:
        """
        Retrieve an AAS object from the local file by its identifier hash

        :raises KeyError: If the respective file could not be found
        """
        # Try to get the correct file
        try:
            with open("{}/{}.json".format(self.directory_path, hash_), "r") as file:
                data = json.load(file, cls=json_deserialization.AASFromJsonDecoder)
                obj = data["data"]
                self.generate_source(obj)
        except FileNotFoundError as e:
            raise KeyError("No Identifiable with hash {} found in local file database".format(hash_)) from e
        # If we still have a local replication of that object (since it is referenced from anywhere else), update that
        # replication and return it.
        with self._object_cache_lock:
            if obj.id in self._object_cache:
                old_obj = self._object_cache[obj.id]
                # If the source does not match the correct source for this CouchDB backend, the object seems to belong
                # to another backend now, so we return a fresh copy
                if old_obj.source == obj.source:
                    old_obj.update_from(obj)
                    return old_obj
        self._object_cache[obj.id] = obj
        return obj

    def get_identifiable(self, identifier: model.Identifier) -> model.Identifiable:
        """
        Retrieve an AAS object from the local file by its :class:`~basyx.aas.model.base.Identifier`

        :raises KeyError: If the respective file could not be found
        """
        try:
            return self.get_identifiable_by_hash(self._transform_id(identifier))
        except KeyError as e:
            raise KeyError("No Identifiable with id {} found in local file database".format(identifier)) from e

    def add(self, x: model.Identifiable) -> None:
        """
        Add an object to the store

        :raises KeyError: If an object with the same id exists already in the object store
        """
        logger.debug("Adding object %s to Local File Store ...", repr(x))
        if os.path.exists("{}/{}.json".format(self.directory_path, self._transform_id(x.id))):
            raise KeyError("Identifiable with id {} already exists in local file database".format(x.id))
        with open("{}/{}.json".format(self.directory_path, self._transform_id(x.id)), "w") as file:
            json.dump({"data": x}, file, cls=json_serialization.AASToJsonEncoder, indent=4)
            with self._object_cache_lock:
                self._object_cache[x.id] = x
            self.generate_source(x)  # Set the source of the object

    def discard(self, x: model.Identifiable) -> None:
        """
        Delete an :class:`~basyx.aas.model.base.Identifiable` AAS object from the local file store

        :param x: The object to be deleted
        :raises KeyError: If the object does not exist in the database
        """
        logger.debug("Deleting object %s from Local File Store database ...", repr(x))
        try:
            os.remove("{}/{}.json".format(self.directory_path, self._transform_id(x.id)))
        except FileNotFoundError as e:
            raise KeyError("No AAS object with id {} exists in local file database".format(x.id)) from e
        with self._object_cache_lock:
            del self._object_cache[x.id]
        x.source = ""

    def __contains__(self, x: object) -> bool:
        """
        Check if an object with the given :class:`~basyx.aas.model.base.Identifier` or the same
        :class:`~basyx.aas.model.base.Identifier` as the given object is contained in the local file database

        :param x: AAS object :class:`~basyx.aas.model.base.Identifier` or :class:`~basyx.aas.model.base.Identifiable`
                  AAS object
        :return: ``True`` if such an object exists in the database, ``False`` otherwise
        """
        if isinstance(x, model.Identifier):
            identifier = x
        elif isinstance(x, model.Identifiable):
            identifier = x.id
        else:
            return False
        logger.debug("Checking existence of object with id %s in database ...", repr(x))
        return os.path.exists("{}/{}.json".format(self.directory_path, self._transform_id(identifier)))

    def __len__(self) -> int:
        """
        Retrieve the number of objects in the local file database

        :return: The number of objects (determined from the number of documents)
        """
        logger.debug("Fetching number of documents from database ...")
        return len(os.listdir(self.directory_path))

    def __iter__(self) -> Iterator[model.Identifiable]:
        """
        Iterate all :class:`~basyx.aas.model.base.Identifiable` objects in the CouchDB database.

        This method returns an iterator, containing only a list of all identifiers in the database and retrieving
        the identifiable objects on the fly.
        """
        logger.debug("Iterating over objects in database ...")
        for name in os.listdir(self.directory_path):
            yield self.get_identifiable_by_hash(name.rstrip(".json"))

    @staticmethod
    def _transform_id(identifier: model.Identifier) -> str:
        """
        Helper method to represent an ASS Identifier as a string to be used as Local file document id
        """
        return hashlib.sha256(identifier.encode("utf-8")).hexdigest()

    def generate_source(self, identifiable: model.Identifiable) -> str:
        """
        Generates the source string for an :class:`~basyx.aas.model.base.Identifiable` object that is backed by the File

        :param identifiable: Identifiable object
        """
        source: str = "file://localhost/{}/{}.json".format(
            self.directory_path,
            self._transform_id(identifiable.id)
        )
        identifiable.source = source
        return source


class FileBackendSourceError(Exception):
    """
    Raised, if the given object's source is not resolvable as a local file
    """
    pass
