"""AKShare 数据源实现"""

import logging
from datetime import date, datetime
from typing import List
import pandas as pd

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

from .base import DataSource

logger = logging.getLogger("caisen_data.sources.akshare")

try:
    from caisen.core.bar import Bar
except ImportError:
    Bar = None  # 使用 load() 返回 Bar 列表时需要 caisen 包；load_*_df() 接口无需此依赖

# 期货主力合约代码映射 (新浪期货主力合约符号)
FUTURES_MAIN_CONTRACT = {
    "ag": "ag0",     # 沪银
    "sc": "sc0",     # 原油（INE）
    "m": "m0",       # 豆粕
    "lh": "LH0",     # 生猪
    "au": "au0",     # 黄金
    "cu": "cu0",     # 铜
    "i": "i0",       # 铁矿石
    "rb": "rb0",     # 螺纹钢
    "ru": "ru0",     # 天然橡胶
}

# ETF 代码映射
ETF_CODES = {
    "信创ETF华夏": "588260.SH",
    "上证50ETF华夏": "510650.SH",
}


class AKShareDataSource(DataSource):
    """AKShare 数据源"""

    name = "akshare"
    supports_freq = ["1d", "5m", "15m", "30m", "60m"]

    def load(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str = "1d"
    ) -> List["Bar"]:
        """从 AKShare 加载数据"""
        if not HAS_AKSHARE:
            raise ImportError("akshare not installed. Run: pip install akshare")

        # 判断是期货还是股票
        if symbol in FUTURES_MAIN_CONTRACT:
            return self._load_futures(symbol, start, end, freq)
        else:
            return self._load_stock(symbol, start, end, freq)

    def _load_stock(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str
    ) -> List["Bar"]:
        """加载股票数据（仅支持日线）"""
        if Bar is None:
            raise ImportError(
                "caisen 未安装，无法使用 load() 返回 Bar 对象。"
                "请运行: pip install caisen，或使用 load_stock_df() 获取 DataFrame"
            )
        df = self.load_stock_df(symbol, start, end, freq)
        return self._df_to_bars(df, symbol, freq)

    def _load_futures(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str
    ) -> List["Bar"]:
        """加载期货数据（支持日线和分钟）"""
        if Bar is None:
            raise ImportError(
                "caisen 未安装，无法使用 load() 返回 Bar 对象。"
                "请运行: pip install caisen，或使用 load_futures_df() 获取 DataFrame"
            )
        df = self.load_futures_df(symbol, start, end, freq)
        return self._df_to_bars(df, symbol, freq)

    @staticmethod
    def _normalize_df_columns(df: pd.DataFrame) -> pd.DataFrame:
        """统一不同 AKShare API 返回的列名为标准 OHLCV 格式"""
        col_map = {
            "日期": "timestamp", "时间": "timestamp", "datetime": "timestamp",
            "开盘价": "open", "开盘": "open", "今开": "open",
            "最高价": "high", "最高": "high",
            "最低价": "low", "最低": "low",
            "收盘价": "close", "收盘": "close",
            "成交量": "volume", "成交": "volume",
        }
        result = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # 确保 timestamp 为 datetime 类型
        if "timestamp" in result.columns:
            result["timestamp"] = pd.to_datetime(result["timestamp"])

        # volume 列可能缺失，填充为 0
        if "volume" not in result.columns:
            result["volume"] = 0.0

        return result

    def load_stock_df(
        self, symbol: str, start: date, end: date, freq: str = "1d"
    ) -> pd.DataFrame:
        """加载股票数据，返回 DataFrame（无需 caisen 依赖）

        Args:
            symbol: 股票代码，如 "000001.SZ"
            start: 开始日期
            end: 结束日期
            freq: 频率（仅支持 "1d"）

        Returns:
            包含 timestamp/open/high/low/close/volume 列的 DataFrame
        """
        if not HAS_AKSHARE:
            raise ImportError("akshare not installed. Run: pip install akshare")
        if freq != "1d":
            raise ValueError(f"股票数据仅支持日线 (1d)，当前请求: {freq}")

        df = ak.stock_zh_a_hist(
            symbol=symbol.replace(".SZ", "").replace(".SH", ""),
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
        result = self._normalize_df_columns(df)
        result["symbol"] = symbol
        result["freq"] = freq
        cols = ["timestamp", "symbol", "freq", "open", "high", "low", "close", "volume"]
        return result[[c for c in cols if c in result.columns]]

    def load_futures_df(
        self, symbol: str, start: date, end: date, freq: str = "1d"
    ) -> pd.DataFrame:
        """加载期货数据，返回 DataFrame（无需 caisen 依赖）

        Args:
            symbol: 期货代码，如 "ag", "m", "lh"
            start: 开始日期
            end: 结束日期
            freq: 频率，支持 "1d", "5m", "15m", "30m", "60m"

        Returns:
            包含 timestamp/open/high/low/close/volume 列的 DataFrame
        """
        if not HAS_AKSHARE:
            raise ImportError("akshare not installed. Run: pip install akshare")

        futures_code = FUTURES_MAIN_CONTRACT.get(symbol, symbol)

        if freq == "1d":
            df = ak.futures_main_sina(
                symbol=futures_code,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
            )
        else:
            period_map = {"5m": "5", "15m": "15", "30m": "30", "60m": "60"}
            period = period_map.get(freq, "5")
            df = ak.futures_zh_minute_sina(symbol=futures_code, period=period)

        result = self._normalize_df_columns(df)
        result["symbol"] = symbol
        result["freq"] = freq
        cols = ["timestamp", "symbol", "freq", "open", "high", "low", "close", "volume"]
        result = result[[c for c in cols if c in result.columns]]

        # 分钟数据需要按日期范围过滤（日线已在 API 调用时过滤）
        if freq != "1d" and "timestamp" in result.columns:
            result = result[
                (result["timestamp"] >= pd.Timestamp(start))
                & (result["timestamp"] <= pd.Timestamp(end) + pd.Timedelta(days=1))
            ].reset_index(drop=True)

        return result

    def _df_to_bars(self, df: pd.DataFrame, symbol: str, freq: str) -> List["Bar"]:
        """DataFrame 转 Bar 列表（优化版：列式处理代替逐行迭代）"""
        if Bar is None:
            raise ImportError(
                "caisen 未安装，无法构造 Bar 对象。请运行: pip install caisen"
            )

        norm_df = self._normalize_df_columns(df)

        # 预先提取列为 numpy 数组，避免 iterrows 的逐行字典构造开销
        timestamps = pd.to_datetime(norm_df.get("timestamp", pd.Series(dtype="datetime64[ns]")))
        opens = pd.to_numeric(norm_df.get("open", pd.Series(dtype=float)), errors="coerce").fillna(0)
        highs = pd.to_numeric(norm_df.get("high", pd.Series(dtype=float)), errors="coerce").fillna(0)
        lows = pd.to_numeric(norm_df.get("low", pd.Series(dtype=float)), errors="coerce").fillna(0)
        closes = pd.to_numeric(norm_df.get("close", pd.Series(dtype=float)), errors="coerce").fillna(0)
        volumes = pd.to_numeric(norm_df.get("volume", pd.Series(dtype=float)), errors="coerce").fillna(0)

        bars: List["Bar"] = []
        for i in range(len(norm_df)):
            ts = timestamps.iloc[i]
            close_val = closes.iloc[i]
            if pd.isna(ts) or pd.isna(close_val):
                continue
            bars.append(Bar(
                timestamp=ts.to_pydatetime(),
                symbol=symbol,
                freq=freq,
                open=float(opens.iloc[i]),
                high=float(highs.iloc[i]),
                low=float(lows.iloc[i]),
                close=float(close_val),
                volume=float(volumes.iloc[i]),
            ))
        return bars

    def list_symbols(self) -> List[str]:
        """获取 A 股列表"""
        if not HAS_AKSHARE:
            logger.warning("akshare 未安装，无法列出标的")
            return []

        try:
            df = ak.stock_info_a_code_name()
            symbols = []
            for _, row in df.iterrows():
                code = str(row["code"])
                if code.startswith("0") or code.startswith("3"):
                    symbols.append(f"{code}.SZ")
                else:
                    symbols.append(f"{code}.SH")
            return symbols
        except Exception as e:
            logger.error("获取 A 股列表失败: %s", e)
            return []