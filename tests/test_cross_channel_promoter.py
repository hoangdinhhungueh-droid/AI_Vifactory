# -*- coding: utf-8 -*-
"""
tests/test_cross_channel_promoter.py
Unit tests for the Smart Multi-Market Cross-Channel Promotion Engine (Phương án A).
"""
import unittest
from unittest.mock import MagicMock, patch
import json
import tempfile
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.cross_channel_promoter import (
    build_description_bridge,
    get_channel_profile,
    get_or_create_partner_playlist,
    add_video_to_partner_playlist,
    distribute_to_all_partner_playlists,
    dispatch_cross_promotion,
    sync_featured_channels,
    SUPPORTED_MARKETS,
    PARTNER_PLAYLIST_SPECS,
)


class TestCrossChannelPromoter(unittest.TestCase):

    def test_supported_markets(self):
        self.assertEqual(SUPPORTED_MARKETS, ["EN", "JP", "KR"])
        for m in SUPPORTED_MARKETS:
            self.assertIn(m, PARTNER_PLAYLIST_SPECS)
            self.assertTrue(len(PARTNER_PLAYLIST_SPECS[m]["title"]) > 5)

    def test_description_bridge_en(self):
        bridge = build_description_bridge("EN")
        self.assertIn("Official Global Investigation Network", bridge)
        self.assertIn("Japanese Edition", bridge)
        self.assertIn("Korean Edition", bridge)
        # Should not include English self-reference
        self.assertNotIn("English Edition:", bridge)

    def test_description_bridge_jp(self):
        bridge = build_description_bridge("JP")
        self.assertIn("公式グローバルネットワーク", bridge)
        self.assertIn("English Edition", bridge)
        self.assertIn("韓国語版", bridge)
        self.assertNotIn("日本語版:", bridge)

    def test_description_bridge_kr(self):
        bridge = build_description_bridge("KR")
        self.assertIn("공식 글로벌 취재 네트워크", bridge)
        self.assertIn("English Edition", bridge)
        self.assertIn("일본어판", bridge)
        self.assertNotIn("한국어판:", bridge)

    @patch("app.services.cross_channel_promoter._save_cache")
    @patch("app.services.cross_channel_promoter._load_cache")
    def test_get_or_create_partner_playlist_found_existing(self, mock_load_cache, mock_save_cache):
        mock_load_cache.return_value = {}
        mock_client = MagicMock()
        mock_playlists = mock_client.playlists.return_value
        
        target_title = PARTNER_PLAYLIST_SPECS["JP"]["title"]
        mock_playlists.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": "PL_EXISTING_JP_123",
                    "snippet": {"title": target_title}
                }
            ]
        }

        res = get_or_create_partner_playlist("JP", youtube_client=mock_client)
        self.assertEqual(res["status"], "found_existing")
        self.assertEqual(res["playlist_id"], "PL_EXISTING_JP_123")
        mock_save_cache.assert_called_once()

    @patch("app.services.cross_channel_promoter._save_cache")
    @patch("app.services.cross_channel_promoter._load_cache")
    def test_get_or_create_partner_playlist_create_new(self, mock_load_cache, mock_save_cache):
        mock_load_cache.return_value = {}
        mock_client = MagicMock()
        mock_playlists = mock_client.playlists.return_value
        
        # None exist initially
        mock_playlists.list.return_value.execute.return_value = {"items": []}
        mock_playlists.insert.return_value.execute.return_value = {"id": "PL_NEW_EN_999"}

        res = get_or_create_partner_playlist("EN", youtube_client=mock_client)
        self.assertEqual(res["status"], "created")
        self.assertEqual(res["playlist_id"], "PL_NEW_EN_999")
        mock_playlists.insert.assert_called_once()
        mock_save_cache.assert_called_once()

    def test_add_video_to_partner_playlist_success(self):
        mock_client = MagicMock()
        mock_items = mock_client.playlistItems.return_value
        
        # Not yet present
        mock_items.list.return_value.execute.return_value = {"items": []}
        mock_items.insert.return_value.execute.return_value = {"id": "PLI_ITEM_555"}

        res = add_video_to_partner_playlist(
            video_id="vid_test_123",
            partner_market="JP",
            playlist_id="PL_TARGET_JP",
            youtube_client=mock_client,
        )
        self.assertEqual(res["status"], "added_success")
        self.assertEqual(res["playlist_item_id"], "PLI_ITEM_555")

    def test_add_video_to_partner_playlist_already_present(self):
        mock_client = MagicMock()
        mock_items = mock_client.playlistItems.return_value
        
        # Already present
        mock_items.list.return_value.execute.return_value = {
            "items": [{"id": "PLI_ALREADY_EXISTS_777"}]
        }

        res = add_video_to_partner_playlist(
            video_id="vid_test_123",
            partner_market="KR",
            playlist_id="PL_TARGET_KR",
            youtube_client=mock_client,
        )
        self.assertEqual(res["status"], "already_present")
        self.assertEqual(res["playlist_item_id"], "PLI_ALREADY_EXISTS_777")
        mock_items.insert.assert_not_called()

    @patch("app.services.cross_channel_promoter.add_video_to_partner_playlist")
    @patch("app.services.cross_channel_promoter._record_ledger_entry")
    def test_dispatch_cross_promotion(self, mock_record, mock_add):
        mock_add.side_effect = lambda video_id, partner_market: {
            "status": "added_success",
            "partner_market": partner_market,
            "video_id": video_id,
        }

        # Source market KR -> should dispatch to EN and JP
        res = dispatch_cross_promotion(
            video_id="vid_kr_ep0005",
            market="KR",
            episode_id="KR_EP0005_test",
            title="Korean Investigation",
        )

        self.assertEqual(res["source_market"], "KR")
        self.assertEqual(res["video_id"], "vid_kr_ep0005")
        self.assertIn("EN", res["results"])
        self.assertIn("JP", res["results"])
        self.assertNotIn("KR", res["results"])
        self.assertEqual(mock_add.call_count, 2)
        mock_record.assert_called_once()

    def test_seo_fallback_package_includes_bridge(self):
        from app.services.seo_package_forge import _fallback_seo_package
        pkg = _fallback_seo_package(
            task_id="JP_EP0099_test",
            target_keyword="Bamboo Audit",
            market="JP",
        )
        desc = pkg.get("description", "")
        self.assertIn("公式グローバルネットワーク", desc)
        self.assertIn("English Edition", desc)
        self.assertIn("韓国語版", desc)

    def test_clean_and_localize_seo_description_integration(self):
        from scripts.execute_b10_auto_seo_upload_gate2 import _clean_and_localize_seo_description
        raw_desc = (
            "Hook line.\n\n"
            "Chapters:\n"
            "00:00 - Intro\n"
            "03:00 - Evidence\n\n"
            "#Tag1 #Tag2 #Tag3\n\n"
            "This video incorporates AI-assisted research, synthetic voice narration."
        )
        cleaned = _clean_and_localize_seo_description(raw_desc, Path("episodes/test"), market="kr")
        self.assertIn("공식 글로벌 취재 네트워크", cleaned)
        self.assertIn("English Edition", cleaned)
        self.assertIn("일본어판", cleaned)
        # Ensure bridge is placed before AI disclosure
        bridge_pos = cleaned.find("공식 글로벌 취재 네트워크")
        ai_pos = cleaned.find("This video incorporates")
        self.assertTrue(bridge_pos != -1 and ai_pos != -1 and bridge_pos < ai_pos)


if __name__ == "__main__":
    unittest.main()
