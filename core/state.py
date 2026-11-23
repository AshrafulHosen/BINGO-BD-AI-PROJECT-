from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, List, Optional
from core.board import (
    ALL_LINES,
    LINE_MASKS,
    build_value_to_index_lut,
    compute_board_marked_mask,
)

DRAW = -1  # Constant for tie/draw terminal state


class GameMode(str, Enum):
    HUMAN_VS_AI = "HUMAN_VS_AI"
    HUMAN_VS_HUMAN = "HUMAN_VS_HUMAN"
    AI_VS_AI = "AI_VS_AI"


class AgentType(str, Enum):
    HUMAN = "HUMAN"
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class GameStatus(str, Enum):
    PLAYING = "PLAYING"
    FINISHED = "FINISHED"


@dataclass(frozen=True, slots=True)
class GameState:
    """
    Immutable representation of the full game state.
    Safe for multi-threaded access and game-tree rollouts.
    """
    board_a: Tuple[int, ...]
    board_b: Tuple[int, ...]
    called_mask: int
    current_player: int  # 0 or 1
    mode: GameMode
    agents: Tuple[AgentType, AgentType]
    status: GameStatus
    winner: Optional[int]  # 0, 1, DRAW (-1), or None
    move_history: Tuple[int, ...]
    version: int = 0
    # Cached lookup tables for fast line and mask calculations
    _lut_a: Tuple[int, ...] = ()
    _lut_b: Tuple[int, ...] = ()

    def __post_init__(self):
        if not self._lut_a:
            object.__setattr__(self, "_lut_a", build_value_to_index_lut(self.board_a))
        if not self._lut_b:
            object.__setattr__(self, "_lut_b", build_value_to_index_lut(self.board_b))

    def is_called(self, number: int) -> bool:
        """Check if number (1..25) has already been called."""
        if number < 1 or number > 25:
            return False
        return bool((self.called_mask >> (number - 1)) & 1)

    @property
    def called_numbers(self) -> List[int]:
        """Return moves in chronological order."""
        return list(self.move_history)

    @property
    def marked_mask_a(self) -> int:
        """Bitmask of marked cell indices for player 0."""
        return compute_board_marked_mask(self._lut_a, self.called_mask)

    @property
    def marked_mask_b(self) -> int:
        """Bitmask of marked cell indices for player 1."""
        return compute_board_marked_mask(self._lut_b, self.called_mask)

    @property
    def lines_a(self) -> int:
        """Count of distinct completed lines on board A (0..12)."""
        marked = self.marked_mask_a
        return sum(1 for mask in LINE_MASKS if (marked & mask) == mask)

    @property
    def lines_b(self) -> int:
        """Count of distinct completed lines on board B (0..12)."""
        marked = self.marked_mask_b
        return sum(1 for mask in LINE_MASKS if (marked & mask) == mask)

    def completed_line_indices_a(self) -> List[int]:
        """Indices (0..11) of completed lines on board A."""
        marked = self.marked_mask_a
        return [i for i, mask in enumerate(LINE_MASKS) if (marked & mask) == mask]

    def completed_line_indices_b(self) -> List[int]:
        """Indices (0..11) of completed lines on board B."""
        marked = self.marked_mask_b
        return [i for i, mask in enumerate(LINE_MASKS) if (marked & mask) == mask]
