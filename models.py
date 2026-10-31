"""
Standalone input/output shapes for the platform's poker-bot.v2 protocol.

These describe the payloads without requiring the platform package to be installed.
Cards use rank 2-9TJQKA + suit cdhs, e.g. As (ace of spades) or Td (ten of diamonds).
All chip counts are integers. Other players' hidden cards are never included.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from typing_extensions import NotRequired, TypedDict

ActionType = Literal["fold", "check", "call", "raise"]
Street = Literal["preflop", "flop", "turn", "river", "showdown", "complete"]
Protocol = Literal["poker-bot.v2"]


class LegalAction(TypedDict):
    """An allowed move. Call amount is extra chips; raise bounds are street totals."""

    action: ActionType
    amount: NotRequired[Annotated[int | None, Field(default=None)]]
    min_amount_to: NotRequired[Annotated[int | None, Field(default=None)]]
    max_amount_to: NotRequired[Annotated[int | None, Field(default=None)]]


class Player(TypedDict):
    """Your private state. Cards use rank 2-9TJQKA and suit cdhs, e.g. As or Td."""

    seat: int
    stack: int
    committed_this_street: int
    hole_cards: list[str]


class PublicSeat(TypedDict):
    """Public player state; stack excludes chips already committed."""

    seat: int
    entrant_id: str
    display_name: str
    kind: Literal["human", "bot"]
    stack: int
    committed_this_street: int
    committed_this_hand: int
    folded: bool
    all_in: bool
    eliminated: bool


class Blinds(TypedDict):
    """Current blind amounts and the ante paid by the big blind."""

    small_blind: int
    big_blind: int
    big_blind_ante: int


class SidePot(TypedDict):
    """A pot and the seats eligible to win it."""

    amount: int
    eligible_seats: list[int]


class PublicAction(TypedDict):
    """A move in this hand; amount_to is the street total for a raise."""

    sequence: int
    seat: int
    street: Street
    action: ActionType
    amount_to: NotRequired[Annotated[int | None, Field(default=None)]]
    automatic: NotRequired[Annotated[bool, Field(default=False)]]


class Table(TypedDict):
    """Public board and betting state. History is ordered by sequence."""

    street: Street
    button_seat: int
    blinds: Blinds
    seats: list[PublicSeat]
    pot: int
    community_cards: NotRequired[Annotated[list[str], Field(default_factory=list)]]
    side_pots: NotRequired[Annotated[list[SidePot], Field(default_factory=list)]]
    action_history: NotRequired[Annotated[list[PublicAction], Field(default_factory=list)]]


class MatchContext(TypedDict):
    """Tournament progress; next-level timing and blinds may be unknown."""

    hand_number: int
    level_number: int
    players_remaining: int
    seconds_until_next_level: NotRequired[Annotated[int | None, Field(default=None)]]
    next_small_blind: NotRequired[Annotated[int | None, Field(default=None)]]
    next_big_blind: NotRequired[Annotated[int | None, Field(default=None)]]


class ShownHand(TypedDict):
    """Cards publicly revealed at showdown; hidden hands are omitted."""

    seat: int
    hole_cards: list[str]


class PotAward(TypedDict):
    """Chips awarded to a seat at the end of a hand."""

    seat: int
    amount: int


class FinalStack(TypedDict):
    """A player’s stack after the previous hand was settled."""

    seat: int
    entrant_id: str
    stack: int


class PreviousHand(TypedDict):
    """Last completed hand at this table, containing only public information."""

    hand_id: str
    hand_number: int
    community_cards: NotRequired[Annotated[list[str], Field(default_factory=list)]]
    shown_hands: NotRequired[Annotated[list[ShownHand], Field(default_factory=list)]]
    awards: NotRequired[Annotated[list[PotAward], Field(default_factory=list)]]
    final_stacks: NotRequired[Annotated[list[FinalStack], Field(default_factory=list)]]


class ActionRequest(BaseModel):
    """Game state sent by the platform whenever your bot must act.

    Nested state uses dictionaries: request.player["hole_cards"],
    request.table["pot"], and request.legal_actions[0]["action"].
    Pydantic validates their declared types, including nested fields.
    All chip counts are integers. Other players' hidden cards are never sent.
    """

    protocol: Protocol = Field(description="Wire protocol version supplied by the platform.")
    match_id: str = Field(description="Match identifier; echo unchanged in the response.")
    table_id: str = Field(description="Table identifier; echo unchanged in the response.")
    hand_id: str = Field(description="Hand identifier; echo unchanged in the response.")
    decision_id: str = Field(description="Decision identifier; echo unchanged in the response.")
    table_version: int = Field(description="State version; echo unchanged in the response.")
    deadline_at: datetime = Field(
        description="Deadline on the platform's clock. Aim to respond within one second."
    )
    table: Table = Field(description="Public board, pot, seats, blinds, and action history.")
    player: Player = Field(description="Your seat, remaining stack, commitment, and hole cards.")
    legal_actions: list[LegalAction] = Field(
        description="Allowed moves with call cost and inclusive raise bounds. Choose one."
    )
    match: MatchContext | None = Field(default=None, description="Tournament progress, if available.")
    previous_hand: PreviousHand | None = Field(
        default=None, description="Previous hand's public showdown and results, if available."
    )


class ActionResponse(BaseModel):
    """Your chosen move, tied to the exact decision supplied by the platform.

    Copy all five identifiers/version fields from the request unchanged.
    Choose an action listed in legal_actions. Only a raise takes amount_to:
    use your TOTAL commitment this street, within the supplied inclusive bounds.
    For example, with 300 already committed, raising to 900 means amount_to=900.
    """

    protocol: Protocol = Field(default="poker-bot.v2", description="Wire protocol version.")
    match_id: str = Field(description="Copy request.match_id.")
    table_id: str = Field(description="Copy request.table_id.")
    hand_id: str = Field(description="Copy request.hand_id.")
    decision_id: str = Field(description="Copy request.decision_id.")
    table_version: int = Field(description="Copy request.table_version.")
    action: ActionType = Field(description="One of the actions supplied in request.legal_actions.")
    amount_to: int | None = Field(
        default=None,
        description="For raises, total chips committed this street; otherwise null.",
    )
