"""Edit this module to implement your strategy."""

from fastapi import HTTPException

from models import ActionRequest, ActionType


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
