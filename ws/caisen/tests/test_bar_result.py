"""BarResult 单元测试。"""

import pytest
from datetime import datetime

from caisen.core.bar_result import BarResult
from caisen.core.order import Order, Side
from caisen.core.annotation import Annotation, AnnotationType
from caisen.strategy.base import BarResult as StrategyBarResult


class TestBarResult:
    """BarResult 数据容器测试。"""

    def test_default_no_action(self):
        result = BarResult()
        assert result.order is None
        assert result.annotations == []

    def test_no_action_factory(self):
        result = BarResult.no_action()
        assert result.order is None
        assert result.annotations == []

    def test_with_order_factory(self):
        order = Order(symbol="TEST", side=Side.BUY, quantity=10)
        result = BarResult.with_order(order)
        assert result.order is order
        assert result.annotations == []

    def test_with_order_and_annotations(self):
        order = Order(symbol="TEST", side=Side.BUY, quantity=10)
        ann = Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 1),
            data={"price": 100},
        )
        result = BarResult.with_order(order, annotations=[ann])
        assert result.order is order
        assert len(result.annotations) == 1
        assert result.annotations[0].type == AnnotationType.BUY_SIGNAL

    def test_annotations_independent_per_instance(self):
        """不同实例的 annotations 列表不共享。"""
        r1 = BarResult()
        r2 = BarResult()
        r1.annotations.append(
            Annotation(type=AnnotationType.TEXT_LABEL, timestamp=datetime(2024, 1, 1), data={})
        )
        assert len(r1.annotations) == 1
        assert len(r2.annotations) == 0

    def test_strategy_base_reexport(self):
        """strategy.base 中 re-export 的 BarResult 与 core 中相同。"""
        assert StrategyBarResult is BarResult
