from . import AsyncSocketController, Logger
from asyncio import open_connection, sleep, Lock, Queue

class Client(AsyncSocketController):
    def __init__(self, logger: Logger):
        super().__init__()
        self.logger = logger
        self.to_send = Queue()
        self.to_send_lock = Lock()
        self.reader = None
        self.writer = None

    async def init(self, host: str, port: int, key: str):
        self.logger.info(f"Trying to connect to {host}:{port}")
        self.reader, self.writer = await open_connection(host, port)
        self.logger.info(f"Success!")

        await self.send_json({"key": key})
        answer = await self.read_json()
        if not answer["connected"]:
            self.logger.critical("Key is invalid.")
            raise Exception("Key is invalid.")

        self.logger.info(f"Registered as {answer['name']}")
    
    async def polling(self):
        try:
            while True:
                if await self.data_available():
                    try:
                        data = await self.read_json()
                        self.logger.debug("Received message from server:", data)
                        await self.process_message(message_type=data["type"], payload=data["payload"], config=data["config"])
                    except Exception as e:
                        raise e
                        self.logger.warning(f"Error reading message from server: {e}")
                
                async with self.to_send_lock:
                    while not self.to_send.empty():
                        task = await self.to_send.get()
                        await self.send_json(task)

                await sleep(0.05)

        except Exception as e:
            self.logger.info(f"Host disconnected: {e}")
            self.writer.close()
            await self.writer.wait_closed()
    
    async def process_message(self, message_type: int, payload: dict):
        raise NotImplementedError