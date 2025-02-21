# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import unittest

from basyx.aas import model


class AssetInformationTest(unittest.TestCase):
    def test_aasd_131_init(self) -> None:
        with self.assertRaises(model.AASConstraintViolation) as cm:
            model.AssetInformation(model.AssetKind.INSTANCE)
        self.assertEqual("An AssetInformation has to have a globalAssetId or a specificAssetId (Constraint AASd-131)",
                         str(cm.exception))
        model.AssetInformation(model.AssetKind.INSTANCE, global_asset_id="https://acplt.org/TestAsset")
        model.AssetInformation(model.AssetKind.INSTANCE, specific_asset_id=(model.SpecificAssetId("test", "test"),))
        model.AssetInformation(model.AssetKind.INSTANCE, global_asset_id="https://acplt.org/TestAsset",
                               specific_asset_id=(model.SpecificAssetId("test", "test"),))

    def test_aasd_131_set(self) -> None:
        asset_information = model.AssetInformation(model.AssetKind.INSTANCE,
                                                   global_asset_id="https://acplt.org/TestAsset",
                                                   specific_asset_id=(model.SpecificAssetId("test", "test"),))
        asset_information.global_asset_id = None
        with self.assertRaises(model.AASConstraintViolation) as cm:
            asset_information.specific_asset_id = model.ConstrainedList(())
        self.assertEqual("An AssetInformation has to have a globalAssetId or a specificAssetId (Constraint AASd-131)",
                         str(cm.exception))

        asset_information = model.AssetInformation(model.AssetKind.INSTANCE,
                                                   global_asset_id="https://acplt.org/TestAsset",
                                                   specific_asset_id=(model.SpecificAssetId("test", "test"),))
        asset_information.specific_asset_id = model.ConstrainedList(())
        with self.assertRaises(model.AASConstraintViolation) as cm:
            asset_information.global_asset_id = None
        self.assertEqual("An AssetInformation has to have a globalAssetId or a specificAssetId (Constraint AASd-131)",
                         str(cm.exception))

    def test_aasd_131_specific_asset_id_add(self) -> None:
        asset_information = model.AssetInformation(model.AssetKind.INSTANCE,
                                                   global_asset_id="https://acplt.org/TestAsset")
        specific_asset_id1 = model.SpecificAssetId("test", "test")
        specific_asset_id2 = model.SpecificAssetId("test", "test")
        asset_information.specific_asset_id.append(specific_asset_id1)
        asset_information.specific_asset_id.extend((specific_asset_id2,))
        self.assertIs(asset_information.specific_asset_id[0], specific_asset_id1)
        self.assertIs(asset_information.specific_asset_id[1], specific_asset_id2)

    def test_aasd_131_specific_asset_id_set(self) -> None:
        asset_information = model.AssetInformation(model.AssetKind.INSTANCE,
                                                   specific_asset_id=(model.SpecificAssetId("test", "test"),))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            asset_information.specific_asset_id[:] = ()
        self.assertEqual("An AssetInformation has to have a globalAssetId or a specificAssetId (Constraint AASd-131)",
                         str(cm.exception))
        specific_asset_id = model.SpecificAssetId("test", "test")
        self.assertIsNot(asset_information.specific_asset_id[0], specific_asset_id)
        asset_information.specific_asset_id[:] = (specific_asset_id,)
        self.assertIs(asset_information.specific_asset_id[0], specific_asset_id)
        asset_information.specific_asset_id[0] = model.SpecificAssetId("test", "test")
        self.assertIsNot(asset_information.specific_asset_id[0], specific_asset_id)

    def test_aasd_131_specific_asset_id_del(self) -> None:
        specific_asset_id = model.SpecificAssetId("test", "test")
        asset_information = model.AssetInformation(model.AssetKind.INSTANCE,
                                                   specific_asset_id=(model.SpecificAssetId("test1", "test1"),
                                                                      specific_asset_id))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            del asset_information.specific_asset_id[:]
        self.assertEqual("An AssetInformation has to have a globalAssetId or a specificAssetId (Constraint AASd-131)",
                         str(cm.exception))
        with self.assertRaises(model.AASConstraintViolation) as cm:
            asset_information.specific_asset_id.clear()
        self.assertEqual("An AssetInformation has to have a globalAssetId or a specificAssetId (Constraint AASd-131)",
                         str(cm.exception))
        self.assertIsNot(asset_information.specific_asset_id[0], specific_asset_id)
        del asset_information.specific_asset_id[0]
        self.assertIs(asset_information.specific_asset_id[0], specific_asset_id)
        with self.assertRaises(model.AASConstraintViolation) as cm:
            del asset_information.specific_asset_id[0]
        self.assertEqual("An AssetInformation has to have a globalAssetId or a specificAssetId (Constraint AASd-131)",
                         str(cm.exception))
