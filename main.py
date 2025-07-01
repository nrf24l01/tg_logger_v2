from modules import Client, Logger
from asyncio import run
from config import HOST, PORT, API_KEY, REDIS_HOST, REDIS_PORT, REDIS_DB
from asyncio import Queue
from redis.asyncio import Redis
from json import loads, dumps
from typing import Tuple

class TgLogger(Client):
    async def init(self, host: str, port: int, key: str, redis_host: str, redis_port: int, redis_db: int):
        super().init(host=host, port=port, key=key)
        self.logger.debug(f"Connecting to redis on {redis_host}:{redis_port}, db: {redis_db}")
        self.redis = Redis(host=redis_host, port=redis_port, db=redis_db)
        self.logger.info(f"Connected to redis server on {redis_host}:{redis_port}, db: {redis_db}")
    
    async def save_message(self, id: int, text: str, author_id: int, author_name: str, chat_id: int):
        payload = {
            "text": text,
            "author_id": author_id,
            "author_name": author_name,
            "chat_id": chat_id
        }
        await self.redis.set(f"message:{id}", dumps(payload), ex=864000*7)
        self.logger.debug(f"Save message with id {id}")
    
    async def get_message(self, id: int) -> Tuple[str, int, str, int] | Tuple[None, None, None, None]:
        if not await self.redis.exists(f"message:{id}"):
            self.logger.warn(f"Message with id {id} not found")
            return None, None, None, None
        self.logger.debug(f"Trying to load message with id {id}")
        raw = await self.redis.get(f"message:{id}")
        parsed = loads(raw)
        self.logger.debug(f"Loaded message with id {id}")
        return parsed["text"], parsed["author_id"], parsed["author_name"], parsed["chat_id"]
    
    async def process_message(self, message_type: int, payload: dict, config: dict):
        if not config.get("log", False):
            return
        
        if message_type == 1:
            if config.get("reply_me", "true") == "true" and payload["my_message"]:
                async with self.to_send_lock:
                    task = {
                        "type": 1,
                        "payload": {
                            "message": payload["message"],
                            "to": payload["from"]
                        }
                    }
                    await self.to_send.put(task)
            if config.get("reply_others", "false") == "true" and not payload["my_message"]:
                async with self.to_send_lock:
                    task = {
                        "type": 1,
                        "payload": {
                            "message": payload["message"],
                            "to": payload["from"]
                        }
                    }
                    await self.to_send.put(task)

async def main():
    logger = Logger()
    client = TgLogger(logger)
    await client.init(HOST, PORT, API_KEY,
                      redis_host=REDIS_HOST,
                      redis_port=REDIS_PORT,
                      redis_db=REDIS_DB
                      )

    await client.polling()

if __name__ == "__main__":
    run(main())