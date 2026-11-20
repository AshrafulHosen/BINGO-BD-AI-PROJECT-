"""
Unit tests for BINGO-BD Game Rules, Line Detection, Terminal Evaluation, and Turn Logic.
"""

import pytest
from core.state import GameState, GameMode, AgentType, GameStatus, DRAW
from core.rules import (
    create_game,
    legal_moves,
    is_legal_move,
    apply_move,
    terminal_result,
    completed_line_count,
    completed_lines_detail,
)


def test_initial_state_rules():
    """Initial game state must have 25 legal moves and 0 completed lines."""
    state = create_game(GameMode.HUMAN_VS_AI, (AgentType.HUMAN, AgentType.EASY), seed=123)
    assert len(legal_moves(state)) == 25
    assert state.called_mask == 0
    assert state.move_history == ()
    assert state.lines_a == 0
    assert state.lines_b == 0
    assert state.status == GameStatus.PLAYING
    assert state.winner is None


def test_calling_valid_number():
    """AC-02: Calling a valid number marks both boards and removes it from legal moves."""
    state = create_game(seed=456)
    num = 17
    assert is_legal_move(state, num)

    next_state = apply_move(state, num)
    assert not is_legal_move(next_state, num)
    assert num not in legal_moves(next_state)
    assert next_state.is_called(num)
    assert len(legal_moves(next_state)) == 24
    assert next_state.move_history == (17,)
    assert next_state.current_player == 1  # Turn alternates


def test_invalid_number_rejected():
    """Ensure duplicate, negative, out-of-range calls are rejected."""
    state = create_game(seed=789)
    with pytest.raises(ValueError):
        apply_move(state, 0)
    with pytest.raises(ValueError):
        apply_move(state, 26)
    with pytest.raises(ValueError):
        apply_move(state, -5)

    # Calling an already-called number raises error
    s1 = apply_move(state, 10)
    with pytest.raises(ValueError):
        apply_move(s1, 10)


def test_row_detection():
    """Complete row 0 on an identity board."""
    board = tuple(range(1, 26))
    mask = 0
    for n in [1, 2, 3, 4, 5]:
        mask |= (1 << (n - 1))
    assert completed_line_count(board, mask) == 1
    assert completed_lines_detail(board, mask) == [0]


def test_column_detection():
    """Complete col 2 on an identity board: 3, 8, 13, 18, 23."""
    board = tuple(range(1, 26))
    mask = 0
    for n in [3, 8, 13, 18, 23]:
        mask |= (1 << (n - 1))
    assert completed_line_count(board, mask) == 1
    assert completed_lines_detail(board, mask) == [7]  # 5 rows + col 2


def test_diagonals_detection():
    """Main diagonal: 1, 7, 13, 19, 25; Anti diagonal: 5, 9, 13, 17, 21."""
    board = tuple(range(1, 26))
    # Main diag
    mask_main = sum(1 << (n - 1) for n in [1, 7, 13, 19, 25])
    assert completed_line_count(board, mask_main) == 1
    assert 10 in completed_lines_detail(board, mask_main)

    # Anti diag
    mask_anti = sum(1 << (n - 1) for n in [5, 9, 13, 17, 21])
    assert completed_line_count(board, mask_anti) == 1
    assert 11 in completed_lines_detail(board, mask_anti)


def test_overlapping_lines_no_double_counting():
    """A single call completing intersecting row and column counts both distinct lines."""
    board = tuple(range(1, 26))
    # Row 0 (1,2,3,4,5) and Col 0 (1,6,11,16,21) share cell 0 (value 1)
    nums = [2, 3, 4, 5, 6, 11, 16, 21]
    mask = sum(1 << (n - 1) for n in nums)
    assert completed_line_count(board, mask) == 0

    # Now call the shared intersection 1
    mask |= (1 << 0)
    assert completed_line_count(board, mask) == 2


def test_victory_at_five_lines():
    """AC-04: Match ends immediately when a player reaches 5 distinct lines."""
    board_a = tuple(range(1, 26))
    from core.board import generate_board
    board_b = generate_board(seed=10)

    # 4 rows called on board A: numbers 1..20
    state = GameState(
        board_a=board_a,
        board_b=board_b,
        called_mask=sum(1 << (n - 1) for n in range(1, 21)),
        current_player=0,
        mode=GameMode.HUMAN_VS_AI,
        agents=(AgentType.HUMAN, AgentType.EASY),
        status=GameStatus.PLAYING,
        winner=None,
        move_history=tuple(range(1, 21)),
    )
    assert state.lines_a == 4
    assert state.lines_b < 5
    assert state.status == GameStatus.PLAYING

    # Calling 21 completes lines on board_a >= 5, while board_b < 5
    s_win = apply_move(state, 21)
    assert s_win.lines_a >= 5
    assert s_win.lines_b < 5
    assert s_win.status == GameStatus.FINISHED
    assert s_win.winner == 0


def test_simultaneous_five_line_draw():
    """AC-05: When both players reach five lines after the same call, result is Draw."""
    # Symmetrical boards
    board_a = tuple(range(1, 26))
    board_b = tuple(range(1, 26))
    # 4 rows called (1..20)
    s = GameState(
        board_a=board_a,
        board_b=board_b,
        called_mask=sum(1 << (n - 1) for n in range(1, 21)),
        current_player=0,
        mode=GameMode.HUMAN_VS_AI,
        agents=(AgentType.HUMAN, AgentType.EASY),
        status=GameStatus.PLAYING,
        winner=None,
        move_history=tuple(range(1, 21)),
    )
    assert s.lines_a == 4
    assert s.lines_b == 4

    # Calling 21 completes lines on both boards simultaneously
    s_final = apply_move(s, 21)
    assert s_final.lines_a >= 5
    assert s_final.lines_b >= 5
    assert s_final.status == GameStatus.FINISHED
    assert s_final.winner == DRAW
