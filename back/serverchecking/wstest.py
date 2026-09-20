# test_ws.py
import asyncio
import websockets

async def test():
    uri = "wss://welfare-1gs5.onrender.com/ws/chat/test_session_1"
    async with websockets.connect(uri) as ws:
        print("연결 성공!")
        await ws.send("STOP_RECORDING")
        response = await ws.recv()
        print("받은 응답:", response)

asyncio.run(test())