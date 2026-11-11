# Poker bot starter

A minimal, standalone FastAPI bot for the platform's `poker-bot.v2` protocol.
No platform installation needed. Python 3.10+.

For networking, verification, poker state, action rules, and debugging with a coding agent, see
the [bot-building FAQ](faq.md).

## Run

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env to set BOT_TOKEN.
uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

Check `http://localhost:8001/v1/health`. Open `http://localhost:8001/docs`
for interactive API documentation, including every request field.
Restart the server after changing `.env`.

## Write your strategy

Edit **`choose_action()` in `bot.py`**. It receives an `ActionRequest` and returns
`(action, amount_to)`. The starter checks when possible, otherwise calls, otherwise folds.
The endpoint copies the current decision identifiers into the response for you.

`models.py` defines `ActionRequest` (input), `ActionResponse` (output), and the
match lifecycle request/response models. Nested action state uses typed dictionaries, which
Pydantic also validates and documents in `/docs`. Access nested fields with
brackets, for example `request.player["hole_cards"]` or `request.table["pot"]`:

| Input | Meaning |
| --- | --- |
| `request.player` | Your seat, stack, street commitment, and private `hole_cards`. |
| `request.table` | Board, pot, side pots, public seats, blinds, and this hand's action history. |
| `request.legal_actions` | Allowed actions, call cost (`amount`), and inclusive raise bounds. |
| `request.match` | Hand number, blind level, players remaining; may be `None`. |
| `request.previous_hand` | Last hand's public showdown, awards, and final stacks; may be `None`. |

Cards look like `"As"` or `"Td"`: rank `2-9TJQKA`, suit `cdhs`. Chip amounts are integers.
Never assume another player's hidden cards are available.

Return `("check", None)`, `("call", None)`, or `("fold", None)` only when listed
in `legal_actions`. To raise, return `("raise", amount_to)` using the supplied bounds.
`amount_to` is your **total commitment this street**: if you already committed 300
and raise to 900, return `("raise", 900)`.

Respond comfortably within one second (the platform times out after three seconds).
`deadline_at` uses the platform's clock. Avoid slow network calls in your strategy.

## Connect to the platform

1. Run the server on the event network. In **My Bots**, register your laptop's numeric
   LAN IP (e.g. `192.168.1.42`) and port `8001`.
2. Copy the generated token into `.env` as `BOT_TOKEN`, then restart the server.
3. Select **Verify Connection**, then join a match with your verified bot.

Use your LAN IP when registering; `localhost` points at the platform machine.
Allow port `8001` through your firewall so the platform can reach your laptop.
Keep `.env` private; it is ignored by Git.

The starter has connection, action, and match lifecycle endpoints.
`/v1/verify` is required because the platform checks your bot's token and challenge
before allowing it to join a match. It needs no separate Pydantic model.

The platform calls these routes (already implemented):

| Route | Purpose | Authentication |
| --- | --- | --- |
| `GET /v1/health` | Return protocol and ready status. | None |
| `POST /v1/verify` | Echo the platform's challenge. | `Authorization: Bearer <BOT_TOKEN>` |
| `POST /v1/action` | Receive game state and return a legal action. | Same bearer token |
| `POST /v1/game/start` | Receive a match start notification. | Same bearer token |
| `POST /v1/game/end` | Receive final results or match cancellation. | Same bearer token |

## Match lifecycle hooks

Customize `on_game_start()` and `on_game_end()` in `bot.py` if your bot needs
per-match setup, results processing, or cleanup. They do nothing by default;
the routes validate requests and return the required acknowledgement automatically:

```json
{"protocol": "poker-bot.v2", "match_id": "m-example", "entrant_id": "e-bot"}
```

Start requests contain `protocol`, `match_id`, `table_id`, `entrant_id`,
`starting_stack`, and `blinds`. End requests contain the same identifiers,
`status` (`completed` or `cancelled`), and `standings`, with each entrant's
`entrant_id`, `position`, and `final_stack`. See `/docs` for the full schemas.

These are notifications from the platform for a whole match, across all hands;
calling them does not command the platform to start or stop a match. Delivery is
best effort. Starts can repeat after platform recovery, and end may arrive without
start or be missed entirely. Keep hooks idempotent, key state by `match_id`,
initialize missing state in `choose_action()` too, and expire abandoned state.
Cancelled matches may have empty or incomplete standings.

## Code organization

| File | Responsibility | Participant edits |
| --- | --- | --- |
| `bot.py` | Strategy and optional lifecycle hooks. | Yes |
| `app.py` | Environment loading and application setup. | Normally leave intact |
| `api.py` | Fixed routes, bearer authentication, and response construction. | Leave intact |
| `models.py` | Platform request and response contracts. | Leave intact |

`app.py` mounts an `APIRouter` from `api.py`. Authentication is shared by all
protected routes, while health stays public. Routers keep protocol plumbing away
from editable bot behavior and group endpoints in `/docs`; they do not enforce
file permissions or prevent participants from modifying Python files.

## Development checks

Install `requirements-dev.txt`, then run `python -m unittest discover -s tests`.

For a complete JSON request example and the authoritative schemas, see the main
platform's [protocol reference](../acm-poker-bot-platform/examples/bots/README.md)
and [schemas](../acm-poker-bot-platform/schemas).
