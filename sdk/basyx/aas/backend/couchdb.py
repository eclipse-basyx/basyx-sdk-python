# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module adds the functionality of storing and retrieving :class:`~basyx.aas.model.base.Identifiable` objects
in a CouchDB.

The :class:`~.CouchDBBackend` takes care of updating and committing objects from and to the CouchDB, while the
:class:`~CouchDBObjectStore` handles adding, deleting and otherwise managing the AAS objects in a specific CouchDB.
"""
import threading
import weakref
from typing import List, Dict, Any, Optional, Iterator, Iterable, Union, Tuple, MutableMapping
import urllib.parse
import urllib.request
import urllib.error
import logging
import json
import urllib3  # type: ignore

from . import backends
from ..adapter.json import json_serialization, json_deserialization
from basyx.aas import model


logger = logging.getLogger(__name__)
_http_pool_manager = urllib3.PoolManager()


class CouchDBBackend(backends.Backend):
    """
    This Backend stores each Identifiable object as a single JSON document in the configured CouchDB database. Each
    document's id is build from the object's identifier. The document's contents comprise a single property ``data``,
    containing the JSON serialization of the BaSyx Python SDK object. The :ref:`adapter.json <adapter.json.__init__>`
    package is used for serialization and deserialization of objects.
    """
    @classmethod
    def update_object(cls,
                      updated_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str]) -> None:

        if not isinstance(store_object, model.Identifiable):
            raise CouchDBSourceError("The given store_object is not Identifiable, therefore cannot be found "
                                     "in the CouchDB")
        url = CouchDBBackend._parse_source(store_object.source)

        try:
            data = CouchDBBackend.do_request(url)
        except CouchDBServerError as e:
            if e.code == 404:
                raise KeyError("No Identifiable found in CouchDB at {}".format(url)) from e
            raise

        updated_store_object = data['data']
        set_couchdb_revision(url, data["_rev"])
        store_object.update_from(updated_store_object)

    @classmethod
    def commit_object(cls,
                      committed_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str]) -> None:
        if not isinstance(store_object, model.Identifiable):
            raise CouchDBSourceError("The given store_object is not Identifiable, therefore cannot be found "
                                     "in the CouchDB")
        url = CouchDBBackend._parse_source(store_object.source)
        # We need to get the revision of the object, if it already exists, otherwise we cannot write to the Couchdb
        if get_couchdb_revision(url) is None:
            raise CouchDBConflictError("No revision found for the given object. Try calling `update` on it.")

        data = json.dumps({'data': store_object, "_rev": get_couchdb_revision(url)},
                          cls=json_serialization.AASToJsonEncoder)

        try:
            response = CouchDBBackend.do_request(
                url, method='PUT', additional_headers={'Content-type': 'application/json'}, body=data.encode('utf-8'))
            set_couchdb_revision(url, response["rev"])
        except CouchDBServerError as e:
            if e.code == 409:
                raise CouchDBConflictError("Could not commit changes to id {} due to a concurrent modification in the "
                                           "database.".format(store_object.id)) from e
            elif e.code == 404:
                raise KeyError("Object with id {} was not found in the CouchDB at {}"
                               .format(store_object.id, url)) from e
            raise

    @classmethod
    def _parse_source(cls, source: str) -> str:
        """
        Parses the source parameter of a model.Referable object

        :param source: Source string of the model.Referable object
        :return: URL to the document
        :raises CouchDBBackendSourceError, if the source has the wrong format
        """
        if source.startswith("couchdbs://"):
            url = source.replace("couchdbs://", "https://", 1)
        elif source.startswith("couchdb://"):
            url = source.replace("couchdb://", "http://", 1)
        else:
            raise CouchDBSourceError("Source has wrong format. "
                                     "Expected to start with {couchdb://, couchdbs://}, got {" + source + "}")
        return url

    @classmethod
    def do_request(cls, url: str, method: str = "GET", additional_headers: Optional[Dict[str, str]] = None,
                   body: Optional[bytes] = None) -> MutableMapping[str, Any]:
        """
        Perform an HTTP(S) request to the CouchDBServer, parse the result and handle errors

        :param url: The HTTP or HTTPS URL to request
        :param method: The HTTP method for the request
        :param additional_headers: Additional headers to insert into the request. The default headers include
            'connection: keep-alive', 'accept-encoding: ...', 'authorization: basic ...', 'Accept: ...'.
        :param body: Request body for POST, PUT, and PATCH requests
        :return: The parsed JSON data if the request ``method`` is other than 'HEAD' or the response headers for 'HEAD'
            requests
        """
        url_parts = urllib.parse.urlparse(url)
        host = url_parts.scheme + url_parts.netloc
        auth = _credentials_store.get(host)
        headers = urllib3.make_headers(keep_alive=True, accept_encoding=True,
                                       basic_auth="{}:{}".format(*auth) if auth else None)
        headers['Accept'] = 'application/json'
        headers.update(additional_headers if additional_headers is not None else {})
        try:
            response = _http_pool_manager.request(method, url, headers=headers, body=body)
        except (urllib3.exceptions.TimeoutError, urllib3.exceptions.SSLError, urllib3.exceptions.ProtocolError) as e:
            raise CouchDBConnectionError("Error while connecting to the CouchDB server: {}".format(e)) from e
        except urllib3.exceptions.HTTPError as e:
            raise CouchDBResponseError("Error while connecting to the CouchDB server: {}".format(e)) from e

        if not (200 <= response.status < 300):
            logger.debug("Request %s %s finished with HTTP status code %s.",
                         method, url, response.status)
            if response.headers.get('Content-type', None) != 'application/json':
                raise CouchDBResponseError("Unexpected Content-type header {} of response from CouchDB server"
                                           .format(response.headers.get('Content-type', None)))

            if method == 'HEAD':
                raise CouchDBServerError(response.status, "", "", "HTTP {}".format(response.status))

            try:
                data = json.loads(response.data.decode('utf-8'))
            except json.JSONDecodeError:
                raise CouchDBResponseError("Could not parse error message of HTTP {}"
                                           .format(response.status))
            raise CouchDBServerError(response.status, data['error'], data['reason'],
                                     "HTTP {}: {} (reason: {})".format(response.status, data['error'], data['reason']))

        # Check response & parse data
        logger.debug("Request %s %s finished successfully.", method, url)
        if method == 'HEAD':
            return response.headers

        if response.headers.get('Content-type') != 'application/json':
            raise CouchDBResponseError("Unexpected Content-type header")
        try:
            data = json.loads(response.data.decode('utf-8'), cls=json_deserialization.AASFromJsonDecoder)
        except json.JSONDecodeError as e:
            raise CouchDBResponseError("Could not parse CouchDB server response as JSON data.") from e
        return data


backends.register_backend("couchdb", CouchDBBackend)
backends.register_backend("couchdbs", CouchDBBackend)


# Global registry for credentials for CouchDB Servers
_credentials_store: Dict[str, Tuple[str, str]] = {}
# Note: The HTTPPasswordMgr is not thread safe during writing, should be thread safe for reading only.


def register_credentials(url: str, username: str, password: str):
    """
    Register the credentials of a CouchDB server to the global credentials store

    .. Warning::

        Do not use this function, while other threads may be accessing the credentials via the
        :class:`~.CouchDBObjectStore` or update or commit functions of :class:`~.basyx.aas.model.base.Referable`
        objects!

    :param url: Toplevel URL
    :param username: Username to that CouchDB instance
    :param password: Password to the Username
    """
    url_parts = urllib.parse.urlparse(url)
    _credentials_store[url_parts.scheme + url_parts.netloc] = (username, password)


# Global registry for CouchDB Revisions
_revision_store_lock = threading.Lock()
_revision_store: Dict[str, str] = {}


def set_couchdb_revision(url: str, revision: str):
    """
    Set the CouchDB revision of the given document in the revision store

    :param url: URL to the CouchDB document
    :param revision: CouchDB revision
    """
    with _revision_store_lock:
        _revision_store[url] = revision


def get_couchdb_revision(url: str) -> Optional[str]:
    """
    Get the CouchDB revision from the revision store for the given URL to a CouchDB Document

    :param url: URL to the CouchDB document
    :return: CouchDB-revision, if there is one, otherwise returns None
    """
    with _revision_store_lock:
        return _revision_store.get(url)


def delete_couchdb_revision(url: str):
    """
    Delete the CouchDB revision from the revision store for the given URL to a CouchDB Document

    :param url: URL to the CouchDB document
    """
    with _revision_store_lock:
        del _revision_store[url]


class CouchDBObjectStore(model.AbstractObjectStore):
    """
    An ObjectStore implementation for :class:`~basyx.aas.model.base.Identifiable` BaSyx Python SDK objects backed
    by a CouchDB database server.

    All methods of the ``CouchDBObjectStore`` are blocking, i.e. they stop the current thread's execution until they
    receive a response from the CouchDB server (or encounter a timeout). However, the ``CouchDBObjectStore`` objects are
    thread-safe, as long as no CouchDB credentials are added (via ``register_credentials()``) during transactions.
    """
    def __init__(self, url: str, database: str):
        """
        Initializer of class CouchDBObjectStore

        :param url: URL to the CouchDB
        :param database: Name of the Database inside the CouchDB
        """
        self.url: str = url
        self.database_name: str = database

        # A dictionary of weak references to local replications of stored objects. Objects are kept in this cache as
        # long as there is any other reference in the Python application to them. We use this to make sure that only one
        # local replication of each object is kept in the application and retrieving an object from the store always
        # returns the **same** (not only equal) object. Still, objects are forgotten, when they are not referenced
        # anywhere else to save memory.
        self._object_cache: weakref.WeakValueDictionary[model.Identifier, model.Identifiable]\
            = weakref.WeakValueDictionary()
        self._object_cache_lock = threading.Lock()

    def check_database(self, create=False):
        """
        Check if the database exists and created it if not (and requested to do so)

        :param create: If True and the database does not exist, try to create it
        :raises CouchDBError: If error occur during the request to the CouchDB server
                              (see ``_do_request()`` for details)
        """

        try:
            CouchDBBackend.do_request("{}/{}".format(self.url, self.database_name), 'HEAD')
        except CouchDBServerError as e:
            # If an HTTPError is raised, re-raise it, unless it is a 404 error and we are requested to create the
            # database
            if e.code != 404 or not create:
                raise e
        else:
            # If no exception is given raised, the database is okay
            return

        # Create database
        logger.info("Creating CouchDB database %s/%s ...", self.url, self.database_name)
        CouchDBBackend.do_request("{}/{}".format(self.url, self.database_name), 'PUT')

    def get_identifiable_by_couchdb_id(self, couchdb_id: str) -> model.Identifiable:
        """
        Retrieve an AAS object from the CouchDB by its couchdb-ID-string

        :raises KeyError: If no such object is stored in the database
        :raises CouchDBError: If error occur during the request to the CouchDB server
                              (see ``_do_request()`` for details)
        """
        # Create and issue HTTP request (raises HTTPError on status != 200)

        try:
            data = CouchDBBackend.do_request(
                "{}/{}/{}".format(self.url, self.database_name, urllib.parse.quote(couchdb_id, safe='')))
        except CouchDBServerError as e:
            if e.code == 404:
                raise KeyError("No Identifiable with couchdb-id {} found in CouchDB database".format(couchdb_id)) from e
            raise

        # Add CouchDB metadata (for later commits) to object
        obj = data['data']
        if not isinstance(obj, model.Identifiable):
            raise CouchDBResponseError("The CouchDB document with id {} does not contain an identifiable AAS object."
                                       .format(couchdb_id))
        self.generate_source(obj)  # Generate the source parameter of this object
        set_couchdb_revision("{}/{}/{}".format(self.url, self.database_name, urllib.parse.quote(couchdb_id, safe='')),
                             data["_rev"])

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
        Retrieve an AAS object from the CouchDB by its :class:`~basyx.aas.model.base.Identifier`

        :raises KeyError: If no such object is stored in the database
        :raises CouchDBError: If error occur during the request to the CouchDB server
                              (see ``_do_request()`` for details)
        """
        try:
            return self.get_identifiable_by_couchdb_id(self._transform_id(identifier, False))
        except KeyError as e:
            raise KeyError("No Identifiable with id {} found in CouchDB database".format(identifier)) from e

    def add(self, x: model.Identifiable) -> None:
        """
        Add an object to the store

        :raises KeyError: If an object with the same id exists already in the database
        :raises CouchDBError: If error occur during the request to the CouchDB server
                              (see ``_do_request()`` for details)
        """
        logger.debug("Adding object %s to CouchDB database ...", repr(x))
        # Serialize data
        data = json.dumps({'data': x}, cls=json_serialization.AASToJsonEncoder)

        # Create and issue HTTP request (raises HTTPError on status != 200)

        try:
            response = CouchDBBackend.do_request(
                "{}/{}/{}".format(self.url, self.database_name, self._transform_id(x.id)),
                'PUT',
                {'Content-type': 'application/json'},
                data.encode('utf-8'))
            set_couchdb_revision("{}/{}/{}".format(self.url, self.database_name, self._transform_id(x.id)),
                                 response["rev"])
        except CouchDBServerError as e:
            if e.code == 409:
                raise KeyError("Identifiable with id {} already exists in CouchDB database".format(x.id)) from e
            raise
        with self._object_cache_lock:
            self._object_cache[x.id] = x
        self.generate_source(x)  # Set the source of the object

    def discard(self, x: model.Identifiable, safe_delete=False) -> None:
        """
        Delete an :class:`~basyx.aas.model.base.Identifiable` AAS object from the CouchDB database

        :param x: The object to be deleted
        :param safe_delete: If ``True``, only delete the object if it has not been modified in the database in
                            comparison to the provided revision. This uses the CouchDB revision token and thus only
                            works with CouchDBIdentifiable objects retrieved from this database.
        :raises KeyError: If the object does not exist in the database
        :raises CouchDBConflictError: If safe_delete is ``True`` and the object has been modified or deleted in the
            database
        :raises CouchDBError: If error occur during the request to the CouchDB server
                              (see ``_do_request()`` for details)
        """
        logger.debug("Deleting object %s from CouchDB database ...", repr(x))
        rev = get_couchdb_revision("{}/{}/{}".format(self.url,
                                                     self.database_name,
                                                     self._transform_id(x.id)))

        if rev is not None and safe_delete:
            logger.debug("using the object's stored revision token %s for deletion." % rev)
        elif safe_delete:
            raise CouchDBConflictError("No CouchDBRevision found for the object")
        else:
            # If not safe_delete, fetch the current document revision from the database using a HEAD request and the
            # ETag response header
            try:
                logger.debug("fetching the current object revision for deletion ...")
                headers = CouchDBBackend.do_request(
                    "{}/{}/{}".format(self.url, self.database_name, self._transform_id(x.id)), 'HEAD')
                rev = headers['ETag'][1:-1]
            except CouchDBServerError as e:
                if e.code == 404:
                    raise KeyError("No AAS object with id {} exists in CouchDB database".format(x.id))\
                        from e
                raise
        try:
            CouchDBBackend.do_request(
                "{}/{}/{}?rev={}".format(self.url, self.database_name, self._transform_id(x.id), rev),
                'DELETE')
        except CouchDBServerError as e:
            if e.code == 404:
                raise KeyError("No AAS object with id {} exists in CouchDB database".format(x.id)) from e
            elif e.code == 409:
                raise CouchDBConflictError(
                    "Object with id {} has been modified in the database since "
                    "the version requested to be deleted.".format(x.id)) from e
            raise
        delete_couchdb_revision("{}/{}/{}".format(self.url,
                                                  self.database_name,
                                                  self._transform_id(x.id)))
        with self._object_cache_lock:
            del self._object_cache[x.id]
        x.source = ""

    def __contains__(self, x: object) -> bool:
        """
        Check if an object with the given :class:`~basyx.aas.model.base.Identifier` or the same
        :class:`~basyx.aas.model.base.Identifier` as the given object is contained in the CouchDB database

        :param x: AAS object :class:`~basyx.aas.model.base.Identifier` or :class:`~basyx.aas.model.base.Identifiable`
                  AAS object
        :return: ``True`` if such an object exists in the database, ``False`` otherwise
        :raises CouchDBError: If error occur during the request to the CouchDB server
                              (see ``_do_request()`` for details)
        """
        if isinstance(x, model.Identifier):
            identifier = x
        elif isinstance(x, model.Identifiable):
            identifier = x.id
        else:
            return False
        logger.debug("Checking existence of object with id %s in database ...", repr(x))

        try:
            CouchDBBackend.do_request(
                "{}/{}/{}".format(self.url, self.database_name, self._transform_id(identifier)), 'HEAD')
        except CouchDBServerError as e:
            if e.code == 404:
                return False
            raise
        return True

    def __len__(self) -> int:
        """
        Retrieve the number of objects in the CouchDB database

        :return: The number of objects (determined from the number of documents)
        :raises CouchDBError: If error occur during the request to the CouchDB server
                              (see ``_do_request()`` for details)
        """
        logger.debug("Fetching number of documents from database ...")
        data = CouchDBBackend.do_request("{}/{}".format(self.url, self.database_name))
        return data['doc_count']

    def __iter__(self) -> Iterator[model.Identifiable]:
        """
        Iterate all :class:`~basyx.aas.model.base.Identifiable` objects in the CouchDB database.

        This method returns a lazy iterator, containing only a list of all identifiers in the database and retrieving
        the identifiable objects on the fly.

        :raises CouchDBError: If error occur during fetching the list of objects from the CouchDB server (see
                              ``_do_request()`` for details)
        """
        # Iterator class storing the list of ids and fetching Identifiable objects on the fly
        class CouchDBIdentifiableIterator(Iterator[model.Identifiable]):
            def __init__(self, store: CouchDBObjectStore, ids: Iterable[str]):
                self._iter = iter(ids)
                self._store = store

            def __next__(self):
                next_id = next(self._iter)
                return self._store.get_identifiable_by_couchdb_id(next_id)

        # Fetch a list of all ids and construct Iterator object
        logger.debug("Creating iterator over objects in database ...")
        data = CouchDBBackend.do_request("{}/{}/_all_docs".format(self.url, self.database_name))
        return CouchDBIdentifiableIterator(self, (row['id'] for row in data['rows']))

    @staticmethod
    def _transform_id(identifier: model.Identifier, url_quote=True) -> str:
        """
        Helper method to represent an ASS Identifier as a string to be used as CouchDB document id

        :param url_quote: If True, the result id string is url-encoded to be used in an HTTP request URL
        """
        if url_quote:
            identifier = urllib.parse.quote(identifier, safe='')
        return identifier

    def generate_source(self, identifiable: model.Identifiable):
        """
        Generates the source string for an :class:`~basyx.aas.model.base.Identifiable` object that is backed
        by the Couchdb

        :param identifiable: Identifiable object
        """
        source: str = self.url.replace("https://", "couchdbs://").replace("http://", "couchdb://")
        source += "/" + self.database_name + "/" + self._transform_id(identifiable.id)
        identifiable.source = source


# #################################################################################################
# Custom Exception classes for reporting errors during interaction with the CouchDB server

class CouchDBError(Exception):
    pass


class CouchDBSourceError(CouchDBError):
    """Exception raised when the source has the wrong format"""
    pass


class CouchDBConnectionError(CouchDBError):
    """Exception raised when the CouchDB server could not be reached"""
    pass


class CouchDBResponseError(CouchDBError):
    """Exception raised by when an HTTP of the CouchDB server could not be handled (e.g.
    no JSON body)"""
    pass


class CouchDBServerError(CouchDBError):
    """Exception raised when the CouchDB server returns an unexpected error code"""
    def __init__(self, code: int, error: str, reason: str, *args):
        super().__init__(*args)
        self.code = code
        self.error = error
        self.reason = reason


class CouchDBConflictError(CouchDBError):
    """Exception raised when an object could not be committed due to a concurrent modification in the database"""
    pass
