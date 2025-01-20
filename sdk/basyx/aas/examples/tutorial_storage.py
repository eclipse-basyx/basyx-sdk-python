#!/usr/bin/env python3
# This work is licensed under a Creative Commons CCZero 1.0 Universal License.
# See http://creativecommons.org/publicdomain/zero/1.0/ for more information.
"""
Tutorial for storing Asset Administration Shells, Submodels and Assets in an ObjectStore and using it for fetching these
objects by id and resolving references.
"""

# For managing a larger number of Identifiable AAS objects (AssetAdministrationShells, Assets, Submodels,
# ConceptDescriptions), the BaSyx Python SDK provides the `ObjectStore` functionality. This tutorial shows the basic
# features of an ObjectStore and how to use them. This includes usage of the built-in `resolve()` method of Reference
# objects, which can be used to easily get the Submodel objects, which are referenced by the
# `AssetAdministrationShell.submodel` set, etc.
#
# Step-by-Step Guide:
# Step 1: creating AssetInformation, Submodel and Asset Administration Shell objects
# Step 2: storing the data in an ObjectStore for easier handling
# Step 3: retrieving objects from the store by their identifier
# Step 4: using the ObjectStore to resolve a reference


from basyx.aas import model
from basyx.aas.model import AssetInformation, AssetAdministrationShell, Submodel


######################################################################################
# Step 1: Creating AssetInformation, Submodel and Asset Administration Shell objects #
######################################################################################

# For more details, take a look at `tutorial_create_simple_aas.py`

asset_information = AssetInformation(
    asset_kind=model.AssetKind.INSTANCE,
    global_asset_id='http://acplt.org/Simple_Asset'
)

prop = model.Property(
    id_short='ExampleProperty',
    value_type=model.datatypes.String,
    value='exampleValue',
    semantic_id=model.ExternalReference(
        (model.Key(
            type_=model.KeyTypes.GLOBAL_REFERENCE,
            value='http://acplt.org/Properties/SimpleProperty'
        ),)
    )
)
submodel = Submodel(
    id_='https://acplt.org/Simple_Submodel',
    submodel_element={prop}
)
aas = AssetAdministrationShell(
    id_='https://acplt.org/Simple_AAS',
    asset_information=asset_information,
    submodel={model.ModelReference.from_referable(submodel)}
)


##################################################################
# Step 2: Storing the Data in an ObjectStore for Easier Handling #
##################################################################

# Step 2.1: create an ObjectStore for identifiable objects
#
# In this tutorial, we use a `DictObjectStore`, which is a simple in-memory store: It just keeps track of the Python
# objects using a dict.
# This may not be a suitable solution, if you need to manage large numbers of objects or objects must be kept in a
# persistent memory (i.e. on hard disk). In this case, you may choose the `CouchDBObjectStore` from
# `aas.backends.couchdb` to use a CouchDB database server as persistent storage. Both ObjectStore implementations
# provide the same interface. In addition, the CouchDBObjectStores allows synchronizing the local object with the
# database via a Backend. See the `tutorial_backend_couchdb.py` for more information.
obj_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()

# step 2.2: add submodel and asset administration shell to store
obj_store.add(submodel)
obj_store.add(aas)


#################################################################
# Step 3: Retrieving Objects From the Store by Their Identifier #
#################################################################

tmp_submodel = obj_store.get_identifiable(
    'https://acplt.org/Simple_Submodel')

assert submodel is tmp_submodel


########################################################
# Step 4: Using the ObjectStore to Resolve a Reference #
########################################################

# The `aas` object already contains a reference to the submodel.
# Let's create a list of all submodels, to which the AAS has references, by resolving each of the submodel references:
submodels = [reference.resolve(obj_store)
             for reference in aas.submodel]

# The first (and only) element of this list should be our example submodel:
assert submodel is submodels[0]

# Now, let's manually create a reference to the Property within the submodel. The reference uses two keys, the first one
# identifying the submodel by its id, the second one resolving to the Property within the submodel by its
# idShort.
property_reference = model.ModelReference(
    (model.Key(
        type_=model.KeyTypes.SUBMODEL,
        value='https://acplt.org/Simple_Submodel'),
     model.Key(
         type_=model.KeyTypes.PROPERTY,
         value='ExampleProperty'),
     ),
    type_=model.Property
)

# Now, we can resolve this new reference.
# The `resolve()` method will fetch the Submodel object from the ObjectStore, traverse down to the included Property
# object and return this object.
tmp_property = property_reference.resolve(obj_store)
assert prop is tmp_property
