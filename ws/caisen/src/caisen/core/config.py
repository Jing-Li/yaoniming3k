"""配置数据类型"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 100000
    commission_rate: float = 0.0003
    slippage: float = 0.001


@dataclass
class StrategyConfig:
    """策略配置"""
    name: str = ""
    file: str = ""  # 策略文件路径
    type: str = "code"  # code 或 llm
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataConfig:
    """数据配置"""
    symbol: str = ""
    freq: str = "1d"
    start: str = ""
    end: str = ""
    data_dir: str = "./data"


@dataclass
class LLMStrategyConfig:
    """LLM 策略配置"""
    provider: str = "openai"
    model: str = "gpt-4"
    prompt: str = ""
    cache_enabled: bool = True
    cache_max_size: int = 10000


@dataclass
class Config:
    """完整配置"""
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    data: DataConfig = field(default_factory=DataConfig)
    llm: Optional[LLMStrategyConfig] = None
    mode: str = "code"  # code 或 llm
    output_dir: str = "./runs"

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """从 YAML 文件加载"""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """从字典创建"""
        backtest = BacktestConfig(**data.get("backtest", {}))
        strategy = StrategyConfig(**data.get("strategy", {}))
        data_cfg = DataConfig(**data.get("data", {}))
        llm = None
        if "llm" in data:
            llm = LLMStrategyConfig(**data["llm"])
        return cls(
            backtest=backtest,
            strategy=strategy,
            data=data_cfg,
            llm=llm,
            mode=data.get("mode", "code"),
            output_dir=data.get("output_dir", "./runs"),
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "backtest": self.backtest.__dict__,
            "strategy": self.strategy.__dict__,
            "data": self.data.__dict__,
            "llm": self.llm.__dict__ if self.llm else None,
            "mode": self.mode,
            "output_dir": self.output_dir,
        }