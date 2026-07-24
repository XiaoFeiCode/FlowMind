# -*- coding: utf-8 -*-
"""
通道模块

提供与用户交互的通道（Channel）实现。
"""

from flowmind.channels.base_channel import (
    InputChannel,
    OutputChannel,
    UserMessage,
    CollectingOutputChannel,
)
from flowmind.channels.rest_channel import RestChannel
from flowmind.channels.socketio_channel import SocketIOChannel
from flowmind.channels.console_channel import ConsoleChannel
from flowmind.channels.inspect_proxy import InspectProxy

__all__ = [
    "InputChannel",
    "OutputChannel",
    "UserMessage",
    "CollectingOutputChannel",
    "RestChannel",
    "SocketIOChannel",
    "ConsoleChannel",
    "InspectProxy",
]
