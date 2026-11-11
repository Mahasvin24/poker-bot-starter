"""Fixed platform protocol routes. Customize bot.py rather than this module."""

import secrets

from fastapi import APIRouter, Body, Depends, Header, HTTPException

import bot
from models import (
    ActionRequest,
    ActionResponse,
    Protocol,
)


def create_router(bot_token: str) -> APIRouter:
    def authorize(authorization: str | None = Header(default=None)) -> None:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(
            token.encode(), bot_token.encode()
        ):
            raise HTTPException(status_code=401, detail="Invalid bearer token")

    router = APIRouter(prefix="/v1")
    authenticated = APIRouter(dependencies=[Depends(authorize)])

    @router.get("/health", tags=["Connection"])
    async def health() -> dict[str, str]:
        return {"protocol": "poker-bot.v2", "status": "ready"}

    @authenticated.post("/verify", tags=["Connection"])
    async def verify(
        protocol: Protocol = Body(), challenge: str = Body()
    ) -> dict[str, str]:
        return {"protocol": protocol, "challenge": challenge}

    @authenticated.post("/action", tags=["Decisions"])
    async def action(request: ActionRequest) -> ActionResponse:
        selected, amount_to = bot.choose_action(request)
        return ActionResponse(
            match_id=request.match_id,
            table_id=request.table_id,
            hand_id=request.hand_id,
            decision_id=request.decision_id,
            table_version=request.table_version,
            action=selected,
            amount_to=amount_to,
        )

    router.include_router(authenticated)
    return router
