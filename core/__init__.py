"""
BINGO-BD Core Package
Contains board representation, state dataclasses, rules engine, and game controller.
"""

from core.board import (
    ALL_LINES,
    LINE_MASKS,
    generate_board,
    validate_board,
    build_value_to_index_lut,
    compute_board_marked_mask,
)
from core.state import (
    GameState,
    GameMode,
    AgentType,
    GameStatus,
    DRAW,
)
from core.rules import (
    create_game,
    legal_moves,
    is_legal_move,
    apply_move,
    terminal_result,
    completed_line_count,
    completed_lines_detail,
)

__all__ = [
    "ALL_LINES",
    "LINE_MASKS",
    "generate_board",
    "validate_board",
    "build_value_to_index_lut",
    "compute_board_marked_mask",
    "GameState",
    "GameMode",
    "AgentType",
    "GameStatus",
    "DRAW",
    "create_game",
    "legal_moves",
    "is_legal_move",
    "apply_move",
    "terminal_result",
    "completed_line_count",
    "completed_lines_detail",
]
