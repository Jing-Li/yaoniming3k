"""测试 LLM 缓存功能"""

import pytest
import json
import tempfile
from pathlib import Path

from caisen.strategy.llm.cache import SignalCache
from caisen.strategy.llm.client import LLMResult


class TestSignalCachePersistence:
    """SignalCache 持久化测试"""

    def test_cache_save_to_file(self):
        """测试缓存保存到文件"""
        cache = SignalCache()
        cache.index_signals([
            {"timestamp": "2024-01-01", "action": "buy"},
            {"timestamp": "2024-01-02", "action": "sell"},
        ])
        cache.set_annotations([
            {"timestamp": "2024-01-01", "type": "buy_signal", "data": {"price": 100}}
        ])

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache.save(f.name)
            cache_path = f.name

        # 验证文件存在
        assert Path(cache_path).exists()

        # 读取内容
        with open(cache_path) as f:
            data = json.load(f)

        assert "signals" in data
        assert len(data["signals"]) == 2
        assert "annotations" in data

        # 清理
        Path(cache_path).unlink()

    def test_cache_load_from_file(self):
        """测试从文件加载缓存"""
        cache = SignalCache()

        # 创建临时缓存文件
        cache_data = {
            "signals": [
                {"timestamp": "2024-01-01", "action": "buy"},
                {"timestamp": "2024-01-03", "action": "hold"},
            ],
            "annotations": [
                {"timestamp": "2024-01-01", "type": "buy_signal", "data": {}}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(cache_data, f)
            cache_path = f.name

        # 加载
        cache.load(cache_path)

        # 验证
        assert cache.get("2024-01-01") == "buy"
        assert cache.get("2024-01-02") == "hold"  # 默认
        assert cache.get("2024-01-03") == "hold"
        assert len(cache.get_annotations()) == 1

        # 清理
        Path(cache_path).unlink()

    def test_cache_file_not_found(self):
        """测试加载不存在的文件"""
        cache = SignalCache()
        cache.load("/nonexistent/path.json")

        # 应该不报错，返回空缓存
        assert cache.get("2024-01-01") == "hold"

    def test_cache_with_confidence_and_reason(self):
        """测试带置信度和原因的缓存"""
        cache = SignalCache()
        cache.index_signals([
            {"timestamp": "2024-01-01", "action": "buy", "confidence": 0.9, "reason": "突破"},
            {"timestamp": "2024-01-02", "action": "hold", "confidence": 0.3},
        ])

        # 保存
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache.save(f.name)
            cache_path = f.name

        # 加载
        cache2 = SignalCache()
        cache2.load(cache_path)

        # 验证
        assert cache2.get("2024-01-01") == "buy"

        # 清理
        Path(cache_path).unlink()


class TestLLMCache:
    """LLM 缓存管理器测试"""

    def test_cache_key_generation(self):
        """测试缓存 key 生成"""
        from caisen.strategy.llm.cache import LLMCache

        cache = LLMCache(cache_dir="./test_cache")

        # 生成 key
        key = cache.generate_key("ag", "1d", "2024-01-01", "2024-12-31")
        assert "ag" in key
        assert "1d" in key

    def test_cache_hit(self):
        """测试缓存命中"""
        from caisen.strategy.llm.cache import LLMCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LLMCache(cache_dir=tmpdir)

            # 模拟 LLM 结果
            result = LLMResult(
                signals=[{"timestamp": "2024-01-01", "action": "buy"}],
                annotations=[{"timestamp": "2024-01-01", "type": "buy_signal", "data": {}}]
            )

            # 保存
            cache.save_result("ag", "1d", "2024-01-01", "2024-12-31", result)

            # 加载
            loaded = cache.load_result("ag", "1d", "2024-01-01", "2024-12-31")

            assert loaded is not None
            assert len(loaded.signals) == 1
            assert loaded.signals[0]["action"] == "buy"

    def test_cache_miss(self):
        """测试缓存未命中"""
        from caisen.strategy.llm.cache import LLMCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LLMCache(cache_dir=tmpdir)

            # 加载不存在的缓存
            loaded = cache.load_result("ag", "1d", "2024-01-01", "2024-12-31")

            assert loaded is None

    def test_cache_clear(self):
        """测试清理缓存"""
        from caisen.strategy.llm.cache import LLMCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LLMCache(cache_dir=tmpdir)

            # 保存缓存
            result = LLMResult(signals=[], annotations=[])
            cache.save_result("ag", "1d", "2024-01-01", "2024-12-31", result)

            # 验证文件存在
            key = cache.generate_key("ag", "1d", "2024-01-01", "2024-12-31")
            assert Path(tmpdir, f"{key}.json").exists()

            # 清理
            cache.clear()

            # 验证文件不存在
            assert not Path(tmpdir, f"{key}.json").exists()