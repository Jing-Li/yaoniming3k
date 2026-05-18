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
    """测试整理平台检测 - 10根K线在3%振幅内波动，量能退潮"""
    strategy = CaiSenStrategy(platform_min_bars=10, platform_max_amplitude=0.05)

    # 生成10根横盘K线（价格在100±1.5，振幅3%）
    # 量能退潮：前半段成交量高，后半段成交量低
    base_price = 100.0
    for i in range(10):
        # 前半段成交量1000，后半段成交量600（退潮40%）
        volume = 1000 if i < 5 else 600
        bar = make_bar(i, base_price, 101.5, 98.5, base_price + (i % 3 - 1), volume=volume)
        order = strategy.on_bar(bar)
        assert order is None  # 前9根不应产生信号

    # 第10根后应检测到整理平台
    assert strategy.platform is not None
    assert strategy.platform.duration() == 10
    assert strategy.platform.amplitude_pct() <= 0.05


def test_breakdown_pullback_buy_signal():
    """测试破底翻产生第一买点信号"""
    # 禁用量能退潮检查，因为测试数据只有5根K线
    strategy = CaiSenStrategy(platform_min_bars=5, platform_max_amplitude=0.05,
                              platform_volume_decline=False)

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
    strategy = CaiSenStrategy(platform_min_bars=5, platform_max_amplitude=0.05,
                              platform_volume_decline=False)

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
    strategy = CaiSenStrategy(platform_min_bars=5, platform_max_amplitude=0.05,
                              platform_volume_decline=False)

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


def test_w_bottom_pattern():
    """测试W底形态识别"""
    from datetime import timedelta

    # 使用较大的platform_min_bars，使第一个底部不构成平台
    strategy = CaiSenStrategy(platform_min_bars=20, platform_max_amplitude=0.05, w_bottom_enabled=True)

    # W底场景：两个低点，中间有反弹
    # 第一个低点 @ 95，反弹到颈线 @ 100，第二个低点 @ 96，突破颈线

    base_time = datetime(2024, 1, 1)

    # 1. 第一个底部区域（4根K线，不足以形成平台）
    for i in range(4):
        bar = make_bar(i, 96, 98, 94, 95, volume=1000)
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 2. 反弹到颈线
    for i in range(4, 7):
        bar = make_bar(i, 96, 101, 98, 100, volume=800)  # 缩量反弹
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 3. 第二个底部（略高于第一个，缩量）
    for i in range(7, 10):
        bar = make_bar(i, 97, 99, 95, 96, volume=600)  # 缩量筑底
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 4. 突破颈线
    bar_breakout = make_bar(10, 100, 103, 100, 102, volume=1500)  # 放量突破
    bar_breakout.timestamp = base_time + timedelta(days=10)
    order = strategy.on_bar(bar_breakout)

    # 应该产生W底买入信号
    assert order is not None
    assert order.side == Side.BUY

    # 验证信号
    w_signals = [s for s in strategy.signals if "W底" in s.reason]
    assert len(w_signals) >= 1


def test_m_top_pattern():
    """测试M头形态识别"""
    from datetime import timedelta

    # 使用较大的platform_min_bars，使第一个顶部不构成平台
    strategy = CaiSenStrategy(platform_min_bars=20, platform_max_amplitude=0.05, m_top_enabled=True)

    # M头场景：两个高点，中间有回调
    # 第一个高点 @ 105，回调到颈线 @ 100，第二个高点 @ 104，跌破颈线

    base_time = datetime(2024, 1, 1)

    # 1. 第一个顶部区域（4根K线，不足以形成平台）
    for i in range(4):
        bar = make_bar(i, 104, 106, 102, 105, volume=1000)
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 2. 回调到颈线
    for i in range(4, 7):
        bar = make_bar(i, 102, 101, 99, 100, volume=800)  # 缩量回调
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 3. 第二个顶部（略低于第一个，缩量）
    for i in range(7, 10):
        bar = make_bar(i, 103, 105, 101, 104, volume=600)  # 缩量筑顶
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 4. 跌破颈线
    bar_breakdown = make_bar(10, 100, 99, 98, 98, volume=1500)  # 放量跌破
    bar_breakdown.timestamp = base_time + timedelta(days=10)
    order = strategy.on_bar(bar_breakdown)

    # 应该产生M头卖出信号
    assert order is not None
    assert order.side == Side.SELL

    # 验证信号
    m_signals = [s for s in strategy.signals if "M头" in s.reason]
    assert len(m_signals) >= 1


def test_head_and_shoulders_bottom_pattern():
    """测试头肩底形态识别"""
    from datetime import timedelta

    # 使用较大的platform_min_bars，禁用W底和M头以避免干扰
    strategy = CaiSenStrategy(platform_min_bars=20, platform_max_amplitude=0.05,
                              w_bottom_enabled=False, m_top_enabled=False,
                              head_and_shoulders_bottom_enabled=True)

    # 头肩底场景：左肩、头（最低）、右肩，然后突破颈线
    base_time = datetime(2024, 1, 1)

    # 1. 左肩（4根K线，确保有足够数据）
    for i in range(4):
        bar = make_bar(i, 96, 98, 94, 95, volume=1000)
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 2. 头部（最低，4根K线）
    for i in range(4, 8):
        bar = make_bar(i, 94, 95, 92, 93, volume=1200)  # 放量下跌
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 3. 右肩（与左肩相近，4根K线）
    for i in range(8, 12):
        bar = make_bar(i, 95, 97, 93, 95, volume=800)  # 缩量反弹
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 4. 突破颈线（确保低点与左肩差异>5%，避免被识别为右肩）
    bar_breakout = make_bar(12, 100, 105, 100, 104, volume=1500)  # 放量突破，低点100与左肩94差异6.4%
    bar_breakout.timestamp = base_time + timedelta(days=12)
    order = strategy.on_bar(bar_breakout)

    # 应该产生头肩底买入信号
    assert order is not None
    assert order.side == Side.BUY

    # 验证信号
    hs_signals = [s for s in strategy.signals if "头肩底" in s.reason]
    assert len(hs_signals) >= 1


def test_head_and_shoulders_top_pattern():
    """测试头肩顶形态识别"""
    from datetime import timedelta

    # 使用较大的platform_min_bars，禁用W底、M头、头肩底以避免干扰
    strategy = CaiSenStrategy(platform_min_bars=20, platform_max_amplitude=0.05,
                              w_bottom_enabled=False, m_top_enabled=False,
                              head_and_shoulders_bottom_enabled=False,
                              head_and_shoulders_top_enabled=True)

    # 头肩顶场景：左肩、头（最高）、右肩，然后跌破颈线
    base_time = datetime(2024, 1, 1)

    # 1. 左肩（4根K线）
    for i in range(4):
        bar = make_bar(i, 104, 106, 102, 105, volume=1000)
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 2. 头部（最高，4根K线）
    for i in range(4, 8):
        bar = make_bar(i, 106, 108, 104, 107, volume=1200)  # 放量上涨
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 3. 右肩（与左肩相近，4根K线）
    for i in range(8, 12):
        bar = make_bar(i, 104, 106, 102, 105, volume=800)  # 缩量反弹
        bar.timestamp = base_time + timedelta(days=i)
        strategy.on_bar(bar)

    # 4. 跌破颈线（确保高点与左肩差异>5%，避免被识别为右肩）
    bar_breakdown = make_bar(12, 100, 100, 98, 98, volume=1500)  # 放量跌破，高点100与左肩106差异5.7%
    bar_breakdown.timestamp = base_time + timedelta(days=12)
    order = strategy.on_bar(bar_breakdown)

    # 应该产生头肩顶卖出信号
    assert order is not None
    assert order.side == Side.SELL

    # 验证信号
    hs_signals = [s for s in strategy.signals if "头肩顶" in s.reason]
    assert len(hs_signals) >= 1


def test_caisen_volume_decline():
    """测试蔡森量能退潮标准 - 平台后半段成交量应小于前半段"""
    # 启用严格的量能退潮检查
    strategy = CaiSenStrategy(platform_min_bars=10, platform_max_amplitude=0.05,
                              platform_volume_decline=True)

    # 场景1：量能退潮（后半段成交量减少40%）- 应检测到平台
    for i in range(10):
        volume = 1000 if i < 5 else 600  # 前半段1000，后半段600
        bar = make_bar(i, 100, 101, 99, 100, volume=volume)
        strategy.on_bar(bar)

    assert strategy.platform is not None, "量能退潮时应检测到整理平台"

    # 重置策略
    strategy2 = CaiSenStrategy(platform_min_bars=10, platform_max_amplitude=0.05,
                               platform_volume_decline=True)

    # 场景2：量能未退潮（后半段成交量增加）- 不应检测到平台
    for i in range(10):
        volume = 600 if i < 5 else 1000  # 前半段600，后半段1000（量能增加）
        bar = make_bar(i, 100, 101, 99, 100, volume=volume)
        strategy2.on_bar(bar)

    assert strategy2.platform is None, "量能未退潮时不应检测到整理平台"


def test_caisen_instant_breakdown():
    """测试蔡森瞬间破底标准 - 破底应在平台形成后1-2根K线内完成"""
    strategy = CaiSenStrategy(platform_min_bars=5, platform_max_amplitude=0.05,
                              platform_volume_decline=False,
                              breakdown_max_bars=2)

    # 1. 形成整理平台（5根K线）
    for i in range(5):
        bar = make_bar(i, 100, 101, 99, 100)
        strategy.on_bar(bar)

    assert strategy.platform is not None
    platform_lower = strategy.platform.lower

    # 2. 平台形成后第1根K线破底（瞬间破底）- 应识别
    breakdown_price = platform_lower * 0.99
    bar_breakdown = make_bar(5, 100, 100, breakdown_price * 0.998, breakdown_price, volume=2000)
    strategy.on_bar(bar_breakdown)

    assert strategy.breakdown_bar is not None, "平台形成后1根K线破底应被识别"

    # 重置策略测试非瞬间破底
    strategy2 = CaiSenStrategy(platform_min_bars=5, platform_max_amplitude=0.05,
                               platform_volume_decline=False,
                               breakdown_max_bars=2)

    # 1. 形成整理平台
    for i in range(5):
        bar = make_bar(i, 100, 101, 99, 100)
        strategy2.on_bar(bar)

    # 2. 平台形成后第3、4根K线在平台内波动
    strategy2.on_bar(make_bar(5, 100, 101, 99, 100))
    strategy2.on_bar(make_bar(6, 100, 101, 99, 100))

    # 3. 第4根K线才破底（超过breakdown_max_bars=2）- 不应识别为瞬间破底
    breakdown_price = platform_lower * 0.99
    bar_breakdown = make_bar(7, 100, 100, breakdown_price * 0.998, breakdown_price, volume=2000)
    strategy2.on_bar(bar_breakdown)

    assert strategy2.breakdown_bar is None, "平台形成后3根K线才破底不应被识别为瞬间破底"
