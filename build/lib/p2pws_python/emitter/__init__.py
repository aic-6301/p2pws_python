import typing
import asyncio

T = typing.TypeVar('T')
Coro = typing.Coroutine[typing.Any, typing.Any, T]
CallableCoroutine = typing.TypeVar("CallableCoroutine", bound=typing.Callable[..., Coro ])

class EventEmitter:
    """
    Represents EventEmitter like a nodejs.

    # Examples
    - A simple example of using the EventEmitter class.
    This class extends the EventEmitter, and emits an event named 'something' with the data.

        ```
            class MyEmitter( EventEmitter ):
                def __init__( self ) -> None:
                    super().__init__()
                
                def something_emit( self , data : any ) -> None:
                    self.emit('something', data)

        ```

    if you want to listen to the event, you can use the `on` method or the `@on` decorator.

        ```
            emitter = MyEmitter()

            @emitter.on
            async def something( data : any ) -> None:
                print(data)
        ```

    # Functions
    - `on( f: CallableCoroutine, / ) -> CallableCoroutine`
        A decorator to add an event listener to the event emitter.
        - `f` : `CallableCoroutine`
            The event listener function.
    
    - `emit( event: str, *args ) -> None`
        Emit an event with the data.
        - `event` : `str`
            The event name.
        - `*args` : `any`
            The data to emit.

    # Returns
        - `None
    """
    def __init__( self ) -> None:
        self._listeners: typing.Dict[str, typing.List[typing.Tuple[ asyncio.Future, typing.Callable[..., bool ]]]] = {}
        """
        thanks to discord.py :)
        """

    def on(self, f: CallableCoroutine, /) -> CallableCoroutine:
        """
        A decorator to add an event listener to the event emitter.
        """
        if not asyncio.iscoroutinefunction(f):
            raise TypeError('\nlistener must be a coroutine function. \nExample: \n @emitter.on \n async def listener( data: any ) -> None: \n    print(data)')
        
        print(f'[EventEmitter] Adding listener {f.__name__}')
        setattr(self, f.__name__, f)
        return f
        

    async def emit(self, event: str, *args ) -> None:
        if hasattr(self, event):
            listener = getattr(self, event)
            if listener:
                await listener(*args)
            else:
                print(f'[EventEmitter] Event {event} has no listeners :( ')