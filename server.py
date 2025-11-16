import asyncio
import websockets
import json

connected_clients = set()

async def handler(websocket):
    connected_clients.add(websocket)
    try:
        async for msg in websocket:
            # Broadcast cho client còn lại
            for client in connected_clients:
                if client != websocket:
                    await client.send(msg)
    finally:
        connected_clients.remove(websocket)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 10000):
        print("Server chạy trên port 10000")
        await asyncio.Future()

asyncio.run(main())
