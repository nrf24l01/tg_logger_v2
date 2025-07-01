from dotenv import load_dotenv
from os import getenv

load_dotenv()

# Socket server conifg
HOST = getenv("HOST", "127.0.0.1")
PORT = int(getenv("PORT", "4375"))
API_KEY = getenv("API_KEY")