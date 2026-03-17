import pytest
from pathlib import Path
import json
import time

from ccfddl.cache import CacheManager, get_default_cache


class TestCacheManager:
    @pytest.fixture
    def cache_manager(self, tmp_path):
        return CacheManager(cache_dir=tmp_path, expiry_hours=1)

    def test_init(self, cache_manager, tmp_path):
        assert cache_manager.cache_dir == tmp_path
        assert cache_manager.expiry_hours == 1

    def test_set_and_get(self, cache_manager):
        key = "test_key"
        data = {"name": "test", "value": 123}
        
        cache_manager.set(key, data)
        result = cache_manager.get(key)
        
        assert result == data

    def test_get_nonexistent(self, cache_manager):
        result = cache_manager.get("nonexistent_key")
        assert result is None

    def test_is_cache_valid(self, cache_manager):
        key = "test_key"
        data = {"test": "data"}
        
        assert not cache_manager.is_cache_valid(key)
        
        cache_manager.set(key, data)
        assert cache_manager.is_cache_valid(key)

    def test_clear(self, cache_manager):
        cache_manager.set("key1", {"a": 1})
        cache_manager.set("key2", {"b": 2})
        
        cache_manager.clear()
        
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None

    def test_get_cache_size(self, cache_manager):
        assert cache_manager.get_cache_size() == 0
        
        cache_manager.set("key", {"data": "x" * 100})
        assert cache_manager.get_cache_size() > 0

    def test_expiry(self, tmp_path):
        cache_manager = CacheManager(cache_dir=tmp_path, expiry_hours=0)
        
        key = "test_key"
        data = {"test": "data"}
        
        cache_manager.set(key, data)
        time.sleep(0.1)
        
        result = cache_manager.get(key)
        assert result is None


class TestGetDefaultCache:
    def test_returns_cache_manager(self):
        cache = get_default_cache()
        assert isinstance(cache, CacheManager)

    def test_default_cache_dir(self):
        cache = get_default_cache()
        assert ".cache" in str(cache.cache_dir)