"""VolumeAnalyzer（量能分析器）- 分阶段量能评估

根据蔡森理论，不同形态阶段对成交量有不同要求：
- 形成期：应缩量（多空均衡、交投清淡）
- 突破/跌破期：应放量（>=1.5倍均量）
- 确认期：持续放量或缩量回踩
"""

from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ....core.bar import Bar


class VolumeAnalyzer:
    """蔡森理论量能分析器 - 分阶段量能评估

    根据蔡森理论，不同形态阶段对成交量有不同要求：
    - 形成期：应缩量（多空均衡、交投清淡）
    - 突破/跌破期：应放量（>=1.5倍均量）
    - 确认期：持续放量或缩量回踩
    """

    def __init__(self, base_period: int = 20, breakout_multiplier: float = 1.5):
        """初始化量能分析器

        Args:
            base_period: 基础均量计算周期
            breakout_multiplier: 突破放量倍数阈值
        """
        self.base_period = base_period
        self.breakout_multiplier = breakout_multiplier

    def get_base_volume(self, bars: List["Bar"], end_idx: int) -> float:
        """计算基础均量（end_idx之前base_period根K线的平均成交量）

        Args:
            bars: K线列表
            end_idx: 计算截止索引（不包含）

        Returns:
            基础均量，若数据不足返回 0.0
        """
        start_idx = max(0, end_idx - self.base_period)
        if start_idx >= end_idx:
            return 0.0

        segment = bars[start_idx:end_idx]
        if not segment:
            return 0.0

        total = sum(b.volume for b in segment)
        return total / len(segment)

    def staged_volume_check(self, bars: List["Bar"], stages: List[Dict]) -> Dict:
        """检查关键阶段的量能递增/递减关系。

        Args:
            bars: K线列表
            stages: 阶段配置列表，格式:
                [
                    {'name': 'formation', 'start_idx': int, 'end_idx': int, 'expect': 'shrink'},
                    {'name': 'breakout', 'start_idx': int, 'end_idx': int, 'expect': 'expand'},
                    {'name': 'confirm', 'start_idx': int, 'end_idx': int, 'expect': 'expand'},
                ]

                expect 取值: 'shrink'（缩量）| 'expand'（放量）| 'progressive'（递增）

        Returns:
            {
                'passed': bool,
                'score': float (0~1),
                'details': {stage_name: {'avg_volume': float, 'ratio_to_base': float, 'passed': bool}}
            }
        """
        if not stages or not bars:
            return {'passed': False, 'score': 0.0, 'details': {}}

        details = {}
        total_score = 0.0
        stage_count = len(stages)

        for stage in stages:
            name = stage['name']
            start_idx = stage['start_idx']
            end_idx = stage['end_idx']
            expect = stage['expect']

            # 计算该阶段的平均成交量
            segment = bars[start_idx:end_idx + 1] if end_idx < len(bars) else bars[start_idx:]
            if not segment:
                details[name] = {'avg_volume': 0.0, 'ratio_to_base': 0.0, 'passed': False}
                continue

            avg_vol = sum(b.volume for b in segment) / len(segment)

            # 计算基础均量（以该阶段起始点之前的数据为基准）
            base_vol = self.get_base_volume(bars, start_idx)
            if base_vol == 0:
                # 无法计算比值时使用阶段均量作为基准
                ratio = 1.0
            else:
                ratio = avg_vol / base_vol

            # 判断是否符合预期
            passed = self._check_stage_expectation(expect, ratio, bars, start_idx, end_idx)

            # 计算该阶段得分
            stage_score = self._calc_stage_score(expect, ratio, bars, start_idx, end_idx)
            total_score += stage_score

            details[name] = {
                'avg_volume': avg_vol,
                'ratio_to_base': ratio,
                'passed': passed,
            }

        overall_score = total_score / stage_count if stage_count > 0 else 0.0
        all_passed = all(d['passed'] for d in details.values()) if details else False

        return {
            'passed': all_passed,
            'score': min(1.0, max(0.0, overall_score)),
            'details': details,
        }

    def grade(self, bars: List["Bar"], breakout_idx: int) -> str:
        """评估突破时的量能等级。

        Args:
            bars: K线列表
            breakout_idx: 突破K线的索引

        Returns:
            'weak' | 'normal' | 'strong'
            - weak: 突破量 < 1.2倍均量
            - normal: 1.2倍 <= 突破量 < 2.0倍均量
            - strong: 突破量 >= 2.0倍均量
        """
        if breakout_idx < 0 or breakout_idx >= len(bars):
            return 'weak'

        breakout_vol = bars[breakout_idx].volume
        base_vol = self.get_base_volume(bars, breakout_idx)

        if base_vol == 0:
            return 'normal'

        ratio = breakout_vol / base_vol

        if ratio >= 2.0:
            return 'strong'
        elif ratio >= 1.2:
            return 'normal'
        else:
            return 'weak'

    def volume_divergence(
        self, bars: List["Bar"], price_new_extreme: bool, direction: str = 'up'
    ) -> bool:
        """检测量价背离。

        Args:
            bars: K线列表（至少需要一定数量的K线）
            price_new_extreme: 价格是否创了新极值
            direction: 方向
                - 'up': 价格创新高但成交量未创新高 → 顶背离
                - 'down': 价格创新低但成交量未创新低 → 底背离

        Returns:
            True 表示存在背离
        """
        if not price_new_extreme or len(bars) < 10:
            return False

        # 将K线分为前半段和后半段比较
        mid = len(bars) // 2
        first_half = bars[:mid]
        second_half = bars[mid:]

        if not first_half or not second_half:
            return False

        if direction == 'up':
            # 顶背离：价格创新高，但成交量未创新高
            first_max_vol = max(b.volume for b in first_half)
            second_max_vol = max(b.volume for b in second_half)
            # 价格创新高但量能未跟上
            return second_max_vol < first_max_vol
        else:
            # 底背离：价格创新低，但成交量未创新低（量萎缩）
            first_max_vol = max(b.volume for b in first_half)
            second_max_vol = max(b.volume for b in second_half)
            # 价格创新低但放量不及之前（恐慌减弱）
            return second_max_vol < first_max_vol

    def progressive_volume(self, bars: List["Bar"], indices: List[int]) -> bool:
        """检查多个关键点的量能是否递增。

        Args:
            bars: K线列表
            indices: 关键K线索引列表（按时间顺序）

        Returns:
            后续量能是否逐步增大
        """
        if len(indices) < 2:
            return False

        volumes = []
        for idx in indices:
            if 0 <= idx < len(bars):
                volumes.append(bars[idx].volume)
            else:
                return False

        # 检查是否严格递增（允许小幅波动，后一个 >= 前一个的90%就算通过）
        for i in range(1, len(volumes)):
            if volumes[i] < volumes[i - 1] * 0.9:
                return False

        # 至少最后一个要大于第一个
        return volumes[-1] > volumes[0]

    def _check_stage_expectation(
        self, expect: str, ratio: float, bars: List["Bar"], start_idx: int, end_idx: int
    ) -> bool:
        """检查阶段量能是否符合预期

        Args:
            expect: 预期类型 ('shrink' | 'expand' | 'progressive')
            ratio: 该阶段均量与基础均量的比值
            bars: K线列表
            start_idx: 阶段起始索引
            end_idx: 阶段结束索引

        Returns:
            是否通过检查
        """
        if expect == 'shrink':
            # 缩量：成交量应低于基础均量（ratio < 1.0）
            return ratio < 1.0
        elif expect == 'expand':
            # 放量：成交量应达到 breakout_multiplier 倍基础均量
            return ratio >= self.breakout_multiplier
        elif expect == 'progressive':
            # 递增：阶段内成交量逐步增大
            actual_end = min(end_idx + 1, len(bars))
            indices = list(range(start_idx, actual_end))
            return self.progressive_volume(bars, indices)
        return False

    def _calc_stage_score(
        self, expect: str, ratio: float, bars: List["Bar"], start_idx: int, end_idx: int
    ) -> float:
        """计算阶段得分（0~1）

        Args:
            expect: 预期类型
            ratio: 该阶段均量与基础均量的比值
            bars: K线列表
            start_idx: 阶段起始索引
            end_idx: 阶段结束索引

        Returns:
            得分 0~1
        """
        if expect == 'shrink':
            # 越缩量得分越高，ratio越小越好
            if ratio >= 1.0:
                return max(0.0, 0.5 - (ratio - 1.0))
            else:
                return min(1.0, 1.0 - ratio * 0.5)
        elif expect == 'expand':
            # 越放量得分越高
            if ratio >= self.breakout_multiplier:
                return min(1.0, ratio / (self.breakout_multiplier * 2))
            else:
                return ratio / self.breakout_multiplier * 0.5
        elif expect == 'progressive':
            actual_end = min(end_idx + 1, len(bars))
            indices = list(range(start_idx, actual_end))
            if self.progressive_volume(bars, indices):
                return 0.8
            return 0.3
        return 0.5
