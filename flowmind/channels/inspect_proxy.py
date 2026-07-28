# -*- coding: utf-8 -*-
"""
Inspect代理

为开发调试提供实时状态查看功能。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Awaitable, TYPE_CHECKING

from flowmind.channels.base_channel import InputChannel, UserMessage

if TYPE_CHECKING:
    from flowmind.core.tracker import DialogueStateTracker
    from flowmind.agent.message_processor import MessageProcessor

logger = logging.getLogger(__name__)


class TrackerStream:
    """Tracker状态流。
    
    通过WebSocket向连接的客户端广播Tracker状态更新。
    """
    
    def __init__(
        self,
        get_tracker_state: Callable[[str], Awaitable[str]],
    ):
        """初始化。
        
        Args:
            get_tracker_state: 获取Tracker状态的回调
        """
        self.get_tracker_state = get_tracker_state
        self._clients: Set[Any] = set()
    
    def add_client(self, websocket: Any) -> None:
        """添加客户端。"""
        self._clients.add(websocket)
    
    def remove_client(self, websocket: Any) -> None:
        """移除客户端。"""
        self._clients.discard(websocket)
    
    async def broadcast(self, message: str) -> None:
        """广播消息给所有客户端。"""
        if not self._clients:
            return
        
        tasks = []
        for client in self._clients.copy():
            try:
                tasks.append(self._send(client, message))
            except Exception:
                self._clients.discard(client)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send(self, websocket: Any, message: str) -> None:
        """发送消息给单个客户端。"""
        try:
            await websocket.send_text(message)
        except Exception:
            self._clients.discard(websocket)


class InspectProxy(InputChannel):
    """Inspect代理通道。
    
    包装底层通道，提供对话状态的实时查看功能。
    
    功能：
    - 包装任意输入通道
    - 提供/inspect.html页面查看对话状态
    - 通过WebSocket实时推送状态更新
    """
    
    def __init__(
        self,
        underlying_channel: InputChannel,
        processor: Optional["MessageProcessor"] = None,
    ):
        """初始化Inspect代理。
        
        Args:
            underlying_channel: 被包装的底层通道
            processor: 消息处理器
        """
        self.underlying = underlying_channel
        self.processor = processor
        self.tracker_stream = TrackerStream(get_tracker_state=self._get_tracker_state)
    
    @property
    def name(self) -> str:
        return f"inspect_{self.underlying.name}"
    
    def set_processor(self, processor: "MessageProcessor") -> None:
        """设置消息处理器。"""
        self.processor = processor
    
    async def _get_tracker_state(self, sender_id: str) -> str:
        """获取Tracker状态的JSON字符串。"""
        if not self.processor:
            return "{}"
        
        # 获取tracker
        tracker = await self.processor.domain.tracker_store.retrieve(sender_id)
        if not tracker:
            return "{}"
        
        # 转换为字典
        state = tracker.current_state()
        return json.dumps(state, ensure_ascii=False, default=str)
    
    async def on_tracker_updated(self, tracker: "DialogueStateTracker") -> None:
        """Tracker更新时广播状态。"""
        try:
            state = tracker.current_state()
            state_json = json.dumps(state, ensure_ascii=False, default=str)
            await self.tracker_stream.broadcast(state_json)
        except Exception as e:
            logger.error(f"Failed to broadcast tracker state: {e}")
    
    def create_routes(
        self,
        on_new_message: Callable[[UserMessage], Awaitable[Any]],
    ) -> Any:
        """创建FastAPI路由。
        
        Args:
            on_new_message: 消息处理回调
            
        Returns:
            FastAPI Router
        """
        from fastapi import APIRouter, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse
        
        router = APIRouter(tags=["inspect"])
        
        # 包装消息处理回调，添加状态广播
        async def wrapped_handler(message: UserMessage) -> Any:
            result = await on_new_message(message)
            # 广播状态更新由钩子处理
            return result
        
        # 添加底层通道的路由
        if hasattr(self.underlying, 'create_routes'):
            underlying_router = self.underlying.create_routes(wrapped_handler)
            router.include_router(underlying_router)
        
        @router.get("/inspect.html", response_class=HTMLResponse)
        async def inspect_page():
            """Inspect页面。"""
            return self._get_inspect_html()
        
        @router.websocket("/tracker_stream")
        async def tracker_stream(websocket: WebSocket):
            """Tracker状态WebSocket流。"""
            await websocket.accept()
            self.tracker_stream.add_client(websocket)
            
            try:
                while True:
                    # 接收客户端消息
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # 处理获取状态请求
                    if message.get("action") == "retrieve":
                        sender_id = message.get("sender_id", "default")
                        state = await self._get_tracker_state(sender_id)
                        await websocket.send_text(state)
                        
            except WebSocketDisconnect:
                pass
            finally:
                self.tracker_stream.remove_client(websocket)
        
        return router
    
    def _get_inspect_html(self) -> str:
        """返回Inspect页面HTML。"""
        return r"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlowMind · 汇智智能客服 — 调试器</title>
    <style>
        :root {
            --bg: #0f0f1a; --bg2: #1a1a2e; --bg3: #222244;
            --border: #2a2a4a; --accent: #6c5ce7; --danger: #e94560;
            --success: #10b981; --text: #e8e8f0; --text2: #9090a8; --text3: #606078;
            --radius: 10px; --transition: 0.2s ease;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Segoe UI', sans-serif;
            background: var(--bg); color: var(--text); height: 100vh; overflow: hidden; font-size: 13px;
        }
        .topbar {
            height: 44px; background: var(--bg2); border-bottom: 1px solid var(--border);
            display: flex; align-items: center; padding: 0 16px; gap: 10px;
        }
        .topbar .logo { font-weight: 700; background: linear-gradient(135deg, var(--accent), var(--danger)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .topbar .spacer { flex: 1; }
        .topbar .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 4px; }
        .topbar .dot.on { background: var(--success); box-shadow: 0 0 6px var(--success); }
        .topbar .dot.off { background: var(--danger); }
        .container { display: flex; height: calc(100vh - 44px); }
        .panel { display: flex; flex-direction: column; }
        .panel-left { flex: 1; min-width: 0; border-right: 1px solid var(--border); }
        .panel-right { width: 340px; background: var(--bg2); }
        .chat-body { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 8px; }
        .chat-body::-webkit-scrollbar { width: 4px; }
        .chat-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
        .msg { max-width: 80%; padding: 10px 14px; border-radius: 14px; font-size: 13px; line-height: 1.5; animation: in 0.2s ease; word-break: break-word; }
        @keyframes in { from { opacity: 0; transform: translateY(8px); } }
        .msg.user { background: var(--accent); color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }
        .msg.bot { background: var(--bg3); color: var(--text); align-self: flex-start; border-bottom-left-radius: 4px; }
        .chat-input { padding: 10px 14px; border-top: 1px solid var(--border); display: flex; gap: 8px; }
        .chat-input input { flex: 1; padding: 10px 14px; background: var(--bg3); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text); font-size: 13px; }
        .chat-input input:focus { outline: none; border-color: var(--accent); }
        .chat-input input::placeholder { color: var(--text3); }
        .btn { padding: 8px 16px; border: none; border-radius: var(--radius); cursor: pointer; font-weight: 500; font-size: 13px; transition: var(--transition); }
        .btn-primary { background: var(--accent); color: #fff; }
        .btn-primary:hover { background: #7c6cf7; }
        .section { padding: 14px 16px; border-bottom: 1px solid var(--border); }
        .section h3 { font-size: 11px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }
        .slot-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 12px; }
        .slot-row .name { color: var(--text2); }
        .slot-row .value { font-family: 'SF Mono', monospace; color: var(--accent); word-break: break-all; font-size: 11px; }
        .flow-name { padding: 8px 12px; background: var(--bg3); border-radius: 6px; font-size: 13px; }
        .flow-name code { color: var(--accent); font-size: 12px; }
        .raw-pre { font-family: 'SF Mono', monospace; font-size: 11px; color: var(--text2); white-space: pre-wrap; line-height: 1.5; max-height: 200px; overflow-y: auto; background: var(--bg3); border-radius: 6px; padding: 10px; }
        .raw-pre::-webkit-scrollbar { width: 4px; }
        .raw-pre::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
        .empty { color: var(--text3); font-size: 12px; font-style: italic; }
    </style>
</head>
<body>
    <div class="topbar">
        <div class="logo">FlowMind · 汇智智能客服</div>
        <span class="spacer"></span>
        <span class="dot off" id="dot"></span>
        <span id="status-text" style="font-size:12px;color:var(--text2);">未连接</span>
    </div>
    <div class="container">
        <div class="panel panel-left">
            <div class="chat-body" id="chat-box"></div>
            <div class="chat-input">
                <input type="text" id="msg-input" placeholder="输入消息，Enter 发送..." onkeypress="if(event.key==='Enter')send()">
                <button class="btn btn-primary" onclick="send()">发送</button>
            </div>
        </div>
        <div class="panel panel-right">
            <div class="section">
                <h3>📌 槽位 (Slots)</h3>
                <div id="slots"><span class="empty">暂无数据</span></div>
            </div>
            <div class="section">
                <h3>📋 活动 Flow</h3>
                <div id="flow" class="flow-name"><span class="empty">暂无</span></div>
            </div>
            <div class="section" style="flex:1;overflow:hidden;">
                <h3>🔍 原始状态</h3>
                <pre class="raw-pre" id="raw-state">{}</pre>
            </div>
        </div>
    </div>
    <script>
        var senderId = 'inspect_' + Date.now(), ws = null;
        function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
        function setStatus(on) {
            document.getElementById('dot').className = 'dot ' + (on ? 'on' : 'off');
            document.getElementById('status-text').textContent = on ? '已连接' : '未连接';
        }
        function connect() {
            var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            try { ws = new WebSocket(proto + '//' + location.host + '/tracker_stream'); } catch(e) { setStatus(false); setTimeout(connect,5000); return; }
            ws.onopen = function() { setStatus(true); ws.send(JSON.stringify({action:'retrieve',sender_id:senderId})); };
            ws.onclose = function() { setStatus(false); setTimeout(connect,3000); };
            ws.onerror = function() { setStatus(false); };
            ws.onmessage = function(e) { try { var s = JSON.parse(e.data); update(s); } catch(x) { console.error(x); } };
        }
        function update(s) {
            var d = document.getElementById('slots');
            if (s.slots && Object.keys(s.slots).length > 0) {
                d.innerHTML = Object.entries(s.slots).map(function(kv) {
                    var v = kv[1] === null ? '<em style="color:var(--text3)">null</em>' : esc(JSON.stringify(kv[1]));
                    return '<div class="slot-row"><span class="name">' + esc(kv[0]) + '</span><span class="value">' + v + '</span></div>';
                }).join('');
            } else { d.innerHTML = '<span class="empty">暂无槽位</span>'; }
            var f = document.getElementById('flow');
            f.innerHTML = s.active_flow ? '<code>' + esc(s.active_flow) + '</code>' : '<span class="empty">暂无活动 Flow</span>';
            document.getElementById('raw-state').textContent = JSON.stringify(s, null, 2);
        }
        function addMessage(t, isUser) {
            var box = document.getElementById('chat-box'), d = document.createElement('div');
            d.className = 'msg ' + (isUser ? 'user' : 'bot'); d.textContent = t;
            box.appendChild(d); box.scrollTop = box.scrollHeight;
        }
        async function send() {
            var inp = document.getElementById('msg-input'), t = inp.value.trim(); if (!t) return;
            addMessage(t, true); inp.value = '';
            try {
                var r = await fetch('/webhooks/rest/webhook', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sender:senderId,message:t})});
                var msgs = await r.json();
                (Array.isArray(msgs) ? msgs : [msgs]).forEach(function(m) { if (m.text) addMessage(m.text, false); });
            } catch(e) { addMessage('发送失败: ' + e.message, false); }
        }
        connect();
    </script>
</body>
</html>"""


# 导出
__all__ = [
    "InspectProxy",
    "TrackerStream",
]
