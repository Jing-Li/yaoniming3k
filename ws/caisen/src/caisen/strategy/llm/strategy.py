"""LLMStrategy - LLM 驱动的交易策略（递增窗口预计算架构）"""

from typing import List, Optional, TYPE_CHECKING
import os

from caisen.strategy.base import Strategy, Annotation, BarResult

if TYPE_CHECKING:
    from caisen.core.bar import Bar
    from caisen.core.order import Order
    from caisen.core.config import BacktestConfig, LLMStrategyConfig
    from caisen.data.source import DataSource


class LLMStrategy(Strategy):
    """LLM 驱动的策略

    采用递增窗口预计算模式：
    1. on_init 时逐根 K 线调用 LLM（bars[0:i+1]），预计算 MA5/MA20
    2. 每根 bar 只取当前 bar 的信号，收集窗口内所有标注（去重）
    3. 缓存 signals 和 annotations
    4. on_bar 逐帧回放，查缓存返回 Order

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
        self._annotations_emitted = False  # 标注是否已随 BarResult 发出

        # Walk-forward 配置
        self._walk_forward = getattr(config, 'walk_forward', True) if config else True

    def _create_client_from_config(self, config: "LLMStrategyConfig"):
        """根据配置创建 LLM 客户端"""
        from .provider import OpenAIProvider

        api_key = config.api_key
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, "")

        # 读取 provider 扩展参数（disable_thinking, max_tokens 等）
        provider_kwargs = {}
        if hasattr(config, '_provider_kwargs'):
            provider_kwargs = config._provider_kwargs

        if config.provider == "openai":
            return OpenAIProvider(
                api_key=api_key,
                model=config.model,
                temperature=config.temperature,
                base_url=config.base_url or "https://api.openai.com/v1",
                **provider_kwargs,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

    def _create_prompt_builder_from_config(self, config: "LLMStrategyConfig"):
        """根据配置创建 PromptBuilder"""
        from .prompt import PromptBuilder
        from pathlib import Path
        import logging

        rules = config.rules

        # 进化闭环：自动加载进化后的规则文件
        if config.evolved_rules_path:
            evolved_path = Path(config.evolved_rules_path)
            if evolved_path.exists():
                rules = evolved_path.read_text(encoding="utf-8")
                logging.getLogger(__name__).info(
                    f"已加载进化规则: {evolved_path} ({len(rules)} chars)"
                )

        return PromptBuilder(
            rules=rules,
            examples_count=config.examples
        )

    def analyze(self, bars, batch_size: int = 50) -> "LLMResult":
        """分析 K 线数据

        支持两种模式：
        - walk_forward=True（默认）：逐根滚动窗口，每根 K 线只看历史数据，消除未来数据泄漏
        - walk_forward=False：批量发送所有数据（快但有未来数据泄漏，仅用于快速验证）

        预计算 MA5/MA20 并注入 bar 数据，让 LLM 有准确的趋势参考。

        Args:
            bars: K 线数据列表
            batch_size: walk_forward=False 时每批最多处理的 K 线数量

        Returns:
            LLMResult: 包含 signals 和 annotations
        """
        if self.prompt_builder is None:
            raise ValueError("prompt_builder is required")
        if self.llm_client is None:
            raise ValueError("llm_client is required")

        from .client import LLMResult

        # 预计算 MA5 / MA20，注入到 bar dict 供 LLM 参考
        enriched = self._enrich_bars_with_ma(bars)

        if self._walk_forward:
            return self._analyze_walk_forward(enriched)
        else:
            return self._analyze_batch(enriched, batch_size)

    def _analyze_walk_forward(self, enriched: list) -> "LLMResult":
        """递增窗口模式：逐根分析，每根 K 线看到从第一根到当前的完整历史

        对第 i 根 K 线，发送 bars[0:i+1] 给 LLM，
        取最后一根的信号，收集窗口内所有标注（timestamp 去重）。
        确保无未来数据泄漏，且标注与信号同源。
        """
        from .client import LLMResult
        import logging

        logger = logging.getLogger(__name__)
        all_signals: list = []
        all_annotations: list = []
        seen_annotation_keys: set = set()
        total = len(enriched)

        logger.info(f"递增窗口模式：逐根分析 {total} 根 K 线")

        for i in range(total):
            # 递增窗口：从第一根到当前根
            window = enriched[:i + 1]

            prompt = self.prompt_builder.build(window)
            response = self.llm_client.call(prompt)
            result = self.response_parser.parse(response)

            # 只取最后一根 K 线（当前 bar）的信号
            current_ts = window[-1].get("timestamp", "")
            for sig in result.signals:
                if sig.get("timestamp") == current_ts:
                    all_signals.append(sig)

            # 收集窗口内所有标注（timestamp+type 去重）
            for ann in result.annotations:
                ann_key = (ann.get("timestamp", ""), ann.get("type", ""))
                if ann_key not in seen_annotation_keys:
                    seen_annotation_keys.add(ann_key)
                    all_annotations.append(ann)

            # 进度日志
            if (i + 1) % 10 == 0 or i + 1 == total:
                logger.info(f"  进度: {i + 1}/{total} ({(i + 1) * 100 // total}%)")

        logger.info(f"递增窗口完成：{len(all_signals)} signals, {len(all_annotations)} annotations")
        return LLMResult(signals=all_signals, annotations=all_annotations)

    def _analyze_batch(self, enriched: list, batch_size: int) -> "LLMResult":
        """批量模式：一次性发送所有数据（快速但有未来数据泄漏）"""
        from .client import LLMResult
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("批量模式：LLM 可看到未来数据，回测结果仅供快速验证参考")

        all_signals: list = []
        all_annotations: list = []

        for i in range(0, len(enriched), batch_size):
            batch = enriched[i:i + batch_size]
            prompt = self.prompt_builder.build(batch)
            response = self.llm_client.call(prompt)
            result = self.response_parser.parse(response)
            all_signals.extend(result.signals)
            all_annotations.extend(result.annotations)

        return LLMResult(signals=all_signals, annotations=all_annotations)

    @staticmethod
    def _enrich_bars_with_ma(bars) -> list:
        """预计算 MA5/MA20 并返回 enriched dict 列表"""
        closes = []
        enriched = []
        for i, bar in enumerate(bars):
            c = bar.close if hasattr(bar, 'close') else bar.get('close', 0)
            closes.append(c)

            if hasattr(bar, 'to_dict'):
                d = bar.to_dict()
            elif isinstance(bar, dict):
                d = dict(bar)
            else:
                d = {
                    "timestamp": str(bar.timestamp) if hasattr(bar, 'timestamp') else str(bar),
                    "open": getattr(bar, 'open', 0),
                    "high": getattr(bar, 'high', 0),
                    "low": getattr(bar, 'low', 0),
                    "close": c,
                    "volume": getattr(bar, 'volume', 0),
                }

            # MA5
            if i >= 4:
                d["ma5"] = round(sum(closes[i-4:i+1]) / 5, 2)
            # MA20
            if i >= 19:
                d["ma20"] = round(sum(closes[i-19:i+1]) / 20, 2)

            enriched.append(d)
        return enriched

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

    def on_bar(self, bar: "Bar") -> "BarResult":
        """每根 K 线调用，返回 BarResult

        第一次调用时附带所有缓存标注（LLM 在 on_init 阶段预计算）。
        """
        from caisen.core.order import Order, Side
        from caisen.strategy.base import AnnotationType
        from datetime import datetime

        # 第一次调用时一次性发出所有标注
        annotations = []
        if not self._annotations_emitted:
            self._annotations_emitted = True
            for raw in self.cache.get_annotations():
                ts = raw.get("timestamp", "")
                type_str = raw.get("type", "neutral_signal")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                try:
                    ann_type = AnnotationType(type_str)
                except ValueError:
                    import warnings
                    warnings.warn(
                        f"LLM 返回了未知 annotation type: '{type_str}'，已降级为 text_label",
                        stacklevel=2
                    )
                    ann_type = AnnotationType.TEXT_LABEL
                annotations.append(Annotation(
                    type=ann_type,
                    timestamp=ts,
                    data=raw.get("data", {})
                ))

        # 查缓存获取信号
        ts_key = bar.timestamp.strftime("%Y-%m-%d")
        action = self.cache.get(ts_key)

        order = None
        if action == "buy" and self.position == 0:
            self.position = 1
            order = Order(symbol=bar.symbol, side=Side.BUY)
        elif action == "sell" and self.position == 1:
            self.position = 0
            order = Order(symbol=bar.symbol, side=Side.SELL)

        return BarResult(order=order, annotations=annotations)

    def on_session_end(self) -> None:
        """回测结束后调用"""
        pass

    def reset(self) -> None:
        """重置策略状态"""
        self.position = 0
        self._bars = []
        self._annotations_emitted = False