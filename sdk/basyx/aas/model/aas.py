# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
The main module of the AAS metamodel. It is used to define the class structures of high level elements such as
AssetAdministrationShell.
"""

from typing import Optional, Set, Iterable, List

from . import base, _string_constraints
from .submodel import Submodel


@_string_constraints.constrain_identifier("asset_type")
class AssetInformation:
    """
    In AssetInformation identifying metadata of the asset that is represented by an AAS is defined.

    The asset may either represent an asset type or an asset instance.
    The asset has a globally unique identifier plus – if needed – additional domain specific (proprietary)
    identifiers. However, to support the corner case of very first phase of lifecycle where a stabilised/constant
    global asset identifier does not already exist, the corresponding attribute ``globalAssetId`` is optional.

    **Constraint AASd-131:**  The globalAssetId or at least one specificAssetId shall be defined for AssetInformation.

    :ivar asset_kind: Denotes whether the Asset is of :class:`~basyx.aas.model.base.AssetKind` ``TYPE`` or ``INSTANCE``.
                      Default is ``INSTANCE``.
    :ivar global_asset_id: :class:`~basyx.aas.model.base.Identifier` modelling the identifier of the asset the AAS is
                           representing.
                           This attribute is required as soon as the AAS is exchanged via partners in the
                           life cycle of the asset. In a first phase of the life cycle the asset might not yet have a
                           global id but already an internal identifier. The internal identifier would be modelled via
                           :attr:`~.specific_asset_id`.
    :ivar specific_asset_id: Additional domain specific, typically proprietary Identifier (Set of
                             :class:`SpecificAssetIds <basyx.aas.model.base.SpecificAssetId>`) for the asset like
                             e.g. serial number etc.
    :ivar asset_type: In case AssetInformation/assetKind is applicable the AssetInformation/assetType is the asset ID
                      of the type asset of the asset under consideration as identified by
                      AssetInformation/globalAssetId.

                      .. note::
                          In case AssetInformation/assetKind is ``Instance`` then the AssetInformation/assetType
                          denotes which ``Type`` the asset is of. But it is also possible to have
                          an AssetInformation/assetType of an asset of kind ``Type``.
    :ivar default_thumbnail: Thumbnail of the asset represented by the asset administration shell. Used as default.
    """

    def __init__(self,
                 asset_kind: base.AssetKind = base.AssetKind.INSTANCE,
                 global_asset_id: Optional[base.Identifier] = None,
                 specific_asset_id: Iterable[base.SpecificAssetId] = (),
                 asset_type: Optional[base.Identifier] = None,
                 default_thumbnail: Optional[base.Resource] = None):

        super().__init__()
        self.asset_kind: base.AssetKind = asset_kind
        self.asset_type: Optional[base.Identifier] = asset_type
        self.default_thumbnail: Optional[base.Resource] = default_thumbnail
        # assign private attributes, bypassing setters, as constraints will be checked below
        self._specific_asset_id: base.ConstrainedList[base.SpecificAssetId] = base.ConstrainedList(
            specific_asset_id,
            item_set_hook=self._check_constraint_set_spec_asset_id,
            item_del_hook=self._check_constraint_del_spec_asset_id
        )
        self._global_asset_id: Optional[base.Identifier] = global_asset_id
        self._validate_global_asset_id(global_asset_id)
        self._validate_aasd_131(global_asset_id, bool(specific_asset_id))

    @property
    def global_asset_id(self) -> Optional[base.Identifier]:
        return self._global_asset_id

    @global_asset_id.setter
    def global_asset_id(self, global_asset_id: Optional[base.Identifier]) -> None:
        self._validate_global_asset_id(global_asset_id)
        self._validate_aasd_131(global_asset_id, bool(self.specific_asset_id))
        self._global_asset_id = global_asset_id

    @property
    def specific_asset_id(self) -> base.ConstrainedList[base.SpecificAssetId]:
        return self._specific_asset_id

    @specific_asset_id.setter
    def specific_asset_id(self, specific_asset_id: Iterable[base.SpecificAssetId]) -> None:
        # constraints are checked via _check_constraint_set_spec_asset_id() in this case
        self._specific_asset_id[:] = specific_asset_id

    def _check_constraint_set_spec_asset_id(self, items_to_replace: List[base.SpecificAssetId],
                                            new_items: List[base.SpecificAssetId],
                                            old_list: List[base.SpecificAssetId]) -> None:
        self._validate_aasd_131(self.global_asset_id,
                                len(old_list) - len(items_to_replace) + len(new_items) > 0)

    def _check_constraint_del_spec_asset_id(self, _item_to_del: base.SpecificAssetId,
                                            old_list: List[base.SpecificAssetId]) -> None:
        self._validate_aasd_131(self.global_asset_id, len(old_list) > 1)

    @staticmethod
    def _validate_global_asset_id(global_asset_id: Optional[base.Identifier]) -> None:
        if global_asset_id is not None:
            _string_constraints.check_identifier(global_asset_id)

    @staticmethod
    def _validate_aasd_131(global_asset_id: Optional[base.Identifier], specific_asset_id_nonempty: bool) -> None:
        if global_asset_id is None and not specific_asset_id_nonempty:
            raise base.AASConstraintViolation(131,
                                              "An AssetInformation has to have a globalAssetId or a specificAssetId")
        if global_asset_id is not None:
            _string_constraints.check_identifier(global_asset_id)

    def __repr__(self) -> str:
        return "AssetInformation(assetKind={}, globalAssetId={}, specificAssetId={}, assetType={}, " \
               "defaultThumbnail={})".format(self.asset_kind, self._global_asset_id, str(self.specific_asset_id),
                                             self.asset_type, str(self.default_thumbnail))


class AssetAdministrationShell(base.Identifiable, base.UniqueIdShortNamespace, base.HasDataSpecification):
    """
    An Asset Administration Shell

    :ivar asset_information: :class:`~.AssetInformation` of the asset this AssetAdministrationShell is representing
    :ivar id: The globally unique id (:class:`~basyx.aas.model.base.Identifier`) of the element.
                            (inherited from :class:`~basyx.aas.model.base.Identifiable`)
    :ivar id_short: Identifying string of the element within its name space. (inherited from
                    :class:`~basyx.aas.model.base.Referable`)
    :ivar display_name: Can be provided in several languages. (inherited from :class:`~basyx.aas.model.base.Referable`)
    :ivar category: The category is a value that gives further meta information w.r.t. to the class of the element.
                    It affects the expected existence of attributes and the applicability of constraints.
                    (inherited from :class:`~basyx.aas.model.base.Referable`)
    :ivar description: Description or comments on the element. (inherited from :class:`~basyx.aas.model.base.Referable`)
    :ivar parent: Reference to the next referable parent element of the element. (inherited from
                  :class:`~basyx.aas.model.base.Referable`)
    :ivar administration: :class:`~basyx.aas.model.base.AdministrativeInformation` of an
                          :class:`~.basyx.aas.model.base.Identifiable` element. (inherited from
                          :class:`~basyx.aas.model.base.Identifiable`)
    :ivar submodel: Unordered list of :class:`~basyx.aas.model.base.ModelReference` to
                    :class:`~basyx.aas.model.submodel.Submodel` to describe typically the asset of an AAS.
    :ivar derived_from: The :class:`reference <basyx.aas.model.base.ModelReference>` to the AAS
                        from which it was derived.
    :ivar embedded_data_specifications: List of Embedded data specification.
    :ivar extension: An extension of the element.
                     (from :class:`~basyx.aas.model.base.HasExtension`)
    """
    def __init__(self,
                 asset_information: AssetInformation,
                 id_: base.Identifier,
                 id_short: Optional[base.NameType] = None,
                 display_name: Optional[base.MultiLanguageNameType] = None,
                 category: Optional[base.NameType] = None,
                 description: Optional[base.MultiLanguageTextType] = None,
                 parent: Optional[base.UniqueIdShortNamespace] = None,
                 administration: Optional[base.AdministrativeInformation] = None,
                 submodel: Optional[Set[base.ModelReference[Submodel]]] = None,
                 derived_from: Optional[base.ModelReference["AssetAdministrationShell"]] = None,
                 embedded_data_specifications: Iterable[base.EmbeddedDataSpecification]
                 = (),
                 extension: Iterable[base.Extension] = ()):
        super().__init__()
        self.id: base.Identifier = id_
        self.asset_information: AssetInformation = asset_information
        self.id_short = id_short
        self.display_name: Optional[base.MultiLanguageNameType] = display_name
        self.category = category
        self.description: Optional[base.MultiLanguageTextType] = description
        self.parent: Optional[base.UniqueIdShortNamespace] = parent
        self.administration: Optional[base.AdministrativeInformation] = administration
        self.derived_from: Optional[base.ModelReference["AssetAdministrationShell"]] = derived_from
        self.submodel: Set[base.ModelReference[Submodel]] = set() if submodel is None else submodel
        self.embedded_data_specifications: List[base.EmbeddedDataSpecification] = list(embedded_data_specifications)
        self.extension = base.NamespaceSet(self, [("name", True)], extension)
