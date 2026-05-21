"""Tests for Strategy base classes"""

import pytest
from datetime import datetime
from typing import Optional
from caisen.strategy.base import Strategy, Annotation, AnnotationType
from caisen.core.bar import Bar
from caisen.core.order import Order, Side


class DummyStrategy(Strategy):
    """A concrete strategy implementation for testing"""

    def __init__(self):
        self.call_count = 0
        self.last_bar = None

    def on_bar(self, bar: Bar) -> Optional[Order]:
        self.call_count += 1
        self.last_bar = bar
        return None


class TestStrategy:
    """Tests for Strategy base class"""

    def test_strategy_on_init_does_not_raise(self):
        """Test that on_init can be called without error"""
        strategy = DummyStrategy()
        strategy.on_init(None)  # Should not raise

    def test_strategy_on_bar_abstract(self):
        """Test that Strategy cannot be instantiated directly"""
        with pytest.raises(TypeError):
            Strategy()

    def test_strategy_on_bar_called_with_bar(self):
        """Test that on_bar is called with correct bar"""
        strategy = DummyStrategy()
        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="TEST",
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000.0,
        )
        strategy.on_bar(bar)

        assert strategy.call_count == 1
        assert strategy.last_bar == bar

    def test_strategy_on_session_end(self):
        """Test that on_session_end can be called"""
        strategy = DummyStrategy()
        strategy.on_session_end()  # Should not raise

    def test_strategy_get_annotations_returns_empty_list(self):
        """Test that default get_annotations returns empty list"""
        strategy = DummyStrategy()
        assert strategy.get_annotations() == []

    def test_strategy_reset(self):
        """Test that reset can be called"""
        strategy = DummyStrategy()
        strategy.reset()  # Should not raise


class TestAnnotation:
    """Tests for Annotation class"""

    def test_annotation_creation(self):
        """Test creating an Annotation"""
        annotation = Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 1),
            data={"price": 100.0, "label": "Test"},
        )

        assert annotation.type == AnnotationType.BUY_SIGNAL
        assert annotation.timestamp == datetime(2024, 1, 1)
        assert annotation.data["price"] == 100.0

    def test_annotation_label_property(self):
        """Test label property"""
        annotation = Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 1),
            data={"label": "My Label"},
        )
        assert annotation.label == "My Label"

    def test_annotation_label_property_default(self):
        """Test label property returns empty string when not set"""
        annotation = Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 1),
            data={},
        )
        assert annotation.label == ""

    def test_annotation_color_property(self):
        """Test color property"""
        annotation = Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 1),
            data={"color": "red"},
        )
        assert annotation.color == "red"

    def test_annotation_color_property_default(self):
        """Test color property returns blue when not set"""
        annotation = Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 1),
            data={},
        )
        assert annotation.color == "blue"

    def test_annotation_price_property(self):
        """Test price property"""
        annotation = Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 1),
            data={"price": 123.45},
        )
        assert annotation.price == 123.45

    def test_annotation_price_property_none(self):
        """Test price property returns None when not set"""
        annotation = Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 1),
            data={},
        )
        assert annotation.price is None

    def test_annotation_to_dict(self):
        """Test to_dict serialization"""
        annotation = Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 1),
            data={"price": 100.0},
        )
        result = annotation.to_dict()

        assert result["type"] == "buy_signal"
        assert result["timestamp"] == "2024-01-01T00:00:00"
        assert result["data"]["price"] == 100.0

    def test_annotation_buy_signal_factory(self):
        """Test buy_signal factory method"""
        annotation = Annotation.buy_signal(
            timestamp=datetime(2024, 1, 1),
            price=100.0,
            label="Buy Here",
        )

        assert annotation.type == AnnotationType.BUY_SIGNAL
        assert annotation.price == 100.0
        assert annotation.label == "Buy Here"
        assert annotation.color == "green"

    def test_annotation_sell_signal_factory(self):
        """Test sell_signal factory method"""
        annotation = Annotation.sell_signal(
            timestamp=datetime(2024, 1, 1),
            price=105.0,
            label="Sell Here",
        )

        assert annotation.type == AnnotationType.SELL_SIGNAL
        assert annotation.price == 105.0
        assert annotation.label == "Sell Here"
        assert annotation.color == "red"

    def test_annotation_horizontal_line_factory(self):
        """Test horizontal_line factory method"""
        annotation = Annotation.horizontal_line(
            timestamp=datetime(2024, 1, 1),
            price=100.0,
            label="Support",
        )

        assert annotation.type == AnnotationType.HORIZONTAL_LINE
        assert annotation.price == 100.0
        assert annotation.label == "Support"

    def test_annotation_pattern_mark_factory(self):
        """Test pattern_mark factory method"""
        points = [
            {"timestamp": datetime(2024, 1, 1), "price": 98.0, "label": "Left Bottom"},
            {"timestamp": datetime(2024, 1, 3), "price": 100.0, "label": "Right Bottom"},
        ]
        annotation = Annotation.pattern_mark(
            timestamp=datetime(2024, 1, 5),
            pattern="w_bottom",
            points=points,
            label="W底",
            neckline=101.0,
        )

        assert annotation.type == AnnotationType.PATTERN_MARK
        assert annotation.data["pattern"] == "w_bottom"
        assert len(annotation.data["points"]) == 2
        assert annotation.data["neckline"] == 101.0

    def test_annotation_text_label_factory(self):
        """Test text_label factory method"""
        annotation = Annotation.text_label(
            timestamp=datetime(2024, 1, 1),
            text="Important Note",
            price=100.0,
        )

        assert annotation.type == AnnotationType.TEXT_LABEL
        assert annotation.data["text"] == "Important Note"

    def test_annotation_serialize_datetime(self):
        """Test that datetime in data is serialized"""
        annotation = Annotation(
            type=AnnotationType.PATTERN_MARK,
            timestamp=datetime(2024, 1, 1),
            data={
                "points": [
                    {"timestamp": datetime(2024, 1, 1), "price": 100.0}
                ]
            },
        )
        result = annotation.to_dict()

        # Datetime should be serialized to ISO format
        assert result["data"]["points"][0]["timestamp"] == "2024-01-01T00:00:00"


class TestAnnotationType:
    """Tests for AnnotationType enum"""

    def test_annotation_type_values(self):
        """Test that AnnotationType enum has expected values"""
        assert AnnotationType.BUY_SIGNAL.value == "buy_signal"
        assert AnnotationType.SELL_SIGNAL.value == "sell_signal"
        assert AnnotationType.NEUTRAL_SIGNAL.value == "neutral_signal"
        assert AnnotationType.HORIZONTAL_LINE.value == "horizontal_line"
        assert AnnotationType.TREND_LINE.value == "trend_line"
        assert AnnotationType.FIB_LINE.value == "fib_line"
        assert AnnotationType.SUPPORT_ZONE.value == "support_zone"
        assert AnnotationType.RESISTANCE_ZONE.value == "resistance_zone"
        assert AnnotationType.VOLUME_SPIKE.value == "volume_spike"
        assert AnnotationType.TEXT_LABEL.value == "text_label"
        assert AnnotationType.PATTERN_MARK.value == "pattern_mark"
        assert AnnotationType.RECTANGLE.value == "rectangle"
        assert AnnotationType.POLYGON.value == "polygon"
