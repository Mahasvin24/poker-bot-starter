"""Run with: uvicorn app:app --host 0.0.0.0 --port 8001 --reload"""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Header, HTTPException

from models import ActionRequest, ActionResponse, ActionType, Protocol

load_dotenv(Path(__file__).with_name(".env"))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in .env (copy .env.example to get started).")

app = FastAPI(title="Poker Bot Starter")


def authorize(authorization: str | None = Header(default=None)) -> None:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(
        token.encode(), BOT_TOKEN.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid bearer token")


def choose_action(request: ActionRequest) -> tuple[ActionType, int | None]:
    """TODO: Replace this function with your poker strategy.

    Use request.player["hole_cards"], request.table, and request.legal_actions.
    For a raise, return ("raise", amount_to) within the provided raise bounds.
    amount_to is your TOTAL commitment this street, not extra chips to add.
    """
    allowed = {option["action"] for option in request.legal_actions}
    for action in ("check", "call", "fold"):
        if action in allowed:
            return action, None
    # The platform always supplies check or fold among the legal actions.
    raise HTTPException(status_code=422, detail="No check, call, or fold available")


# Do not modify this route; implement your strategy in choose_action() above.
@app.post("/v1/action", dependencies=[Depends(authorize)])
async def action(request: ActionRequest) -> ActionResponse:
    selected, amount_to = choose_action(request)
    return ActionResponse(
        match_id=request.match_id,
        table_id=request.table_id,
        hand_id=request.hand_id,
        decision_id=request.decision_id,
        table_version=request.table_version,
        action=selected,
        amount_to=amount_to,
    )


# Do not modify the routes below. The platform requires these exact responses
# to check that your bot is running and verify its connection.
@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"protocol": "poker-bot.v2", "status": "ready"}


@app.post("/v1/verify", dependencies=[Depends(authorize)])
async def verify(
    protocol: Protocol = Body(), challenge: str = Body()
) -> dict[str, str]:
    """Required by the platform's connection check; echo its challenge unchanged."""
    return {"protocol": protocol, "challenge": challenge}
