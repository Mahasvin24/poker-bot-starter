"""Standalone input/output shapes for the platform's poker-bot.v2 protocol.

These describe the payloads without requiring the platform package to be installed.
Cards use rank 2-9TJQKA + suit cdhs, e.g. As (ace of spades) or Td (ten of diamonds).
All chip counts are integers. Other players' hidden cards are never included.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ActionType = Literal["fold", "check", "call", "raise"]
Street = Literal["preflop", "flop", "turn", "river", "showdown", "complete"]
Protocol = Literal["poker-bot.v2"]


class VerifyMessage(BaseModel):
    protocol: Protocol
    challenge: str


class LegalAction(BaseModel):
    action: ActionType
    amount: int | None = None  # Call cost: extra chips needed to call.
    min_amount_to: int | None = None  # Inclusive raise bounds (street totals).
    max_amount_to: int | None = None


class Player(BaseModel):
    seat: int
    stack: int
    committed_this_street: int
    hole_cards: list[str]


class PublicSeat(BaseModel):
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


class Blinds(BaseModel):
    small_blind: int
    big_blind: int
    big_blind_ante: int


class SidePot(BaseModel):
    amount: int
    eligible_seats: list[int]


class PublicAction(BaseModel):
    sequence: int
    seat: int
    street: Street
    action: ActionType
    amount_to: int | None = None
    automatic: bool = False


class Table(BaseModel):
    street: Street
    button_seat: int
    blinds: Blinds
    seats: list[PublicSeat]
    pot: int
    community_cards: list[str] = Field(default_factory=list)
    side_pots: list[SidePot] = Field(default_factory=list)
    action_history: list[PublicAction] = Field(default_factory=list)


class MatchContext(BaseModel):
    hand_number: int
    level_number: int
    players_remaining: int
    seconds_until_next_level: int | None = None
    next_small_blind: int | None = None
    next_big_blind: int | None = None


class ShownHand(BaseModel):
    seat: int
    hole_cards: list[str]


class PotAward(BaseModel):
    seat: int
    amount: int


class FinalStack(BaseModel):
    seat: int
    entrant_id: str
    stack: int


class PreviousHand(BaseModel):
    hand_id: str
    hand_number: int
    community_cards: list[str] = Field(default_factory=list)
    shown_hands: list[ShownHand] = Field(default_factory=list)
    awards: list[PotAward] = Field(default_factory=list)
    final_stacks: list[FinalStack] = Field(default_factory=list)


class ActionRequest(BaseModel):
    protocol: Protocol
    # Echo these five fields unchanged in your response.
    match_id: str
    table_id: str
    hand_id: str
    decision_id: str
    table_version: int
    deadline_at: datetime  # Platform server time; aim to reply within one second.
    table: Table
    player: Player
    legal_actions: list[LegalAction]
    match: MatchContext | None = None
    previous_hand: PreviousHand | None = None


class ActionResponse(BaseModel):
    protocol: Protocol = "poker-bot.v2"
    match_id: str
    table_id: str
    hand_id: str
    decision_id: str
    table_version: int
    action: ActionType
    amount_to: int | None = None  # Only raises accept a number; otherwise null.
