"""LLMStrategy - LLM 驱动的交易策略（离线预计算架构）"""

from typing import List, Optional, TYPE_CHECKING
import os

from caisen.strategy.base import Strategy, Annotation

if TYPE_CHECKING:
    from caisen.core.bar import Bar
    from caisen.core.order import Order
    from caisen.core.config import BacktestConfig, LLMStrategyConfig
    from caisen.data.source import DataSource


class LLMStrategy(Strategy):
    """LLM 驱动的策略

    采用离线预计算模式：
    1. on_init 时一次性获取所有数据，调用 LLM 分析
    2. 缓存 signals 和 annotations
    3. on_bar 逐帧回放，查缓存返回 Order

    组件组合（简化后）：
    - PromptBuilder: 构建 prompt
    - LLMClient: 调用 LLM API
    - ResponseParser: 解析响应
    - DataSource: 数据加载（通过依赖注入）
    """

    def __init__(
        self,
        llm_client=None,
        config: "LLMStrategyConfig" = None,
        prompt_builder=None,
        response_parser=None,
        data_source: "DataSource" = None
    ):
        """初始化

        Args:
            llm_client: LLM 客户端，需实现 call(prompt) -> str
            config: LLM 策略配置
            prompt_builder: Prompt 构建器（可选）
            response_parser: 响应解析器（可选）
            data_source: 数据源（可选，用于注入自定义数据源）
        """
        from .cache import SignalCache
        from .prompt import PromptBuilder
        from .response import ResponseParser

        self.llm_client = llm_client
        self.config = config
        self.prompt_builder = prompt_builder
        self.response_parser = response_parser or ResponseParser()
        self.data_source = data_source

        # 如果没有提供 client，根据配置创建
        if self.llm_client is None and config is not None:
            self.llm_client = self._create_client_from_config(config)

        # 如果没有提供 prompt_builder，根据配置创建
        if self.prompt_builder is None and config is not None:
            self.prompt_builder = self._create_prompt_builder_from_config(config)

        self.position = 0  # 0=空仓, 1=持仓
        self._bars = []  # 保存所有 bar 用于后续处理
        self.cache = SignalCache()
        self._annotations_returned = False  # 跟踪是否已返回标注

    def _create_client_from_config(self, config: "LLMStrategyConfig"):
        """根据配置创建 LLM 客户端"""
        from .provider import OpenAIProvider

        api_key = config.api_key
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, "")

        if config.provider == "openai":
            return OpenAIProvider(
                api_key=api_key,
                model=config.model,
                temperature=config.temperature,
                base_url=config.base_url or "https://api.openai.com/v1"
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

    def _create_prompt_builder_from_config(self, config: "LLMStrategyConfig"):
        """根据配置创建 PromptBuilder"""
        from .prompt import PromptBuilder

        return PromptBuilder(
            rules=config.rules,
            examples_count=config.examples
        )

    def analyze(self, bars) -> "LLMResult":
        """分析 K 线数据（组合三个组件）

        Args:
            bars: K 线数据列表

        Returns:
            LLMResult: 包含 signals 和 annotations
        """
        if self.prompt_builder is None:
            raise ValueError("prompt_builder is required")
        if self.llm_client is None:
            raise ValueError("llm_client is required")

        prompt = self.prompt_builder.build(bars)
        response = self.llm_client.call(prompt)
        return self.response_parser.parse(response)

    def on_init(self, config: "BacktestConfig") -> None:
        """回测开始前调用

        一次性获取所有数据，调用 LLM 分析，缓存结果

        Args:
            config: BacktestConfig，包含 data_dir, symbol, start, end, freq
        """
        # 如果没有缓存的 bars，从数据源加载
        if not self._bars:
            # 优先使用注入的数据源
            if self.data_source is not None:
                from caisen.data.config import DataConfig
                data_config = DataConfig(
                    symbol=config.symbol if hasattr(config, 'symbol') else "UNKNOWN",
                    freq=config.freq if hasattr(config, 'freq') else "1d",
                    start=config.start if hasattr(config, 'start') else "",
                    end=config.end if hasattr(config, 'end') else "",
                    data_dir=getattr(config, 'data_dir', '')
                )
                self._bars = self.data_source.load(data_config)
            elif hasattr(config, 'data_dir') and hasattr(config, 'symbol'):
                from caisen.data.local_source import LocalDataSource
                from caisen.data.config import DataConfig

                data_config = DataConfig(
                    symbol=config.symbol if hasattr(config, 'symbol') else "UNKNOWN",
                    freq=config.freq if hasattr(config, 'freq') else "1d",
                    start=config.start if hasattr(config, 'start') else "",
                    end=config.end if hasattr(config, 'end') else "",
                    data_dir=config.data_dir
                )
                data_source = LocalDataSource(config.data_dir)
                self._bars = data_source.load(data_config)
            else:
                # config 没有数据信息，无法加载，跳过
                return

        # 如果仍然没有 bars，跳过
        if not self._bars:
            return

        # 调用 LLM 分析
        result = self.analyze(self._bars)

        # 缓存 signals
        self.cache.index_signals(result.signals)
        self.cache.set_annotations(result.annotations)

    def on_bar(self, bar: "Bar") -> Optional["Order"]:
        """每根 K 线调用

        查缓存获取信号，返回对应的 Order
        """
        from caisen.core.order import Order, Side

        # 获取时间戳字符串
        ts = bar.timestamp.strftime("%Y-%m-%d")

        # 查缓存获取信号
        action = self.cache.get(ts)

        # 根据信号和持仓状态决定是否下单
        if action == "buy" and self.position == 0:
            self.position = 1
            return Order(symbol=bar.symbol, side=Side.BUY)
        elif action == "sell" and self.position == 1:
            self.position = 0
            return Order(symbol=bar.symbol, side=Side.SELL)

        # hold 或状态不匹配，返回 None
        return None

    def on_session_end(self) -> None:
        """回测结束后调用"""
        pass

    def get_annotations(self) -> List[Annotation]:
        """获取可视化标注

        注意：每个标注只返回一次，避免重复
        """
        if self._annotations_returned:
            return []

        self._annotations_returned = True

        from caisen.strategy.base import Annotation as BaseAnnotation, AnnotationType
        from datetime import datetime

        annotations = []
        for ann in self.cache.get_annotations():
            ts = ann.get("timestamp", "")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            annotations.append(BaseAnnotation(
                type=AnnotationType(ann.get("type", "neutral_signal")),
                timestamp=ts,
                data=ann.get("data", {})
            ))
        return annotations

    def reset(self) -> None:
        """重置策略状态"""
        self.position = 0
        self._bars = []