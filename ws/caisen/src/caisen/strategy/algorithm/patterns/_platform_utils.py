"""平台识别工具函数

破底翻和假突破检测器共享的整理平台识别逻辑。
"""

from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.bar import Bar


def find_platform(
    bars: List["Bar"],
    lookback_period: int = 30,
    max_amplitude: float = 0.05,
    min_platform_bars: int = 8,
) -> Optional[Tuple[float, float, int, int]]:
    """识别整理平台

    在 lookback 窗口内找高低点趋平的区间（振幅 <= max_amplitude 且长度 >= min_platform_bars）。

    算法：滑动窗口扫描，找振幅最小的最长连续区间。

    Args:
        bars: K线列表
        lookback_period: 回看周期
        max_amplitude: 最大振幅（相对于均价）
        min_platform_bars: 平台最少K线数

    Returns:
        (upper, lower, start_idx, end_idx) 或 None
        start_idx/end_idx 是相对于 bars 列表的绝对索引
    """
    if len(bars) < lookback_period:
        window = bars
    else:
        window = bars[-lookback_period:]

    if len(window) < min_platform_bars:
        return None

    # 滑动窗口寻找最佳平台区间
    best = None
    best_score = -1  # score = length * (1 - amplitude/avg_price)

    offset = len(bars) - len(window)

    for start in range(len(window) - min_platform_bars + 1):
        for end in range(start + min_platform_bars - 1, len(window)):
            segment = window[start : end + 1]
            seg_high = max(b.high for b in segment)
            seg_low = min(b.low for b in segment)
            avg_price = (seg_high + seg_low) / 2

            if avg_price == 0:
                continue

            amplitude = (seg_high - seg_low) / avg_price
            if amplitude > max_amplitude:
                break  # 继续扩大只会增大振幅

            # 评分：越长越好，振幅越小越好
            score = len(segment) * (1.0 - amplitude / max_amplitude)
            if score > best_score:
                best_score = score
                best = (
                    seg_high,
                    seg_low,
                    offset + start,
                    offset + end,
                )

    return best
