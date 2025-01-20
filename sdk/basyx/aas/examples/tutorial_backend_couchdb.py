#!/usr/bin/env python3
# This work is licensed under a Creative Commons CCZero 1.0 Universal License.
# See http://creativecommons.org/publicdomain/zero/1.0/ for more information.
"""
Tutorial for storing Asset Administration Shells, Submodels and Assets in a CouchDB database server, using the
CouchDBObjectStore and CouchDB Backend.
"""

from configparser import ConfigParser
from pathlib import Path

import basyx.aas.examples.data.example_aas
import basyx.aas.backend.couchdb

# To execute this tutorial, you'll need a running CouchDB server, including an empty database and a user account with
# access to that database.
# After installing CouchDB, you can use the CouchDB web interface "Fauxton" (typically at
# http://localhost:5984/_utils/) to create a new database. Optionally, you can create a new user by adding a document
# to the `_users` database with the following contents (notice that the username is required in two positions):
#
#     {"_id": "org.couchdb.user:<your username>",
#      "name": "<your username>",
#      "password": "<your password>",
#      "roles": [],
#      "type": "user"}
#
# Afterwards you can add the new user to the set of "Members" of your new database (via the "Permissions" section in the
# user interface). Alternatively, you can use the admin credentials with the BaSyx Python SDK (see below).

# Step-by-Step Guide:
# step 1: connecting to a CouchDB server
# step 2: storing objects in CouchDBObjectStore


##########################################
# Step 1: Connecting to a CouchDB Server #
##########################################

# Well, actually, connections to the CouchDB server are created by the CouchDB backend, as required. However, we need
# to provide the login credentials to the server for this to work.
#
# Here, we take the test configuration to work with BaSyx development environments. You should replace these with
# the url of your CouchDB server (typically http://localhost:5984), the name of the empty database, and the name and
# password of a CouchDB user account which is "member" of this database (see above). Alternatively, you can provide
# your CouchDB server's admin credentials.
config = ConfigParser()
config.read([Path(__file__).parent.parent.parent.parent / 'test' / 'test_config.default.ini',
             Path(__file__).parent.parent.parent.parent / 'test' / 'test_config.ini'])

couchdb_url = config['couchdb']['url']
couchdb_database = config['couchdb']['database']
couchdb_user = config['couchdb']['user']
couchdb_password = config['couchdb']['password']


# Provide the login credentials to the CouchDB backend.
# These credentials are used whenever communication with this CouchDB server is required via the CouchDBObjectStore.
basyx.aas.backend.couchdb.register_credentials(couchdb_url, couchdb_user, couchdb_password)

# Now, we create a CouchDBObjectStore as an interface for managing the objects in the CouchDB server.
object_store = basyx.aas.backend.couchdb.CouchDBObjectStore(couchdb_url, couchdb_database)


#####################################################
# Step 2: Storing objects in the CouchDBObjectStore #
#####################################################

# Create some example objects
example_submodel1 = basyx.aas.examples.data.example_aas.create_example_asset_identification_submodel()
example_submodel2 = basyx.aas.examples.data.example_aas.create_example_bill_of_material_submodel()

# The CouchDBObjectStore behaves just like other ObjectStore implementations (see `tutorial_storage.py`). The objects
# are transferred to the CouchDB immediately.
object_store.add(example_submodel1)
object_store.add(example_submodel2)

# For more information on how to use `ObjectStore`s in general, please refer to `tutorial_storage.py`.

############
# Clean up #
############

# Let's delete the Submodels from the CouchDB to leave it in a clean state
object_store.discard(example_submodel1)
object_store.discard(example_submodel2)
