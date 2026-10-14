#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_agq_fleet.py
Kiểm thử tự động cho hệ thống AGQ Fleet Sentinel.
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.agq_proto_parser import extract_user_status_proto
from app.services.agq_fleet_manager import AGQFleetManager


class TestAGQFleet(unittest.TestCase):

    def test_extract_user_status_proto(self):
        """Kiểm tra trích xuất dữ liệu thực tế từ state.vscdb."""
        info = extract_user_status_proto()
        self.assertIsNotNone(info, "Không được trả về None khi file state.vscdb tồn tại")
        self.assertIn("email", info)
        self.assertIn("google_models_quota_percent", info)
        self.assertIn("display_name", info)
        self.assertTrue("@" in info["email"], f"Email phải chứa ký tự @: {info.get('email')}")
        self.assertGreaterEqual(info["google_models_quota_percent"], 0.0)
        self.assertLessEqual(info["google_models_quota_percent"], 100.0)

    def test_fleet_manager_lifecycle(self):
        """Kiểm tra vòng đời dữ liệu và gợi ý tài khoản tiếp theo."""
        mgr = AGQFleetManager()
        status = mgr.get_fleet_status()
        self.assertGreaterEqual(status["total_accounts"], 6)
        self.assertIn("recommended_acc_id", status)
        self.assertTrue(status["recommended_acc_id"].startswith("acc_"))

        # Kiểm tra nạp dữ liệu từ parser
        current_proto = extract_user_status_proto()
        if current_proto and current_proto.get("email"):
            mgr.update_from_parser(current_proto)
            new_status = mgr.get_fleet_status()
            self.assertEqual(new_status["active_email"], current_proto["email"].strip().lower())
            self.assertIsNotNone(new_status["active_account"])


if __name__ == "__main__":
    unittest.main()
