"""
Unit tests for BINGO-BD Board generation, validation, and bitmasking.
"""

import pytest
from core.board import (
    generate_board,
    validate_board,
    build_value_to_index_lut,
    compute_board_marked_mask,
    ROW_LINES,
    COL_LINES,
    ALL_LINES,
    LINE_MASKS,
)


def test_board_size_and_elements():
    """AC-01: Each board contains exactly 25 numbers, 1-25 without repetition."""
    board = generate_board()
    assert len(board) == 25
    assert set(board) == set(range(1, 26))
    assert validate_board(board) is True


def test_board_independence():
    """Ensure two generated boards have independent permutations."""
    board_a = generate_board(seed=101)
    board_b = generate_board(seed=202)
    assert board_a != board_b
    assert validate_board(board_a)
    assert validate_board(board_b)


def test_board_seed_reproducibility():
    """Deterministic seed must produce identical boards."""
    b1 = generate_board(seed=42)
    b2 = generate_board(seed=42)
    assert b1 == b2


def test_invalid_board_validation():
    """Verify validation catches corrupted boards."""
    assert validate_board((1, 2, 3)) is False
    assert validate_board(tuple(range(1, 26))[:-1] + (24,)) is False  # duplicate 24


def test_line_definitions_count():
    """There must be exactly 12 winning lines: 5 rows, 5 cols, 2 diagonals."""
    assert len(ROW_LINES) == 5
    assert len(COL_LINES) == 5
    assert len(ALL_LINES) == 12
    assert len(LINE_MASKS) == 12
    for line in ALL_LINES:
        assert len(line) == 5
        assert len(set(line)) == 5
