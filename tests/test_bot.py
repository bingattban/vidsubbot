"""
Basic tests for the bot functionality.
"""
import pytest
from pathlib import Path
from utils.validators import validate_url, sanitize_filename


def test_validate_url():
    """Test URL validation."""
    assert validate_url("https://www.youtube.com/watch?v=example") == True
    assert validate_url("https://vimeo.com/123456") == True
    assert validate_url("not_a_url") == False
    assert validate_url("") == False


def test_sanitize_filename():
    """Test filename sanitization."""
    assert sanitize_filename("test/file.txt") == "testfile.txt"
    assert sanitize_filename("hello world.mp4") == "hello_world.mp4"
    assert sanitize_filename("valid_file.mp4") == "valid_file.mp4"


def test_temp_directory():
    """Test temporary directory creation."""
    temp_dir = Path("/tmp/test_bot")
    temp_dir.mkdir(parents=True, exist_ok=True)
    assert temp_dir.exists()
    temp_dir.rmdir()