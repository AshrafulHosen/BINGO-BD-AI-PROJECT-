"""
BINGO-BD Core Board Module
Handles 5x5 board representation, permutations, line indices, and bitmasks.
Pure Python - NO Pygame imports.
"""

from __future__ import annotations
import random
from typing import Tuple, List

# Precomputed line definitions (indices 0..24 in row-major order)
# 5 rows
ROW_LINES: Tuple[Tuple[int, ...], ...] = tuple(
    tuple(r * 5 + c for c in range(5)) for r in range(5)
)

# 5 columns
COL_LINES: Tuple[Tuple[int, ...], ...] = tuple(
    tuple(r * 5 + c for r in range(5)) for c in range(5)
)

# 2 diagonals
MAIN_DIAG_LINE: Tuple[int, ...] = (0, 6, 12, 18, 24)
ANTI_DIAG_LINE: Tuple[int, ...] = (4, 8, 12, 16, 20)

ALL_LINES: Tuple[Tuple[int, ...], ...] = ROW_LINES + COL_LINES + (MAIN_DIAG_LINE, ANTI_DIAG_LINE)

# 12 line bitmasks (bit i represents cell index i)
LINE_MASKS: Tuple[int, ...] = tuple(
    sum(1 << idx for idx in line) for line in ALL_LINES
)


def generate_board(seed: int | None = None) -> Tuple[int, ...]:
    """
    Generate an independent 5x5 board containing integers 1..25 exactly once.
    Deterministic if seed is provided.
    """
    nums = list(range(1, 26))
    if seed is not None:
        rng = random.Random(seed)
        rng.shuffle(nums)
    else:
        random.shuffle(nums)
    return tuple(nums)


def validate_board(board: Tuple[int, ...]) -> bool:
    """
    Validates that a board has length 25 and contains 1..25 without repetition.
    """
    if not isinstance(board, tuple) and not isinstance(board, list):
        return False
    if len(board) != 25:
        return False
    return set(board) == set(range(1, 26))


def build_value_to_index_lut(board: Tuple[int, ...]) -> Tuple[int, ...]:
    """
    Precomputes lookup table where lut[val] = cell_index (0..24).
    Index 0 is unused (value is 1-based, 1..25).
    """
    lut = [0] * 26
    for idx, val in enumerate(board):
        lut[val] = idx
    return tuple(lut)


def compute_board_marked_mask(board_lut: Tuple[int, ...], called_mask: int) -> int:
    """
    Convert 25-bit called_mask (where bit n-1 is 1 if number n is called)
    into a 25-bit board cell mask (where bit idx is 1 if cell idx on this board is marked).
    """
    marked = 0
    # Check set bits in called_mask
    mask = called_mask
    val = 1
    while mask > 0:
        if mask & 1:
            marked |= (1 << board_lut[val])
        mask >>= 1
        val += 1
    return marked
