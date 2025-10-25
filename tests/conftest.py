"""
Pytest configuration to exclude slow integration tests
"""
import pytest

collect_ignore_glob = [
    "scenarios/*.py",
    "standalone/*.py",
]
