"""SignalCache - 信号缓存，按时间戳索引"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class SignalCache:
    """缓存 LLM 输出的信号和标注，按时间戳索引"""

    def __init__(self):
        self._signals: Dict[str, str] = {}  # timestamp -> action
        self._annotations: List[dict] = []

    def index_signals(self, signals: List[dict]) -> None:
        """索引信号列表

        Args:
            signals: [{"timestamp": "YYYY-MM-DD", "action": "buy"|"sell"|"hold", ...}, ...]
        """
        self._signals = {}
        for signal in signals:
            ts = signal.get("timestamp")
            if ts:
                self._signals[ts] = signal.get("action", "hold")

    def get(self, timestamp: str) -> str:
        """获取指定时间戳的信号

        Args:
            timestamp: 日期字符串 "YYYY-MM-DD"

        Returns:
            action 字符串，无信号时返回 "hold"
        """
        return self._signals.get(timestamp, "hold")

    def set_annotations(self, annotations: List[dict]) -> None:
        """设置标注列表"""
        self._annotations = annotations

    def get_annotations(self) -> List[dict]:
        """获取标注列表"""
        return self._annotations

    def reset(self) -> None:
        """重置缓存"""
        self._signals = {}
        self._annotations = []

    def save(self, path: str) -> None:
        """保存缓存到文件

        Args:
            path: 文件路径
        """
        data = {
            "signals": [
                {"timestamp": ts, "action": action}
                for ts, action in self._signals.items()
            ],
            "annotations": self._annotations
        }
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        """从文件加载缓存

        Args:
            path: 文件路径
        """
        try:
            with open(path) as f:
                data = json.load(f)

            self._signals = {}
            for item in data.get("signals", []):
                ts = item.get("timestamp")
                if ts:
                    self._signals[ts] = item.get("action", "hold")

            self._annotations = data.get("annotations", [])
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # 静默处理，不存在的文件


class LLMCache:
    """LLM 缓存管理器 - 管理完整回测的缓存"""

    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_key(self, symbol: str, freq: str, start: str, end: str) -> str:
        """生成缓存 key

        Args:
            symbol: 品种代码
            freq: 频率
            start: 开始日期
            end: 结束日期

        Returns:
            缓存 key
        """
        return f"llm_{symbol}_{freq}_{start}_{end}"

    def get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.json"

    def save_result(self, symbol: str, freq: str, start: str, end: str, result) -> None:
        """保存 LLM 结果到缓存

        Args:
            symbol: 品种代码
            freq: 频率
            start: 开始日期
            end: 结束日期
            result: LLMResult 对象
        """
        key = self.generate_key(symbol, freq, start, end)
        cache_path = self.get_cache_path(key)

        data = {
            "signals": result.signals,
            "annotations": result.annotations,
            "meta": {
                "symbol": symbol,
                "freq": freq,
                "start": start,
                "end": end
            }
        }

        with open(cache_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_result(self, symbol: str, freq: str, start: str, end: str):
        """从缓存加载 LLM 结果

        Args:
            symbol: 品种代码
            freq: 频率
            start: 开始日期
            end: 结束日期

        Returns:
            LLMResult 对象，如果缓存不存在返回 None
        """
        from .client import LLMResult

        key = self.generate_key(symbol, freq, start, end)
        cache_path = self.get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                data = json.load(f)

            return LLMResult(
                signals=data.get("signals", []),
                annotations=data.get("annotations", [])
            )
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def clear(self) -> None:
        """清空所有缓存"""
        for cache_file in self.cache_dir.glob("llm_*.json"):
            cache_file.unlink()