"""
BINGO-BD Core Rules Engine
Pure-function implementation of official BINGO-BD game mechanics.
Implements line detection, terminal condition checks, legal moves, and transitions.
Pure Python - NO Pygame imports.
"""

from __future__ import annotations
import numbers
from typing import List, Tuple, Optional
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


def completed_line_count(board: Tuple[int, ...], called_mask: int) -> int:
    """
    Returns the integer count (0..12) of completed lines on a board
    given the called_mask.
    """
    lut = build_value_to_index_lut(board)
    marked = compute_board_marked_mask(lut, called_mask)
    return sum(1 for mask in LINE_MASKS if (marked & mask) == mask)


def completed_lines_detail(board: Tuple[int, ...], called_mask: int) -> List[int]:
    """
    Returns the list of completed line indices (0..11) on a board.
    Indices: 0..4 = Rows 0..4, 5..9 = Cols 0..4, 10 = Main diag, 11 = Anti diag.
    """
    lut = build_value_to_index_lut(board)
    marked = compute_board_marked_mask(lut, called_mask)
    return [i for i, mask in enumerate(LINE_MASKS) if (marked & mask) == mask]


def legal_moves(state: GameState) -> List[int]:
    """
    Returns an ordered list of uncalled numbers (1..25) that can be legally called.
    If the game is finished, returns empty list.
    """
    if state.status == GameStatus.FINISHED:
        return []
    mask = state.called_mask
    return [n for n in range(1, 26) if not ((mask >> (n - 1)) & 1)]


def is_legal_move(state: GameState, number: int) -> bool:
    """Check if number is an integer 1..25 and has not been called."""
    if state.status != GameStatus.PLAYING:
        return False
    # bool is a subclass of int in Python; reject it explicitly so that
    # apply_move(state, True) can never silently call number 1.
    if isinstance(number, bool) or not isinstance(number, numbers.Integral):
        return False
    number = int(number)
    if number < 1 or number > 25:
        return False
    return not bool((state.called_mask >> (number - 1)) & 1)


def terminal_result(state: GameState) -> Tuple[bool, Optional[int]]:
    """
    Evaluates whether the game is in a terminal state.
    Returns: (is_terminal, winner)
      is_terminal: True if match ended, False otherwise
      winner: 0 (Player 1/Human), 1 (Player 2/AI), DRAW (-1), or None
    """
    lines_a = state.lines_a
    lines_b = state.lines_b

    # Five-line victory rule & simultaneous draw rule
    if lines_a >= 5 and lines_b >= 5:
        return True, DRAW
    if lines_a >= 5:
        return True, 0
    if lines_b >= 5:
        return True, 1

    # Number exhaustion draw rule (all 25 numbers called)
    if len(state.move_history) >= 25:
        return True, DRAW

    return False, None


def apply_move(state: GameState, number: int) -> GameState:
    """
    Validates legal number and returns a NEW GameState with:
    - Number added to called_mask
    - Number appended to move_history
    - Terminal condition verified
    - Next turn updated (if not terminal)
    - Version incremented
    Raises ValueError on illegal call.
    """
    if not is_legal_move(state, number):
        raise ValueError(f"Illegal move: {number!r}. Must be uncalled integer 1..25.")
    number = int(number)

    new_called_mask = state.called_mask | (1 << (number - 1))
    new_move_history = state.move_history + (number,)

    # Determine lines directly from luts
    marked_a = compute_board_marked_mask(state._lut_a, new_called_mask)
    marked_b = compute_board_marked_mask(state._lut_b, new_called_mask)

    lines_a = sum(1 for mask in LINE_MASKS if (marked_a & mask) == mask)
    lines_b = sum(1 for mask in LINE_MASKS if (marked_b & mask) == mask)

    if lines_a >= 5 and lines_b >= 5:
        new_status = GameStatus.FINISHED
        new_winner = DRAW
        next_player = state.current_player
    elif lines_a >= 5:
        new_status = GameStatus.FINISHED
        new_winner = 0
        next_player = state.current_player
    elif lines_b >= 5:
        new_status = GameStatus.FINISHED
        new_winner = 1
        next_player = state.current_player
    elif len(new_move_history) >= 25:
        new_status = GameStatus.FINISHED
        new_winner = DRAW
        next_player = state.current_player
    else:
        new_status = GameStatus.PLAYING
        new_winner = None
        next_player = 1 - state.current_player

    return GameState(
        board_a=state.board_a,
        board_b=state.board_b,
        called_mask=new_called_mask,
        current_player=next_player,
        mode=state.mode,
        agents=state.agents,
        status=new_status,
        winner=new_winner,
        move_history=new_move_history,
        version=state.version + 1,
        _lut_a=state._lut_a,
        _lut_b=state._lut_b,
    )


def create_game(
    mode: GameMode = GameMode.HUMAN_VS_AI,
    agents: Tuple[AgentType, AgentType] = (AgentType.HUMAN, AgentType.EASY),
    seed: Optional[int] = None,
) -> GameState:
    """
    Creates a new initial GameState with two independent 5x5 boards.
    Supports deterministic board generation via seed.
    """
    if seed is not None:
        # Generate independent seeds for board A and board B
        board_a = generate_board(seed=seed)
        board_b = generate_board(seed=seed + 1000003)
    else:
        board_a = generate_board()
        board_b = generate_board()

    return GameState(
        board_a=board_a,
        board_b=board_b,
        called_mask=0,
        current_player=0,
        mode=mode,
        agents=agents,
        status=GameStatus.PLAYING,
        winner=None,
        move_history=(),
        version=0,
    )
