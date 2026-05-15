"""测试蔡森策略"""

from datetime import datetime
from caisen.core.bar import Bar
from caisen.core.order import Side
from caisen.strategy.cai_sen import CaiSenStrategy


def make_bar(idx: int, open_p: float, high: float, low: float, close: float, volume: float = 1000) -> Bar:
    """创建测试K线"""
    return Bar(
        timestamp=datetime(2024, 1, 1),
        symbol="TEST",
        open=open_p,
        high=high,
        low=low,
        close=close,
        volume=volume
    )


def test_platform_detection():
    """测试整理平台检测 - 10根K线在3%振幅内波动"""
    strategy = CaiSenStrategy(platform_min_bars=10, platform_max_amplitude=0.05)
    
    # 生成10根横盘K线（价格在100±1.5，振幅3%）
    base_price = 100.0
    for i in range(10):
        bar = make_bar(i, base_price, 101.5, 98.5, base_price + (i % 3 - 1))
        order = strategy.on_bar(bar)
        assert order is None  # 前9根不应产生信号
    
    # 第10根后应检测到整理平台
    assert strategy.platform is not None
    assert strategy.platform.duration() == 10
    assert strategy.platform.amplitude_pct() <= 0.05


def test_breakdown_pullback_buy_signal():
    """测试破底翻产生第一买点信号"""
    strategy = CaiSenStrategy(platform_min_bars=5, platform_max_amplitude=0.05)
    
    # 1. 形成整理平台（5根K线，价格100±1）
    for i in range(5):
        bar = make_bar(i, 100, 101, 99, 100)
        strategy.on_bar(bar)
    
    assert strategy.platform is not None
    platform_lower = strategy.platform.lower  # 约99
    platform_upper = strategy.platform.upper  # 约101
    
    # 2. 破底（跌破平台下沿1%）
    breakdown_price = platform_lower * 0.99  # 约98
    bar_breakdown = make_bar(5, 100, 100, breakdown_price * 0.998, breakdown_price, volume=2000)
    order = strategy.on_bar(bar_breakdown)
    assert order is None  # 破底时不应产生信号
    
    # 3. 拉回（站回平台下沿之上）
    pullback_price = platform_lower * 1.005  # 约99.5
    bar_pullback = make_bar(6, breakdown_price, pullback_price * 1.01, breakdown_price * 0.995, pullback_price, volume=2500)
    order = strategy.on_bar(bar_pullback)
    
    # 应产生第一买点买入信号
    assert order is not None
    assert order.side == Side.BUY
    
    # 验证信号记录
    assert len(strategy.signals) == 1
    signal = strategy.signals[0]
    assert signal.action == "BUY_1"
    assert "破底翻" in signal.reason


def test_breakout_second_buy_signal():
    """测试突破平台上沿产生第二买点"""
    strategy = CaiSenStrategy(platform_min_bars=5, platform_max_amplitude=0.05)
    
    # 1. 形成整理平台
    for i in range(5):
        bar = make_bar(i, 100, 101, 99, 100)
        strategy.on_bar(bar)
    
    platform_upper = strategy.platform.upper
    platform_lower = strategy.platform.lower
    
    # 2. 破底
    breakdown_price = platform_lower * 0.99
    strategy.on_bar(make_bar(5, 100, 100, breakdown_price * 0.998, breakdown_price, volume=2000))
    
    # 3. 拉回（第一买点）
    strategy.on_bar(make_bar(6, breakdown_price, platform_lower * 1.02, breakdown_price * 0.995, platform_lower * 1.01, volume=2500))
    assert strategy.position == 1
    
    # 4. 突破平台上沿（第二买点）
    breakout_price = platform_upper * 1.02
    bar_breakout = make_bar(7, platform_lower * 1.01, breakout_price * 1.01, platform_upper * 0.995, breakout_price, volume=3000)
    order = strategy.on_bar(bar_breakout)
    
    assert order is not None
    assert order.side == Side.BUY
    assert strategy.position == 2
    
    # 验证第二买点信号
    assert len(strategy.signals) == 2
    signal = strategy.signals[1]
    assert signal.action == "BUY_2"
    assert "第二买点" in signal.reason


def test_target_calculation():
    """测试等幅测距目标价计算"""
    strategy = CaiSenStrategy(platform_min_bars=5, platform_max_amplitude=0.05)
    
    # 设置平台：上沿102，下沿98
    for i in range(5):
        bar = make_bar(i, 100, 102, 98, 100)
        strategy.on_bar(bar)
    
    # 破底到95
    strategy.breakdown_low = 95.0
    
    # 等幅测距：平台下沿(98) - 破底低点(95) = 3
    # 目标价 = 平台上沿(102) + 3 = 105
    target = strategy._calculate_target()
    assert target == 105.0


def test_stop_loss():
    """测试止损逻辑"""
    strategy = CaiSenStrategy(platform_min_bars=5, platform_max_amplitude=0.05)
    
    # 形成平台并触发第一买点
    for i in range(5):
        bar = make_bar(i, 100, 101, 99, 100)
        strategy.on_bar(bar)
    
    platform_lower = strategy.platform.lower
    breakdown_price = platform_lower * 0.99
    strategy.on_bar(make_bar(5, 100, 100, breakdown_price * 0.998, breakdown_price, volume=2000))
    
    pullback_price = platform_lower * 1.01
    strategy.on_bar(make_bar(6, breakdown_price, pullback_price * 1.01, breakdown_price * 0.995, pullback_price, volume=2500))
    
    # 记录止损位
    stop_loss = strategy.stop_loss
    
    # 价格跌破止损位，应产生卖出信号
    stop_trigger_price = stop_loss * 0.99
    bar_stop = make_bar(7, pullback_price, pullback_price * 1.01, stop_trigger_price, stop_trigger_price)
    order = strategy.on_bar(bar_stop)
    
    assert order is not None
    assert order.side == Side.SELL
    assert strategy.position == 0
