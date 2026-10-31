# Poker bot building and debugging FAQ

This is a reference for participants and the coding agents helping them build and debug bots.
Start with the symptom table, then read the relevant questions. This file lives beside your
bot so you and your coding agent can use it without installing the platform. Commands say
which machine they belong on; platform-side checks may require help from the organizer.

These answers describe the platform protocol supported by this starter. The event's actual website URL,
network range, match settings, and competition policies come from the organizer. Example IPs
below are placeholders, not addresses you should copy into your registration.

## Find your symptom

| Symptom | Start here |
| --- | --- |
| Bot will not start, or changes seem ignored | [Starter and local development](#starter-and-local-development) |
| Health works on my laptop, but the platform cannot connect | [Networking](#networking) |
| Verification fails, or the bot returns 401 | [Registration, verification, and tokens](#registration-verification-and-tokens) |
| Verified bot folds, ignores its strategy, or fails during play | [Failures and diagnostics](#failures-and-diagnostics) |
| Unsure how to bet, raise, call, or go all-in | [Actions and chip amounts](#actions-and-chip-amounts) |
| Unsure what cards, history, or opponent information are available | [Understanding game state](#understanding-game-state) |
| Cannot join, leave, or start a match | [Accounts and match lifecycle](#accounts-and-match-lifecycle) |
| Website loads but login/actions fail, or a table stops advancing | [When to ask the organizer](#when-to-ask-the-organizer) |
| Need to hand a failure to an agent or organizer | [A useful debugging report](#what-should-i-give-a-coding-agent-or-organizer) |

## What runs where?

### What is this platform?

It runs play-money no-limit Texas Hold'em matches with humans and bots at the same table.
Each match has one table with two to six seats. The organizer chooses the settings and starts
the match. The platform uses PokerKit to enforce poker rules, deals the cards, decides whose
turn it is, validates actions, settles pots, and records results.

A participant bot chooses an action. It does not deal cards, implement the authoritative game
engine, calculate official payouts, or manage the match clock.

### Does my bot connect to the platform, or does the platform connect to my bot?

**The platform connects to your bot.** Your bot is an HTTP server on your laptop. You register
its numeric LAN IP and port in the website. When your seat must act, the platform backend sends
an authenticated `POST /v1/action` to that address, and your server returns JSON.

```text
Participant's browser -> platform website -> platform API -> PostgreSQL
                                               |
                                               +-> participant's laptop:8001/v1/action
                                                        |
                                                        +-> action JSON in the HTTP response
```

There is no bot WebSocket connection, polling loop, or separate "submit move" call to write.
Opening the website successfully proves browser-to-platform access; it does not prove that the
platform can reach your laptop in the other direction.

### Do I need to run the whole platform to write a bot?

No. The standalone [`poker-bot-starter`](README.md) needs Python 3.10+ and
its own `requirements.txt`. Run it on your laptop and use the organizer's website to register
and join. You do not need PostgreSQL, Docker, Node.js, platform administrator access, or the
platform's deployment secret for that workflow.

The platform repository also includes Python and JavaScript [example bots](../acm-poker-bot-platform/examples/bots/README.md).
Its Python example uses the platform package and Python 3.12+. Do not confuse those installation
instructions with the standalone starter's requirements.

### Which protocol and documentation should an agent use?

Use this FAQ, the local [README](README.md), [app.py](app.py), and [models.py](models.py)
first. The platform references below are optional and point into a sibling platform checkout;
you do not need that checkout to implement your bot. If unavailable, ask the organizer for the
protocol reference or use your bot's local `/docs` to inspect the input and output shapes.

The protocol string is exactly `poker-bot.v2`. Start with the
[building guide](../acm-poker-bot-platform/docs/building-a-bot.md), [complete request/response example](../acm-poker-bot-platform/examples/bots/README.md),
and [JSON Schemas](../acm-poker-bot-platform/schemas/). The schemas are generated from
[`bots/models.py`](../acm-poker-bot-platform/src/poker_bot_platform/bots/models.py), which defines the platform's strict
wire models. Old tournament APIs or `poker-bot.v1` examples are not the current contract.

The standalone starter's `models.py` is convenient for strategy development, but successful
local Pydantic validation alone does not prove the platform will accept a response. The
platform also enforces stricter types, action legality, current identifiers, and deadlines.

## Starter and local development

### What should I edit in the Python starter?

Edit `choose_action()` in `poker-bot-starter/app.py`. It receives an `ActionRequest` and returns
`(action, amount_to)`. The existing endpoint builds the response and copies the decision
identifiers for you. Keep the health, authorization, verification, and action route plumbing
intact while developing your strategy.

Nested input values are dictionaries, not Pydantic objects:

```python
cards = request.player["hole_cards"]
pot = request.table["pot"]
allowed = {option["action"] for option in request.legal_actions}
```

`request.player.hole_cards` will fail in this starter. Conversely, the platform's own Python
example uses platform models; do not blindly transplant its attribute access into the standalone
starter.

### What is the shortest way to start and inspect the standalone bot?

From `poker-bot-starter/`, after creating its virtual environment and installing requirements:

```bash
source .venv/bin/activate
# Copy .env.example to .env if you have not already, then set BOT_TOKEN there.
uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

In another terminal on the same laptop:

```bash
curl --max-time 3 -i http://127.0.0.1:8001/v1/health
```

Expect HTTP 200, JSON content type, and `{"protocol":"poker-bot.v2","status":"ready"}`.
Visit `http://127.0.0.1:8001/docs` for the starter's interactive request documentation. This is
your bot's documentation, separate from the platform API's `/docs` on port 8000.

### Why does startup say `Set BOT_TOKEN in .env`?

The starter refuses to import without a nonempty token. For isolated local testing, any
nonempty test value works. Before platform verification, replace it with the exact token issued
for your registered bot. A placeholder token can pass health and still fail authenticated calls.

The starter loads `.env` beside `app.py`. An already exported `BOT_TOKEN` takes precedence over
the file because `load_dotenv()` does not override existing environment variables by default.
Check the environment without printing the token. Restart after changing it; `--reload` should
not be relied on to reload `.env` edits.

### Why am I getting import errors or `Could not import module "app"`?

Run Uvicorn from the starter directory with the starter's virtual environment active. Install
`requirements.txt` using that environment's Python. For a platform example, use the platform's
environment instead. This workspace contains multiple files named `app.py`; a command run from
the wrong directory can load the wrong application.

### Why do my changes seem to do nothing, or the port is already in use?

Check the running process's working directory, interpreter, port, and startup logs. An old bot
may still be listening on 8001 while you edit a different copy. Stop the process you started,
then restart the intended bot. If you intentionally change the port, update the platform profile
and verify again. Merely changing a Python variable does not change Uvicorn's listening port.

### Can I use another language, libraries, simulations, or a model API?

The protocol supports any language that can serve HTTP and exchange JSON. The platform receives
only the response, not your source code. Libraries and simulations must still finish within the
request budget. Load large assets before serving decisions and put a firm bound on computation;
network calls in the action path can easily miss the deadline.

This technical capability does not establish event policy. Ask the organizer about permitted
external services, AI assistance, collaboration, or compute limits; those rules are not encoded
in the bot protocol.

### Can I keep opponent statistics between decisions?

Yes, in your own bot process or storage. Key state by match/table and use `hand_id` and
`decision_id` to avoid mixing games or counting the same information twice. Process memory is
lost on restart. Do not assume you will receive a dedicated hand-end callback: `previous_hand`
arrives with a later action request, and a bot that is eliminated or never acts again may not
receive one. Keep cached strategy data separate from the identifiers for the current response.

## Networking

### Which IP and port should I register?

Register your laptop's numeric address on the event network, for example `192.168.1.42`, and
the port your bot actually listens on, usually `8001`. Enter an IP, not a URL: omit `http://`,
paths, and the port from the IP field. Ports must be integers from 1024 through 65535.

The organizer configures `POKER_PARTICIPANT_SUBNET` and blocked infrastructure addresses.
The default subnet is `192.168.0.0/16`, but the actual event may use another range. The platform
rejects addresses outside its configured subnet, blocked IPs, loopback, and other disallowed
address classes. A rejected valid-looking LAN IP may require the organizer to check network
configuration.

### Why are `localhost`, `127.0.0.1`, and `0.0.0.0` wrong for registration?

`localhost` and `127.0.0.1` refer to the machine making the request: the platform server would
call itself. `0.0.0.0` is a listening address meaning "all local IPv4 interfaces"; it is not the
address another machine uses to reach you. Bind to `0.0.0.0`, then register your actual LAN IP.

Hostnames, public tunnel URLs, and arbitrary HTTPS URLs are not supported registration inputs.
The gateway constructs plain HTTP URLs using the validated numeric IP, port, and fixed paths.

### How do I find my LAN IP?

Look at the active Wi-Fi adapter's network settings. On Windows, `ipconfig` lists adapter IPv4
addresses; on Linux, `ip -4 addr` does. On macOS, `ipconfig getifaddr en0` often works, but the
Wi-Fi interface name can differ. Choose the address belonging to the event connection, not a
VPN, Docker interface, loopback adapter, or disconnected network.

### Local health succeeds. Why does Verify still fail?

Test the connection in this order:

1. On the bot laptop, call `http://127.0.0.1:8001/v1/health`.
2. On the bot laptop, call `http://YOUR_LAN_IP:8001/v1/health`.
3. From the **platform machine**, call that same LAN URL with a short timeout.
4. Once it is reachable, use **Verify Connection** to test the token and challenge.

Step 1 checks that a process is alive; step 2 helps catch a loopback-only bind; step 3 checks the
actual network path; step 4 checks authentication and protocol behavior. A health result alone
does not validate your action response.

If step 3 fails, check the IP, port, firewall permission for the bot process, Wi-Fi membership,
VPN routing, and router AP/client isolation. Being on the same Wi-Fi name does not guarantee
device-to-device traffic is allowed. The organizer may need to change the network. Avoid solving
this by disabling the platform's endpoint validation.

### Can two participants both use port 8001? Can I run multiple bots?

Different laptops can use the same port because their IPs differ. On one laptop, give independent
bot servers different ports. Each registered profile has its own token; a starter process using
one `BOT_TOKEN` will not authenticate other profiles' tokens automatically. Separate profiles
must not accidentally point to a server expecting the wrong token.

### What about Docker, WSL, a VPN, or a cloud-hosted bot?

The platform must reach the registered address and port directly. Containers need the listening
port published to the laptop, and WSL or virtual machines may need host networking or forwarding
appropriate to that setup. A successful call inside a container does not establish external
reachability. VPNs can change routes or the address you select. Generic cloud/tunnel setups do
not fit the event's LAN allowlist by default; coordinate exceptions with the organizer.

### What happens if my laptop sleeps or changes networks?

The platform cannot reach a sleeping laptop or a stopped bot. Keep the machine awake, powered,
and connected throughout the match. A reconnect can change its DHCP address: update **My Bots**,
keep the existing token, and verify the new endpoint. Reopening the website does not update a
registered bot address automatically.

## Registration, verification, and tokens

### What is the full connection sequence?

1. Sign up as a bot participant and open `/dashboard` → **My Bots**.
2. Create a profile with your bot's name, LAN IP, and port.
3. Save the token shown at creation in your local `BOT_TOKEN` configuration.
4. Start or restart the bot with that token.
5. Select **Verify Connection** in the website.
6. Join the organizer's lobby using its code and your verified profile.
7. Keep the bot server running while the organizer starts and runs the match.

Profiles belong to an account and can be reused in later matches. Registration does not seat
the bot, and verification does not start a match.

### Which of the token, join code, password, and secret key goes in `BOT_TOKEN`?

Only the bearer token issued for that bot profile. The join code identifies a match; your
password signs you into the website; `poker_session` is the browser session cookie;
`POKER_SECRET_KEY` is the organizer's deployment secret for encrypting stored bot tokens.
They are different values with different purposes.

### I lost the token. Can the website show it again?

Tokens are shown once when created or rotated. If you no longer have it, rotate it in **My Bots**,
save the new value, restart your bot, and verify again. Rotation makes the old value unusable.
Do not create a new profile just to change an IP or recover from a normal process restart.

### Which changes require verification again?

Changing the registered IP or port invalidates verification but preserves the token. Rotating
the token invalidates verification and requires updating your local configuration. A name-only
edit does not change the endpoint or token. A bot process restart with the same settings does
not itself erase stored verification, though the bot still needs to be reachable during play.

### What does verification actually check?

The platform sends `POST /v1/verify` with `Authorization: Bearer <token>` and JSON containing
`protocol` and a random `challenge`. Your server must validate the token and echo that challenge
unchanged with `protocol: "poker-bot.v2"`. This proves the endpoint can answer the authenticated
challenge at that moment. It does not prove your strategy will handle all poker states or stay
online. Match start also normally checks bot readiness and health.

### Why does health work while verification returns 401 or 422?

Health is intentionally unauthenticated. A 401 from the starter usually means a missing, wrong,
or stale bearer token. Check whether an exported variable overrides `.env`, whether the bot was
restarted, and whether the profile points at the correct server.

A 422 means FastAPI rejected the request shape. Verification needs a JSON object with the
protocol and challenge, not a raw string, form submission, or action payload. Inspect the bot's
validation error and confirm you kept the starter's route contract intact.

### Does the bot need browser CORS settings or a TLS certificate?

The platform-to-bot connection is server-to-server plain HTTP; browser CORS does not govern it.
Do not add CORS middleware as a fix for platform-to-bot connection failures. Keep the exact
`/v1/health`, `/v1/verify`, and `/v1/action` paths: the gateway does not follow redirects, including
trailing-slash redirects or HTTP-to-HTTPS redirects.

## Actions and chip amounts

### What can my bot return?

An action response is one JSON object with the protocol, all five identifiers copied from the
current request, the selected action, and an optional `amount_to`:

```json
{
  "protocol": "poker-bot.v2",
  "match_id": "copy-from-request",
  "table_id": "copy-from-request",
  "hand_id": "copy-from-request",
  "decision_id": "copy-from-request",
  "table_version": 3,
  "action": "check",
  "amount_to": null
}
```

The strings and version above are illustrative; use the actual request values. Choose from
that request's `legal_actions`. Do not return prose, a JSON code fence, a tuple serialized as a
list, the entire input request, or a framework wrapper such as `{"data": {...}}`.

### Why are valid-looking responses rejected?

The platform rejects extra fields, duplicate JSON keys, an incorrect protocol string, and wrong
types. Versions and chip amounts must be JSON integers: `900`, not `"900"`, `900.0`, or `true`.
Convert numerical-library scalar types to plain Python integers before serialization. Send
JSON with `Content-Type: application/json`, a 2xx status, and no redirect. The complete response
must fit in 4096 bytes, so keep explanations, logs, and strategy statistics out of it.

### What does `amount_to` mean?

For a raise it means **your total commitment on this street after the action**. It is not the
additional chips to put in, not your total for the whole hand, and not the pot size.

If you have committed 300 this street and want to raise to 900, return `("raise", 900)` in the
starter. You add 600 chips. Do not send 600 or add earlier streets' commitments. Use the request's
inclusive `min_amount_to` and `max_amount_to` bounds, rather than recreating raise rules yourself.

### How do I call? Should I send the call amount?

Return `("call", None)`. The legal call's `amount` is the extra cost for strategy evaluation,
not a value to put in response `amount_to`. For `call`, `check`, and `fold`, omit `amount_to` or
send `null`; even `0` is invalid. A legal call can be a short all-in call when your stack is
insufficient to match the full wager.

### How do I bet or go all-in? Why is there no `bet` or `all_in` action?

The action vocabulary is `fold`, `check`, `call`, and `raise`. An opening bet uses `raise` with
the supplied bounds. To shove when raising is legal, use that option's `max_amount_to`. If
only an all-in call is legal, choose `call`. Never invent `bet`, `all_in`, `all-in`, or `reraise`.

If `raise` is missing, you cannot raise on this decision. Poker rules can restrict raising after
a short all-in; "I have chips left" does not prove a raise is legal. Follow `legal_actions`.

### Can I always check or fold?

No: choose an action actually listed in this decision. The platform guarantees at least `check`
or `fold` is available so it can resolve failures safely. Do not assume all four actions always
appear, or that an action valid on the last request is valid now.

### Should I calculate my own decision IDs or increment `table_version`?

No. Echo `match_id`, `table_id`, `hand_id`, `decision_id`, and `table_version` exactly. They bind
the response to one specific decision. A legal action with an old identifier is rejected as
`stale`. Caching a strategy calculation is fine; caching and replaying an old response envelope
is not. The platform derives the acting seat from the request and does not need a response
`seat` field.

## Understanding game state

### What information is available to my strategy?

| Field | Meaning and common trap |
| --- | --- |
| `player` | Your private hole cards, numeric seat, remaining stack, and street commitment. |
| `table.seats` | Public player state, keyed by each object's `seat`; do not assume array index equals seat. |
| `table.community_cards` | The board dealt so far; it can be empty preflop. |
| `table.button_seat` | Dealer button, useful for deriving position among occupied seats. |
| `table.blinds` | Current small blind, big blind, and big-blind ante amount. |
| `table.pot` | All chips committed this hand, including current-street commitments. |
| `table.side_pots` | Pot amounts and eligible seats; do not assume your seat can win every pot. |
| `table.action_history` | Current hand's actions, in sequence, with street and automatic-action flags. |
| `legal_actions` | Current legal choices, call cost, and raise bounds. |
| `match` | Hand number, blind level, players remaining, and optional next-level information. |
| `previous_hand` | Last completed hand's public board, shown cards, awards, and final stacks. |

### Are seats zero-based? Will the array always contain six active players?

Seats are numbered 1 through 6, and occupied seat numbers can have gaps even at initial seating.
Use `player.seat` and each public seat's `seat`, not `seats[player.seat]` or `seat - 1` indexing.
Use the public flags and current state to distinguish folded, all-in, and eliminated players.
Do not assume the same opponents or seat layout across matches.

### How are cards encoded? Do I get opponents' cards or the deck seed?

Cards are two-character strings: rank `2-9TJQKA` followed by suit `cdhs`. `As` is ace of spades;
`Td` is ten of diamonds. Handle zero, three, four, or five board cards as appropriate to the
street. A preflop equity calculation must not expect a complete board.

You receive your own private cards and public information. Other players' hidden or mucked
cards and the private dealing seed are not available. `previous_hand.shown_hands` contains
only publicly shown cards, so its absence is not evidence of a missing payload field. Admin
spectator views also do not reveal everyone's private cards.

### How should I interpret stacks, commitments, pot odds, and side pots?

`stack` is chips still behind; committed chips have already left it. `committed_this_street`
resets for a new betting street; `committed_this_hand` includes earlier streets. Do not add
public commitments to `table.pot` again. Side pots describe eligibility within the committed
chips; do not blindly add them to `pot` as extra money.

For a simple decision without side-pot complications, calling cost `C` into pot `P` gives a
break-even equity estimate of `C / (P + C)`. Side pots, multiple opponents, and future betting
need more care. Use the supplied call amount and raise bounds even if your own calculation
disagrees; capture the state for debugging rather than submitting an out-of-contract action.

### Why is `previous_hand` or `match` null? Why is history incomplete?

`match` is optional context. `previous_hand` is null before a hand has completed and should
always be treated as optional. It describes one preceding hand, not the entire match.
`action_history` describes the current hand, not all historical actions or a separate stream of
every engine event. A bot receives requests only for its own decisions; folded or all-in bots
do not receive an update on every other player's action.

If tracking opponents, process history by hand and sequence to avoid repeatedly counting the
same entries in successive requests. Handle absent optional lists and nullable next-level
fields using the published contract.

### Are blinds fixed? Are human and bot thinking times the same?

The organizer can choose fixed blinds or timed increases. Fixed-blind matches have null
next-level timing/blind fields. A hand captures its blind level when it begins; do not assume a
level timer expiring changes the blinds halfway through that hand.

Bot requests have a 500 ms connection timeout and a total budget of at most 3 seconds, further
limited by the current decision deadline. Human decision time is configurable and defaults to
30 seconds. Changing the human timeout does not give bots more time.

### How should I use `deadline_at`?

It is a timezone-aware timestamp on the platform's clock. Clock skew makes subtracting your
laptop's wall clock unreliable. Start a local monotonic timer when your handler begins, bound
your work, and aim to return comfortably within one second. Network transit, parsing, and
serialization also consume time. Finishing strategy computation at exactly three seconds is
too late; the platform needs the complete response before the deadline.

## Failures and diagnostics

### My bot folded even though my strategy wanted to call. What happened?

Check **My Bots → Diagnostics** and the bot server logs. On a failed or late response the
platform records one automatic action: check if legal, otherwise fold. It does not use your
intended action, retry it indefinitely, or automatically call. The current hand's action
history marks automatic actions with `automatic: true`.

A log saying "selected call" proves only that your code chose it. Check the completed HTTP
response, serialization, latency, identifiers, and acceptance diagnostics as well. Failed bot
requests do not stop the other players' match.

### What do the failure reasons mean?

| Reason | What to inspect |
| --- | --- |
| `connection` | Process not running, wrong IP/port, firewall, network isolation, or connection dropped. |
| `timeout` | Connection exceeded 500 ms, full exchange exceeded its budget, or the decision deadline passed. |
| `http_status` | Bot returned non-2xx; inspect its logs for 401, 404, 422, 500, or a redirect. |
| `content_type` | Response is missing the JSON content type or returns HTML/text. |
| `malformed_json` | Invalid JSON or duplicate keys; inspect actual response bytes. |
| `schema` | Wrong protocol, missing/extra field, wrong type, or amount on a non-raise. |
| `stale` | Wrong echoed decision identifiers; for verification, a challenge mismatch. |
| `illegal_action` | Action absent from this request, or raise outside the inclusive bounds. |
| `oversized` | Response exceeds 4 KiB; the gateway also caps outgoing request bodies at 64 KiB. |

### Why do I stop seeing action requests after several failures?

After three consecutive connection, timeout, or HTTP-status failures, the runtime health-probes
the bot before trying another decision, with a 500 ms health budget. If unhealthy, it skips the
action request and falls back so a crashed bot does not stall everyone. Keep `/v1/health` fast
and operational. A successful action resets the failure streak. Successful health alone does
not prove action handling works.

### Why does the bot return 500, or sometimes stop answering health too?

Read the bot's traceback. Common strategy bugs include dictionary/attribute confusion, assuming
`previous_hand` is non-null, indexing missing cards, returning an unsupported action, or failing
to serialize a library's number type. Reproduce with the same state and temporarily restore
the starter's simple check/call/fold strategy to isolate transport from poker logic.

The starter calls synchronous `choose_action()` inside an async handler. Long CPU work or
blocking network calls there can block that server's event loop, including health requests.
Bound expensive work and preserve a fast legal response; adding `async` to a function name
alone does not make blocking computation concurrent.

### What should I log? Why did Diagnostics reset?

Useful fields include match/table/hand/decision IDs, table version, elapsed milliseconds,
legal actions, selected action, HTTP status, and a sanitized exception traceback. Action
payloads contain private hole cards; keep any full replay fixtures private during live play.
Never log Authorization headers, tokens, passwords, session cookies, or `.env` contents.

Bot diagnostics and failure counters are in platform process memory and reset when its API
restarts. They are not a permanent event log. Save the relevant sanitized evidence while
investigating; a reset counter does not mean past failures did not occur.

### How can I test without waiting for an actual match?

First run local and remote health checks. If you have the platform development environment,
use its black-box conformance tool from the platform repository:

```bash
python -m poker_bot_platform.bots.conformance \
  --ip 192.168.1.42 --port 8001 \
  --token '<your-bot-token>' \
  --participant-subnet 192.168.0.0/16
```

Replace the example IP, token, and subnet. Use this in a private terminal; token arguments may
be visible in shell history/process listings. This tool requires the platform package, not
just the standalone starter's requirements. The organizer can run it from the platform machine.

Expect `health`, `verified`, and `action_accepted` to be true. The tool sends a synthetic action
request; it does not join a real match or mark the website profile as verified. It covers one
representative state, not every strategy branch. Also test call/fold decisions, minimum and
maximum raises, short stacks, all-ins, side pots, empty preflop boards, and null optional context.

## Accounts and match lifecycle

### Why can't my human account register or join as a bot?

New accounts choose a participant kind at signup. Human accounts play in the browser; bot
accounts register and join with bots. The backend enforces that choice, so changing a dropdown
or manually sending an API request does not switch the account. Administrator role is separate.
If you chose incorrectly, ask the organizer how to resolve it. Older accounts may have a null
kind for compatibility; do not assume their behavior is the rule for new accounts.

### Why does my join code fail, or why can't I join a paused match?

A match code identifies an open match, but joining is allowed only in its lobby before start.
Codes can be revoked or regenerated by the organizer. A full, started, paused, completed, or
cancelled match is not a joinable lobby. Confirm the current code and match with the organizer.
Joining as a bot also requires a verified profile owned by your signed-in account. Display names
must be unique within the match, ignoring case.

### Can I leave, switch bots, or join twice after the match starts?

Entries can be removed only in the lobby. The same bot profile cannot occupy two seats in one
match; an account cannot hold duplicate human seats. Restarting your existing bot process is
different from replacing the seated profile. Do not delete a seated profile as a recovery step:
the runtime still needs it to contact your bot.

### My bot is verified and seated. Why aren't requests arriving?

The organizer must start the match with at least two entrants. Once running, your bot gets a
request only when its seat has a decision. No requests are expected while paused, after
elimination, while folded/all-in for the rest of a hand, or after completion. Also inspect
Diagnostics for health-breaker behavior and confirm the registered endpoint still matches the
running server. Keeping the browser open is not what drives bot decisions; the backend does.

### Why is play slower with humans? Is the table stuck?

Tables with seated humans include server-side presentation pauses: 3 seconds for dealing,
1.5 seconds after actions, 2.5 seconds for street changes, and 5 seconds at hand end. Human
decision clocks open after presentation pauses. Bot-only tables skip those presentation delays.
Distinguish normal pacing or a pending human decision from a database pause, administrative
pause, or quarantined table before treating the lack of immediate movement as a bug.

### What happens if a human closes the browser?

The backend continues running the match. Expired human decisions also check when possible or
fold. After two timeouts the player is marked Away and subsequent decision budgets shorten to
at most 5 seconds. A successful human action clears that state. Refreshing the page does not
rewind a timed-out turn.

### Do pause, end, and cancel mean the same thing?

Pause normally finishes the current hand before entering the paused state. End finishes the
current hand and records final standings, ranking remaining players by stack. Cancel terminates
the match rather than completing it normally. A pause request still showing active play can be
expected while the current hand finishes. Organizers should use the appropriate console action.

### How are finishes and simultaneous eliminations ranked?

Players with zero chips are eliminated after hand settlement. If multiple players bust in one
hand, the player with the larger start-of-hand stack ranks ahead; equal starting stacks share a
position. When a match ends with survivors, larger final stacks rank ahead and equal stacks tie.
These are implemented standings rules; prizes or event-level scoring remain organizer policy.

### I requested a password reset. Why didn't I receive an email?

The implemented forgot-password flow records a request for an administrator. It does not send
an automated reset email. Contact the organizer, who can issue a temporary password; that reset
revokes existing sessions. Browser sessions normally last 12 hours, so an expired session may
also explain a website 401. Do not replace your bot bearer token with a temporary login password.

## When to ask the organizer

### What can I fix locally, and what needs platform access?

You can fix your strategy, response formatting, process startup, listening address, local token
configuration, and laptop firewall. The organizer controls the event subnet allowlist, router
isolation, website configuration, match settings, account administration, and platform recovery.
If your bot answers correctly from the platform machine but the website still fails, share the
exact error and ask the organizer to inspect the platform side.

You do not need to install or modify the backend to debug a participant bot. Do not change the
protocol or remove authentication to work around an integration error. Keep a simple legal
strategy available to help separate a strategy bug from a connection problem.

### The website loads, but login or other actions fail. Is that my bot?

Your bot does not handle website login or browser actions. The frontend and platform API are
separate services. The platform API requires browser mutations to come from the configured
website origin; a mismatch involving the hostname, port, or HTTP/HTTPS scheme can reject them.
Report the failing browser request's status and error body to the organizer. A website 401 may
mean your browser session expired, while a 401 in your bot's logs concerns its bearer token.
For a 429 response, honor `Retry-After` and stop repeatedly retrying while investigating.

### The demo works. Does that prove my bot is connected?

No. The interactive `/demo` uses built-in bots. It does not exercise your laptop, registered
profile, token, or event-network path. Use your bot's health checks, **Verify Connection**,
Diagnostics, and a real lobby/match to establish that your own bot works.

### The whole table stopped or the platform restarted. Should I restart my bot?

First confirm that your process is reachable and check whether the match is administratively
paused or waiting on a human. The backend can also pause when PostgreSQL is unavailable or stop
a table after an engine invariant failure. Those require organizer investigation, not a change
to your strategy. One unavailable bot normally causes automatic checks/folds while play continues.

The platform restores durable gameplay after a backend restart. An interrupted decision may
receive a recorded `restart_recovery` fallback, and in-memory Diagnostics may reset. Keep your
bot running and preserve sanitized evidence. Restarting your bot cannot rewind a completed turn.

## What should I give a coding agent or organizer?

Share a focused report, for example:

```text
Goal: Connect/debug a participant bot using poker-bot.v2.
Project: standalone poker-bot-starter / platform example / custom server.
Expected behavior:
Observed behavior and exact error/failure reason:
First seen (timestamp and timezone):
OS, Python/Node version, launch command and working directory:
Registered LAN IP/port and actual listening IP/port:
Local health result:
Platform-machine-to-bot health result (if available):
Verification result and Diagnostics reason:
Match/table/hand/decision IDs and table_version (if relevant):
Elapsed action time, HTTP status, sanitized traceback:
Recent changes (strategy, IP, port, token rotation, restart, network):
Minimal private replay fixture / reproduction steps:
```

Omit tokens, passwords, session cookies, deployment secrets, and `.env` contents. Redact private
cards before posting publicly; use a private fixture when those cards are necessary to reproduce
strategy behavior. Tell the agent which machine can run each check: an agent on your laptop
cannot prove connectivity from the platform machine without a remote result.

A useful initial agent instruction is: "Read `faq.md`, the bot README, and the v2 protocol
reference. Identify whether this is startup, reachability, authentication, response validation,
timing, strategy, or platform state. Reproduce the failing layer, preserve the route contract,
and verify with both a legal response and platform-side diagnostics."
