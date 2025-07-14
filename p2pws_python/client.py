
import websockets
import typing
import json
import asyncio

from .types.clientOptions import ClientOptions
from .emitter import EventEmitter

from .types.p2pquakes.earthquakeReport import EarthquakeReports
from .types.p2pquakes.eew import EEW
from .types.p2pquakes.tsunami import Tsunami

from .utils.cache import DataCacheManager

class Client( EventEmitter ):
    """
    Represents the p2pquake websocket client.

    ## Examples
    - A simple example of using the Client class.

    ```
        from src.client import Client
        from src.types.p2pquakes.earthquakeReport import EarthquakeReports

        client = Client()

        @client.on
        async def ready() -> None:
            print('ready client :)')

        @client.on
        async def earthquake( data: EarthquakeReports ):
            print(f' hypocenterName: {data.earthquake.hypocenter.name} ')

        # Simply call start() - asyncio is handled automatically
        client.start()
    ```

    ## ClientOptions
    - `isDebug` : `bool`
        Whether to output debug messages.
    - `isSandbox` : `bool`
        Whether to use the sandbox server.

    ## Functions
    - `start() -> None`

        Start the websocket client.

        ⚠️ Automatically handles asyncio event loop. You can simply call client.start().

    ## Events
    - `ready() -> None` : Emitted when the websocket client is connected to the server.
    - `earthquake( data: EarthquakeReports ) -> None` : Emitted when the websocket client receives an earthquake report.
    - `eew( data: EEW ) -> None` : Emitted when the websocket client receives an EEW report.

    """
    option: ClientOptions
    ws: typing.Optional[websockets.WebSocketServerProtocol] = None
    isReady: bool = False
    cache : DataCacheManager

    def __init__( 
            self, 
            isDebug: typing.Optional[bool] = False, 
            isSandbox: typing.Optional[bool] = False 
    ) -> None:
        super().__init__()
        self.option = ClientOptions(
            isDebug,
            isSandbox
        )
        # self.cache = DataCacheManager()


    def start( self ):
        """
        Start the websocket client connection.
        Automatically runs in asyncio event loop.
        """
        # Check if there's already a running event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an async context, create a task
            task = loop.create_task(self._start_async())
            return task
        except RuntimeError:
            # No running loop, so we can use asyncio.run()
            return asyncio.run(self._start_async())

    async def _start_async( self, max_retries: int = 10, retry_interval: float = 5.0 ):
        """
        Internal async start method with auto-reconnect.
        max_retries: 最大再接続回数（Noneで無限）
        retry_interval: 再接続までの待機秒数
        """
        uri = self.__get_ws_url__()
        retries = 0
        while True:
            self.__debug_message__(f"[client] Connecting to {uri} (try {retries+1})")
            try:
                async with websockets.connect(uri) as websocket:
                    self.ws = websocket
                    await self.__on_ready()
                    async for message in websocket:
                        await self.__on_message(message)
                self.__debug_message__(f"[client -> ws] Connection closed normally")
                await self.__on_close()
                break  # 正常終了ならループ脱出
            except websockets.exceptions.ConnectionClosed:
                self.__debug_message__(f"[client -> ws] Connection closed unexpectedly. Reconnecting...")
                await self.__on_close()
            except Exception as error:
                self.__debug_message__(f"[client -> ws] Error occurred: {error}. Reconnecting...")
                await self.__on_error(error)
            retries += 1
            if max_retries is not None and retries >= max_retries:
                self.__debug_message__(f"[client] Max retries reached. Giving up.")
                break
            self.__debug_message__(f"[client] Waiting {retry_interval} seconds before reconnect...")
            await asyncio.sleep(retry_interval)

    async def __on_ready( self ) -> None:
        """
        @private
        on_open event handler. ( ready )

        This function is called when the websocket client is connected to the server.
        """
        self.isReady = True;
        self.__debug_message__(f"[client -> ws] connected to the websocket server. (url: {self.__get_ws_url__()})")
        await self.emit('ready')
        pass;

    async def __on_message( self, message: str ) -> None:
        """
        @private
        on_message event handler.

        This function is called when the websocket client receives a message from the server.
        """
        await self.emit('rawmessage', message)
        try:
            # 最初はdictにする
            data = json.loads( message )
            self.__debug_message__(f"[ws -> client] received data: {data['code']}")

            # 551 ・・・ 地震情報（震源・震度・各地の震度）
            if data['code'] == 551:
                dataClass = EarthquakeReports( data )
                await self.emit('earthquake', dataClass )
                self.cache.set( dataClass._id, dataClass )
            
            # 552 ・・・ 津波予報
            if data['code'] == 552:
                dataClass = Tsunami( data )
                await self.emit('tsunami', dataClass )
                self.cache.set( dataClass._id, dataClass )

            # 556 ・・・ 緊急地震速報 配信データ
            if data['code'] == 556:
                dataClass = EEW( data )
                await self.emit('eew', dataClass )
                self.cache.set( dataClass._id, dataClass )

        except Exception as e:
            self.__debug_message__(f"[client] json parsing error")
            self.__debug_message__( e )
        pass;
    
    async def __on_error( self, error: typing.Any ) -> None:
        self.__debug_message__(f"[client -> ws] error occurred. (url: {self.__get_ws_url__()})")
        self.__debug_message__( error )
        await self.emit('error', error)
        pass;
    
    async def __on_close( self ) -> None:
        self.__debug_message__(f"[client -> ws] disconnected from the websocket server. (url: {self.__get_ws_url__()})")
        self.isReady = False
        await self.emit('close')
        pass;

    
    def __debug_message__( 
            self, 
            message: str 
    ) -> None:
        if self.option.isDebug:
            print( message )

    def __get_ws_url__( self ):
        return "wss://api.p2pquake.net/v2/ws" if not self.option.isSandBox else "wss://api-realtime-sandbox.p2pquake.net/v2/ws"