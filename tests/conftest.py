import os
import sys
import pytest

# Must set env before any app import
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-used-in-unit-tests"
os.environ["JWT_SECRET"] = "test-secret-minimum-32-bytes-long-hmac"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_TEST_DB = os.path.join(os.path.dirname(__file__), "test_shared.db")

# Patch Config.DB_PATH once before anything imports it
from config import Config
Config.DB_PATH = _TEST_DB


@pytest.fixture(autouse=True)
def fresh_db():
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    from db.init_db import init_db
    init_db()
    yield
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
