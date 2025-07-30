import asyncio
import inspect
import websockets
import logging
import json
import traceback

from .types.p2pquakes.earthquakeReport import EarthquakeReports
from .types.p2pquakes.eew import EEW
from .types.p2pquakes.tsunami import Tsunami

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventHandler:
    def __init__(self, client):
        self._handlers = {}
        self.client = client
        self._code_map = {
            551: ("on_earthquake", EarthquakeReports),  # 地震情報
            556: ("on_eew", EEW),                       # 緊急地震速報
            552: ("on_tsunami", Tsunami),               # 津波予報
        }
        # 特別なイベント（接続関連）
        self._connection_events = ["on_ready", "on_disconnect", "on_reconnect"]

    def register(self, name, func):
        self._handlers[name] = func

    def get(self, name):
        return self._handlers.get(name)
    
    async def _fire_event(self, event_name: str, *args):
        """接続関連のイベントを発火"""
        handler = self.get(event_name)
        if handler:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(*args)
                else:
                    handler(*args)
            except Exception as e:
                print(f"[EventError] {event_name}: {e}")
                traceback.print_exc()

    def resolve_event(self, data_dict: dict):
        event_type = data_dict.get("code")
        return self._code_map.get(event_type, ("on_message", dict))  # デフォルトはon_messageにdict

    async def dispatch(self, raw_data):
        try:
            data_dict = json.loads(raw_data)

            event_name, expected_type = self.resolve_event(data_dict)
            handler = self.get(event_name)
            if not handler:
                return  # ハンドラが登録されていなければ無視

            # 型付きデータクラスに変換
            if expected_type is dict:
                args = (data_dict,)
            else:
                args = (expected_type(data_dict),)

            if inspect.iscoroutinefunction(handler):
                await handler(*args)
            else:
                handler(*args)

        except Exception as e:
            print(f"[DispatchError] {e}")
            traceback.print_exc()


class Client:
    """
    WebSocketクライアント
    
    :param  isSandbox: bool
    地震情報の履歴を取得できます。
    ※このオプションの使用は非推奨です。
        
    """
    def __init__(self, isSandbox: bool = False, auto_reconnect: bool = True, reconnect_delay: float = 5.0):
        self.isSandbox = isSandbox
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.handlers = EventHandler(self)
        self.url = self.__get_url__()
        self._task = None
        self._running = False
        self._connected = False
        self._connection_lock = asyncio.Lock()

    def event(self, func):
        self.handlers.register(func.__name__, func)
        return func

    async def _single_connection(self):
        """単一の接続を管理"""
        try:
            print(f"WebSocket接続を試行中: {self.url}")
            async with websockets.connect(self.url, logger=logger) as ws:
                print("WebSocket接続が確立されました")
                self._connected = True
                
                # 接続成功イベントを発火
                if not hasattr(self, '_ever_connected'):
                    await self.handlers._fire_event("on_ready")
                    self._ever_connected = True
                else:
                    await self.handlers._fire_event("on_reconnect")
                
                # メッセージ受信ループ
                async for message in ws:
                    if not self._running:
                        break
                    await self.handlers.dispatch(message)
                        
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"WebSocket接続が切断されました: {e}")
            await self.handlers._fire_event("on_disconnect", str(e))
            raise
        except Exception as e:
            print(f"WebSocket接続エラー: {e}")
            await self.handlers._fire_event("on_disconnect", str(e))
            raise
        finally:
            self._connected = False

    async def _connect(self):
        """再接続ロジックを含む接続管理"""
        while self._running:
            try:
                await self._single_connection()
                # 正常に切断された場合（_runningがFalseになった）はループを抜ける
                if not self._running:
                    break
                    
            except Exception:
                # 接続エラーまたは切断が発生
                if not self.auto_reconnect or not self._running:
                    break
                
                print(f"{self.reconnect_delay}秒後に再接続を試行します...")
                try:
                    await asyncio.sleep(self.reconnect_delay)
                except asyncio.CancelledError:
                    break
    
    def __get_url__(self):
        if self.isSandbox:
            return "wss://api-realtime-sandbox.p2pquake.net/v2/ws"
        return "wss://api.p2pquake.net/v2/ws"

    @property
    def is_connected(self):
        return self._running and self._connected

    async def start(self):
        """WebSocket接続を開始します（discord.pyとの統合用）"""
        async with self._connection_lock:
            if self._running:
                print("既に実行中です")
                return
                
            self._running = True
            try:
                await self._connect()
            except Exception as e:
                print(f"WebSocket接続エラー: {e}")
            finally:
                self._running = False
                self._connected = False

    def run(self, loop=None):
        """WebSocket接続を開始します（非同期でバックグラウンド実行）"""
        # 既に実行中の場合は既存のタスクを返す
        if self._running and self._task and not self._task.done():
            print("既に実行中です")
            return self._task
            
        # 現在のイベントループを取得（discord.pyのループを使用）
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # イベントループが実行中でない場合は新しく作成
                return self.run_sync()
        
        # 前のタスクをクリーンアップ
        if self._task and not self._task.done():
            self._task.cancel()
        
        self._task = loop.create_task(self.start())
        return self._task
            
    def run_sync(self):
        """WebSocket接続を開始します（同期実行、ブロッキング）"""
        if self._running:
            print("既に実行中です")
            return
            
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            pass
            
    async def stop(self):
        """WebSocket接続を停止します"""
        async with self._connection_lock:
            if not self._running:
                print("既に停止しています")
                return
                
            print("WebSocket接続を停止しています...")
            self._running = False
            
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                    
            self._connected = False
            print("WebSocket接続が停止されました")