"""AKShare 数据源实现"""

from datetime import date, datetime
from typing import List
import pandas as pd

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

from .base import DataSource

try:
    from caisen.core.bar import Bar
except ImportError:
    Bar = None

# 期货主力合约代码映射 (新浪期货主力合约符号)
FUTURES_MAIN_CONTRACT = {
    "ag": "ag0",     # 沪银
    "m": "m0",       # 豆粕
    "lh": "LH0",     # 生猪
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
        if freq != "1d":
            raise ValueError(f"股票数据仅支持 1d，当前: {freq}")

        df = ak.stock_zh_a_hist(
            symbol=symbol.replace(".SZ", "").replace(".SH", ""),
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq"
        )
        return self._df_to_bars(df, symbol, "1d")

    def _load_futures(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str
    ) -> List["Bar"]:
        """加载期货数据（支持日线和分钟）"""
        futures_code = FUTURES_MAIN_CONTRACT.get(symbol, symbol)

        if freq == "1d":
            # 日线数据
            df = ak.futures_main_sina(
                symbol=futures_code,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
            )
        else:
            # 分钟数据
            period_map = {"5m": "5", "15m": "15", "30m": "30", "60m": "60"}
            period = period_map.get(freq, "5")

            df = ak.futures_zh_minute_sina(
                symbol=futures_code,
                period=period,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
            )

        return self._df_to_bars(df, symbol, freq)

    def _df_to_bars(self, df: pd.DataFrame, symbol: str, freq: str) -> List["Bar"]:
        """DataFrame 转 Bar 列表"""
        bars = []
        for _, row in df.iterrows():
            # 尝试多种可能的列名
            ts = row.get("日期") or row.get("时间") or row.get("datetime")
            open_ = row.get("开盘价") or row.get("开盘") or row.get("open")
            high = row.get("最高价") or row.get("最高") or row.get("high")
            low = row.get("最低价") or row.get("最低") or row.get("low")
            close = row.get("收盘价") or row.get("收盘") or row.get("close")
            volume = row.get("成交量") or row.get("volume") or row.get("成交")

            if ts is None or close is None:
                continue

            bars.append(Bar(
                timestamp=pd.to_datetime(ts).to_pydatetime() if isinstance(ts, str) else ts,
                symbol=symbol,
                freq=freq,
                open=float(open_) if open_ else 0,
                high=float(high) if high else 0,
                low=float(low) if low else 0,
                close=float(close) if close else 0,
                volume=float(volume) if volume else 0,
            ))
        return bars

    def list_symbols(self) -> List[str]:
        """获取 A 股列表"""
        if not HAS_AKSHARE:
            return []

        try:
            df = ak.stock_info_a_code_name()
            symbols = []
            for _, row in df.iterrows():
                code = str(row["code"])
                symbols.append(f"{code}.SZ" if code.startswith("0") or code.startswith("3") else f"{code}.SH")
            return symbols
        except Exception:
            return []