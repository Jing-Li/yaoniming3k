"""caisen-data 数据抓取模块"""

import logging

__version__ = "0.1.0"

# 默认不添加 handler，由调用方配置；设置 NullHandler 避免 "No handler found" 警告
logging.getLogger("caisen_data").addHandler(logging.NullHandler())