"""Edit this module to implement your strategy and optional match lifecycle hooks."""

from fastapi import HTTPException

from models import ActionRequest, ActionType, GameEndRequest, GameStartRequest


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


def on_game_start(request: GameStartRequest) -> None:
    """Optional: initialize match state, keyed by request.match_id.

    Starts can repeat after a platform restart; preserve existing state.
    Delivery is best effort, so choose_action must also initialize missing state.
    """
    pass


def on_game_end(request: GameEndRequest) -> None:
    """Optional: consume standings and clean up request.match_id's state.

    Tolerate duplicate ends and ends without a start. Cancelled matches may have
    incomplete standings. Expire abandoned state too: end delivery is not guaranteed.
    """
    pass
