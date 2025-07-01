from dotenv import load_dotenv
from os import getenv

load_dotenv()

# Socket server conifg
HOST = getenv("HOST", "127.0.0.1")
PORT = int(getenv("PORT", "4375"))
API_KEY = getenv("API_KEY")

# Redis configs
REDIS_HOST = getenv("HOST", "127.0.0.1")
REDIS_PORT = int(getenv("REDIS_PORT", "6379"))
REDIS_DB = int(getenv("REDIS_DB", "0"))

# Bot config
BOT_TOKEN = getenv("BOT_TOKEN")
ADMIN_ID = int(getenv("ADMIN_ID"))