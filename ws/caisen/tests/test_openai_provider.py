"""测试 OpenAI LLM Provider"""

import pytest
from unittest.mock import Mock, patch


class TestOpenAIProvider:
    """OpenAI Provider 测试"""

    def test_init_with_api_key(self):
        """测试初始化带 API key"""
        from caisen.strategy.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key-123")

        assert provider.api_key == "test-key-123"
        assert provider.model == "gpt-4o"
        assert provider.temperature == 0.3

    def test_init_with_custom_config(self):
        """测试初始化带自定义配置"""
        from caisen.strategy.llm import OpenAIProvider

        provider = OpenAIProvider(
            api_key="test-key",
            model="gpt-4o-mini",
            temperature=0.7
        )

        assert provider.model == "gpt-4o-mini"
        assert provider.temperature == 0.7

    def test_call_llm_not_implemented(self):
        """测试 call_llm 基类抛出 NotImplementedError"""
        from caisen.strategy.llm.client import LLMClient

        # 直接测试基类的 call_llm
        client = LLMClient(provider_name="test")
        with pytest.raises(NotImplementedError):
            client.call_llm("test prompt")


class TestOpenAIProviderIntegration:
    """OpenAI Provider 集成测试（需要真实 API key）"""

    @pytest.fixture
    def api_key(self):
        """从环境变量获取 API key"""
        import os
        return os.environ.get("OPENAI_API_KEY")

    @pytest.mark.skipif(
        True,  # 跳过，需要真实 API key
        reason="Requires real OpenAI API key"
    )
    def test_real_api_call(self, api_key):
        """测试真实 API 调用（仅在有 API key 时运行）"""
        from caisen.strategy.llm import OpenAIProvider

        provider = OpenAIProvider(api_key=api_key)

        # 简单测试
        prompt = "Output JSON: {\"signals\": [], \"annotations\": []}"
        result = provider.call_llm(prompt)

        assert isinstance(result, str)
        assert "signals" in result