"""Application setup. Run: uvicorn app:app --host 0.0.0.0 --port 8001 --reload"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from api import create_router

load_dotenv(Path(__file__).with_name(".env"))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in .env (copy .env.example to get started).")

app = FastAPI(title="Poker Bot Starter")
app.include_router(create_router(BOT_TOKEN))
