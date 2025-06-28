import asyncio
from p2pws_python.client import Client
from p2pws_python.types.p2pquakes.earthquakeReport import EarthquakeReports
from p2pws_python.types.p2pquakes.eew import EEW
from p2pws_python.types.p2pquakes.tsunami import Tsunami

async def main():
    client = Client(isDebug=True, isSandbox=True)

    @client.on
    async def ready() -> None:
        print('Client is ready! 🎉')

    @client.on
    async def earthquake(data: EarthquakeReports) -> None:
        print(f'🌍 Earthquake detected: {data.earthquake.hypocenter.name}')

    @client.on
    async def eew(data: EEW) -> None:
        print(f'⚠️ EEW Alert: {data.eew.hypoName}')

    @client.on
    async def tsunami(data: Tsunami) -> None:
        print(f'🌊 Tsunami warning issued')

    @client.on
    async def error(error) -> None:
        print(f'❌ Error occurred: {error}')

    @client.on
    async def close() -> None:
        print('🔌 Connection closed')

    # Start the client
    try:
        await client.start()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())
