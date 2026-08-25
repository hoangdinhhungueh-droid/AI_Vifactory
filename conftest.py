"""
Pytest root conftest cho VF pipeline (Pha 5.2 - test harness).

Vai tro chinh:
1. Dam bao project root (/root/video_factory) nam trong sys.path de cac test
   import duoc `app.services.*`. Vi tests/ khong co __init__.py, pytest chi
   prepend `tests/` vao sys.path -> can conftest o root de bo sung.
2. Cung cap mot so fixture co ban dung chung (opt-in, KHONG autouse de tranh
   thay doi hanh vi cac test hien co): project_root, tmp_workspace,
   mock_config, mock_api_client.

Chua co fixture nao duoc port tu code cu, cac fixture duoi day la toi thieu -
mo rong khi can.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Duong dan goc repo."""
    return PROJECT_ROOT


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Thu muc lam viec tam thoi, tu dong don sau moi test."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def mock_config() -> dict:
    """Config toi thieu cho test, khong chua secret thuc te."""
    return {
        "env": "test",
        "dry_run": True,
        "telegram": {"enabled": False, "token": "TEST_TOKEN", "chat_id": "0"},
        "notion": {"enabled": False, "token": "TEST_TOKEN"},
        "tts": {"provider": "edge", "voice": "vi-VN-NamMinhNeural"},
        "render": {"aspect": "9:16", "fps": 30},
    }


@pytest.fixture
def mock_api_client() -> MagicMock:
    """Client HTTP gia lap - dung de chan goi mang thuc trong unit test."""
    client = MagicMock(name="mock_api_client")
    client.get.return_value = MagicMock(status_code=200, json=lambda: {})
    client.post.return_value = MagicMock(status_code=200, json=lambda: {})
    return client
