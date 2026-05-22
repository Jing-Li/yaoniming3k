"""Strategy 模块

目录结构:
├── algorithm/          # 算法策略
│   ├── patterns/       # 形态检测器
│   ├── cai_sen.py     # 蔡森策略
│   ├── detector.py    # 形态检测基类
│   └── ...
├── llm/               # LLM 策略
│   ├── ...
└── base.py           # 策略基类
"""

from .base import Strategy, Annotation, AnnotationType

# 算法策略
from .algorithm.cai_sen import CaiSenStrategy
from .algorithm.detector import PatternDetector, PatternSignal

__all__ = [
    "Strategy", "Annotation", "AnnotationType",
    "CaiSenStrategy",
    "PatternDetector", "PatternSignal",
]