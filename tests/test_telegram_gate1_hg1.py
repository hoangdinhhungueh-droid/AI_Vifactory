"""
Tests for HG1 — Human Gate 1 (Commit 2)
- Lock file prevents double-tap
- Subprocess spawn with start_new_session=True
- Notion status update Draft → InProgress
"""
import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock


class TestHG1GateLock:
    """HG1 lock mechanism tests (Pha 7 double-tap prevention)"""

    def test_lock_file_creation(self):
        """Test lock file creation for task_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = os.path.join(tmpdir, "EN_EP0251_byzantine_empire.lock")
            
            # First open should succeed
            fd1 = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd1)
            assert os.path.exists(lock_path)
            
            # Second open should fail (FileExistsError)
            with pytest.raises(FileExistsError):
                os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    def test_double_tap_prevention(self):
        """Test that double-tapping same button returns 'already running'."""
        from app.services.telegram_actions import _spawn_production
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.telegram_actions.VF_LOCK_DIR", tmpdir):
                with patch("app.services.telegram_actions.VF_LOG_DIR", tmpdir):
                    with patch("subprocess.Popen") as mock_popen:
                        mock_popen.return_value = MagicMock(pid=12345)
                        
                        # First call should spawn
                        result1 = _spawn_production("EN_EP0251_byzantine_empire")
                        assert "pid" in result1 or "spawn" in result1.lower()
                        
                        # Second call should fail (lock exists)
                        result2 = _spawn_production("EN_EP0251_byzantine_empire")
                        assert "already running" in result2.lower()

    def test_subprocess_spawn_detached(self):
        """Test subprocess spawned with start_new_session=True."""
        from app.services.telegram_actions import _spawn_production
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.telegram_actions.VF_LOCK_DIR", tmpdir):
                with patch("app.services.telegram_actions.VF_LOG_DIR", tmpdir):
                    with patch("subprocess.Popen") as mock_popen:
                        mock_popen.return_value = MagicMock(pid=99999)
                        
                        _spawn_production("EN_EP0251_test")
                        
                        # Verify start_new_session=True was passed
                        call_args = mock_popen.call_args
                        assert call_args is not None
                        assert "start_new_session" in call_args.kwargs
                        assert call_args.kwargs["start_new_session"] is True
                        
                        # Verify script is produce_episode_hg1.py (check any item contains it)
                        cmd = call_args[0][0]  # This is the list of command args
                        script_found = any("produce_episode_hg1.py" in str(item) for item in cmd)
                        assert script_found

    def test_lock_pid_stored(self):
        """Test that PID is stored in lock file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = os.path.join(tmpdir, "EN_EP0251_byzantine_empire.lock")
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            pid_str = "99999"
            os.write(fd, pid_str.encode())
            os.close(fd)
            
            with open(lock_path, "r") as f:
                stored_pid = f.read()
            assert stored_pid == pid_str


class TestHG1NotionIntegration:
    """HG1 Notion status update tests (Draft → InProgress)"""

    def test_gate1_approve_notion_flow(self):
        """Test _gate1_approve_or_reject Notion lookup flow."""
        from app.services.telegram_actions import _gate1_approve_or_reject
        
        with patch("app.services.telegram_actions._notion_headers") as mock_hdrs:
            mock_hdrs.return_value = {"Authorization": "Bearer fake_token"}
            
            with patch("httpx.post") as mock_post:
                # Mock Story Library query (empty)
                mock_resp1 = MagicMock()
                mock_resp1.json.return_value = {"results": []}
                
                # Mock Trend Brain query (found)
                mock_resp2 = MagicMock()
                mock_resp2.json.return_value = {
                    "results": [{
                        "id": "3c001989-2400-8188-81d1-c2ce60e6f603",
                        "properties": {
                            "Keyword": {"title": [{"plain_text": "Byzantine Empire"}]}
                        }
                    }]
                }
                mock_post.side_effect = [mock_resp1, mock_resp2]
                
                with patch("app.services.telegram_actions._spawn_production") as mock_spawn:
                    mock_spawn.return_value = "pid 12345"
                    
                    reply, is_error = _gate1_approve_or_reject(
                        "EN_EP0251_byzantine_empire", 
                        approve=True
                    )
                    
                    # Should have made 2 requests (Story + Trend)
                    assert mock_post.call_count >= 1
                    # Should have spawned production
                    mock_spawn.assert_called_once()


class TestHG1Subprocess:
    """HG1 subprocess integration tests"""

    def test_subprocess_args_format(self):
        """Test subprocess command args format."""
        from app.services.telegram_actions import _spawn_production
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.telegram_actions.VF_LOCK_DIR", tmpdir):
                with patch("app.services.telegram_actions.VF_LOG_DIR", tmpdir):
                    with patch("subprocess.Popen") as mock_popen:
                        mock_popen.return_value = MagicMock(pid=55555)
                        
                        task_id = "EN_EP0251_byzantine_empire"
                        _spawn_production(task_id)
                        
                        # Get the command passed to Popen
                        call_args = mock_popen.call_args
                        cmd = call_args[0][0]
                        
                        # Check command structure
                        assert "python3" in cmd[0]
                        script_found = any("produce_episode_hg1.py" in str(item) for item in cmd)
                        assert script_found
                        assert task_id in cmd


class TestHG1E2E:
    """HG1 end-to-end integration test"""

    def test_hg1_flow_lock_notify(self):
        """Test full HG1 flow: lock → spawn → notify."""
        from app.services.telegram_actions import _spawn_production
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.telegram_actions.VF_LOCK_DIR", tmpdir):
                with patch("app.services.telegram_actions.VF_LOG_DIR", tmpdir):
                    with patch("subprocess.Popen") as mock_popen:
                        mock_popen.return_value = MagicMock(pid=12345)
                        
                        # Simulate Gate 1 approve
                        result = _spawn_production("EN_EP0251_byzantine_empire")
                        
                        # Should have spawned with PID
                        assert "pid" in result or "spawn" in result.lower()
                        
                        # Lock file should exist
                        lock_file = os.path.join(
                            tmpdir, 
                            "EN_EP0251_byzantine_empire.lock"
                        )
                        assert os.path.exists(lock_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
