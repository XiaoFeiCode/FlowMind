# -*- coding: utf-8 -*-
"""
flowmind API模块

提供基于FastAPI的Web服务接口。
"""

from flowmind.api.server import FlowMindServer, create_app

__all__ = [
    "FlowMindServer",
    "create_app",
]
