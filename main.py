from modules import Client, Logger, escape_markdown_v2
from asyncio import run
from config import HOST, PORT, API_KEY, REDIS_HOST, REDIS_PORT, REDIS_DB, BOT_TOKEN, ADMIN_ID
from asyncio import Queue
from redis.asyncio import Redis
from json import loads, dumps
from typing import Tuple
import aiohttp


class TgLogger(Client):
    async def init(self, host: str, port: int, key: str, redis_host: str, redis_port: int, redis_db: int, bot_token: str, admin_id: int):
        await super().init(host=host, port=port, key=key)
        self.logger.debug(f"Connecting to redis on {redis_host}:{redis_port}, db: {redis_db}")
        self.redis = Redis(host=redis_host, port=redis_port, db=redis_db)
        self.logger.info(f"Connected to redis server on {redis_host}:{redis_port}, db: {redis_db}")
        
        self.bot_token = bot_token
        self._session = aiohttp.ClientSession()
        self.admin_id = admin_id
            
    async def save_message(self, id: int, text: str, author_id: int, author_name: str, chat_id: int):
        payload = {
            "text": text,
            "author_id": author_id,
            "author_name": author_name,
            "chat_id": chat_id
        }
        await self.redis.set(f"message:{id}", dumps(payload), ex=864000*7)
        self.logger.debug(f"Save message with id {id}")
    
    async def send_changes(self, text: str):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.admin_id,
            "text": text,
            "parse_mode": "MarkdownV2"
        }
        try:
            async with self._session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text_resp = await resp.text()
                    self.logger.error(f"Failed to send message to {self.admin_id}, status {resp.status}: {text_resp}")
                    return False
                data = await resp.json()
                if not data.get("ok"):
                    self.logger.error(f"Telegram API error: {data}")
                    return False
                self.logger.info(f"Message sent to chat_id={self.admin_id}")
                return True
        except Exception as e:
            self.logger.error(f"Exception during send_message: {e}")
            return False
    
    async def get_message(self, id: int) -> Tuple[str, int, str, int] | Tuple[None, None, None, None]:
        if not await self.redis.exists(f"message:{id}"):
            self.logger.warning(f"Message with id {id} not found")
            return None, None, None, None
        self.logger.debug(f"Trying to load message with id {id}")
        raw = await self.redis.get(f"message:{id}")
        parsed = loads(raw)
        self.logger.debug(f"Loaded message with id {id}")
        return parsed["text"], parsed["author_id"], parsed["author_name"], parsed["chat_id"]
    
    async def process_message(self, message_type: int, payload: dict, config: dict, system_config: dict):
        if not config.get("log", True):
            return
        
        if message_type == 1:
            await self.save_message(payload["msg_id"], payload["message"], payload["sender"]["id"], payload["sender"]["name"], payload["chat_id"])
            self.logger.info(f"Saved message with id {payload['msg_id']}")
        elif message_type == 2:
            message_id = payload["msg_id"]
            old_text, auid, aunm, chat_id = await self.get_message(message_id)
            if not old_text:
                return
            if old_text != payload["message"]:
                old_text_escaped = escape_markdown_v2(old_text)
                new_text_escaped = escape_markdown_v2(payload["message"])
                author_name_escaped = escape_markdown_v2(aunm)
                chat_id_str = str(chat_id)
                message_id_str = str(message_id)
                author_id_str = str(auid)
                
                changes_text = (
                    f"Было изменено сообщение [{author_name_escaped}](tg://user?id={author_id_str}) "
                    f"в [чате](https://t.me/c/{chat_id_str}/{message_id_str})\\. Было\n"
                    f"```{old_text_escaped}```стало```{new_text_escaped}```"
                )
                await self.save_message(message_id, payload["message"], auid, aunm, chat_id)
                await self.send_changes(changes_text)
                self.logger.info(f"Detected change into {payload['msg_id']}")
        elif message_type == 3:
            message_id = payload["msg_id"]
            self.logger.debug(f"Deleted msg with id {message_id}")
            old_text, auid, aunm, chat_id = await self.get_message(message_id)
            if not old_text:
                self.logger.warning(f"Сообщение с id {message_id} не найдено")
                return
            old_text_escaped = escape_markdown_v2(old_text)
            author_name_escaped = escape_markdown_v2(aunm)
            chat_id_str = str(chat_id)
            message_id_str = str(message_id)
            author_id_str = str(auid)
            
            changes_text = (
                f"Было удаленно сообщение [{author_name_escaped}](tg://user?id={author_id_str}) "
                f"в [чате](https://t.me/c/{chat_id_str}/{message_id_str})\\. Сообщение\n"
                f"```{old_text_escaped}```"
            )
            await self.send_changes(changes_text)
            self.logger.info(f"Detected deletion of message {message_id}.")

async def main():
    logger = Logger()
    client = TgLogger(logger)
    await client.init(HOST, PORT, API_KEY,
                      redis_host=REDIS_HOST,
                      redis_port=REDIS_PORT,
                      redis_db=REDIS_DB,
                      admin_id=ADMIN_ID,
                      bot_token=BOT_TOKEN
                      )
    try:
        await client.polling()
    except KeyboardInterrupt as e:
        await client.close()
    finally:
        await client.close()

if __name__ == "__main__":
    run(main())